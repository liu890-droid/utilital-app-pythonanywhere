from flask import Blueprint, render_template, jsonify, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from .models import Notificacao
from . import db

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/")
@login_required
def list_notifications():
    """Lista todas as notificações do usuário, não lidas primeiro."""
    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = Notificacao.query.filter_by(usuario_id=current_user.id)\
                                .order_by(Notificacao.lida.asc(), Notificacao.data_criacao.desc())\
                                .paginate(page=page, per_page=per_page, error_out=False)
    notificacoes = pagination.items
    return render_template("notifications/list.html", notificacoes=notificacoes, pagination=pagination)

@notifications_bp.route("/<int:id>/read", methods=["POST"])
@login_required
def mark_as_read(id):
    """Marca uma notificação específica como lida."""
    notificacao = Notificacao.query.get_or_404(id)
    if notificacao.usuario_id != current_user.id:
        abort(403) # Não pode marcar notificação de outro usuário
    if not notificacao.lida:
        notificacao.lida = True
        try:
            db.session.commit()
            # Retornar sucesso ou redirecionar dependendo do contexto (AJAX vs Form)
            # Se for via AJAX, retornar um JSON
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                 return jsonify({"success": True, "message": "Notificação marcada como lida."})
            flash("Notificação marcada como lida.", "success")
        except Exception as e:
            db.session.rollback()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                 return jsonify({"success": False, "message": f"Erro ao marcar como lida: {e}"}), 500
            flash(f"Erro ao marcar notificação como lida: {e}", "danger")

    # Redirecionar de volta para a lista ou para a origem?
    # Por simplicidade, redireciona para a lista de notificações
    return redirect(url_for("notifications.list_notifications"))

@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_as_read():
    """Marca todas as notificações não lidas do usuário como lidas."""
    try:
        updated_count = Notificacao.query.filter_by(usuario_id=current_user.id, lida=False)\
                                     .update({"lida": True})
        db.session.commit()
        if updated_count > 0:
            flash(f"{updated_count} notificações marcadas como lidas.", "success")
        else:
            flash("Nenhuma notificação nova para marcar como lida.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao marcar todas as notificações como lidas: {e}", "danger")

    return redirect(url_for("notifications.list_notifications"))

# Helper para obter contagem de não lidas (pode ser usado no contexto do template)
def get_unread_notification_count(user_id):
    return Notificacao.query.filter_by(usuario_id=user_id, lida=False).count()



@notifications_bp.route("/unread-count")
@login_required
def unread_count():
    """Retorna a contagem de notificações não lidas para o usuário atual (JSON)."""
    count = get_unread_notification_count(current_user.id)
    return jsonify({"count": count})

