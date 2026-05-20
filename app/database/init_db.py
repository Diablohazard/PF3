from app.database.engine import engine  # Importe un élément spécifique depuis un module.
from app.database.base import Base  # Importe un élément spécifique depuis un module.

# IMPORTANT : importer les modèles
from app.models.roles import roles  # Importe un élément spécifique depuis un module.
from app.models.users import Users  # Importe un élément spécifique depuis un module.
from app.models.commandes import commandes  # Importe un élément spécifique depuis un module.
from app.models.donnees_cpu import donnees_cpu  # Importe un élément spécifique depuis un module.
from app.models.donnees_ram import donnees_ram  # Importe un élément spécifique depuis un module.
from app.models.donnees_maint import donnees_maint  # Importe un élément spécifique depuis un module.
from app.models.productions import productions  # Importe un élément spécifique depuis un module.
from app.models.recettes import recettes  # Importe un élément spécifique depuis un module.
from app.models.intervention import intervention  # Importe un élément spécifique depuis un module.
from app.models.productions import productions  # Importe un élément spécifique depuis un module.
from app.models.suivi_conso import suivi_conso  # Importe un élément spécifique depuis un module.

def init_db():  # Définit la fonction init_db.
    Base.metadata.create_all(bind=engine)  # Affecte une valeur à une variable.
