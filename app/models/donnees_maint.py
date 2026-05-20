from sqlalchemy import Column, Integer, String, ForeignKey  # Importe un élément spécifique depuis un module.
from sqlalchemy.orm import relationship  # Importe un élément spécifique depuis un module.
from app.database.base import Base  # Importe un élément spécifique depuis un module.

class donnees_maint(Base):  # Définit la classe donnees_maint.
    __tablename__ = "donnees_maint"  # Affecte une valeur à une variable.

    id_donnees_maint = Column(Integer, primary_key=True, autoincrement=True)  # Affecte une valeur à une variable.
    temps_cycle = Column(float, nullable=False)  # Affecte une valeur à une variable.
    defaut = Column(String(5000), nullable=True)  # Affecte une valeur à une variable.

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)  # Affecte une valeur à une variable.
    donnees_maintenance = relationship("donnees_maint", back_populates="donnees_maint")  # Affecte une valeur à une variable.
