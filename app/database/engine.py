import os  # Importe un module ou un package.
from sqlalchemy import create_engine  # Importe un élément spécifique depuis un module.
from sqlalchemy.orm import sessionmaker  # Importe un élément spécifique depuis un module.
from dotenv import load_dotenv  # Importe un élément spécifique depuis un module.

#charger le .env
load_dotenv()  # Effectue une opération de traitement.

DB_USER = os.getenv("DB_USER")  # Affecte une valeur à une variable.
DB_PASSWORD = os.getenv("DB_PASSWORD")  # Affecte une valeur à une variable.
DB_HOST = os.getenv("DB_HOST")  # Affecte une valeur à une variable.
DB_PORT = os.getenv("DB_PORT", "8181")  # Affecte une valeur à une variable.
DB_NAME = os.getenv("DB_NAME")  # Affecte une valeur à une variable.

DATABASE_URL = (  # Affecte une valeur à une variable.
    f"mysql + pymsql://{DB_USER}:{DB_PASSWORD}"  # Effectue une opération de traitement.
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"  # Effectue une opération de traitement.
)  # Effectue une opération de traitement.

engine = create_engine(  # Affecte une valeur à une variable.
    DATABASE_URL,  # Effectue une opération de traitement.
    echo=True,  # Affecte une valeur à une variable.
    future=True  # Affecte une valeur à une variable.
)  # Effectue une opération de traitement.

SessionLocal = sessionmaker(  # Affecte une valeur à une variable.
    bind=engine,   # Affecte une valeur à une variable.
    autocommit=False,   # Affecte une valeur à une variable.
    autoflush=False,  # Affecte une valeur à une variable.
    expire_on_commit=False  # Affecte une valeur à une variable.
)  # Effectue une opération de traitement.
