from sqlalchemy import Column, Date, ForeignKey, Integer, String, Time
from sqlalchemy.orm import relationship
from app.database.base import Base

class commandes(Base):
    __tablename__ = "commandes"

    id_commande = Column(Integer, primary_key=True, autoincrement=True)
    nb_caisse = Column(Integer, nullable=False)
    type_recette = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    heure_debut = Column(Time, nullable=False)
    heure_fin = Column(Time, nullable=False)

    ## Pour la jointure
    id_prod = Column(Integer, ForeignKey("productions.id_prod"), nullable=True)
    productions = relationship("productions", back_populates="commandes")
    id_recette = Column(Integer, ForeignKey("recettes.id_recette"), nullable=True)
    recettes = relationship("recettes", back_populates="commandes")

    ## Pour afficher l'objet Commande
    #def __repr__(self):
    #   return f"<Commande(date_commande={self.date_commande}, montant={self.montant})>"
