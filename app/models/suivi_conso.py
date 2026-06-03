from sqlalchemy import Column, Float, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship
from app.database.base import Base

class suivi_conso(Base):
    __tablename__ = "suivi_conso"

    id_suivi = Column(Integer, primary_key=True, autoincrement=True)
    courant = Column(Float, nullable=False)
    puissance = Column(Float, nullable=False)
    energie = Column(Numeric(15, 2), nullable=False)

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)
    role = relationship("roles", back_populates="suivi_conso")

    ## Pour afficher l'objet Commande
    #def __repr__(self):
    #   return f"<Commande(date_commande={self.date_commande}, montant={self.montant})>"
