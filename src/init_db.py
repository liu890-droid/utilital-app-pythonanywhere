from run import app
from src import db

with app.app_context():
    db.create_all()
    print("Tabelas criadas com sucesso!")