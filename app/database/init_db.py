from app.database.engine import engine
from app.database.base import Base

# IMPORTANT : importer les modèles
from app.models.roles import roles
from app.models.users import Users
from app.models.commandes import commandes
from app.models.donnees_cpu import donnees_cpu
from app.models.donnees_maint import donnees_maint
from app.models.productions import productions
from app.models.recettes import recettes
from app.models.intervention import intervention
from app.models.suivi_conso import suivi_conso

def init_db():
    Base.metadata.create_all(bind=engine)
