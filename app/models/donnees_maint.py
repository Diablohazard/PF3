from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import Base

class donnees_maint(Base):
    __tablename__ = "donnees_maint"

    id_donnees_maint = Column(Integer, primary_key=True, autoincrement=True)
    temps_cycle = Column(Float, nullable=False)
    defaut = Column(String(5000), nullable=True)

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)
    role = relationship("roles", back_populates="donnees_maint")
