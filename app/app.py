import os
from datetime import datetime
 
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
 
load_dotenv()
 
app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = "une_cle_secrete_tres_longue"
 
 
 
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost").strip('"'),
        port=int(os.getenv("DB_PORT", "8181").strip('"')),
        user=os.getenv("DB_USER", "root").strip('"'),
        password=os.getenv("DB_PASSWORD", "").strip('"'),
        database=os.getenv("DB_NAME", os.getenv("DB_DATABASE", "PF3")).strip('"')
    )
 
 
def get_intervention_table_name(cursor):
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('Intervention', 'intervention')
        ORDER BY CASE WHEN TABLE_NAME = 'Intervention' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )
    row = cursor.fetchone()
 
    if row:
        return row[0]
 
    return "Intervention"
 
 
def ensure_intervention_table(cursor, table_name):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            id_inter INT AUTO_INCREMENT PRIMARY KEY,
            nom VARCHAR(255) NOT NULL,
            horodatage DATETIME NOT NULL
        )
        """
    )
 
 
def parse_horodatage(date_value):
    return datetime.strptime(date_value, "%Y-%m-%d")
 
 
def enregistrer_intervention(nom, horodatage):
    conn = get_db_connection()
    cursor = conn.cursor()
 
    try:
        table_name = get_intervention_table_name(cursor)
        ensure_intervention_table(cursor, table_name)
        sql = f"INSERT INTO `{table_name}` (nom, horodatage) VALUES (%s, %s)"
        cursor.execute(sql, (nom, horodatage))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
 
 
def recuperer_interventions():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()
 
    try:
        table_name = get_intervention_table_name(table_cursor)
        ensure_intervention_table(table_cursor, table_name)
        cursor.execute(f"SELECT nom, horodatage FROM `{table_name}` ORDER BY horodatage DESC")
        return cursor.fetchall()
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()
 
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
            
            session["logged_in"] = True
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
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    interventions = recuperer_interventions()
    return render_template("dashboard.html", interventions=interventions)
 
 
@app.route("/planifier_maintenance", methods=["POST"])
def planifier_maintenance():
    date = (request.form.get("date_maintenance") or "").strip()
    commentaire = (request.form.get("commentaire") or "").strip()
 
    if not date or not commentaire:
        return jsonify({"success": False, "message": "Date et commentaire obligatoires."}), 400
 
    try:
        horodatage = parse_horodatage(date)
        enregistrer_intervention(commentaire, horodatage)
    except ValueError:
        return jsonify({"success": False, "message": "Format de date invalide."}), 400
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500
 
    return jsonify({"success": True})
 
@app.route("/responsable")
def dashboard_resp():
    return render_template("dashboard_SB_respo.html")
 
@app.route("/integrateur")
def dashboard_integ():
    return render_template("dashboard_SB_integ.html")
 
# Route pour la page d'administration
@app.route("/admin", methods=["GET", "POST"])
def admin():
    return render_template("admin.html")
 
# Route pour créer un nouvel utilisateur (pour l'instant, on enregistre dans un fichier)
@app.route("/create_user", methods=["POST"])
def create_user():
    username = request.form["new_username"]
    password = request.form["new_password"]
 
    # Enregistrement dans le fichier users.txt à la racine du projet
    users_file_path = os.path.join(os.path.dirname(__file__), "../users.txt")
    with open(users_file_path, "a") as f:
        f.write(f"{username}:{password}\n")
 
    return render_template("admin.html", message="Utilisateur créé avec succès !")
 
# --- TOUJOURS À LA FIN DU FICHIER ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8180, debug=True)