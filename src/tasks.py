from flask import Blueprint, request, jsonify, abort, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from .models import Tarefa, StatusTarefa, TipoTarefa, Usuario, Notificacao, AtualizacaoTarefa # Adicionar AtualizacaoTarefa
from . import db
from datetime import datetime, timedelta
from .decorators import admin_required, gestor_required
from .notification_utils import criar_notificacao # Importar função de notificação

tasks = Blueprint("tasks", __name__)


@tasks.route("/<int:id>/visualizar", methods=["POST"])
@login_required
def marcar_como_em_andamento(id):
    tarefa = Tarefa.query.get_or_404(id)
    if tarefa.executor_id != current_user.id:
        flash("Você não tem permissão para visualizar esta tarefa.", "danger")
        return redirect(url_for("tasks.view_task", id=id))
    if tarefa.status.nome == "Solicitado":
        status_andamento = StatusTarefa.query.filter_by(nome="Em andamento").first()
        if status_andamento:
            tarefa.status = status_andamento
            db.session.commit()
            flash("Tarefa marcada como 'Em andamento'.", "success")
    return redirect(url_for("tasks.view_task", id=id))


@tasks.route("/<int:id>/concluir", methods=["POST"])
@login_required
def marcar_como_concluida(id):
    tarefa = Tarefa.query.get_or_404(id)
    if tarefa.executor_id != current_user.id:
        flash("Você não pode concluir esta tarefa.", "danger")
        return redirect(url_for("tasks.view_task", id=id))

    hoje = datetime.utcnow().date()
    prazo = tarefa.data_previsao.date()

    if hoje > prazo:
        status = StatusTarefa.query.filter_by(nome="Concluído com Atraso").first()
    else:
        status = StatusTarefa.query.filter_by(nome="Concluído").first()

    if status:
        tarefa.status = status
        db.session.commit()
        flash("Tarefa marcada como concluída.", "success")
    return redirect(url_for("tasks.view_task", id=id))


# --- Rotas para Tarefas ---

@tasks.route("/")
@login_required
def list_tasks():
    """Lista tarefas com filtros e paginação."""
    page = request.args.get("page", 1, type=int)
    per_page = 10
    status_filter = request.args.get("status")

    query = Tarefa.query

    # Filtrar por usuário
    if current_user.nivel_acesso == "executor":
        query = query.filter(Tarefa.executor_id == current_user.id)
    elif current_user.nivel_acesso == "gestor":
        # Gestor vê tarefas que ele solicitou ou que foram atribuídas a ele
        query = query.filter(
            (Tarefa.solicitante_id == current_user.id) | (Tarefa.executor_id == current_user.id)
        )
    # Admin vê todas

    # Filtrar por status
    if status_filter:
        status_obj = StatusTarefa.query.filter_by(nome=status_filter).first()
        if status_obj:
            query = query.filter(Tarefa.status_id == status_obj.id)

    pagination = query.order_by(Tarefa.data_previsao.asc()).paginate(page=page, per_page=per_page, error_out=False)
    tarefas = pagination.items
    all_status = StatusTarefa.query.all()

    return render_template("tasks/list.html", tarefas=tarefas, pagination=pagination, all_status=all_status, current_status_filter=status_filter)

