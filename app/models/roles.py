from sqlalchemy import Column, Integer, String, ForeignKey  # Importe un élément spécifique depuis un module.
from sqlalchemy.orm import relationship  # Importe un élément spécifique depuis un module.
from app.database.base import Base  # Importe un élément spécifique depuis un module.

class roles(Base):  # Définit la classe roles.
    __tablename__ = "roles"  # Affecte une valeur à une variable.

    id_role = Column(Integer, primary_key=True, autoincrement=True)  # Affecte une valeur à une variable.
    nom = Column(String(50), unique=True, nullable=False)  # Affecte une valeur à une variable.

    ## Pour la jointure
    id_user = Column(Integer, ForeignKey("Users.id_user"), nullable=True)  # Affecte une valeur à une variable.
    user = relationship("Users", back_populates="roles")  # Affecte une valeur à une variable.
    id_cpu = Column(Integer, ForeignKey("donnes_cpu.id_cpu"), nullable=True)  # Affecte une valeur à une variable.
    donnees_cpu = relationship("donnes_cpu", back_populates="roles")  # Affecte une valeur à une variable.
    id_inter = Column(Integer, ForeignKey("intervention.id_inter"), nullable=True)  # Affecte une valeur à une variable.
    intervention = relationship("intervention", back_populates="roles")  # Affecte une valeur à une variable.
    id_suivi = Column(Integer, ForeignKey("suivi_conso.id_suivi"), nullable=True)  # Affecte une valeur à une variable.
    suivi = relationship("suivi_conso", back_populates="roles")  # Affecte une valeur à une variable.
    id_donnees_maint = Column(Integer, ForeignKey("donnees_maint.id_donnees_maint"), nullable=True)  # Affecte une valeur à une variable.
    donnees_maint = relationship("donnees_maint", back_populates="roles")  # Affecte une valeur à une variable.

    ## Pour afficher l'objet Role
    #def __repr__(self):
    #    return f"<Role(nom={self.nom})>"
