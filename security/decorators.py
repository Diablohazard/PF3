from functools import wraps
from flask_login import current_user
from flask import abort

from app.database.engine import SessionLocal
from app.models.users import Users

"""
Lorsqu'un seul role ou plusieurs peuvent avoir accès à la route
usage:
@roles_required("user", "admin")
"""
def roles_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)

            # Recharger depuis la DB
            with SessionLocal() as session:
                user = session.get(Users, current_user.id)
                user_roles = [role.nom for role in user.roles]

            if not any(role in user_roles for role in roles):
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return wrapper