from sqlalchemy import Column, Integer, String, ForeignKey  # Importe un élément spécifique depuis un module.
from sqlalchemy.orm import relationship  # Importe un élément spécifique depuis un module.
from app.database.base import Base  # Importe un élément spécifique depuis un module.

class Users(Base):  # Définit la classe Users.
    __tablename__ = "Users"  # Affecte une valeur à une variable.

    id_user = Column(Integer, primary_key=True, autoincrement=True)  # Affecte une valeur à une variable.
    prenom = Column(String(50), nullable=False)  # Affecte une valeur à une variable.
    nom = Column(String(50), nullable=False)  # Affecte une valeur à une variable.
    login = Column(String(50), unique=True, nullable=False)  # Affecte une valeur à une variable.
    password = Column(String(255), nullable=False)  # Affecte une valeur à une variable.
    salt = Column(String(64), nullable=True)  # Affecte une valeur à une variable.

    ## Pour la jointure
    id_role = Column(Integer, ForeignKey("roles.id_role"), nullable=True)  # Affecte une valeur à une variable.
    role = relationship("roles", back_populates="users")  # Affecte une valeur à une variable.

    ## Pour afficher l'objet Artiste
    #def __repr__(self):
    #    return f"<Artiste(nom={self.nom}, prenom={self.prenom})>"
