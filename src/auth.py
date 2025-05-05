from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash # Import generate_password_hash
from .models import Usuario
from . import db

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index")) # Redireciona se já estiver logado

    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")
        remember = True if request.form.get("remember") else False

        user = Usuario.query.filter_by(email=email).first()

        if not user or not user.verificar_senha(senha):
            flash("E-mail ou senha inválidos. Por favor, tente novamente.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user, remember=remember)
        flash("Login realizado com sucesso!", "success")
        # Redirecionar para o painel apropriado baseado no nível de acesso?
        # Por enquanto, redireciona para a página inicial.
        return redirect(url_for("main.index"))

    # Se GET, apenas renderiza o template de login
    return render_template("auth/login.html")


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você foi desconectado.", "info")
    return redirect(url_for("auth.login"))

# Rota de Registro (Exemplo - Apenas Admin poderia criar usuários via interface)
# @auth.route("/register", methods=["GET", "POST"])
# def register():
#     if request.method == "POST":
#         email = request.form.get("email")
#         nome = request.form.get("nome")
#         senha = request.form.get("senha")
#         nivel = request.form.get("nivel_acesso", "executor") # Padrão executor

#         user = Usuario.query.filter_by(email=email).first()

#         if user:
#             flash("E-mail já cadastrado.", "warning")
#             return redirect(url_for("auth.register"))

#         new_user = Usuario(
#             email=email,
#             nome=nome,
#             senha=senha, # O setter vai hashear
#             nivel_acesso=nivel
#         )

#         db.session.add(new_user)
#         db.session.commit()

#         flash("Usuário criado com sucesso!", "success")
#         # Idealmente logar o novo usuário ou redirecionar para login/admin
#         return redirect(url_for("auth.login"))

#     # return render_template("auth/register.html")
#     return "Página de Registro (GET request) - Template será criado depois."


