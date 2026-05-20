from sqlalchemy import Column, Integer, String, ForeignKey  # Importe un élément spécifique depuis un module.
from sqlalchemy.orm import relationship  # Importe un élément spécifique depuis un module.
from app.database.base import Base  # Importe un élément spécifique depuis un module.

class suivi_conso(Base):  # Définit la classe suivi_conso.
    __tablename__ = "suivi_conso"  # Affecte une valeur à une variable.

    id_suivi = Column(Integer, primary_key=True, autoincrement=True)  # Affecte une valeur à une variable.
    courant = Column(float(50), nullable=False)  # Affecte une valeur à une variable.
    puissance = Column(float(50), nullable=False)  # Affecte une valeur à une variable.
    energie = Column(Numeric(15, 2), nullable=False)  # Affecte une valeur à une variable.

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)  # Affecte une valeur à une variable.
    role = relationship("roles", back_populates="suivi_conso")  # Affecte une valeur à une variable.

    ## Pour afficher l'objet Commande
    #def __repr__(self):
    #   return f"<Commande(date_commande={self.date_commande}, montant={self.montant})>"
