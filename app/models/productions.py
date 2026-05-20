from sqlalchemy import Column, Integer, String, ForeignKey  # Importe un élément spécifique depuis un module.
from sqlalchemy.orm import relationship  # Importe un élément spécifique depuis un module.
from app.database.base import Base  # Importe un élément spécifique depuis un module.

class productions(Base):  # Définit la classe productions.
    __tablename__ = "productions"  # Affecte une valeur à une variable.

    id_prod = Column(Integer, primary_key=True, autoincrement=True)  # Affecte une valeur à une variable.
    temps_tot = Column(float(100), nullable=False)  # Affecte une valeur à une variable.
    nb_caisse_fini = Column(String(50), nullable=False)  # Affecte une valeur à une variable.
    nb_cycle_fini = Column(Integer, nullable=False)  # Affecte une valeur à une variable.

    ## Pour la jointure
    id_commande = Column(Integer, ForeignKey("commandes.id_commande"), nullable=True)  # Affecte une valeur à une variable.
    commandes = relationship("Commandes", back_populates="productions")  # Affecte une valeur à une variable.

    ## Pour afficher l'objet Commande
    #def __repr__(self):
    #   return f"<Commande(date_commande={self.date_commande}, montant={self.montant})>"
