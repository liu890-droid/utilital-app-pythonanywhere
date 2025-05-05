from flask_mail import Message
from flask import current_app, render_template
from . import mail, db
from .models import Notificacao, Usuario, Tarefa # Adicionar Tarefa
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
            print(f"Email enviado para {msg.recipients}")
        except Exception as e:
            print(f"Erro ao enviar email para {msg.recipients}: {e}")

def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    try:
        msg = Message(app.config["MAIL_SUBJECT_PREFIX"] + subject,
                      sender=app.config["MAIL_DEFAULT_SENDER"],
                      recipients=[to])
        msg.body = render_template(template + ".txt", **kwargs)
        msg.html = render_template(template + ".html", **kwargs)
        thr = Thread(target=send_async_email, args=[app, msg])
        thr.start()
        return thr
    except Exception as e:
        print(f"Erro ao preparar email para {to}: {template} - {e}")
        return None

def criar_notificacao(usuario_id, mensagem, tarefa_id=None, atualizacao_id=None):
    """Cria uma notificação no banco de dados e tenta enviar por email."""
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            print(f"Erro: Usuário {usuario_id} não encontrado para notificação.")
            return

        # Adicionar link/nome da tarefa à mensagem se aplicável
        tarefa_titulo = ""
        if tarefa_id:
            tarefa = Tarefa.query.get(tarefa_id)
            if tarefa:
                tarefa_titulo = tarefa.titulo
                mensagem += f"\"{tarefa_titulo}\"" # Adiciona título à mensagem padrão

        nova_notificacao = Notificacao(
            usuario_id=usuario_id,
            mensagem=mensagem,
            tarefa_id=tarefa_id,
            atualizacao_id=atualizacao_id
        )
        db.session.add(nova_notificacao)
        db.session.commit() # Commit para ter o ID da notificação se necessário
        print(f"Notificação criada no DB para user {usuario_id}: {mensagem}")

        # Tentar enviar email (se configurado e se for um evento relevante para email)
        # Definir quais eventos disparam email (ex: nova tarefa, status concluído, atualização importante?)
        # Por agora, vamos tentar enviar para a maioria dos casos
        # TODO: Adicionar configuração para habilitar/desabilitar emails por tipo de notificação
        if usuario.email:
            # Determinar o template de email com base no tipo de evento (simplificado)
            email_template = "email/notification" # Template genérico
            email_subject = "Nova Notificação - utili&tal Tarefas"
            
            # Poderia ter lógica para escolher template/assunto específico
            if "Nova tarefa" in mensagem:
                 email_template = "email/new_task" # Precisa criar este template
                 email_subject = "Nova Tarefa Atribuída - utili&tal Tarefas"
            elif "status da tarefa" in mensagem:
                 email_template = "email/status_update" # Precisa criar este template
                 email_subject = "Atualização de Status da Tarefa - utili&tal Tarefas"
            elif "Nova atualização" in mensagem:
                 email_template = "email/task_update" # Precisa criar este template
                 email_subject = "Nova Atualização na Tarefa - utili&tal Tarefas"

            send_email(usuario.email, 
                       email_subject, 
                       email_template, 
                       user=usuario, 
                       message=mensagem, 
                       tarefa=tarefa if tarefa_id else None)

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar notificação ou enviar email para user {usuario_id}: {e}")

