# 1. Installer le module : pip install mysql-connector-python
import mysql.connector  # Importe un module ou un package.
from flask import Flask, render_template  # Importe un élément spécifique depuis un module.

app = Flask(__name__)  # Affecte une valeur à une variable.

def enregistrer_intervention(nom, horodatage):  # Définit la fonction enregistrer_intervention.
    # 2. Connexion à la base de données
    conn = mysql.connector.connect(  # Affecte une valeur à une variable.
        host="localhost",      # adapte si besoin
        user="",# adapte avec ton utilisateur MySQL
        password="",    # adapte avec ton mot de passe MySQL
        database="PF3"  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement.
    cursor = conn.cursor()  # Affecte une valeur à une variable.
    # 3. Requête d'insertion
    sql = "INSERT INTO intervention (nom, horodatage) VALUES (%s, %s)"  # Affecte une valeur à une variable.
    cursor.execute(sql, (nom, horodatage))  # Exécute une requête SQL.
    conn.commit()  # Valide la transaction en base de données.
    cursor.close()  # Ferme le curseur SQL.
    conn.close()  # Ferme la connexion à la base de données.
    print("Intervention enregistrée dans la base.")  # Effectue une opération de traitement.

# Exemple d'utilisation :
# enregistrer_intervention("Maintenance préventive", "2024-06-07 10:00:00")

def recuperer_interventions():  # Définit la fonction recuperer_interventions.
    conn = mysql.connector.connect(  # Affecte une valeur à une variable.
        host="localhost",  # Affecte une valeur à une variable.
        user="",  # Affecte une valeur à une variable.
        password="",  # Affecte une valeur à une variable.
        database="PF3"  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.

    cursor.execute("SELECT nom, horodatage FROM intervention ORDER BY horodatage DESC")  # Exécute une requête SQL.
    data = cursor.fetchall()  # Affecte une valeur à une variable.

    cursor.close()  # Ferme le curseur SQL.
    conn.close()  # Ferme la connexion à la base de données.

    return data  # Retourne une valeur depuis la fonction.

@app.route("/")  # Déclare un décorateur ou une route Flask.
def dashboard():  # Définit la fonction dashboard.
    interventions = recuperer_interventions()  # Affecte une valeur à une variable.
    return render_template("dashboard.html", interventions=interventions)  # Retourne une valeur depuis la fonction.

# Importe ta nouvelle fonction en haut du fichier
from app.services.opcua_status import get_opcua_status_details  # Importe un élément spécifique depuis un module.

# ... dans la définition de ta route login :
@app.route('/') # ou '/login'
def login():  # Définit la fonction login.
    # On teste l'automate
    automate_status = get_opcua_status_details()  # Affecte une valeur à une variable.
    
    # On envoie le résultat (True/False) à la page web
    return render_template(  # Retourne une valeur depuis la fonction.
        'login.html',  # Effectue une opération de traitement.
        automate_ok=automate_status['ok'],  # Affecte une valeur à une variable.
        automate_error=automate_status['error'],  # Affecte une valeur à une variable.
        automate_error_code=automate_status['error_code'],  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement.
