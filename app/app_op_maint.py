# 1. Installer le module : pip install mysql-connector-python
import mysql.connector

def enregistrer_intervention(nom, horodatage):
    # 2. Connexion à la base de données
    conn = mysql.connector.connect(
        host="localhost",      # adapte si besoin
        user="",# adapte avec ton utilisateur MySQL
        password="",    # adapte avec ton mot de passe MySQL
        database="PF3"
    )
    cursor = conn.cursor()
    # 3. Requête d'insertion
    sql = "INSERT INTO intervention (nom, horodatage) VALUES (%s, %s)"
    cursor.execute(sql, (nom, horodatage))
    conn.commit()
    cursor.close()
    conn.close()
    print("Intervention enregistrée dans la base.")

# Exemple d'utilisation :
# enregistrer_intervention("Maintenance préventive", "2024-06-07 10:00:00")

def recuperer_interventions():
    conn = mysql.connector.connect(
        host="localhost",
        user="",
        password="",
        database="PF3"
    )
    cursor = conn.cursor(dictionary=True)

    sql = "SELECT nom, horodatage FROM intervention ORDER BY horodatage DESC"
    cursor.execute(sql)

    resultats = cursor.fetchall()

    cursor.close()
    conn.close()

    return resultats