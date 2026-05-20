from sqlalchemy import Column, Integer, DATETIME, String, ForeignKey  # Importe un élément spécifique depuis un module.
from sqlalchemy.orm import relationship  # Importe un élément spécifique depuis un module.
from app.database.base import Base  # Importe un élément spécifique depuis un module.

class donnees_cpu(Base):  # Définit la classe donnees_cpu.
    __tablename__ = "donnees_cpu"  # Affecte une valeur à une variable.

    id_inter = Column(Integer, primary_key=True, autoincrement=True)  # Affecte une valeur à une variable.
    nom = Column(String(50), nullable=False)  # Affecte une valeur à une variable.
    horodatage = Column(DATETIME, nullable=False)  # Affecte une valeur à une variable.
    signalisation = Column(String(1000), nullable=False)  # Affecte une valeur à une variable.

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)  # Affecte une valeur à une variable.
    role = relationship("roles", back_populates="intervention")  # Affecte une valeur à une variable.