@tasks.route("/new", methods=["GET", "POST"])
@login_required # Permitir que Gestores criem tarefas
def create_task():
    if current_user.nivel_acesso not in ["administrador", "gestor"]:
        flash("Apenas Administradores e Gestores podem criar tarefas.", "danger")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        titulo = request.form.get("titulo")
        descricao = request.form.get("descricao")
        executor_id = request.form.get("executor_id", type=int)
        tipo_id = request.form.get("tipo_id", type=int)
        # Campo data_previsao removido do formulário

        # Validar campos obrigatórios do formulário
        if not all([titulo, executor_id, tipo_id]):
            flash("Todos os campos (Assunto, Solicitado, Tipo) são obrigatórios.", "danger")
            # Recarregar dados para o template em caso de erro
            executores = Usuario.query.all() # Permitir selecionar qualquer nível
            tipos_tarefa = TipoTarefa.query.all()
            return render_template("tasks/create_edit.html", executores=executores, tipos_tarefa=tipos_tarefa, titulo=titulo, descricao=descricao, executor_id=executor_id, tipo_id=tipo_id)
        else:
            try:
                tipo_tarefa = TipoTarefa.query.get(tipo_id)
                executor = Usuario.query.get(executor_id)
                status_solicitado = StatusTarefa.query.filter_by(nome="Solicitado").first()

                if not tipo_tarefa or not executor or not status_solicitado:
                    flash("Dados inválidos (Tipo, Executor ou Status 'Solicitado' não encontrado).", "danger")
                elif tipo_tarefa.prazo_dias is None or tipo_tarefa.prazo_dias <= 0:
                     flash(f"O tipo de tarefa selecionado ('{tipo_tarefa.nome}') não possui um prazo válido definido.", "danger")
                else:
                    # Calcular data_previsao automaticamente
                    data_criacao = datetime.utcnow()
                    # Adicionar 1 segundo para garantir que a previsão seja sempre no futuro, mesmo com prazo 0
                    data_previsao = data_criacao + timedelta(days=tipo_tarefa.prazo_dias, seconds=1) 

                    nova_tarefa = Tarefa(
                        titulo=titulo,
                        descricao=descricao,
                        solicitante_id=current_user.id,
                        executor_id=executor_id,
                        tipo_id=tipo_id,
                        status_id=status_solicitado.id,
                        data_criacao=data_criacao, # Definir data de criação
                        data_previsao=data_previsao # Usar data calculada
                    )
                    db.session.add(nova_tarefa)
                    db.session.commit()
                    flash("Tarefa criada com sucesso!", "success")

                    # Criar notificação para o executor
                    criar_notificacao(
                        usuario_id=executor_id,
                        mensagem=f"Nova tarefa '{nova_tarefa.titulo}' atribuída a você.", # Mensagem mais específica
                        tarefa_id=nova_tarefa.id
                    )

                    return redirect(url_for("tasks.list_tasks"))
            except Exception as e:
                db.session.rollback()
                flash(f"Erro ao criar tarefa: {e}", "danger")
                # Recarregar dados para o template em caso de erro
                executores = Usuario.query.filter(Usuario.nivel_acesso.in_(["executor", "gestor"])).all() # Manter filtro por enquanto
                tipos_tarefa = TipoTarefa.query.all()
                return render_template("tasks/create_edit.html", executores=executores, tipos_tarefa=tipos_tarefa, titulo=titulo, descricao=descricao, executor_id=executor_id, tipo_id=tipo_id)
                flash(f"Erro ao criar tarefa: {e}", "danger")

    # GET Request
    # Permitir selecionar qualquer nível de usuário como executor
    executores = Usuario.query.all()
    tipos_tarefa = TipoTarefa.query.all()
    return render_template("tasks/create_edit.html", executores=executores, tipos_tarefa=tipos_tarefa)

@tasks.route("/<int:id>")
@login_required
def view_task(id):
    tarefa = Tarefa.query.get_or_404(id)
    # Verificar permissão (Admin, Solicitante ou Executor)
    if not (current_user.nivel_acesso == "administrador" or \
            tarefa.solicitante_id == current_user.id or \
            tarefa.executor_id == current_user.id):
        abort(403)
        
    # Buscar atualizações da tarefa
    atualizacoes = tarefa.atualizacoes.order_by(AtualizacaoTarefa.data_criacao.desc()).all()
    
    return render_template("tasks/view.html", task=tarefa, atualizacoes=atualizacoes)

