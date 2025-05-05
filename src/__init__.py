import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from dotenv import load_dotenv

load_dotenv() # Carrega variáveis de ambiente do .env

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()

def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=False)
    
    # Configurações
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "uma_chave_secreta_muito_segura")
    
    # --- AJUSTE AQUI: Priorizar DATABASE_URL do ambiente/.env ---
    database_url = os.getenv("DATABASE_URL")
    
    # Se DATABASE_URL não estiver no ambiente, tentar variáveis específicas do PythonAnywhere
    if not database_url and "MYSQL_USER" in os.environ and "MYSQL_PASSWORD" in os.environ and "MYSQL_HOST" in os.environ and "MYSQL_DB" in os.environ:
        mysql_user = os.environ["MYSQL_USER"]
        mysql_password = os.environ["MYSQL_PASSWORD"]
        mysql_host = os.environ["MYSQL_HOST"]
        mysql_db = os.environ["MYSQL_DB"]
        database_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"
        print("INFO: Using PythonAnywhere MySQL environment variables.")

    # Se ainda não houver URL, usar SQLite como último recurso (e avisar)
    if not database_url:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "utilital_tasks.db")
        database_url = f"sqlite:///{db_path}"
        print("WARNING: Using SQLite database as fallback. Check environment variables.")
        
    # Garantir que uma URL foi definida
    if not database_url:
        raise ValueError("Database configuration not found. Set DATABASE_URL or PythonAnywhere MySQL variables.")

    print(f"INFO: Connecting to database: {database_url.split('@')[-1]}") # Log para depuração (sem senha)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # --- FIM DO AJUSTE ---
    
    # Configurações de Email (usar variáveis de ambiente)
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.googlemail.com")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "true").lower() in ["true", "on", "1"]
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "your-email@example.com") # Substituir por email real
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "your-password") # Substituir por senha real ou senha de app
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", ("utili&tal Tarefas", os.getenv("MAIL_USERNAME", "noreply@utilital.com")))
    app.config["MAIL_SUBJECT_PREFIX"] = "[utili&tal Tarefas] "

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        # user_id é a chave primária da tabela Usuario
        from .models import Usuario
        return Usuario.query.get(int(user_id))

    with app.app_context():
        # Importar blueprints
        from .auth import auth as auth_bp
        from .main import main_bp # Corrigido aqui
        from .tasks import tasks as tasks_bp
        from .notifications import notifications_bp # Corrigido aqui

        app.register_blueprint(auth_bp, url_prefix="/auth")
        app.register_blueprint(main_bp)
        app.register_blueprint(tasks_bp, url_prefix="/tasks")
        app.register_blueprint(notifications_bp, url_prefix="/notifications")

        # A criação das tabelas e dados iniciais será feita via Flask-Migrate e um script/comando separado

        return app

