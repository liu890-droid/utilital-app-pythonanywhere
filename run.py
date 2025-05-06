import os
import click
from dotenv import load_dotenv
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src.__init__ import create_app, db
from src import seed # Importar o módulo seed

load_dotenv()

app = create_app()

# Registrar comandos CLI
seed.init_app(app)

# --- Comando Temporário para Criar Tabelas ---
@app.cli.command("create-tables")
def create_tables():
    """Cria todas as tabelas do banco de dados diretamente via SQLAlchemy."""
    try:
        print("INFO: Tentando criar tabelas via db.create_all()...")
        db.create_all()
        print("SUCCESS: db.create_all() executado.")
    except Exception as e:
        print(f"ERROR: Erro durante db.create_all(): {e}")
# --- Fim do Comando Temporário ---

if __name__ == "__main__":
    # Tentar usar a porta 8082 como alternativa
    port = int(os.environ.get("PORT", 8082))
    app.run(host="0.0.0.0", port=port, debug=True)