@tasks.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required # Permitir que Gestores editem tarefas que criaram
def edit_task(id):
    tarefa = Tarefa.query.get_or_404(id)
    # Verificar permissão (Admin ou Solicitante)
    if not (current_user.nivel_acesso == "administrador" or tarefa.solicitante_id == current_user.id):
        flash("Você não tem permissão para editar esta tarefa.", "danger")
        return redirect(url_for("tasks.view_task", id=id))

    if request.method == "POST":
        titulo = request.form.get("titulo")
        descricao = request.form.get("descricao")
        executor_id = request.form.get("executor_id", type=int)
        tipo_id = request.form.get("tipo_id", type=int)
        status_id = request.form.get("status_id", type=int) # Permitir edição de status?
        # Campo data_previsao removido do formulário

        # Validar campos obrigatórios do formulário
        if not all([titulo, executor_id, tipo_id, status_id]):
            flash("Todos os campos (Assunto, Solicitado, Tipo, Status) são obrigatórios.", "danger")
            # Recarregar dados para o template em caso de erro
            executores = Usuario.query.filter(Usuario.nivel_acesso.in_(["executor", "gestor"])).all() # Manter filtro por enquanto
            tipos_tarefa = TipoTarefa.query.all()
            status_list = StatusTarefa.query.all()
            return render_template("tasks/create_edit.html", task=tarefa, executores=executores, tipos_tarefa=tipos_tarefa, status_list=status_list)
        else:
            try:
                tipo_tarefa = TipoTarefa.query.get(tipo_id)
                executor = Usuario.query.get(executor_id)
                status = StatusTarefa.query.get(status_id)

                if not tipo_tarefa or not executor or not status:
                    flash("Dados inválidos (Tipo, Executor ou Status não encontrado).", "danger")
                elif tipo_tarefa.prazo_dias is None or tipo_tarefa.prazo_dias <= 0:
                     flash(f"O tipo de tarefa selecionado (\'{tipo_tarefa.nome}\') não possui um prazo válido definido.", "danger")
                else:
                    # Calcular data_previsao automaticamente com base na data de CRIAÇÃO original
                    # Adicionar 1 segundo para garantir que a previsão seja sempre no futuro, mesmo com prazo 0
                    data_previsao = tarefa.data_criacao + timedelta(days=tipo_tarefa.prazo_dias, seconds=1)

                    tarefa.titulo = titulo
                    tarefa.descricao = descricao
                    tarefa.executor_id = executor_id
                    tarefa.tipo_id = tipo_id
                    tarefa.status_id = status_id
                    tarefa.data_previsao = data_previsao # Usar data calculada

                    db.session.commit()
                    flash("Tarefa atualizada com sucesso!", "success")
                    # Criar notificação se o executor mudou?
                    # Criar notificação se o tipo/prazo mudou?
                    return redirect(url_for("tasks.view_task", id=id))
            except Exception as e:
                db.session.rollback()
                flash(f"Erro ao atualizar tarefa: {e}", "danger")
                # Recarregar dados para o template em caso de erro
                executores = Usuario.query.all() # Permitir selecionar qualquer nível
                tipos_tarefa = TipoTarefa.query.all()
                status_list = StatusTarefa.query.all()
                return render_template("tasks/create_edit.html", task=tarefa, executores=executores, tipos_tarefa=tipos_tarefa, status_list=status_list)

    # GET Request
    # Permitir selecionar qualquer nível de usuário como executor
    executores = Usuario.query.all()
    tipos_tarefa = TipoTarefa.query.all()
    status_list = StatusTarefa.query.all()
    return render_template("tasks/create_edit.html", task=tarefa, executores=executores, tipos_tarefa=tipos_tarefa, status_list=status_list)

@tasks.route("/<int:id>/delete", methods=["POST"])
@login_required # Permitir que Gestores excluam tarefas que criaram
def delete_task(id):
    tarefa = Tarefa.query.get_or_404(id)
    # Verificar permissão (Admin ou Solicitante)
    if not (current_user.nivel_acesso == "administrador" or tarefa.solicitante_id == current_user.id):
        flash("Você não tem permissão para excluir esta tarefa.", "danger")
        return redirect(url_for("tasks.list_tasks"))

    try:
        # Excluir notificações e atualizações associadas primeiro
        Notificacao.query.filter_by(tarefa_id=id).delete()
        AtualizacaoTarefa.query.filter_by(tarefa_id=id).delete()
        
        db.session.delete(tarefa)
        db.session.commit()
        flash("Tarefa excluída com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir tarefa: {e}", "danger")

    return redirect(url_for("tasks.list_tasks"))

