from functools import wraps  # Importe un utilitaire pour préserver les métadonnées des fonctions décorées.
from flask_login import current_user  # Importe l'utilisateur connecté depuis Flask-Login.
from flask import abort  # Importe la fonction d'arrêt HTTP pour renvoyer des codes d'erreur.

from app.database.engine import SessionLocal  # Importe le gestionnaire de session SQLAlchemy.
from app.models.users import Users  # Importe le modèle utilisateur pour les requêtes.

"""
Lorsqu'un seul rôle ou plusieurs peuvent avoir accès à la route.
usage:
@roles_required("user", "admin")
"""

def roles_required(*roles):  # Définit le décorateur roles_required acceptant un ou plusieurs rôles.
    def wrapper(f):  # Crée le wrapper autour de la fonction décorée.
        @wraps(f)  # Préserve le nom et la documentation de la fonction originelle.
        def decorated_function(*args, **kwargs):  # Définit la fonction qui sera exécutée en remplacement.
            if not current_user.is_authenticated:  # Vérifie que l'utilisateur est authentifié.
                abort(401)  # Renvoie un code 401 lorsque l'accès est refusé.

            # Recharger depuis la DB
            with SessionLocal() as session:  # Ouvre une session de base de données.
                user = session.get(Users, current_user.id)  # Récupère l'utilisateur courant en base.
                user_roles = [role.nom for role in user.roles]  # Extrait les noms de rôles associés à l'utilisateur.

            if not any(role in user_roles for role in roles):  # Vérifie la présence d'un rôle autorisé.
                abort(403)  # Renvoie un code 403 si l'utilisateur n'a pas le bon rôle.

            return f(*args, **kwargs)  # Appelle la fonction décorée lorsque l'accès est autorisé.
        return decorated_function  # Retourne la fonction décorée au wrapper.
    return wrapper  # Retourne le décorateur configuré avec les rôles attendus.
