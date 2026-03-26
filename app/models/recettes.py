from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class recettes(Base):
    __tablename__ = "recettes"

    id_recette = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(String(50), unique=True, nullable=False)

    ## Pour la jointure
    id_commande = Column(Integer, ForeignKey("commandes.id_commande"), nullable=True)
    commandes = relationship("commandes", back_populates="recettes")
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)
    roles = relationship("roles", back_populates="recettes")

    ## Pour afficher l'objet Commande
    #def __repr__(self):
    #   return f"<Commande(date_commande={self.date_commande}, montant={self.montant})>"