@tasks.route("/<int:id>/status", methods=["POST"])
@login_required # Executor pode mudar status
def update_task_status(id):
    tarefa = Tarefa.query.get_or_404(id)
    # Verificar permissão (Executor da tarefa ou Admin/Gestor)
    if not (tarefa.executor_id == current_user.id or current_user.nivel_acesso in ["administrador", "gestor"]):
        flash("Você não tem permissão para alterar o status desta tarefa.", "danger")
        return redirect(url_for("tasks.view_task", id=id))

    novo_status_id = request.form.get("status_id", type=int)
    novo_status = StatusTarefa.query.get(novo_status_id)

    if not novo_status:
        flash("Status inválido.", "danger")
    else:
        status_anterior = tarefa.status.nome
        tarefa.status_id = novo_status_id
        
        # Marcar data de conclusão se o status for "Concluído" ou "Concluído com Atraso"
        if novo_status.nome in ["Concluído", "Concluído com Atraso"]:
            tarefa.data_conclusao = datetime.utcnow()
            # Verificar se estava atrasado
            if tarefa.data_conclusao > tarefa.data_previsao and novo_status.nome == "Concluído":
                status_atrasado = StatusTarefa.query.filter_by(nome="Concluído com Atraso").first()
                if status_atrasado:
                    tarefa.status_id = status_atrasado.id
                    novo_status = status_atrasado # Atualiza para notificação
        else:
            tarefa.data_conclusao = None # Limpar data se não for concluído

        try:
            db.session.commit()
            flash(f"Status da tarefa atualizado para ", "success")
            
            # Notificar Solicitante sobre mudança de status
            if tarefa.solicitante_id != current_user.id:
                criar_notificacao(
                    usuario_id=tarefa.solicitante_id,
                    mensagem=f"O status da tarefa ",
                    tarefa_id=tarefa.id
                )
            
            # Lógica de recorrência (após commit)
            if tarefa.tipo.recorrente and novo_status.nome in ["Concluído", "Concluído com Atraso"]:
                try:
                    # Calcular nova data de criação (dia seguinte à previsão original)
                    nova_data_criacao = tarefa.data_previsao + timedelta(days=1)
                    # Calcular nova data de previsão
                    nova_data_previsao = nova_data_criacao + timedelta(days=tarefa.tipo.prazo_dias)
                    
                    nova_tarefa_recorrente = Tarefa(
                        titulo=tarefa.titulo,
                        descricao=tarefa.descricao,
                        solicitante_id=tarefa.solicitante_id,
                        executor_id=tarefa.executor_id,
                        tipo_id=tarefa.tipo_id,
                        status_id=StatusTarefa.query.filter_by(nome="Solicitado").first().id,
                        data_previsao=nova_data_previsao,
                        data_criacao=nova_data_criacao, # Definir data de criação
                        tarefa_origem_id=tarefa.id
                    )
                    db.session.add(nova_tarefa_recorrente)
                    db.session.commit()
                    print(f"Tarefa recorrente {nova_tarefa_recorrente.id} criada a partir da tarefa {tarefa.id}.")
                    # Notificar executor sobre nova tarefa recorrente
                    criar_notificacao(
                        usuario_id=tarefa.executor_id,
                        mensagem=f"Nova tarefa recorrente ",
                        tarefa_id=nova_tarefa_recorrente.id
                    )
                except Exception as e_recor:
                    db.session.rollback()
                    print(f"Erro ao criar tarefa recorrente: {e_recor}")
                    flash(f"Status atualizado, mas erro ao criar tarefa recorrente: {e_recor}", "warning")
                    
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar status: {e}", "danger")

    return redirect(url_for("tasks.view_task", id=id))

# --- Rota para Adicionar Atualização --- (NOVA)
@tasks.route("/<int:id>/add_update", methods=["POST"])
@login_required
def add_task_update(id):
    tarefa = Tarefa.query.get_or_404(id)
    # Verificar permissão (Executor, Solicitante, Gestor, Admin)
    if not (tarefa.executor_id == current_user.id or \
            tarefa.solicitante_id == current_user.id or \
            current_user.nivel_acesso in ["administrador", "gestor"]):
        flash("Você não tem permissão para adicionar atualizações a esta tarefa.", "danger")
        return redirect(url_for("tasks.view_task", id=id))

    conteudo = request.form.get("conteudo_atualizacao")
    if not conteudo:
        flash("O conteúdo da atualização não pode estar vazio.", "warning")
    else:
        try:
            nova_atualizacao = AtualizacaoTarefa(
                conteudo=conteudo,
                tarefa_id=id,
                autor_id=current_user.id
            )
            db.session.add(nova_atualizacao)
            db.session.commit()
            flash("Atualização adicionada com sucesso!", "success")
            
            # Notificar o outro usuário envolvido (se não for o próprio)
            notificar_usuario_id = None
            if tarefa.solicitante_id == current_user.id and tarefa.executor_id != current_user.id:
                notificar_usuario_id = tarefa.executor_id
            elif tarefa.executor_id == current_user.id and tarefa.solicitante_id != current_user.id:
                notificar_usuario_id = tarefa.solicitante_id
            # Adicionar lógica para notificar gestor/admin se necessário?
                
            if notificar_usuario_id:
                 criar_notificacao(
                    usuario_id=notificar_usuario_id,
                    mensagem=f"Nova atualização na tarefa ",
                    tarefa_id=tarefa.id,
                    atualizacao_id=nova_atualizacao.id
                 )
                 
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao adicionar atualização: {e}", "danger")

    return redirect(url_for("tasks.view_task", id=id))


