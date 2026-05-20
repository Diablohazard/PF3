from sqlalchemy import Column, Integer, String, ForeignKey  # Importe un élément spécifique depuis un module.
from sqlalchemy.orm import relationship  # Importe un élément spécifique depuis un module.
from app.database.base import Base  # Importe un élément spécifique depuis un module.

class commandes(Base):  # Définit la classe commandes.
    __tablename__ = "commandes"  # Affecte une valeur à une variable.

    id_commande = Column(Integer, primary_key=True, autoincrement=True)  # Affecte une valeur à une variable.
    nb_caisse = Column(Integer(100), nullable=False)  # Affecte une valeur à une variable.
    type_recette = Column(String(50), nullable=False)  # Affecte une valeur à une variable.
    date = Column(Date, nullable=False)  # Affecte une valeur à une variable.
    heure_debut = Column(Time, nullable=False)  # Affecte une valeur à une variable.
    heure_fin = Column(Time, nullable=False)  # Affecte une valeur à une variable.

    ## Pour la jointure
    id_prod = Column(Integer, ForeignKey("productions.id_prod"), nullable=True)  # Affecte une valeur à une variable.
    productions = relationship("Productions", back_populates="commandes")  # Affecte une valeur à une variable.
    id_recette = Column(Integer, ForeignKey("recettes.id_recette"), nullable=True)  # Affecte une valeur à une variable.
    recettes = relationship("Recettes", back_populates="commandes")  # Affecte une valeur à une variable.

    ## Pour afficher l'objet Commande
    #def __repr__(self):
    #   return f"<Commande(date_commande={self.date_commande}, montant={self.montant})>"
