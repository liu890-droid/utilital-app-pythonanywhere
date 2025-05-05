from flask import Blueprint, render_template
from flask_login import login_required, current_user

# Renomear o blueprint para evitar conflito de nome com o módulo
main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@main_bp.route("/index")
@login_required # Requer que o usuário esteja logado para acessar a página inicial
def index():
    # Futuramente, esta rota renderizará um template com o dashboard
    return render_template("index.html")

# Poderíamos adicionar outras rotas principais aqui, como "sobre" ou "perfil"
@main_bp.route("/profile")
@login_required
def profile():
    # return render_template("profile.html", user=current_user)
    return f"Página de Perfil para {current_user.nome}. (Template será criado depois)"

