import os
from datetime import datetime
 
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from services.opcua_status import get_opcua_status_details
 
load_dotenv()
 
app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = "une_cle_secrete_tres_longue"
 
 
 
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost").strip('"'),
        port=int(os.getenv("DB_PORT", "8181").strip('"')),
        user=os.getenv("DB_USER", "root").strip('"'),
        password=os.getenv("DB_PASSWORD", "").strip('"'),
        database=os.getenv("DB_NAME", os.getenv("DB_DATABASE", "pf3")).strip('"')
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
    "Operat": "Operateur",
    "Respo": "Responsable",
    "Integ": "Integrateur",
    "Admin": "Administrateur",
}
ROLE_VALUE_TO_CODE = {}
for _role_code, _role_label in AVAILABLE_ROLES.items():
    ROLE_VALUE_TO_CODE[_role_code.casefold()] = _role_code
    ROLE_VALUE_TO_CODE[_role_label.casefold()] = _role_code
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
            nom VARCHAR(50) NOT NULL,
            id_user INT NULL
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
            password VARCHAR(50) NOT NULL
        )
        """
    )


def ensure_user_management_tables(cursor):
    roles_table_name = get_roles_table_name(cursor)
    ensure_roles_table(cursor, roles_table_name)
    users_table_name = get_users_table_name(cursor)
    ensure_users_table(cursor, users_table_name, roles_table_name)
    users_columns = get_table_columns(cursor, users_table_name)
    role_columns = get_table_columns(cursor, roles_table_name)

    if "id_role" not in users_columns:
        cursor.execute(f"ALTER TABLE `{users_table_name}` ADD COLUMN id_role INT NULL")

    if "id_user" not in role_columns:
        cursor.execute(f"ALTER TABLE `{roles_table_name}` ADD COLUMN id_user INT NULL")
        role_columns = get_table_columns(cursor, roles_table_name)

    for role_name in AVAILABLE_ROLES:
        get_or_create_role_id(cursor, roles_table_name, role_name, role_columns)
    return users_table_name, roles_table_name


def get_table_columns(cursor, table_name):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        (table_name,),
    )
    return {row[0] for row in cursor.fetchall()}


def normalize_role_code(role_value):
    if not role_value:
        return ""
    return ROLE_VALUE_TO_CODE.get(str(role_value).strip().casefold(), "")


def get_role_label(role_value):
    role_code = normalize_role_code(role_value)
    if role_code:
        return AVAILABLE_ROLES[role_code]
    return str(role_value).strip() if role_value else ""


def get_or_create_role_id(cursor, roles_table_name, role_name, role_columns):
    role_code = normalize_role_code(role_name) or role_name
    role_label = get_role_label(role_code)
    cursor.execute(
        f"SELECT id_role, nom FROM `{roles_table_name}` WHERE LOWER(nom) IN (%s, %s) ORDER BY id_role ASC LIMIT 1",
        (role_label.casefold(), str(role_name).strip().casefold()),
    )
    row = cursor.fetchone()
    if row:
        if row[1] != role_label:
            cursor.execute(
                f"UPDATE `{roles_table_name}` SET nom = %s WHERE id_role = %s",
                (role_label, row[0]),
            )
        return row[0]

    if "id_user" in role_columns:
        cursor.execute(
            f"INSERT INTO `{roles_table_name}` (nom, id_user) VALUES (%s, NULL)",
            (role_label,),
        )
    else:
        cursor.execute(
            f"INSERT INTO `{roles_table_name}` (nom) VALUES (%s)",
            (role_label,),
        )
    return cursor.lastrowid


def get_role_by_user_id(cursor, users_table_name, roles_table_name, user_id, user_id_role=None):
    users_columns = get_table_columns(cursor, users_table_name)
    role_columns = get_table_columns(cursor, roles_table_name)

    if "id_role" in users_columns and user_id_role:
        cursor.execute(
            f"SELECT nom FROM `{roles_table_name}` WHERE id_role = %s LIMIT 1",
            (user_id_role,),
        )
        row = cursor.fetchone()
        if row and row[0]:
            return normalize_role_code(row[0])

    if "id_user" in role_columns:
        cursor.execute(
            f"SELECT nom FROM `{roles_table_name}` WHERE id_user = %s ORDER BY id_role DESC LIMIT 1",
            (user_id,),
        )
        row = cursor.fetchone()
        if row and row[0]:
            return normalize_role_code(row[0])

    return ""


def set_role_for_user(cursor, users_table_name, roles_table_name, user_id, role_name):
    users_columns = get_table_columns(cursor, users_table_name)
    role_columns = get_table_columns(cursor, roles_table_name)
    role_code = normalize_role_code(role_name)

    if not role_code:
        return

    if "id_role" in users_columns:
        role_id = get_or_create_role_id(cursor, roles_table_name, role_code, role_columns)
        cursor.execute(
            f"UPDATE `{users_table_name}` SET id_role = %s WHERE id_user = %s",
            (role_id, user_id),
        )
        return

    if "id_user" in role_columns:
        cursor.execute(
            f"SELECT id_role FROM `{roles_table_name}` WHERE id_user = %s ORDER BY id_role DESC LIMIT 1",
            (user_id,),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                f"UPDATE `{roles_table_name}` SET nom = %s WHERE id_role = %s",
                (get_role_label(role_code), existing[0]),
            )
        else:
            cursor.execute(
                f"INSERT INTO `{roles_table_name}` (nom, id_user) VALUES (%s, %s)",
                (get_role_label(role_code), user_id),
            )

        return


def fetch_registered_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)
        users_columns = get_table_columns(table_cursor, users_table_name)
        select_id_role = ", u.id_role" if "id_role" in users_columns else ""
        cursor.execute(
            f"""
            SELECT u.id_user, u.prenom, u.nom, u.login, u.password{select_id_role}
            FROM `{users_table_name}` u
            ORDER BY u.nom ASC, u.prenom ASC, u.login ASC
            """
        )
        users = cursor.fetchall()

        result = []
        for user in users:
            role_name = get_role_by_user_id(
                table_cursor,
                users_table_name,
                roles_table_name,
                user["id_user"],
                user.get("id_role") if "id_role" in user else None,
            ) or "Operat"
            result.append(
                {
                    "nom": user["nom"],
                    "prenom": user["prenom"],
                    "identifiant": user["login"],
                    "mot_de_passe": user.get("password", ""),
                    "role": role_name,
                    "role_label": get_role_label(role_name),
                }
            )
        return result
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
        users_columns = get_table_columns(table_cursor, users_table_name)
        select_id_role = ", u.id_role" if "id_role" in users_columns else ""
        cursor.execute(
            f"""
            SELECT u.id_user, u.login, u.password{select_id_role}
            FROM `{users_table_name}` u
            WHERE LOWER(u.login) = LOWER(%s)
            LIMIT 1
            """,
            (login,)
        )
        account = cursor.fetchone()
        if not account:
            return None

        role_name = get_role_by_user_id(
            table_cursor,
            users_table_name,
            roles_table_name,
            account["id_user"],
            account.get("id_role") if "id_role" in account else None,
        ) or "Operat"
        account["role"] = role_name
        return account
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

    role = normalize_role_code(account.get("role") or "Operat")
    return role if role in AVAILABLE_ROLES else None


def create_registered_user(nom, prenom, identifiant, password, role):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        role_code = normalize_role_code(role)
        if not role_code:
            return False, "Rôle invalide."

        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)
        cursor.execute(
            f"SELECT id_user FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) LIMIT 1",
            (identifiant,)
        )
        if cursor.fetchone() or identifiant.casefold() == BOOTSTRAP_ADMIN_LOGIN.casefold():
            return False, "Cet identifiant existe déjà."

        cursor.execute(
            f"""
            INSERT INTO `{users_table_name}` (prenom, nom, login, password)
            VALUES (%s, %s, %s, %s)
            """,
            (prenom, nom, identifiant, password)
        )
        user_id = cursor.lastrowid
        set_role_for_user(table_cursor, users_table_name, roles_table_name, user_id, role_code)
        conn.commit()
        return True, "Utilisateur créé avec succès !"
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def update_registered_user_role(identifiant, role):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        role_code = normalize_role_code(role)
        if not role_code:
            return False, "Rôle invalide."

        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)
        cursor.execute(
            f"SELECT id_user FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) LIMIT 1",
            (identifiant,),
        )
        user = cursor.fetchone()
        if not user:
            return False, "Utilisateur introuvable."

        set_role_for_user(table_cursor, users_table_name, roles_table_name, user["id_user"], role_code)
        conn.commit()
        return True, "Rôle mis à jour avec succès."
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def update_registered_user(original_identifiant, nom, prenom, identifiant, password, role):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        role_code = normalize_role_code(role)
        if not role_code:
            return False, "Rôle invalide."

        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)
        cursor.execute(
            f"SELECT id_user FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) LIMIT 1",
            (original_identifiant,),
        )
        user = cursor.fetchone()
        if not user:
            return False, "Utilisateur introuvable."

        cursor.execute(
            f"SELECT id_user FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) AND id_user <> %s LIMIT 1",
            (identifiant, user["id_user"]),
        )
        if cursor.fetchone() or identifiant.casefold() == BOOTSTRAP_ADMIN_LOGIN.casefold():
            return False, "Cet identifiant existe déjà."

        cursor.execute(
            f"""
            UPDATE `{users_table_name}`
            SET prenom = %s, nom = %s, login = %s, password = %s
            WHERE id_user = %s
            """,
            (prenom, nom, identifiant, password, user["id_user"]),
        )
        set_role_for_user(table_cursor, users_table_name, roles_table_name, user["id_user"], role_code)
        conn.commit()
        return True, "Utilisateur mis à jour avec succès."
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def delete_registered_user(identifiant):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)
        users_columns = get_table_columns(table_cursor, users_table_name)
        role_columns = get_table_columns(table_cursor, roles_table_name)

        select_id_role = ", id_role" if "id_role" in users_columns else ""
        cursor.execute(
            f"SELECT id_user{select_id_role} FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) LIMIT 1",
            (identifiant,),
        )
        user = cursor.fetchone()
        if not user:
            return False, "Utilisateur introuvable."

        if identifiant.casefold() == BOOTSTRAP_ADMIN_LOGIN.casefold():
            return False, "Suppression du compte bootstrap interdite."

        if "id_user" in role_columns:
            table_cursor.execute(
                f"DELETE FROM `{roles_table_name}` WHERE id_user = %s",
                (user["id_user"],),
            )

        cursor.execute(
            f"DELETE FROM `{users_table_name}` WHERE id_user = %s",
            (user["id_user"],),
        )
        conn.commit()
        return True, "Utilisateur supprimé avec succès."
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
 
    # Vérifier l'état de la connexion OPC UA avec l'automate
    automate_status = get_opcua_status_details()
    return render_template(
        "login.html",
        error=error,
        automate_ok=automate_status["ok"],
        automate_error=automate_status["error"],
        automate_error_code=automate_status["error_code"],
    )
 
@app.route("/dashboard")
def dashboard_op():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    automate_status = get_opcua_status_details()
    interventions = recuperer_interventions()
    return render_template(
        "dashboard_operateur.html",
        interventions=interventions,
        role=session.get("role"),
        registered_users=fetch_registered_users(),
        available_roles=AVAILABLE_ROLES,
        automate_ok=automate_status["ok"],
        automate_error=automate_status["error"],
        automate_error_code=automate_status["error_code"],
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

    if not normalize_role_code(role):
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


@app.route("/update_user_role", methods=["POST"])
def update_user_role():
    if not session.get("logged_in") or session.get("role") != "Admin":
        return jsonify({"success": False, "message": "Accès refusé."}), 403

    identifiant = (request.form.get("identifiant") or "").strip()
    role = (request.form.get("role") or "").strip()

    if not identifiant or not role:
        return jsonify({"success": False, "message": "Identifiant et rôle obligatoires."}), 400

    if not normalize_role_code(role):
        return jsonify({"success": False, "message": "Rôle invalide."}), 400

    try:
        updated, message = update_registered_user_role(identifiant, role)
        if not updated:
            return jsonify({"success": False, "message": message}), 404
        users = fetch_registered_users()
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    return jsonify({"success": True, "message": message, "users": users})


@app.route("/update_user", methods=["POST"])
def update_user():
    if not session.get("logged_in") or session.get("role") != "Admin":
        return jsonify({"success": False, "message": "Accès refusé."}), 403

    original_identifiant = (request.form.get("original_identifiant") or "").strip()
    nom = (request.form.get("nom") or "").strip()
    prenom = (request.form.get("prenom") or "").strip()
    identifiant = (request.form.get("identifiant") or "").strip()
    password = (request.form.get("mot_de_passe") or "").strip()
    role = (request.form.get("role") or "").strip()

    if not original_identifiant or not nom or not prenom or not identifiant or not password or not role:
        return jsonify({"success": False, "message": "Tous les champs sont obligatoires."}), 400

    if not normalize_role_code(role):
        return jsonify({"success": False, "message": "Rôle invalide."}), 400

    try:
        updated, message = update_registered_user(original_identifiant, nom, prenom, identifiant, password, role)
        if not updated:
            return jsonify({"success": False, "message": message}), 409
        users = fetch_registered_users()
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    return jsonify({"success": True, "message": message, "users": users})


@app.route("/delete_user", methods=["POST"])
def delete_user():
    if not session.get("logged_in") or session.get("role") != "Admin":
        return jsonify({"success": False, "message": "Accès refusé."}), 403

    identifiant = (request.form.get("identifiant") or "").strip()
    if not identifiant:
        return jsonify({"success": False, "message": "Identifiant obligatoire."}), 400

    try:
        deleted, message = delete_registered_user(identifiant)
        if not deleted:
            return jsonify({"success": False, "message": message}), 404
        users = fetch_registered_users()
    except mysql.connector.Error as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    return jsonify({"success": True, "message": message, "users": users})
 
# --- TOUJOURS À LA FIN DU FICHIER ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8180, debug=True)