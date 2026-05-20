from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Users(Base):
    __tablename__ = "Users"

    id_user = Column(Integer, primary_key=True, autoincrement=True)
    prenom = Column(String(50), nullable=False)
    nom = Column(String(50), nullable=False)
    login = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=True)

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)
    role = relationship("roles", back_populates="users")

    ## Pour afficher l'objet Artiste
    #def __repr__(self):
    #    return f"<Artiste(nom={self.nom}, prenom={self.prenom})>"