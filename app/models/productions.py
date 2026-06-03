from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import Base

class productions(Base):
    __tablename__ = "productions"

    id_prod = Column(Integer, primary_key=True, autoincrement=True)
    temps_tot = Column(Float, nullable=False)
    nb_caisse_fini = Column(String(50), nullable=False)
    nb_cycle_fini = Column(Integer, nullable=False)

    ## Pour la jointure
    id_commande = Column(Integer, ForeignKey("commandes.id_commande"), nullable=True)
    commandes = relationship("commandes", back_populates="productions")

    ## Pour afficher l'objet Commande
    #def __repr__(self):
    #   return f"<Commande(date_commande={self.date_commande}, montant={self.montant})>"
