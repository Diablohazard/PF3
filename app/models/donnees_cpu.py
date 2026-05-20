from sqlalchemy import Column, Integer, String, ForeignKey  # Importe un élément spécifique depuis un module.
from sqlalchemy.orm import relationship  # Importe un élément spécifique depuis un module.
from app.database.base import Base  # Importe un élément spécifique depuis un module.

class donnees_cpu(Base):  # Définit la classe donnees_cpu.
    __tablename__ = "donnees_cpu"  # Affecte une valeur à une variable.

    id_cpu = Column(Integer, primary_key=True, autoincrement=True)  # Affecte une valeur à une variable.
    charge = Column(float, nullable=False)  # Affecte une valeur à une variable.
    ram = Column(float, nullable=False)  # Affecte une valeur à une variable.
    temperature = Column(float, nullable=False)  # Affecte une valeur à une variable.
    alerte = Column(String(50), nullable=True)  # Affecte une valeur à une variable.
    
    # Seuils d'alertes
    seuil_charge = Column(float, nullable=False)  # Affecte une valeur à une variable.
    seuil_ram = Column(float, nullable=False)  # Affecte une valeur à une variable.
    seuil_temperature = Column(float, nullable=False)  # Affecte une valeur à une variable.
    

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)  # Affecte une valeur à une variable.
    role = relationship("roles", back_populates="donnees_cpu")  # Affecte une valeur à une variable.
