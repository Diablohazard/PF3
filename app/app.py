import os
import hashlib
import hmac
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
        cursor.execute(f"SELECT id_inter, nom, horodatage FROM `{table_name}` ORDER BY horodatage DESC")
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
    return session.get("logged_in") and session.get("role") in ("Respo", "Integ")
 
AUTH_PEPPER = os.getenv("AUTH_PEPPER", "dev-pepper-change-me")
SCRYPT_PARAMS = {"n": 2**14, "r": 8, "p": 1, "dklen": 64}

# Identifiants stockés sous forme hachée (scrypt salé + poivré)
USERS_HASHED = [
    {
        "role": "Operat",
        "username_salt": "b84a49226efe6de60ea68eca437f9993",
        "username_hash": "b86c25dd254b20ba49c0c673edcfac925fa26e792d6315fbfbd5be54b43f30b2bf99b6ee70f3515c78ed78f691a94f4c5ae01e39d019c3084f4f0474eeb2cc88",
        "password_salt": "3927ff3bdfd63b619ee5c15ad827fc0e",
        "password_hash": "c72d57bb5e33086600ae39437d814e207127196a80e09592b744d9f032e797e7895c37e901c54ebf2da75557d8ad84d9d71b7d0cdb84ed0a17d11851f18bef0d",
    },
    {
        "role": "Respo",
        "username_salt": "47c580670c1f28c1f4ee370435db56eb",
        "username_hash": "3d6a7163fb861b2ae13f7e95ca131f996bb044f54977863eaf7e8d12b852c72ca3ac67b21f94fff082339ec9f9ff04ea7c1146f90f77018e951823ac0be189dc",
        "password_salt": "e808fee4bae9b64d6527eed397ac853f",
        "password_hash": "1c5c499b7ad867aa7e502a246064fa8089acf3e98610bd1dd59c3c5a1115c471b1b523ca31daac38a6d7ceadd09ea7073dcf1d1b07c592c8b6a01cf4f4b58729",
    },
    {
        "role": "Integ",
        "username_salt": "3d88b1505e0d69bfa615d82b5d68ffe0",
        "username_hash": "2499c728f0b6456fa397421f25796005d454a9e81fc1046b6cfda7f3eba794892d6675b9239b83b7fd81ebb6d8830ccbe8178c88649140841d3049a00a885e38",
        "password_salt": "b08734f827c86bc5b57f54b1860d412a",
        "password_hash": "d6d23fa77df8d0ba06874568bf6a18165f2c8fa0488eaef7373c33f04bcd05576f13480b8a7302892b5842aee621354f585f92b6b1d3051af93f5779f360869e",
    },
    {
        "role": "Admin",
        "username_salt": "0b96e3b2cf350a8979964b8bebec32b5",
        "username_hash": "821d36427abda02b2f1b2f5b2736aeb029594a1dfd479952a3e87a687ceecbd4ee1a41919ebfd0837468c3d803ed47ae8f049455d33a1d3db0b3f65a79847cfe",
        "password_salt": "8461eaf628a1bace8462d1482e966ba0",
        "password_hash": "d1b04cf2bc715a86280a9bf8b7e57f06352b98f51ae86b823f1cb8c7ffb2a83c08397a0e15b9131e8165da8442136e916afe64a4be9c3e80f1bb315a01e10667",
    },
]


def scrypt_hex(value, salt_hex, purpose):
    salt = bytes.fromhex(salt_hex)
    payload = f"{purpose}:{value}:{AUTH_PEPPER}".encode("utf-8")
    return hashlib.scrypt(payload, salt=salt, **SCRYPT_PARAMS).hex()


def authenticate_user(username, password):
    for account in USERS_HASHED:
        expected_username_hash = account["username_hash"]
        computed_username_hash = scrypt_hex(username, account["username_salt"], "username")

        if hmac.compare_digest(expected_username_hash, computed_username_hash):
            expected_password_hash = account["password_hash"]
            computed_password_hash = scrypt_hex(password, account["password_salt"], "password")
            if hmac.compare_digest(expected_password_hash, computed_password_hash):
                return account["role"]
            return None

        # Compatibilité temporaire : anciennes entrées générées avec username/password inversés.
        computed_username_hash_legacy = scrypt_hex(password, account["username_salt"], "username")
        computed_password_hash_legacy = scrypt_hex(username, account["password_salt"], "password")
        if hmac.compare_digest(expected_username_hash, computed_username_hash_legacy) and hmac.compare_digest(
            account["password_hash"], computed_password_hash_legacy
        ):
            return account["role"]

    return None


def build_hashed_credentials(username, password):
    username_salt = os.urandom(16).hex()
    password_salt = os.urandom(16).hex()
    return {
        "username_salt": username_salt,
        "username_hash": scrypt_hex(username, username_salt, "username"),
        "password_salt": password_salt,
        "password_hash": scrypt_hex(password, password_salt, "password"),
    }
 
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
                return redirect(url_for("admin"))
        
        else:
            error = "Identifiants incorrects"
 
    return render_template("login.html", error=error)
 
@app.route("/dashboard")
def dashboard_op():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    interventions = recuperer_interventions()
    return render_template("dashboard_operateur.html", interventions=interventions, role=session.get("role"))
 
 
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
    hashed = build_hashed_credentials(username, password)
 
    # Enregistrement dans le fichier users.txt à la racine du projet
    users_file_path = os.path.join(os.path.dirname(__file__), "../users.txt")
    with open(users_file_path, "a") as f:
        f.write(
            f"{hashed['username_salt']}:{hashed['username_hash']}:"
            f"{hashed['password_salt']}:{hashed['password_hash']}\n"
        )
 
    return render_template("admin.html", message="Utilisateur créé avec succès !")
 
# --- TOUJOURS À LA FIN DU FICHIER ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8180, debug=True)