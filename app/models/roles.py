from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class roles(Base):
    __tablename__ = "roles"

    id_role = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(50), unique=True, nullable=False)

    ## Pour la jointure
    id_user = Column(Integer, ForeignKey("Users.id_user"), nullable=True)
    users = relationship("Users", back_populates="role")
    id_cpu = Column(Integer, ForeignKey("donnees_cpu.id_cpu"), nullable=True)
    donnees_cpu = relationship("donnees_cpu", back_populates="role")
    id_inter = Column(Integer, ForeignKey("intervention.id_inter"), nullable=True)
    intervention = relationship("intervention", back_populates="role")
    id_suivi = Column(Integer, ForeignKey("suivi_conso.id_suivi"), nullable=True)
    suivi_conso = relationship("suivi_conso", back_populates="role")
    id_donnees_maint = Column(Integer, ForeignKey("donnees_maint.id_donnees_maint"), nullable=True)
    donnees_maint = relationship("donnees_maint", back_populates="role")
    recettes = relationship("recettes", back_populates="roles")

    ## Pour afficher l'objet Role
    #def __repr__(self):
    #    return f"<Role(nom={self.nom})>"
