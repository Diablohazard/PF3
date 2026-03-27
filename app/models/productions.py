from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class productions(Base):
    __tablename__ = "productions"

    id_prod = Column(Integer, primary_key=True, autoincrement=True)
    temps_tot = Column(float(100), nullable=False)
    nb_caisse_fini = Column(String(50), nullable=False)
    nb_cycle_fini = Column(Integer, nullable=False)

    ## Pour la jointure
    id_commande = Column(Integer, ForeignKey("commandes.id_commande"), nullable=True)
    commandes = relationship("Commandes", back_populates="productions")

    ## Pour afficher l'objet Commande
    #def __repr__(self):
    #   return f"<Commande(date_commande={self.date_commande}, montant={self.montant})>"