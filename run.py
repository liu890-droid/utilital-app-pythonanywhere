import os
from dotenv import load_dotenv
from src import create_app
from src import seed # Importar o módulo seed

load_dotenv()

app = create_app()

# Registrar comandos CLI
seed.init_app(app)

if __name__ == "__main__":
    # Tentar usar a porta 8082 como alternativa
    port = int(os.environ.get("PORT", 8082))
    app.run(host="0.0.0.0", port=port, debug=True)

