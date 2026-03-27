from sqlalchemy import Column, Integer, DATETIME, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class donnees_cpu(Base):
    __tablename__ = "donnees_cpu"

    id_inter = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(50), nullable=False)
    horodatage = Column(DATETIME, nullable=False)
    signalisation = Column(String(1000), nullable=False)

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)
    role = relationship("roles", back_populates="intervention")