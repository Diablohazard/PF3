from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class donnees_maint(Base):
    __tablename__ = "donnees_maint"

    id_donnees_maint = Column(Integer, primary_key=True, autoincrement=True)
    temps_cycle = Column(float, nullable=False)
    defaut = Column(String(5000), nullable=True)

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)
    donnees_maintenance = relationship("donnees_maint", back_populates="donnees_maint")