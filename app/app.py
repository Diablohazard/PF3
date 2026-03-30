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
        cursor.execute(f"SELECT id_inter, nom, horodatage FROM `{table_name}` ORDER BY horodatage ASC")
        return cursor.fetchall()
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def modifier_intervention(id_inter, nom, horodatage):
    conn = get_db_connection()
    cursor = conn.cursor()
    table_cursor = conn.cursor()

    try:
        table_name = get_intervention_table_name(table_cursor)
        ensure_intervention_table(table_cursor, table_name)
        sql = f"UPDATE `{table_name}` SET nom = %s, horodatage = %s WHERE id_inter = %s"
        cursor.execute(sql, (nom, horodatage, id_inter))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def supprimer_intervention(id_inter):
    conn = get_db_connection()
    cursor = conn.cursor()
    table_cursor = conn.cursor()

    try:
        table_name = get_intervention_table_name(table_cursor)
        ensure_intervention_table(table_cursor, table_name)
        sql = f"DELETE FROM `{table_name}` WHERE id_inter = %s"
        cursor.execute(sql, (id_inter,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def can_manage_maintenance():
    return session.get("logged_in") and session.get("role") in ("Respo", "Integ", "Admin")
 
AVAILABLE_ROLES = {
    "Operat": "Opérateur",
    "Respo": "Responsable",
    "Integ": "Intégrateur",
    "Admin": "Administrateur",
}
BOOTSTRAP_ADMIN_LOGIN = "Admin"
BOOTSTRAP_ADMIN_PASSWORD = "administrator"


def get_users_table_name(cursor):
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('Users', 'users')
        ORDER BY CASE WHEN TABLE_NAME = 'Users' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    return row[0] if row else "Users"


def get_roles_table_name(cursor):
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('roles', 'Roles')
        ORDER BY CASE WHEN TABLE_NAME = 'roles' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    return row[0] if row else "roles"


def ensure_roles_table(cursor, table_name):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            id_role INT AUTO_INCREMENT PRIMARY KEY,
            nom VARCHAR(50) UNIQUE NOT NULL
        )
        """
    )


def ensure_users_table(cursor, users_table_name, roles_table_name):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{users_table_name}` (
            id_user INT AUTO_INCREMENT PRIMARY KEY,
            prenom VARCHAR(50) NOT NULL,
            nom VARCHAR(50) NOT NULL,
            login VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(50) NOT NULL,
            id_role INT NULL,
            CONSTRAINT fk_users_role FOREIGN KEY (id_role) REFERENCES `{roles_table_name}` (id_role)
        )
        """
    )


def ensure_user_management_tables(cursor):
    roles_table_name = get_roles_table_name(cursor)
    ensure_roles_table(cursor, roles_table_name)
    users_table_name = get_users_table_name(cursor)
    ensure_users_table(cursor, users_table_name, roles_table_name)
    return users_table_name, roles_table_name


def get_or_create_role_id(cursor, roles_table_name, role_name):
    cursor.execute(f"SELECT id_role FROM `{roles_table_name}` WHERE nom = %s", (role_name,))
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(f"INSERT INTO `{roles_table_name}` (nom) VALUES (%s)", (role_name,))
    return cursor.lastrowid


def fetch_registered_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)
        cursor.execute(
            f"""
            SELECT u.prenom, u.nom, u.login, r.nom AS role
            FROM `{users_table_name}` u
            LEFT JOIN `{roles_table_name}` r ON r.id_role = u.id_role
            ORDER BY u.nom ASC, u.prenom ASC, u.login ASC
            """
        )
        users = cursor.fetchall()
        return [
            {
                "nom": user["nom"],
                "prenom": user["prenom"],
                "identifiant": user["login"],
                "role": user["role"] or "",
                "role_label": AVAILABLE_ROLES.get(user["role"] or "", user["role"] or ""),
            }
            for user in users
        ]
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def get_registered_user_for_auth(login):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)
        cursor.execute(
            f"""
            SELECT u.login, u.password, r.nom AS role
            FROM `{users_table_name}` u
            LEFT JOIN `{roles_table_name}` r ON r.id_role = u.id_role
            WHERE LOWER(u.login) = LOWER(%s)
            LIMIT 1
            """,
            (login,)
        )
        return cursor.fetchone()
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def authenticate_user(username, password):
    if username == BOOTSTRAP_ADMIN_LOGIN and password == BOOTSTRAP_ADMIN_PASSWORD:
        return "Admin"

    account = get_registered_user_for_auth(username)
    if not account:
        return None

    if account["password"] != password:
        return None

    role = account.get("role") or "Operat"
    return role if role in AVAILABLE_ROLES else None


