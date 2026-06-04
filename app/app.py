import os
import re
import time
from datetime import datetime
 
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from werkzeug.exceptions import HTTPException
from services.opcua_status import (
    get_alert_thresholds_details,
    get_automate_variables_details,
    get_cpu_metrics_details,
    get_opcua_status_details,
    set_alert_thresholds_details,
)
from services.opcua_requests import close_persistent_client
 
load_dotenv()
 
app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = "une_cle_secrete_tres_longue"
 
 
@app.errorhandler(Exception)
def handle_api_exception(exc):
    if request.path.startswith("/api/"):
        status_code = exc.code if isinstance(exc, HTTPException) else 500
        return jsonify(
            {
                "ok": False,
                "error": str(exc),
                "error_code": type(exc).__name__,
            }
        ), status_code
    raise exc


 
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost").strip('"'),
        port=int(os.getenv("DB_PORT", "8181").strip('"')),
        user=os.getenv("DB_USER", "pf3user").strip('"'),
        password=os.getenv("DB_PASSWORD", "pf3password").strip('"'),
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


def get_cpu_data_table_name(cursor):
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('donnees_cpu', 'Donnees_cpu')
        ORDER BY CASE WHEN TABLE_NAME = 'donnees_cpu' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    return row[0] if row else "donnees_cpu"


def ensure_cpu_data_table(cursor, table_name):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            id_cpu INT AUTO_INCREMENT PRIMARY KEY,
            charge FLOAT NOT NULL,
            ram FLOAT NOT NULL,
            temperature FLOAT NOT NULL,
            alerte VARCHAR(50),
            seuil_charge FLOAT NOT NULL,
            seuil_ram FLOAT NOT NULL,
            seuil_temperature FLOAT NOT NULL,
            id_role INT,
            horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Migration douce: ajouter les colonnes de seuil si la table existe déjà.
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
    existing_columns = {row[0].lower() for row in cursor.fetchall()}
    if "seuil_charge" not in existing_columns:
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN seuil_charge FLOAT NULL")
    if "seuil_ram" not in existing_columns:
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN seuil_ram FLOAT NULL")
    if "seuil_temperature" not in existing_columns:
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN seuil_temperature FLOAT NULL")


