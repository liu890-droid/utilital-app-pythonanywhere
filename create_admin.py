from src import db
from src.models import Usuario
from werkzeug.security import generate_password_hash
from run import app

admin = Usuario(
    nome="Administrador",
    email="admin@utilital.com",
    senha_hash=generate_password_hash("123456"),
    nivel_acesso="admin"
)

with app.app_context():
    db.session.add(admin)
    db.session.commit()
    print("Usuário admin criado com sucesso!")