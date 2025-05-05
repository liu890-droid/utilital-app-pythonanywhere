#!/usr/bin/env python
import click
from flask.cli import with_appcontext
from . import db
from .models import StatusTarefa, Usuario
from werkzeug.security import generate_password_hash

@click.command("seed-db")
@with_appcontext
def seed_db_command():
    """Cria as tabelas do banco de dados e popula com dados iniciais."""
    try:
        # Criar tabelas (se já não existirem via migrate)
        # db.create_all() # O migrate já faz isso

        # Criar status iniciais se não existirem
        status_iniciais = ["Solicitado", "Em Andamento", "Pendente", "Concluído", "Concluído com Atraso", "Cancelado"]
        created_status = False
        for nome_status in status_iniciais:
            if not StatusTarefa.query.filter_by(nome=nome_status).first():
                status = StatusTarefa(nome=nome_status)
                db.session.add(status)
                created_status = True
        if created_status:
            db.session.commit()
            click.echo("Status iniciais criados com sucesso.")
        else:
            click.echo("Status iniciais já existem.")

        # Criar usuário administrador padrão se não existir
        admin_email = "admin@utilital.com"
        if not Usuario.query.filter_by(email=admin_email).first():
            admin_user = Usuario(
                email=admin_email,
                nome="Admin utili&tal",
                senha="senha123", # O setter fará o hash
                nivel_acesso="administrador"
            )
            db.session.add(admin_user)
            db.session.commit()
            click.echo(f"Usuário administrador padrão ")
        else:
            click.echo(f"Usuário administrador padrão ")

    except Exception as e:
        db.session.rollback()
        click.echo(f"Erro ao popular o banco de dados: {e}")

# Adicionar o comando ao app Flask para que possa ser chamado via CLI
# Isso geralmente é feito no arquivo onde o app Flask é criado ou em run.py

def init_app(app):
    app.cli.add_command(seed_db_command)

