from app.database.engine import engine
from app.database.base import Base

# IMPORTANT : importer les modèles
from app.models.artiste import Artiste
from app.models.instrument import Instrument

def init_db():
    Base.metadata.create_all(bind=engine)