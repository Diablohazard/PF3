from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class donnees_cpu(Base):
    __tablename__ = "donnees_cpu"

    id_cpu = Column(Integer, primary_key=True, autoincrement=True)
    charge = Column(float, nullable=False)
    ram = Column(float, nullable=False)
    temperature = Column(float, nullable=False)
    alerte = Column(String(50), nullable=True)
    
    # Seuils d'alertes
    seuil_charge = Column(float, nullable=False)
    seuil_ram = Column(float, nullable=False)
    seuil_temperature = Column(float, nullable=False)
    

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)
    role = relationship("roles", back_populates="donnees_cpu")