# --- Rotas para Tipos de Tarefa ---

@tasks.route("/types")
@admin_required # Apenas Admin
def list_types():
    # if current_user.nivel_acesso not in ["administrador", "gestor"]:
    #     abort(403)
    tipos = TipoTarefa.query.all()
    return render_template("tasks/list_types.html", tipos=tipos)

@tasks.route("/types/new", methods=["GET", "POST"])
@admin_required # Apenas Admin
def create_type():
    # if current_user.nivel_acesso not in ["administrador", "gestor"]:
    #     abort(403)
        
    if request.method == "POST":
        nome = request.form.get("nome")
        prazo_dias = request.form.get("prazo_dias", type=int)
        recorrente = "recorrente" in request.form

        if not nome or prazo_dias is None or prazo_dias <= 0:
            flash("Nome e Prazo (positivo) são obrigatórios.", "danger")
            return render_template("tasks/create_edit_type.html", nome=nome, prazo_dias=prazo_dias, recorrente=recorrente)

        novo_tipo = TipoTarefa(nome=nome, prazo_dias=prazo_dias, recorrente=recorrente)
        db.session.add(novo_tipo)
        try:
            db.session.commit()
            flash("Tipo de tarefa criado com sucesso!", "success")
            return redirect(url_for("tasks.list_types"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar tipo de tarefa: {e}", "danger")
            return render_template("tasks/create_edit_type.html", nome=nome, prazo_dias=prazo_dias, recorrente=recorrente)

    return render_template("tasks/create_edit_type.html")

# --- Rotas para Gerenciamento de Usuários (Admin) ---
@tasks.route("/users")
@admin_required
def list_users():
    users = Usuario.query.all()
    return render_template("admin/list_users.html", users=users)

@tasks.route("/users/new", methods=["GET", "POST"])
@admin_required
def create_user():
    if request.method == "POST":
        email = request.form.get("email")
        nome = request.form.get("nome")
        senha = request.form.get("senha")
        nivel = request.form.get("nivel_acesso", "executor")

        if not all([email, nome, senha, nivel]) or nivel not in ["administrador", "gestor", "executor"]:
            flash("Todos os campos são obrigatórios e o nível deve ser válido.", "danger")
            return render_template("admin/create_edit_user.html", email=email, nome=nome, nivel_acesso=nivel)

        user = Usuario.query.filter_by(email=email).first()
        if user:
            flash("E-mail já cadastrado.", "warning")
            return render_template("admin/create_edit_user.html", email=email, nome=nome, nivel_acesso=nivel)

        new_user = Usuario(
            email=email,
            nome=nome,
            senha=senha, # Setter faz o hash
            nivel_acesso=nivel
        )
        db.session.add(new_user)
        try:
            db.session.commit()
            flash("Usuário criado com sucesso!", "success")
            return redirect(url_for("tasks.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar usuário: {e}", "danger")
            return render_template("admin/create_edit_user.html", email=email, nome=nome, nivel_acesso=nivel)

    return render_template("admin/create_edit_user.html")

# ROTA EDITADA: Editar Usuário
@tasks.route("/users/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(id):
    user = Usuario.query.get_or_404(id)

    if request.method == "POST":
        email = request.form.get("email")
        nome = request.form.get("nome")
        senha = request.form.get("senha") # Senha é opcional na edição
        nivel = request.form.get("nivel_acesso")

        if not all([email, nome, nivel]) or nivel not in ["administrador", "gestor", "executor"]:
            flash("Campos Nome, E-mail e Nível são obrigatórios e o nível deve ser válido.", "danger")
            return render_template("admin/create_edit_user.html", user=user)

        # Verificar se o email já existe (e não é o próprio usuário)
        existing_user = Usuario.query.filter(Usuario.email == email, Usuario.id != id).first()
        if existing_user:
            flash("Este e-mail já está sendo usado por outro usuário.", "warning")
            return render_template("admin/create_edit_user.html", user=user)

        user.email = email
        user.nome = nome
        user.nivel_acesso = nivel
        if senha: # Atualizar senha apenas se fornecida
            user.senha = senha # Setter faz o hash

        try:
            db.session.commit()
            flash("Usuário atualizado com sucesso!", "success")
            return redirect(url_for("tasks.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar usuário: {e}", "danger")
            return render_template("admin/create_edit_user.html", user=user)

    # GET Request
    return render_template("admin/create_edit_user.html", user=user)

# ROTA EDITADA: Deletar Usuário
@tasks.route("/users/<int:id>/delete", methods=["POST"])
@admin_required
def delete_user(id):
    user = Usuario.query.get_or_404(id)

    if user.id == current_user.id:
        flash("Você não pode excluir sua própria conta.", "danger")
        return redirect(url_for("tasks.list_users"))

    # Opcional: Reatribuir tarefas do usuário excluído? Ou impedir exclusão se tiver tarefas?
    # Simplificado: Apenas exclui o usuário.
    # Relacionamentos (tarefas solicitadas/atribuídas) podem precisar ser tratados (SET NULL? CASCADE?)
    # Verificar configuração do SQLAlchemy nos models.

    try:
        # Excluir notificações e atualizações do usuário
        Notificacao.query.filter_by(usuario_id=id).delete()
        AtualizacaoTarefa.query.filter_by(autor_id=id).delete()
        
        # O que fazer com tarefas onde ele é executor ou solicitante?
        # Opção 1: Impedir exclusão (mais seguro inicialmente)
        if Tarefa.query.filter((Tarefa.executor_id == id) | (Tarefa.solicitante_id == id)).first():
             flash("Não é possível excluir o usuário pois ele possui tarefas associadas (como executor ou solicitante). Reatribua ou exclua as tarefas primeiro.", "danger")
             return redirect(url_for("tasks.list_users"))
             
        # Opção 2: Reatribuir (complexo)
        # Opção 3: Excluir tarefas (perda de dados)
        # Opção 4: Definir como NULL (requer alteração no model)

        db.session.delete(user)
        db.session.commit()
        flash("Usuário excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir usuário: {e}.", "danger")

    return redirect(url_for("tasks.list_users"))




# --- Rota para Editar Tipo de Tarefa (NOVA) ---
@tasks.route("/types/<int:id>/edit", methods=["GET", "POST"])
@admin_required # Apenas Admin pode editar tipos
def edit_type(id):
    tipo = TipoTarefa.query.get_or_404(id)

    if request.method == "POST":
        nome = request.form.get("nome")
        prazo_dias = request.form.get("prazo_dias", type=int)
        recorrente = "recorrente" in request.form

        if not nome or prazo_dias is None or prazo_dias <= 0:
            flash("Nome e Prazo (positivo) são obrigatórios.", "danger")
            # Passar o objeto 'tipo' para o template na falha
            return render_template("tasks/create_edit_type.html", tipo=tipo)

        # Verificar se já existe outro tipo com o mesmo nome
        existing_type = TipoTarefa.query.filter(TipoTarefa.nome == nome, TipoTarefa.id != id).first()
        if existing_type:
            flash("Já existe um tipo de tarefa com este nome.", "warning")
            return render_template("tasks/create_edit_type.html", tipo=tipo)

        tipo.nome = nome
        tipo.prazo_dias = prazo_dias
        tipo.recorrente = recorrente

        try:
            db.session.commit()
            flash("Tipo de tarefa atualizado com sucesso!", "success")
            return redirect(url_for("tasks.list_types"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar tipo de tarefa: {e}", "danger")
            # Passar o objeto 'tipo' para o template na falha
            return render_template("tasks/create_edit_type.html", tipo=tipo)

    # GET Request
    return render_template("tasks/create_edit_type.html", tipo=tipo)

# --- Rota para Excluir Tipo de Tarefa (NOVA) ---
@tasks.route("/types/<int:id>/delete", methods=["POST"])
@admin_required # Apenas Admin pode excluir tipos
def delete_type(id):
    tipo = TipoTarefa.query.get_or_404(id)

    # Verificar se o tipo está sendo usado por alguma tarefa
    if Tarefa.query.filter_by(tipo_id=id).first():
        flash("Não é possível excluir este tipo, pois ele está associado a tarefas existentes.", "danger")
        return redirect(url_for("tasks.list_types"))

    try:
        db.session.delete(tipo)
        db.session.commit()
        flash("Tipo de tarefa excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir tipo de tarefa: {e}", "danger")

    return redirect(url_for("tasks.list_types"))

