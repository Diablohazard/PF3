import os
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify

load_dotenv()

app = Flask(__name__, template_folder="../templates", static_folder="../static")


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost").strip('"'),
        port=int(os.getenv("DB_PORT", "8181").strip('"')),
        user=os.getenv("DB_USER", "root").strip('"'),
        password=os.getenv("DB_PASSWORD", "").strip('"'),
        database=os.getenv("DB_NAME", os.getenv("DB_DATABASE", "PF3")).strip('"')
    )


def enregistrer_intervention(nom, horodatage):
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "INSERT INTO intervention (nom, horodatage) VALUES (%s, %s)"
    cursor.execute(sql, (nom, horodatage))
    conn.commit()
    cursor.close()
    conn.close()


def recuperer_interventions():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT nom, horodatage FROM intervention ORDER BY horodatage DESC")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# On définit les identifiants pour les deux types d'utilisateurs
USERS = {
    "Operat": "Operator",
    "Respo": "Responsable",
    "Integ": "Integrator",
    "Admin": "Administrator"
}

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = request.form.get("username")
        password = request.form.get("password")

        # 1. Vérification si l'utilisateur existe et si le mot de passe est correct
        if user in USERS and USERS[user] == password:
            
            # 2. Redirection selon le rôle (on compare avec les clés du dictionnaire)
            if user == "Respo":
                return redirect(url_for("dashboard_resp"))
            
            elif user == "Integ":
                return redirect(url_for("dashboard_integ"))
            
            elif user == "Operat":
                return redirect(url_for("dashboard_op"))
        
        else:
            error = "Identifiants incorrects"

    return render_template("login.html", error=error)

@app.route("/dashboard")
def dashboard_op():
    interventions = recuperer_interventions()
    return render_template("dashboard.html", interventions=interventions)


@app.route("/planifier_maintenance", methods=["POST"])
def planifier_maintenance():
    date = request.form.get("date_maintenance")
    commentaire = request.form.get("commentaire")
    enregistrer_intervention(commentaire, date)
    return jsonify({"success": True, "date": date, "commentaire": commentaire})

@app.route("/responsable")
def dashboard_resp():
    return render_template("dashboard_SB_respo.html")

@app.route("/integrateur")
def dashboard_integ():
    return render_template("dashboard_SB_integ.html")

# --- TOUJOURS À LA FIN DU FICHIER ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8180, debug=True)