def create_registered_user(nom, prenom, identifiant, password, role):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)
        cursor.execute(
            f"SELECT id_user FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) LIMIT 1",
            (identifiant,)
        )
        if cursor.fetchone() or identifiant.casefold() == BOOTSTRAP_ADMIN_LOGIN.casefold():
            return False, "Cet identifiant existe déjà."

        role_id = get_or_create_role_id(table_cursor, roles_table_name, role)
        cursor.execute(
            f"""
            INSERT INTO `{users_table_name}` (prenom, nom, login, password, id_role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (prenom, nom, identifiant, password, role_id)
        )
        conn.commit()
        return True, "Utilisateur créé avec succès !"
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()
 
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        role = authenticate_user(user, password)
 
        # 1. Vérification avec identifiants hachés
        if role:
            
            session["logged_in"] = True
            session["role"] = role
            # 2. Redirection selon le rôle
            if role == "Respo":
                return redirect(url_for("dashboard_op"))
            
            elif role == "Integ":
                return redirect(url_for("dashboard_op"))
            
            elif role == "Operat":
                return redirect(url_for("dashboard_op"))

            elif role == "Admin":
                return redirect(url_for("dashboard_op"))
        
        else:
            error = "Identifiants incorrects"
 
    return render_template("login.html", error=error)
 
@app.route("/dashboard")
def dashboard_op():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    interventions = recuperer_interventions()
    return render_template(
        "dashboard_operateur.html",
        interventions=interventions,
        role=session.get("role"),
        registered_users=fetch_registered_users(),
        available_roles=AVAILABLE_ROLES,
    )
 
 
@app.route("/planifier_maintenance", methods=["POST"])
def planifier_maintenance():
    if not can_manage_maintenance():
        return jsonify({"success": False, "message": "Accès refusé."}), 403

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


@app.route("/modifier_maintenance", methods=["POST"])
def modifier_maintenance():
    if not can_manage_maintenance():
        return jsonify({"success": False, "message": "Accès refusé."}), 403

    id_inter = (request.form.get("id_inter") or "").strip()
    date = (request.form.get("date_maintenance") or "").strip()
    commentaire = (request.form.get("commentaire") or "").strip()

    if not id_inter or not date or not commentaire:
        return jsonify({"success": False, "message": "ID, date et commentaire obligatoires."}), 400

    try:
        id_inter_int = int(id_inter)
    except ValueError:
        return jsonify({"success": False, "message": "ID intervention invalide."}), 400

    try:
        horodatage = parse_horodatage(date)
        updated = modifier_intervention(id_inter_int, commentaire, horodatage)
        if not updated:
            return jsonify({"success": False, "message": "Intervention introuvable."}), 404
    except ValueError:
        return jsonify({"success": False, "message": "Format de date invalide."}), 400
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    return jsonify({"success": True})


@app.route("/supprimer_maintenance", methods=["POST"])
def supprimer_maintenance():
    if not can_manage_maintenance():
        return jsonify({"success": False, "message": "Accès refusé."}), 403

    id_inter = (request.form.get("id_inter") or "").strip()
    if not id_inter:
        return jsonify({"success": False, "message": "ID intervention obligatoire."}), 400

    try:
        id_inter_int = int(id_inter)
    except ValueError:
        return jsonify({"success": False, "message": "ID intervention invalide."}), 400

    try:
        deleted = supprimer_intervention(id_inter_int)
        if not deleted:
            return jsonify({"success": False, "message": "Intervention introuvable."}), 404
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    return jsonify({"success": True})
 
@app.route("/get_interventions")
def get_interventions_json():
    if not session.get("logged_in"):
        return jsonify({"success": False, "message": "Non authentifié."}), 401
    try:
        interventions = recuperer_interventions()
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500
    result = [
        {
            "id_inter": row["id_inter"],
            "nom": row["nom"],
            "horodatage": row["horodatage"].strftime("%Y-%m-%d") if row["horodatage"] else "",
        }
        for row in interventions
    ]
    return jsonify({"success": True, "interventions": result})


@app.route("/responsable")
def dashboard_resp():
    return render_template("dashboard_SB_respo.html")
 
@app.route("/integrateur")
def dashboard_integ():
    return render_template("dashboard_SB_integ.html")
 
# Route pour la page d'administration
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return redirect(url_for("dashboard_op"))
 
# Route pour créer un nouvel utilisateur
@app.route("/create_user", methods=["POST"])
def create_user():
    if not session.get("logged_in") or session.get("role") != "Admin":
        return jsonify({"success": False, "message": "Accès refusé."}), 403

    nom = (request.form.get("nom") or "").strip()
    prenom = (request.form.get("prenom") or "").strip()
    identifiant = (request.form.get("identifiant") or "").strip()
    password = (request.form.get("mot_de_passe") or "").strip()
    role = (request.form.get("role") or "").strip()

    if not nom or not prenom or not identifiant or not password or not role:
        return jsonify({"success": False, "message": "Tous les champs sont obligatoires."}), 400

    if role not in AVAILABLE_ROLES:
        return jsonify({"success": False, "message": "Rôle invalide."}), 400

    try:
        created, message = create_registered_user(nom, prenom, identifiant, password, role)
        if not created:
            return jsonify({"success": False, "message": message}), 409
        users = fetch_registered_users()
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    return jsonify(
        {
            "success": True,
            "message": message,
            "users": users,
        }
    )
 
# --- TOUJOURS À LA FIN DU FICHIER ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8180, debug=True)