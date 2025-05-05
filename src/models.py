from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    nivel_acesso = db.Column(db.String(20), nullable=False, default="executor")  # administrador, gestor, executor
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    tarefas_solicitadas = db.relationship('Tarefa', foreign_keys='Tarefa.solicitante_id', backref='solicitante', lazy='dynamic')
    tarefas_atribuidas = db.relationship('Tarefa', foreign_keys='Tarefa.executor_id', backref='executor', lazy='dynamic')
    notificacoes = db.relationship('Notificacao', backref='usuario', lazy='dynamic')
    atualizacoes = db.relationship('AtualizacaoTarefa', backref='autor', lazy='dynamic')
    
    @property
    def senha(self):
        raise AttributeError('senha não é um atributo legível')
    
    @senha.setter
    def senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def __repr__(self):
        return f'<Usuario {self.nome}>'

class StatusTarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    
    # Relacionamentos
    tarefas = db.relationship('Tarefa', backref='status', lazy='dynamic')
    
    def __repr__(self):
        return f'<StatusTarefa {self.nome}>'

class TipoTarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    prazo_dias = db.Column(db.Integer, default=1)
    recorrente = db.Column(db.Boolean, default=False)
    
    # Relacionamentos
    tarefas = db.relationship('Tarefa', backref='tipo', lazy='dynamic')
    
    def __repr__(self):
        return f'<TipoTarefa {self.nome}>'

class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_previsao = db.Column(db.DateTime, nullable=False)
    data_conclusao = db.Column(db.DateTime)
    
    # Chaves estrangeiras
    solicitante_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    executor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('status_tarefa.id'), nullable=False)
    tipo_id = db.Column(db.Integer, db.ForeignKey('tipo_tarefa.id'), nullable=False)
    tarefa_origem_id = db.Column(db.Integer, db.ForeignKey('tarefa.id'))
    
    # Relacionamentos
    tarefa_origem = db.relationship('Tarefa', remote_side=[id], backref='tarefas_recorrentes')
    atualizacoes = db.relationship('AtualizacaoTarefa', backref='tarefa', lazy='dynamic', order_by='AtualizacaoTarefa.data_criacao.desc()')
    
    def __repr__(self):
        return f'<Tarefa {self.titulo}>'

class Notificacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mensagem = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    lida = db.Column(db.Boolean, default=False)
    
    # Chaves estrangeiras
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tarefa_id = db.Column(db.Integer, db.ForeignKey('tarefa.id'))
    atualizacao_id = db.Column(db.Integer, db.ForeignKey('atualizacao_tarefa.id'))
    
    # Relacionamentos
    tarefa = db.relationship('Tarefa', backref='notificacoes')
    atualizacao = db.relationship('AtualizacaoTarefa', backref='notificacoes')
    
    def __repr__(self):
        return f'<Notificacao {self.id}>'

# Nova classe para o quadro de atualizações
class AtualizacaoTarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conteudo = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Chaves estrangeiras
    tarefa_id = db.Column(db.Integer, db.ForeignKey('tarefa.id'), nullable=False)
    autor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    def __repr__(self):
        return f'<AtualizacaoTarefa {self.id}>'