def enregistrer_temperature(charge, ram, temperature, alerte=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        table_name = get_cpu_data_table_name(cursor)
        ensure_cpu_data_table(cursor, table_name)
        sql = f"INSERT INTO `{table_name}` (charge, ram, temperature, alerte) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (charge, ram, temperature, alerte))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def recuperer_derniere_temperature():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        table_name = get_cpu_data_table_name(table_cursor)
        ensure_cpu_data_table(table_cursor, table_name)
        cursor.execute(
            f"SELECT charge, ram, temperature, alerte, horodatage "
            f"FROM `{table_name}` "
            f"WHERE COALESCE(alerte, '') <> 'SEUILS' "
            f"ORDER BY horodatage DESC LIMIT 1"
        )
        return cursor.fetchone()
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def recuperer_historique_temperature(limit=60):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        table_name = get_cpu_data_table_name(table_cursor)
        ensure_cpu_data_table(table_cursor, table_name)
        cursor.execute(
            f"SELECT charge, ram, temperature, alerte, horodatage "
            f"FROM `{table_name}` "
            f"WHERE COALESCE(alerte, '') <> 'SEUILS' "
            f"ORDER BY horodatage DESC LIMIT %s",
            (limit,)
        )
        return cursor.fetchall()
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def enregistrer_seuils_alerte(charge, ram, temperature):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        table_name = get_cpu_data_table_name(cursor)
        ensure_cpu_data_table(cursor, table_name)
        # Les seuils sont stockés dans les colonnes dédiées, avec un marqueur alerte='SEUILS'.
        sql = (
            f"INSERT INTO `{table_name}` "
            f"(charge, ram, temperature, alerte, seuil_charge, seuil_ram, seuil_temperature) "
            f"VALUES (%s, %s, %s, %s, %s, %s, %s)"
        )
        cursor.execute(
            sql,
            (
                0.0,
                0.0,
                0.0,
                "SEUILS",
                float(charge),
                float(ram),
                float(temperature),
            ),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def recuperer_derniers_seuils_alerte():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        table_name = get_cpu_data_table_name(table_cursor)
        ensure_cpu_data_table(table_cursor, table_name)
        cursor.execute(
            f"SELECT seuil_charge, seuil_ram, seuil_temperature, charge, ram, temperature, horodatage FROM `{table_name}` "
            "WHERE alerte = 'SEUILS' ORDER BY horodatage DESC LIMIT 1"
        )
        return cursor.fetchone()
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def get_suivi_conso_table_name(cursor):
    cursor.execute(
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('suivi_conso', 'Suivi_conso')
        ORDER BY CASE WHEN TABLE_NAME = 'suivi_conso' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    return row[0] if row else "suivi_conso"


def ensure_suivi_conso_table(cursor, table_name):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            id_suivi INT AUTO_INCREMENT PRIMARY KEY,
            courant FLOAT NOT NULL,
            puissance FLOAT NOT NULL,
            energie DECIMAL(15,2) NOT NULL,
            id_role INT,
            horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Backward-compatible migration: ensure expected columns exist on older tables.
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
    existing_columns = {row[0].lower() for row in cursor.fetchall()}

    if "horodatage" not in existing_columns:
        cursor.execute(
            f"ALTER TABLE `{table_name}` ADD COLUMN horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        )

    if "id_role" not in existing_columns:
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN id_role INT")


def enregistrer_suivi_conso(courant, puissance, energie):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        table_name = get_suivi_conso_table_name(cursor)
        ensure_suivi_conso_table(cursor, table_name)
        sql = f"INSERT INTO `{table_name}` (courant, puissance, energie) VALUES (%s, %s, %s)"
        cursor.execute(sql, (courant, puissance, energie))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def recuperer_dernier_suivi_conso():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        table_name = get_suivi_conso_table_name(table_cursor)
        ensure_suivi_conso_table(table_cursor, table_name)
        cursor.execute(
            f"SELECT courant, puissance, energie, horodatage FROM `{table_name}` ORDER BY horodatage DESC LIMIT 1"
        )
        return cursor.fetchone()
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def recuperer_historique_suivi_conso(limit=60):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    table_cursor = conn.cursor()

    try:
        table_name = get_suivi_conso_table_name(table_cursor)
        ensure_suivi_conso_table(table_cursor, table_name)
        cursor.execute(
            f"SELECT id_suivi, courant, puissance, energie, horodatage FROM `{table_name}` "
            "ORDER BY horodatage DESC, id_suivi DESC LIMIT %s",
            (limit,)
        )
        # On récupère les N derniers points, puis on les remet en ordre chronologique
        # pour l'affichage du graphe de gauche à droite.
        return list(reversed(cursor.fetchall()))
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


 
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


def validate_password_strength(password):
    # Politique minimale de complexité appliquée à toute création/modification de compte.
    # Règle minimale demandée pour tous les comptes créés/modifiés depuis l'application.
    if len(password or "") < 12:
        return False, "Le mot de passe doit contenir au moins 12 caractères."
    if not re.search(r"[A-Z]", password):
        return False, "Le mot de passe doit contenir au moins une majuscule."
    if not re.search(r"\d", password):
        return False, "Le mot de passe doit contenir au moins un chiffre."
    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "Le mot de passe doit contenir au moins un caractère spécial."
    return True, ""


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


def is_user_registry_empty():
    # Utilisé pour activer le mode bootstrap uniquement au tout premier démarrage.
    conn = get_db_connection()
    cursor = conn.cursor()
    table_cursor = conn.cursor()

    try:
        users_table_name, _ = ensure_user_management_tables(table_cursor)
        cursor.execute(f"SELECT COUNT(*) FROM `{users_table_name}`")
        row = cursor.fetchone()
        return int(row[0] if row else 0) == 0
    finally:
        table_cursor.close()
        cursor.close()
        conn.close()


def authenticate_user(username, password):
    # Authentification standard uniquement via comptes stockés en base.
    # Le couple bootstrap Admin/administrator n'est plus accepté ici.
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

        # Contrôle serveur obligatoire: empêche de contourner la validation HTML du formulaire.
        password_ok, password_message = validate_password_strength(password)
        if not password_ok:
            return False, password_message

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

        # On réapplique la même règle lors de la modification pour garder une politique homogène.
        password_ok, password_message = validate_password_strength(password)
        if not password_ok:
            return False, password_message

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

        # Flux de bootstrap: si aucun utilisateur n'existe encore,
        # le couple Admin/administrator ouvre la création du premier compte admin.
        # Dès qu'un utilisateur existe, ces identifiants sont rejetés.
        if user == BOOTSTRAP_ADMIN_LOGIN and password == BOOTSTRAP_ADMIN_PASSWORD:
            try:
                if is_user_registry_empty():
                    session.clear()
                    # Jeton de session temporaire pour autoriser la page /bootstrap-admin.
                    session["bootstrap_admin_setup_allowed"] = True
                    return redirect(url_for("bootstrap_admin_setup"))
                error = "Identifiants incorrects"
            except mysql.connector.Error as exc:
                error = str(exc)

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
 
    # Rafraîchir immédiatement le statut OPC UA (au lieu de relire juste le cache statique)
    # Cela évite que le badge reste "Hors Ligne" longtemps après l'affichage de la page
    try:
        status = get_opcua_status_details()
        _last_opcua_status["ok"] = status.get("ok")
        _last_opcua_status["error"] = status.get("error")
        _last_opcua_status["error_code"] = status.get("error_code")
    except Exception as exc:
        _last_opcua_status["ok"] = False
        _last_opcua_status["error"] = str(exc)
        _last_opcua_status["error_code"] = type(exc).__name__

    return render_template(
        "login.html",
        error=error,
        automate_ok=_last_opcua_status["ok"],
        automate_error=_last_opcua_status["error"],
        automate_error_code=_last_opcua_status["error_code"],
    )


@app.route("/bootstrap-admin", methods=["GET", "POST"])
def bootstrap_admin_setup():
    try:
        bootstrap_mode = is_user_registry_empty()
    except mysql.connector.Error as exc:
        return render_template("bootstrap_admin.html", error=str(exc))

    if not bootstrap_mode:
        session.pop("bootstrap_admin_setup_allowed", None)
        return redirect(url_for("login"))

    # Protection: impossible d'accéder à la création du premier admin
    # sans être passé par le challenge bootstrap sur la page login.
    if not session.get("bootstrap_admin_setup_allowed"):
        return redirect(url_for("login"))

    error = None
    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        prenom = (request.form.get("prenom") or "").strip()
        identifiant = (request.form.get("identifiant") or "").strip()
        password = (request.form.get("mot_de_passe") or "").strip()

        if not nom or not prenom or not identifiant or not password:
            error = "Tous les champs sont obligatoires."
        else:
            try:
                # Le premier entrant est forcé au rôle Admin.
                created, message = create_registered_user(nom, prenom, identifiant, password, "Admin")
                if not created:
                    error = message
                else:
                    session.pop("bootstrap_admin_setup_allowed", None)
                    session["logged_in"] = True
                    session["role"] = "Admin"
                    return redirect(url_for("dashboard_op"))
            except mysql.connector.Error as exc:
                error = str(exc)

    return render_template("bootstrap_admin.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    close_persistent_client()
    return redirect(url_for("login"))
 
@app.route("/dashboard")
def dashboard_op():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    interventions = recuperer_interventions()
    
    # Rafraîchir immédiatement le statut OPC UA au sens lié (évite un badge "Hors Ligne" statique)
    try:
        status = get_opcua_status_details()
        _last_opcua_status["ok"] = status.get("ok")
        _last_opcua_status["error"] = status.get("error")
        _last_opcua_status["error_code"] = status.get("error_code")
    except Exception as exc:
        _last_opcua_status["ok"] = False
        _last_opcua_status["error"] = str(exc)
        _last_opcua_status["error_code"] = type(exc).__name__
    
    return render_template(
        "dashboard_operateur.html",
        interventions=interventions,
        role=session.get("role"),
        registered_users=fetch_registered_users(),
        available_roles=AVAILABLE_ROLES,
        automate_ok=_last_opcua_status["ok"],
        automate_error=_last_opcua_status["error"],
        automate_error_code=_last_opcua_status["error_code"],
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


# Statut OPC UA en cache — mis à jour à chaque lecture de variable (cpu-temperature, suivi-consommation).
_last_opcua_status = {"ok": None, "error": None, "error_code": None}


# ============================================================================
# CACHE OPC UA CÔTÉ SERVEUR — Réduit les appels répétés à l'automate
# ============================================================================
# TTL en secondes pour le cache OPC UA (défaut: 5s).
# Augmente si tu veux moins de requêtes OPC UA mais acceptes des données plus "vieilles".
OPCUA_CACHE_TTL = 10

_opcua_variables_cache = {
    "data": None,
    "timestamp": 0,
}

_opcua_cpu_metrics_cache = {
    "data": None,
    "timestamp": 0,
}


def _get_cached_automate_variables(force_refresh=False):
    """
    Retourne les variables OPC UA depuis le cache si encore valide (< TTL),
    sinon refait une requête OPC UA et met à jour le cache.
    Réduit drastiquement les temps de chargement des graphiques.
    """
    global _opcua_variables_cache
    
    now = time.time()
    age = now - _opcua_variables_cache["timestamp"]
    
    # Si cache valide et pas de force_refresh, retourner le cache
    if not force_refresh and age < OPCUA_CACHE_TTL and _opcua_variables_cache["data"] is not None:
        return _opcua_variables_cache["data"], False  # (données, was_refreshed)
    
    # Sinon, refaire la requête OPC UA
    result = get_automate_variables_details()
    _opcua_variables_cache["data"] = result
    _opcua_variables_cache["timestamp"] = now
    
    return result, True  # (données, was_refreshed=True)


def _get_cached_cpu_metrics(force_refresh=False):
    global _opcua_cpu_metrics_cache

    now = time.time()
    age = now - _opcua_cpu_metrics_cache["timestamp"]

    if not force_refresh and age < OPCUA_CACHE_TTL and _opcua_cpu_metrics_cache["data"] is not None:
        return _opcua_cpu_metrics_cache["data"], False

    result = get_cpu_metrics_details()
    _opcua_cpu_metrics_cache["data"] = result
    _opcua_cpu_metrics_cache["timestamp"] = now

    return result, True


def _build_alert_statuses(seuils, automate_values):
    """Construit le statut d'alerte à partir des valeurs live de l'automate."""
    def _status(current_value, threshold_value):
        if current_value is None or threshold_value is None:
            return "Inconnu"
        return "Déclenchée" if float(current_value) >= float(threshold_value) else "Normale"

    return {
        "seuil_cpu": _status(automate_values.get("cpu_load"), seuils.get("seuil_cpu")),
        "seuil_ram": _status(automate_values.get("ram_usage"), seuils.get("seuil_ram")),
        "seuil_temp": _status(automate_values.get("temp_c"), seuils.get("seuil_temp")),
    }


def _update_opcua_status_from_read_error(error_message, error_code):
    _last_opcua_status["error"] = error_message
    _last_opcua_status["error_code"] = error_code
    _last_opcua_status["ok"] = error_code == "BadNodeIdUnknown"


# ============================================================================
@app.route("/api/automate-status")
def api_automate_status():
    """Retourne le dernier statut OPC UA connu sans déclencher de connexion supplémentaire."""
    return jsonify(_last_opcua_status)


@app.route("/api/alert-thresholds", methods=["GET"])
def api_get_alert_thresholds():
    if not session.get("logged_in"):
        return jsonify({"ok": False, "error": "Non authentifié."}), 401

    # Source prioritaire: valeurs courantes lues sur l'automate.
    opcua_result = get_alert_thresholds_details()
    if opcua_result.get("ok") and opcua_result.get("data"):
        values = opcua_result["data"]
        payload = {
            "seuil_cpu": float(values.get("seuil_cpu", 0)),
            "seuil_ram": float(values.get("seuil_ram", 0)),
            "seuil_temp": float(values.get("seuil_temp", 0)),
        }
        automate_values, _ = _get_cached_automate_variables()
        statuses = _build_alert_statuses(payload, (automate_values or {}).get("data") or {})
        _last_opcua_status["ok"] = True
        _last_opcua_status["error"] = None
        _last_opcua_status["error_code"] = None
        try:
            # On garde aussi un snapshot DB pour afficher des valeurs en fallback.
            enregistrer_seuils_alerte(
                charge=payload["seuil_cpu"],
                ram=payload["seuil_ram"],
                temperature=payload["seuil_temp"],
            )
        except Exception:
            pass
        return jsonify({"ok": True, "data": payload, "statuses": statuses, "source": "opcua"})

    # Fallback: dernières valeurs connues en base si l'OPC UA est indisponible.
    db_values = recuperer_derniers_seuils_alerte()
    if db_values:
        payload = {
            "seuil_cpu": float(db_values["seuil_charge"] if db_values["seuil_charge"] is not None else db_values["charge"]),
            "seuil_ram": float(db_values["seuil_ram"] if db_values["seuil_ram"] is not None else db_values["ram"]),
            "seuil_temp": float(db_values["seuil_temperature"] if db_values["seuil_temperature"] is not None else db_values["temperature"]),
        }
        automate_values, _ = _get_cached_automate_variables()
        statuses = _build_alert_statuses(payload, (automate_values or {}).get("data") or {})
        return jsonify(
            {
                "ok": True,
                "data": payload,
                "statuses": statuses,
                "source": "database",
                "opcua_error": opcua_result.get("error"),
                "opcua_error_code": opcua_result.get("error_code"),
            }
        )

    return jsonify(
        {
            "ok": False,
            "error": opcua_result.get("error") or "Aucun seuil disponible",
            "error_code": opcua_result.get("error_code"),
        }
    ), 404


@app.route("/api/alert-thresholds", methods=["POST"])
def api_set_alert_thresholds():
    if not session.get("logged_in"):
        return jsonify({"ok": False, "error": "Non authentifié."}), 401

    if session.get("role") not in ("Integ", "Admin"):
        return jsonify({"ok": False, "error": "Accès refusé."}), 403

    payload = request.get_json(silent=True) or request.form

    try:
        seuil_cpu = float((payload.get("seuil_cpu") or "").strip() if isinstance(payload.get("seuil_cpu"), str) else payload.get("seuil_cpu"))
        seuil_ram = float((payload.get("seuil_ram") or "").strip() if isinstance(payload.get("seuil_ram"), str) else payload.get("seuil_ram"))
        seuil_temp = float((payload.get("seuil_temp") or "").strip() if isinstance(payload.get("seuil_temp"), str) else payload.get("seuil_temp"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Valeurs seuil invalides."}), 400

    # Ordre volontaire: écrire d'abord sur l'automate, puis persister en base.
    write_result = set_alert_thresholds_details(seuil_ram=seuil_ram, seuil_cpu=seuil_cpu, seuil_temp=seuil_temp)
    if not write_result.get("ok"):
        _last_opcua_status["ok"] = False
        _last_opcua_status["error"] = write_result.get("error")
        _last_opcua_status["error_code"] = write_result.get("error_code")
        return jsonify({"ok": False, "error": write_result.get("error"), "error_code": write_result.get("error_code")}), 502

    _last_opcua_status["ok"] = True
    _last_opcua_status["error"] = None
    _last_opcua_status["error_code"] = None

    try:
        enregistrer_seuils_alerte(charge=seuil_cpu, ram=seuil_ram, temperature=seuil_temp)
    except Exception as exc:
        return jsonify(
            {
                "ok": True,
                "data": {
                    "seuil_cpu": seuil_cpu,
                    "seuil_ram": seuil_ram,
                    "seuil_temp": seuil_temp,
                },
                "warning": f"Seuils ecrits sur automate mais sauvegarde DB echouee: {exc}",
            }
        )

    return jsonify(
        {
            "ok": True,
            "data": {
                "seuil_cpu": seuil_cpu,
                "seuil_ram": seuil_ram,
                "seuil_temp": seuil_temp,
            },
        }
    )


@app.route("/api/cpu-temperature")
def api_cpu_temperature():
    """Affiche la dernière valeur de base et met à jour la base via OPC UA quand possible."""
    opcua_error = None
    opcua_error_code = None
    live_data = None

    # 1) Tenter une lecture OPC UA pour enrichir la base, sans bloquer l'affichage.
    # OPTIMISATION: utiliser le cache OPC UA côté serveur au lieu de refaire une requête à chaque fois.
    try:
        variables, was_refreshed = _get_cached_cpu_metrics()
        if variables.get("ok") and variables.get("data"):
            data = variables["data"]
            charge = data.get("cpu_load", 0)
            ram = data.get("ram_usage", 0)
            temp = data.get("temp_c", 0)
            live_data = {
                "charge": charge,
                "ram": ram,
                "temperature": temp,
                "horodatage": datetime.utcnow().isoformat() + "Z",
            }
            _last_opcua_status["ok"] = True
            _last_opcua_status["error"] = None
            _last_opcua_status["error_code"] = None
            # Enregistrer en base que si on vient de refaire la requête OPC UA
            # (évite d'écrire en DB à chaque requête web)
            if was_refreshed:
                try:
                    enregistrer_temperature(charge, ram, temp)
                except Exception:
                    # Si l'insertion échoue, on continue quand meme avec la lecture DB/fallback live.
                    pass
        else:
            opcua_error = (variables or {}).get("error", "Lecture OPC UA impossible")
            opcua_error_code = (variables or {}).get("error_code")
            _update_opcua_status_from_read_error(opcua_error, opcua_error_code)
    except Exception as exc:
        opcua_error = str(exc)
        opcua_error_code = type(exc).__name__
        _last_opcua_status["ok"] = False
        _last_opcua_status["error"] = opcua_error
        _last_opcua_status["error_code"] = opcua_error_code

    # 2) Source principale: dernière valeur en base.
    try:
        dernier = recuperer_derniere_temperature()
        if dernier:
            return jsonify(
                {
                    "ok": True,
                    "source": "database",
                    "charge": dernier["charge"],
                    "ram": dernier["ram"],
                    "temperature": dernier["temperature"],
                    "alerte": dernier["alerte"],
                    "horodatage": dernier["horodatage"].isoformat() if dernier["horodatage"] else None,
                    "opcua_ok": opcua_error is None,
                    "opcua_error": opcua_error,
                    "opcua_error_code": opcua_error_code,
                }
            )
    except Exception as db_exc:
        # 3) Si la base échoue mais qu'on a une valeur live, on l'affiche quand meme.
        if live_data is not None:
            return jsonify(
                {
                    "ok": True,
                    "source": "opcua_live",
                    "charge": live_data["charge"],
                    "ram": live_data["ram"],
                    "temperature": live_data["temperature"],
                    "alerte": None,
                    "horodatage": live_data["horodatage"],
                    "db_error": str(db_exc),
                    "opcua_ok": True,
                }
            )
        return jsonify({"ok": False, "error": str(db_exc)}), 500

    # 4) Si la base est vide mais qu'on a une valeur live OPC UA, on l'utilise.
    if live_data is not None:
        return jsonify(
            {
                "ok": True,
                "source": "opcua_live",
                "charge": live_data["charge"],
                "ram": live_data["ram"],
                "temperature": live_data["temperature"],
                "alerte": None,
                "horodatage": live_data["horodatage"],
                "opcua_ok": True,
            }
        )

    return jsonify(
        {
            "ok": False,
            "error": "Aucune donnée CPU disponible",
            "opcua_error": opcua_error,
            "opcua_error_code": opcua_error_code,
        }
    ), 404


@app.route("/api/suivi-consommation-historique")
def api_suivi_consommation_historique():
    """Retourne l'historique des données de consommation (derniers 60 enregistrements)."""
    try:
        historique = recuperer_historique_suivi_conso(limit=60)
        if not historique:
            return jsonify({
                "ok": False,
                "message": "Aucune donnée d'historique disponible"
            }), 404
        
        result = [
            {
                "courant": float(row["courant"]),
                "puissance": float(row["puissance"]),
                "energie": float(row["energie"]),
                "horodatage": row["horodatage"].isoformat() if row["horodatage"] else None,
            }
            for row in historique
        ]
        return jsonify({
            "ok": True,
            "data": result,
            "count": len(result)
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500

@app.route("/api/suivi-consommation")
def api_suivi_consommation():
    """Mappe les variables énergétiques OPC UA vers suivi_conso et retourne la dernière ligne."""
    opcua_error = None
    opcua_error_code = None
    live_data = None

    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    try:
        # OPTIMISATION: utiliser le cache OPC UA côté serveur
        variables, was_refreshed = _get_cached_automate_variables()
        if variables.get("ok") and variables.get("data"):
            data = variables["data"]
            courant = _safe_float(data.get("energ_act_l1"), 0.0)
            puissance = _safe_float(data.get("energ_act_l2"), 0.0)
            energie = _safe_float(data.get("energ_act_tot"), 0.0)
            _last_opcua_status["ok"] = True
            _last_opcua_status["error"] = None
            _last_opcua_status["error_code"] = None
            live_data = {
                "courant": courant,
                "puissance": puissance,
                "energie": energie,
                "horodatage": datetime.utcnow().isoformat() + "Z",
            }
            # Enregistrer en base que si on vient de refaire la requête OPC UA
            if was_refreshed:
                try:
                    enregistrer_suivi_conso(courant, puissance, energie)
                except Exception:
                    pass
        else:
            opcua_error = (variables or {}).get("error", "Lecture OPC UA impossible")
            opcua_error_code = (variables or {}).get("error_code")
            _update_opcua_status_from_read_error(opcua_error, opcua_error_code)
    except Exception as exc:
        opcua_error = str(exc)
        opcua_error_code = type(exc).__name__
        _last_opcua_status["ok"] = False
        _last_opcua_status["error"] = opcua_error
        _last_opcua_status["error_code"] = opcua_error_code

    try:
        dernier = recuperer_dernier_suivi_conso()
        if dernier:
            return jsonify(
                {
                    "ok": True,
                    "source": "database",
                    "courant": float(dernier["courant"]),
                    "puissance": float(dernier["puissance"]),
                    "energie": float(dernier["energie"]),
                    "horodatage": dernier["horodatage"].isoformat() if dernier["horodatage"] else None,
                    "opcua_ok": opcua_error is None,
                    "opcua_error": opcua_error,
                    "opcua_error_code": opcua_error_code,
                }
            )
    except Exception as db_exc:
        if live_data is not None:
            return jsonify(
                {
                    "ok": True,
                    "source": "opcua_live",
                    "courant": live_data["courant"],
                    "puissance": live_data["puissance"],
                    "energie": live_data["energie"],
                    "horodatage": live_data["horodatage"],
                    "db_error": str(db_exc),
                }
            )
        return jsonify({"ok": False, "error": str(db_exc)}), 500

    if live_data is not None:
        return jsonify(
            {
                "ok": True,
                "source": "opcua_live",
                "courant": live_data["courant"],
                "puissance": live_data["puissance"],
                "energie": live_data["energie"],
                "horodatage": live_data["horodatage"],
            }
        )

    return jsonify(
        {
            "ok": False,
            "error": "Aucune donnée de consommation disponible",
            "opcua_error": opcua_error,
            "opcua_error_code": opcua_error_code,
        }
    ), 404


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
