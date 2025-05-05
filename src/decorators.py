from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(f):
    """Decorator para rotas que exigem nível de administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.nivel_acesso != "administrador":
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def gestor_required(f):
    """Decorator para rotas que exigem nível de gestor ou administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.nivel_acesso not in ["administrador", "gestor"]:
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

