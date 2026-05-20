from sqlalchemy import Column, Integer, String, ForeignKey  # Importe un élément spécifique depuis un module.
from sqlalchemy.orm import relationship  # Importe un élément spécifique depuis un module.
from app.database.base import Base  # Importe un élément spécifique depuis un module.

class recettes(Base):  # Définit la classe recettes.
    __tablename__ = "recettes"  # Affecte une valeur à une variable.

    id_recette = Column(Integer, primary_key=True, autoincrement=True)  # Affecte une valeur à une variable.
    numero = Column(String(50), unique=True, nullable=False)  # Affecte une valeur à une variable.

    ## Pour la jointure
    id_commande = Column(Integer, ForeignKey("commandes.id_commande"), nullable=True)  # Affecte une valeur à une variable.
    commandes = relationship("commandes", back_populates="recettes")  # Affecte une valeur à une variable.
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)  # Affecte une valeur à une variable.
    roles = relationship("roles", back_populates="recettes")  # Affecte une valeur à une variable.

    ## Pour afficher l'objet Commande
    #def __repr__(self):
    #   return f"<Commande(date_commande={self.date_commande}, montant={self.montant})>"
