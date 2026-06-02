import os  # Importe un module Python nécessaire.
import re  # Importe un module Python nécessaire.
import time  # Importe un module Python nécessaire.
from datetime import datetime  # Importe des éléments spécifiques depuis un module.
import hashlib  # Importe un module Python nécessaire.
import secrets  # Importe un module Python nécessaire.

import mysql.connector  # Importe un module Python nécessaire.
from dotenv import load_dotenv  # Importe des éléments spécifiques depuis un module.
from flask import Flask, render_template, request, redirect, url_for, jsonify, session  # Importe des éléments spécifiques depuis un module.
from services.opcua_status import (  # Importe des éléments spécifiques depuis un module.
    get_alert_thresholds_details,  # Effectue une opération de traitement des données.
    get_automate_variables_details,  # Effectue une opération de traitement des données.
    get_opcua_status_details,  # Effectue une opération de traitement des données.
    set_alert_thresholds_details,  # Effectue une opération de traitement des données.
)  # Effectue une opération de traitement des données.
from services.opcua_requests import close_persistent_client  # Importe des éléments spécifiques depuis un module.
 
load_dotenv()  # Effectue une opération de traitement des données.
 
app = Flask(__name__, template_folder="../templates", static_folder="../static")  # Affecte une valeur à une variable.
app.secret_key = "une_cle_secrete_tres_longue"  # Affecte une valeur à une variable.

PASSWORD_HASH_ALGORITHM = "sha256"  # Affecte une valeur à une variable.
PASSWORD_HASH_ITERATIONS = 150000  # Affecte une valeur à une variable.
PASSWORD_SALT_BYTES = 32  # Affecte une valeur à une variable.
PASSWORD_PEPPER_ENV = "PASSWORD_PEPPER"  # Affecte une valeur à une variable.


def get_db_connection():  # Définit la fonction get_db_connection.
    return mysql.connector.connect(  # Retourne une valeur depuis la fonction.
        host=os.getenv("DB_HOST", "localhost").strip('"'),  # Affecte une valeur à une variable.
        port=int(os.getenv("DB_PORT", "8181").strip('"')),  # Affecte une valeur à une variable.
        user=os.getenv("DB_USER", "pf3user").strip('"'),  # Affecte une valeur à une variable.
        password=os.getenv("DB_PASSWORD", "pf3password").strip('"'),  # Affecte une valeur à une variable.
        database=os.getenv("DB_NAME", os.getenv("DB_DATABASE", "pf3")).strip('"')  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement des données.
 
 
def get_intervention_table_name(cursor):  # Définit la fonction get_intervention_table_name.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('Intervention', 'intervention')
        ORDER BY CASE WHEN TABLE_NAME = 'Intervention' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )  # Effectue une opération de traitement des données.
    row = cursor.fetchone()  # Affecte une valeur à une variable.
 
    if row:  # Teste une condition.
        return sanitize_sql_identifier(row[0])  # Retourne une valeur depuis la fonction.
 
    return "Intervention"  # Retourne une valeur depuis la fonction.
 
 
def ensure_intervention_table(cursor, table_name):  # Définit la fonction ensure_intervention_table.
    table_name = sanitize_sql_identifier(table_name)  # Affecte une valeur à une variable.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
        f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            id_inter INT AUTO_INCREMENT PRIMARY KEY,
            nom VARCHAR(255) NOT NULL,
            horodatage DATETIME NOT NULL
        )
        """
    )  # Effectue une opération de traitement des données.
 
 
def parse_horodatage(date_value):  # Définit la fonction parse_horodatage.
    return datetime.strptime(date_value, "%Y-%m-%d")  # Retourne une valeur depuis la fonction.
 
 
def enregistrer_intervention(nom, horodatage):  # Définit la fonction enregistrer_intervention.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor()  # Affecte une valeur à une variable.
 
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_intervention_table_name(cursor)  # Affecte une valeur à une variable.
        ensure_intervention_table(cursor, table_name)  # Effectue une opération de traitement des données.
        sql = f"INSERT INTO `{table_name}` (nom, horodatage) VALUES (%s, %s)"  # Affecte une valeur à une variable.
        cursor.execute(sql, (nom, horodatage))  # Exécute une requête SQL avec des paramètres sécurisés.
        conn.commit()  # Valide les changements effectués dans la base de données.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.
 
 
def recuperer_interventions():  # Définit la fonction recuperer_interventions.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.
 
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_intervention_table_name(table_cursor)  # Affecte une valeur à une variable.
        ensure_intervention_table(table_cursor, table_name)  # Effectue une opération de traitement des données.
        cursor.execute(f"SELECT id_inter, nom, horodatage FROM `{table_name}` ORDER BY horodatage ASC")  # Exécute une requête SQL avec des paramètres sécurisés.
        return cursor.fetchall()  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def modifier_intervention(id_inter, nom, horodatage):  # Définit la fonction modifier_intervention.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor()  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_intervention_table_name(table_cursor)  # Affecte une valeur à une variable.
        ensure_intervention_table(table_cursor, table_name)  # Effectue une opération de traitement des données.
        sql = f"UPDATE `{table_name}` SET nom = %s, horodatage = %s WHERE id_inter = %s"  # Affecte une valeur à une variable.
        cursor.execute(sql, (nom, horodatage, id_inter))  # Exécute une requête SQL avec des paramètres sécurisés.
        conn.commit()  # Valide les changements effectués dans la base de données.
        return cursor.rowcount > 0  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def supprimer_intervention(id_inter):  # Définit la fonction supprimer_intervention.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor()  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_intervention_table_name(table_cursor)  # Affecte une valeur à une variable.
        ensure_intervention_table(table_cursor, table_name)  # Effectue une opération de traitement des données.
        sql = f"DELETE FROM `{table_name}` WHERE id_inter = %s"  # Affecte une valeur à une variable.
        cursor.execute(sql, (id_inter,))  # Exécute une requête SQL avec des paramètres sécurisés.
        conn.commit()  # Valide les changements effectués dans la base de données.
        return cursor.rowcount > 0  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def can_manage_maintenance():  # Définit la fonction can_manage_maintenance.
    return session.get("logged_in") and session.get("role") in ("Respo", "Integ", "Admin")  # Retourne une valeur depuis la fonction.


def get_cpu_data_table_name(cursor):  # Définit la fonction get_cpu_data_table_name.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('donnees_cpu', 'Donnees_cpu')
        ORDER BY CASE WHEN TABLE_NAME = 'donnees_cpu' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )  # Effectue une opération de traitement des données.
    row = cursor.fetchone()  # Affecte une valeur à une variable.
    return sanitize_sql_identifier(row[0]) if row else "donnees_cpu"  # Retourne une valeur depuis la fonction.


def ensure_cpu_data_table(cursor, table_name):  # Définit la fonction ensure_cpu_data_table.
    table_name = sanitize_sql_identifier(table_name)  # Affecte une valeur à une variable.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
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
    )  # Effectue une opération de traitement des données.

    # Migration douce: ajouter les colonnes de seuil si la table existe déjà.
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")  # Exécute une requête SQL avec des paramètres sécurisés.
    existing_columns = {row[0].lower() for row in cursor.fetchall()}  # Affecte une valeur à une variable.
    if "seuil_charge" not in existing_columns:  # Teste une condition.
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN seuil_charge FLOAT NULL")  # Exécute une requête SQL avec des paramètres sécurisés.
    if "seuil_ram" not in existing_columns:  # Teste une condition.
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN seuil_ram FLOAT NULL")  # Exécute une requête SQL avec des paramètres sécurisés.
    if "seuil_temperature" not in existing_columns:  # Teste une condition.
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN seuil_temperature FLOAT NULL")  # Exécute une requête SQL avec des paramètres sécurisés.
    if "horodatage" not in existing_columns:  # Teste une condition.
        cursor.execute(
            f"ALTER TABLE `{table_name}` ADD COLUMN horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        )  # Exécute une requête SQL avec des paramètres sécurisés.


def enregistrer_temperature(charge, ram, temperature, alerte=None):  # Définit la fonction enregistrer_temperature.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_cpu_data_table_name(cursor)  # Affecte une valeur à une variable.
        ensure_cpu_data_table(cursor, table_name)  # Effectue une opération de traitement des données.
        sql = f"INSERT INTO `{table_name}` (charge, ram, temperature, alerte) VALUES (%s, %s, %s, %s)"  # Affecte une valeur à une variable.
        cursor.execute(sql, (charge, ram, temperature, alerte))  # Exécute une requête SQL avec des paramètres sécurisés.
        conn.commit()  # Valide les changements effectués dans la base de données.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def recuperer_derniere_temperature():  # Définit la fonction recuperer_derniere_temperature.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_cpu_data_table_name(table_cursor)  # Affecte une valeur à une variable.
        ensure_cpu_data_table(table_cursor, table_name)  # Effectue une opération de traitement des données.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT charge, ram, temperature, alerte, horodatage "  # Effectue une opération de traitement des données.
            f"FROM `{table_name}` "  # Effectue une opération de traitement des données.
            f"WHERE COALESCE(alerte, '') <> 'SEUILS' "  # Effectue une opération de traitement des données.
            f"ORDER BY horodatage DESC LIMIT 1"  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        return cursor.fetchone()  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def recuperer_historique_temperature(limit=60):  # Définit la fonction recuperer_historique_temperature.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_cpu_data_table_name(table_cursor)  # Affecte une valeur à une variable.
        ensure_cpu_data_table(table_cursor, table_name)  # Effectue une opération de traitement des données.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT charge, ram, temperature, alerte, horodatage "  # Effectue une opération de traitement des données.
            f"FROM `{table_name}` "  # Effectue une opération de traitement des données.
            f"WHERE COALESCE(alerte, '') <> 'SEUILS' "  # Effectue une opération de traitement des données.
            f"ORDER BY horodatage DESC LIMIT %s",  # Effectue une opération de traitement des données.
            (limit,)  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        return cursor.fetchall()  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def enregistrer_seuils_alerte(charge, ram, temperature):  # Définit la fonction enregistrer_seuils_alerte.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_cpu_data_table_name(cursor)  # Affecte une valeur à une variable.
        ensure_cpu_data_table(cursor, table_name)  # Effectue une opération de traitement des données.
        # Les seuils sont stockés dans les colonnes dédiées, avec un marqueur alerte='SEUILS'.
        sql = (  # Affecte une valeur à une variable.
            f"INSERT INTO `{table_name}` "  # Effectue une opération de traitement des données.
            f"(charge, ram, temperature, alerte, seuil_charge, seuil_ram, seuil_temperature) "  # Effectue une opération de traitement des données.
            f"VALUES (%s, %s, %s, %s, %s, %s, %s)"  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            sql,  # Effectue une opération de traitement des données.
            (  # Effectue une opération de traitement des données.
                0.0,  # Effectue une opération de traitement des données.
                0.0,  # Effectue une opération de traitement des données.
                0.0,  # Effectue une opération de traitement des données.
                "SEUILS",  # Effectue une opération de traitement des données.
                float(charge),  # Effectue une opération de traitement des données.
                float(ram),  # Effectue une opération de traitement des données.
                float(temperature),  # Effectue une opération de traitement des données.
            ),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        conn.commit()  # Valide les changements effectués dans la base de données.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def recuperer_derniers_seuils_alerte():  # Définit la fonction recuperer_derniers_seuils_alerte.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_cpu_data_table_name(table_cursor)  # Affecte une valeur à une variable.
        ensure_cpu_data_table(table_cursor, table_name)  # Effectue une opération de traitement des données.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT seuil_charge, seuil_ram, seuil_temperature, charge, ram, temperature, horodatage FROM `{table_name}` "  # Effectue une opération de traitement des données.
            "WHERE alerte = 'SEUILS' ORDER BY horodatage DESC LIMIT 1"  # Affecte une valeur à une variable.
        )  # Effectue une opération de traitement des données.
        return cursor.fetchone()  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def get_suivi_conso_table_name(cursor):  # Définit la fonction get_suivi_conso_table_name.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('suivi_conso', 'Suivi_conso')
        ORDER BY CASE WHEN TABLE_NAME = 'suivi_conso' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )  # Effectue une opération de traitement des données.
    row = cursor.fetchone()  # Affecte une valeur à une variable.
    return sanitize_sql_identifier(row[0]) if row else "suivi_conso"  # Retourne une valeur depuis la fonction.


def ensure_suivi_conso_table(cursor, table_name):  # Définit la fonction ensure_suivi_conso_table.
    table_name = sanitize_sql_identifier(table_name)  # Affecte une valeur à une variable.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
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
    )  # Effectue une opération de traitement des données.

    # Backward-compatible migration: ensure expected columns exist on older tables.
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")  # Exécute une requête SQL avec des paramètres sécurisés.
    existing_columns = {row[0].lower() for row in cursor.fetchall()}  # Affecte une valeur à une variable.

    if "horodatage" not in existing_columns:  # Teste une condition.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"ALTER TABLE `{table_name}` ADD COLUMN horodatage TIMESTAMP DEFAULT CURRENT_TIMESTAMP"  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.

    if "id_role" not in existing_columns:  # Teste une condition.
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN id_role INT")  # Exécute une requête SQL avec des paramètres sécurisés.


def enregistrer_suivi_conso(courant, puissance, energie):  # Définit la fonction enregistrer_suivi_conso.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_suivi_conso_table_name(cursor)  # Affecte une valeur à une variable.
        ensure_suivi_conso_table(cursor, table_name)  # Effectue une opération de traitement des données.
        sql = f"INSERT INTO `{table_name}` (courant, puissance, energie) VALUES (%s, %s, %s)"  # Affecte une valeur à une variable.
        cursor.execute(sql, (courant, puissance, energie))  # Exécute une requête SQL avec des paramètres sécurisés.
        conn.commit()  # Valide les changements effectués dans la base de données.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def recuperer_dernier_suivi_conso():  # Définit la fonction recuperer_dernier_suivi_conso.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_suivi_conso_table_name(table_cursor)  # Affecte une valeur à une variable.
        ensure_suivi_conso_table(table_cursor, table_name)  # Effectue une opération de traitement des données.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT courant, puissance, energie, horodatage FROM `{table_name}` ORDER BY horodatage DESC LIMIT 1"  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        return cursor.fetchone()  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def recuperer_historique_suivi_conso(limit=60):  # Définit la fonction recuperer_historique_suivi_conso.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        table_name = get_suivi_conso_table_name(table_cursor)  # Affecte une valeur à une variable.
        ensure_suivi_conso_table(table_cursor, table_name)  # Effectue une opération de traitement des données.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT id_suivi, courant, puissance, energie, horodatage FROM `{table_name}` "  # Effectue une opération de traitement des données.
            "ORDER BY horodatage DESC, id_suivi DESC LIMIT %s",  # Effectue une opération de traitement des données.
            (limit,)  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        # On récupère les N derniers points, puis on les remet en ordre chronologique
        # pour l'affichage du graphe de gauche à droite.
        return list(reversed(cursor.fetchall()))  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


 
AVAILABLE_ROLES = {  # Affecte une valeur à une variable.
    "Operat": "Operateur",  # Effectue une opération de traitement des données.
    "Respo": "Responsable",  # Effectue une opération de traitement des données.
    "Integ": "Integrateur",  # Effectue une opération de traitement des données.
    "Admin": "Administrateur",  # Effectue une opération de traitement des données.
}  # Effectue une opération de traitement des données.
ROLE_VALUE_TO_CODE = {}  # Affecte une valeur à une variable.
for _role_code, _role_label in AVAILABLE_ROLES.items():  # Boucle sur une séquence d éléments.
    ROLE_VALUE_TO_CODE[_role_code.casefold()] = _role_code  # Affecte une valeur à une variable.
    ROLE_VALUE_TO_CODE[_role_label.casefold()] = _role_code  # Affecte une valeur à une variable.
BOOTSTRAP_ADMIN_LOGIN = "Admin"  # Affecte une valeur à une variable.
BOOTSTRAP_ADMIN_PASSWORD = "administrator"  # Affecte une valeur à une variable.


def get_users_table_name(cursor):  # Définit la fonction get_users_table_name.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('Users', 'users')
        ORDER BY CASE WHEN TABLE_NAME = 'Users' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )  # Effectue une opération de traitement des données.
    row = cursor.fetchone()  # Affecte une valeur à une variable.
    return sanitize_sql_identifier(row[0]) if row else "Users"  # Retourne une valeur depuis la fonction.


def get_roles_table_name(cursor):  # Définit la fonction get_roles_table_name.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
        """
        SELECT TABLE_NAME
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('roles', 'Roles')
        ORDER BY CASE WHEN TABLE_NAME = 'roles' THEN 0 ELSE 1 END
        LIMIT 1
        """
    )  # Effectue une opération de traitement des données.
    row = cursor.fetchone()  # Affecte une valeur à une variable.
    return sanitize_sql_identifier(row[0]) if row else "roles"  # Retourne une valeur depuis la fonction.


def ensure_roles_table(cursor, table_name):  # Définit la fonction ensure_roles_table.
    table_name = sanitize_sql_identifier(table_name)  # Affecte une valeur à une variable.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
        f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
            id_role INT AUTO_INCREMENT PRIMARY KEY,
            nom VARCHAR(50) NOT NULL,
            id_user INT NULL
        )
        """
    )  # Effectue une opération de traitement des données.


def ensure_users_table(cursor, users_table_name, roles_table_name):  # Définit la fonction ensure_users_table.
    users_table_name = sanitize_sql_identifier(users_table_name)  # Affecte une valeur à une variable.
    roles_table_name = sanitize_sql_identifier(roles_table_name)  # Affecte une valeur à une variable.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
        f"""
        CREATE TABLE IF NOT EXISTS `{users_table_name}` (
            id_user INT AUTO_INCREMENT PRIMARY KEY,
            prenom VARCHAR(50) NOT NULL,
            nom VARCHAR(50) NOT NULL,
            login VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            salt VARCHAR(64) NULL
        )
        """
    )  # Effectue une opération de traitement des données.


def get_password_pepper():  # Définit la fonction get_password_pepper.
    return os.getenv(PASSWORD_PEPPER_ENV, "").strip('"')  # Retourne une valeur depuis la fonction.


def generate_password_salt():  # Définit la fonction generate_password_salt.
    return secrets.token_hex(PASSWORD_SALT_BYTES)  # Retourne une valeur depuis la fonction.


def hash_password(password, salt=None):  # Définit la fonction hash_password.
    if salt is None:  # Teste une condition.
        salt = generate_password_salt()  # Affecte une valeur à une variable.

    pepper = get_password_pepper()  # Affecte une valeur à une variable.
    password_bytes = (password + pepper).encode("utf-8")  # Affecte une valeur à une variable.
    salt_bytes = bytes.fromhex(salt)  # Affecte une valeur à une variable.
    hashed = hashlib.pbkdf2_hmac(  # Affecte une valeur à une variable.
        PASSWORD_HASH_ALGORITHM,  # Effectue une opération de traitement des données.
        password_bytes,  # Effectue une opération de traitement des données.
        salt_bytes,  # Effectue une opération de traitement des données.
        PASSWORD_HASH_ITERATIONS,  # Effectue une opération de traitement des données.
    )  # Effectue une opération de traitement des données.
    return hashed.hex(), salt  # Retourne une valeur depuis la fonction.


def verify_password(password, stored_hash, salt):  # Définit la fonction verify_password.
    if not stored_hash or not salt:  # Teste une condition.
        return False  # Retourne une valeur depuis la fonction.
    hashed_password, _ = hash_password(password, salt)  # Affecte une valeur à une variable.
    return secrets.compare_digest(hashed_password, stored_hash)  # Retourne une valeur depuis la fonction.


def upgrade_legacy_user_password(user_id, password):  # Définit la fonction upgrade_legacy_user_password.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor()  # Affecte une valeur à une variable.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        users_table_name = sanitize_sql_identifier(get_users_table_name(cursor))  # Affecte une valeur à une variable.
        hashed_password, salt = hash_password(password)  # Affecte une valeur à une variable.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"UPDATE `{users_table_name}` SET password = %s, salt = %s WHERE id_user = %s",  # Affecte une valeur à une variable.
            (hashed_password, salt, user_id),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        conn.commit()  # Valide les changements effectués dans la base de données.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def sanitize_sql_identifier(identifier):  # Définit la fonction sanitize_sql_identifier.
    if not isinstance(identifier, str):  # Teste une condition.
        raise ValueError("Invalid SQL identifier")  # Effectue une opération de traitement des données.
    if not re.fullmatch(r"[A-Za-z0-9_]+", identifier):  # Teste une condition.
        raise ValueError("Invalid SQL identifier")  # Effectue une opération de traitement des données.
    return identifier  # Retourne une valeur depuis la fonction.


def ensure_user_management_tables(cursor):  # Définit la fonction ensure_user_management_tables.
    roles_table_name = get_roles_table_name(cursor)  # Affecte une valeur à une variable.
    ensure_roles_table(cursor, roles_table_name)  # Effectue une opération de traitement des données.
    users_table_name = get_users_table_name(cursor)  # Affecte une valeur à une variable.
    ensure_users_table(cursor, users_table_name, roles_table_name)  # Effectue une opération de traitement des données.
    users_columns = get_table_columns(cursor, users_table_name)  # Affecte une valeur à une variable.
    role_columns = get_table_columns(cursor, roles_table_name)  # Affecte une valeur à une variable.

    if "id_role" not in users_columns:  # Teste une condition.
        cursor.execute(f"ALTER TABLE `{users_table_name}` ADD COLUMN id_role INT NULL")  # Exécute une requête SQL avec des paramètres sécurisés.

    if "salt" not in users_columns:  # Teste une condition.
        cursor.execute(f"ALTER TABLE `{users_table_name}` ADD COLUMN salt VARCHAR(64) NULL")  # Exécute une requête SQL avec des paramètres sécurisés.
        users_columns.add("salt")  # Effectue une opération de traitement des données.

    if "password" in users_columns:  # Teste une condition.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"ALTER TABLE `{users_table_name}` MODIFY COLUMN password VARCHAR(255) NOT NULL"  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.

    if "id_user" not in role_columns:  # Teste une condition.
        cursor.execute(f"ALTER TABLE `{roles_table_name}` ADD COLUMN id_user INT NULL")  # Exécute une requête SQL avec des paramètres sécurisés.
        role_columns = get_table_columns(cursor, roles_table_name)  # Affecte une valeur à une variable.

    for role_name in AVAILABLE_ROLES:  # Boucle sur une séquence d éléments.
        get_or_create_role_id(cursor, roles_table_name, role_name, role_columns)  # Effectue une opération de traitement des données.
    return users_table_name, roles_table_name  # Retourne une valeur depuis la fonction.


def get_table_columns(cursor, table_name):  # Définit la fonction get_table_columns.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        (table_name,),  # Effectue une opération de traitement des données.
    )  # Effectue une opération de traitement des données.
    return {row[0] for row in cursor.fetchall()}  # Retourne une valeur depuis la fonction.


def normalize_role_code(role_value):  # Définit la fonction normalize_role_code.
    if not role_value:  # Teste une condition.
        return ""  # Retourne une valeur depuis la fonction.
    return ROLE_VALUE_TO_CODE.get(str(role_value).strip().casefold(), "")  # Retourne une valeur depuis la fonction.


def validate_password_strength(password):  # Définit la fonction validate_password_strength.
    # Politique minimale de complexité appliquée à toute création/modification de compte.
    # Règle minimale demandée pour tous les comptes créés/modifiés depuis l'application.
    if len(password or "") < 12:  # Teste une condition.
        return False, "Le mot de passe doit contenir au moins 12 caractères."  # Retourne une valeur depuis la fonction.
    if not re.search(r"[A-Z]", password):  # Teste une condition.
        return False, "Le mot de passe doit contenir au moins une majuscule."  # Retourne une valeur depuis la fonction.
    if not re.search(r"\d", password):  # Teste une condition.
        return False, "Le mot de passe doit contenir au moins un chiffre."  # Retourne une valeur depuis la fonction.
    if not re.search(r"[^A-Za-z0-9]", password):  # Teste une condition.
        return False, "Le mot de passe doit contenir au moins un caractère spécial."  # Retourne une valeur depuis la fonction.
    return True, ""  # Retourne une valeur depuis la fonction.


def get_role_label(role_value):  # Définit la fonction get_role_label.
    role_code = normalize_role_code(role_value)  # Affecte une valeur à une variable.
    if role_code:  # Teste une condition.
        return AVAILABLE_ROLES[role_code]  # Retourne une valeur depuis la fonction.
    return str(role_value).strip() if role_value else ""  # Retourne une valeur depuis la fonction.


def get_or_create_role_id(cursor, roles_table_name, role_name, role_columns):  # Définit la fonction get_or_create_role_id.
    role_code = normalize_role_code(role_name) or role_name  # Affecte une valeur à une variable.
    role_label = get_role_label(role_code)  # Affecte une valeur à une variable.
    cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
        f"SELECT id_role, nom FROM `{roles_table_name}` WHERE LOWER(nom) IN (%s, %s) ORDER BY id_role ASC LIMIT 1",  # Effectue une opération de traitement des données.
        (role_label.casefold(), str(role_name).strip().casefold()),  # Effectue une opération de traitement des données.
    )  # Effectue une opération de traitement des données.
    row = cursor.fetchone()  # Affecte une valeur à une variable.
    if row:  # Teste une condition.
        if row[1] != role_label:  # Teste une condition.
            cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
                f"UPDATE `{roles_table_name}` SET nom = %s WHERE id_role = %s",  # Affecte une valeur à une variable.
                (role_label, row[0]),  # Effectue une opération de traitement des données.
            )  # Effectue une opération de traitement des données.
        return row[0]  # Retourne une valeur depuis la fonction.

    if "id_user" in role_columns:  # Teste une condition.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"INSERT INTO `{roles_table_name}` (nom, id_user) VALUES (%s, NULL)",  # Effectue une opération de traitement des données.
            (role_label,),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
    else:  # Prend le chemin alternatif si la condition précédente est fausse.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"INSERT INTO `{roles_table_name}` (nom) VALUES (%s)",  # Effectue une opération de traitement des données.
            (role_label,),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
    return cursor.lastrowid  # Retourne une valeur depuis la fonction.


def get_role_by_user_id(cursor, users_table_name, roles_table_name, user_id, user_id_role=None):  # Définit la fonction get_role_by_user_id.
    users_columns = get_table_columns(cursor, users_table_name)  # Affecte une valeur à une variable.
    role_columns = get_table_columns(cursor, roles_table_name)  # Affecte une valeur à une variable.

    if "id_role" in users_columns and user_id_role:  # Teste une condition.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT nom FROM `{roles_table_name}` WHERE id_role = %s LIMIT 1",  # Affecte une valeur à une variable.
            (user_id_role,),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        row = cursor.fetchone()  # Affecte une valeur à une variable.
        if row and row[0]:  # Teste une condition.
            return normalize_role_code(row[0])  # Retourne une valeur depuis la fonction.

    if "id_user" in role_columns:  # Teste une condition.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT nom FROM `{roles_table_name}` WHERE id_user = %s ORDER BY id_role DESC LIMIT 1",  # Affecte une valeur à une variable.
            (user_id,),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        row = cursor.fetchone()  # Affecte une valeur à une variable.
        if row and row[0]:  # Teste une condition.
            return normalize_role_code(row[0])  # Retourne une valeur depuis la fonction.

    return ""  # Retourne une valeur depuis la fonction.


def set_role_for_user(cursor, users_table_name, roles_table_name, user_id, role_name):  # Définit la fonction set_role_for_user.
    users_columns = get_table_columns(cursor, users_table_name)  # Affecte une valeur à une variable.
    role_columns = get_table_columns(cursor, roles_table_name)  # Affecte une valeur à une variable.
    role_code = normalize_role_code(role_name)  # Affecte une valeur à une variable.

    if not role_code:  # Teste une condition.
        return  # Retourne sans valeur.

    if "id_role" in users_columns:  # Teste une condition.
        role_id = get_or_create_role_id(cursor, roles_table_name, role_code, role_columns)  # Affecte une valeur à une variable.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"UPDATE `{users_table_name}` SET id_role = %s WHERE id_user = %s",  # Affecte une valeur à une variable.
            (role_id, user_id),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        return  # Retourne sans valeur.

    if "id_user" in role_columns:  # Teste une condition.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT id_role FROM `{roles_table_name}` WHERE id_user = %s ORDER BY id_role DESC LIMIT 1",  # Affecte une valeur à une variable.
            (user_id,),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        existing = cursor.fetchone()  # Affecte une valeur à une variable.

        if existing:  # Teste une condition.
            cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
                f"UPDATE `{roles_table_name}` SET nom = %s WHERE id_role = %s",  # Affecte une valeur à une variable.
                (get_role_label(role_code), existing[0]),  # Effectue une opération de traitement des données.
            )  # Effectue une opération de traitement des données.
        else:  # Prend le chemin alternatif si la condition précédente est fausse.
            cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
                f"INSERT INTO `{roles_table_name}` (nom, id_user) VALUES (%s, %s)",  # Effectue une opération de traitement des données.
                (get_role_label(role_code), user_id),  # Effectue une opération de traitement des données.
            )  # Effectue une opération de traitement des données.

        return  # Retourne sans valeur.


def fetch_registered_users():  # Définit la fonction fetch_registered_users.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)  # Affecte une valeur à une variable.
        users_columns = get_table_columns(table_cursor, users_table_name)  # Affecte une valeur à une variable.
        select_id_role = ", u.id_role" if "id_role" in users_columns else ""  # Affecte une valeur à une variable.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"""
            SELECT u.id_user, u.prenom, u.nom, u.login{select_id_role}
            FROM `{users_table_name}` u
            ORDER BY u.nom ASC, u.prenom ASC, u.login ASC
            """
        )  # Effectue une opération de traitement des données.
        users = cursor.fetchall()  # Affecte une valeur à une variable.

        result = []  # Affecte une valeur à une variable.
        for user in users:  # Boucle sur une séquence d éléments.
            role_name = get_role_by_user_id(  # Affecte une valeur à une variable.
                table_cursor,  # Effectue une opération de traitement des données.
                users_table_name,  # Effectue une opération de traitement des données.
                roles_table_name,  # Effectue une opération de traitement des données.
                user["id_user"],  # Effectue une opération de traitement des données.
                user.get("id_role") if "id_role" in user else None,  # Effectue une opération de traitement des données.
            ) or "Operat"  # Effectue une opération de traitement des données.
            result.append(  # Effectue une opération de traitement des données.
                {  # Effectue une opération de traitement des données.
                    "nom": user["nom"],  # Effectue une opération de traitement des données.
                    "prenom": user["prenom"],  # Effectue une opération de traitement des données.
                    "identifiant": user["login"],  # Effectue une opération de traitement des données.
                    "mot_de_passe": "",  # Effectue une opération de traitement des données.
                    "role": role_name,  # Effectue une opération de traitement des données.
                    "role_label": get_role_label(role_name),  # Effectue une opération de traitement des données.
                }  # Effectue une opération de traitement des données.
            )  # Effectue une opération de traitement des données.
        return result  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def get_registered_user_for_auth(login):  # Définit la fonction get_registered_user_for_auth.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)  # Affecte une valeur à une variable.
        users_columns = get_table_columns(table_cursor, users_table_name)  # Affecte une valeur à une variable.
        select_id_role = ", u.id_role" if "id_role" in users_columns else ""  # Affecte une valeur à une variable.
        select_salt = ", u.salt" if "salt" in users_columns else ""  # Affecte une valeur à une variable.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"""
            SELECT u.id_user, u.login, u.password{select_id_role}{select_salt}
            FROM `{users_table_name}` u
            WHERE LOWER(u.login) = LOWER(%s)
            LIMIT 1
            """,
            (login,)  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        account = cursor.fetchone()  # Affecte une valeur à une variable.
        if not account:  # Teste une condition.
            return None  # Retourne une valeur depuis la fonction.

        role_name = get_role_by_user_id(  # Affecte une valeur à une variable.
            table_cursor,  # Effectue une opération de traitement des données.
            users_table_name,  # Effectue une opération de traitement des données.
            roles_table_name,  # Effectue une opération de traitement des données.
            account["id_user"],  # Effectue une opération de traitement des données.
            account.get("id_role") if "id_role" in account else None,  # Effectue une opération de traitement des données.
        ) or "Operat"  # Effectue une opération de traitement des données.
        account["role"] = role_name  # Affecte une valeur à une variable.
        return account  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def is_user_registry_empty():  # Définit la fonction is_user_registry_empty.
    # Utilisé pour activer le mode bootstrap uniquement au tout premier démarrage.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor()  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        users_table_name, _ = ensure_user_management_tables(table_cursor)  # Affecte une valeur à une variable.
        cursor.execute(f"SELECT COUNT(*) FROM `{users_table_name}`")  # Exécute une requête SQL avec des paramètres sécurisés.
        row = cursor.fetchone()  # Affecte une valeur à une variable.
        return int(row[0] if row else 0) == 0  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def authenticate_user(username, password):  # Définit la fonction authenticate_user.
    # Authentification standard uniquement via comptes stockés en base.
    # Le couple bootstrap Admin/administrator n'est plus accepté ici.
    account = get_registered_user_for_auth(username)  # Affecte une valeur à une variable.
    if not account:  # Teste une condition.
        return None  # Retourne une valeur depuis la fonction.

    if account.get("salt"):  # Teste une condition.
        if not verify_password(password, account["password"], account["salt"]):  # Teste une condition.
            return None  # Retourne une valeur depuis la fonction.
    else:  # Prend le chemin alternatif si la condition précédente est fausse.
        if account["password"] != password:  # Teste une condition.
            return None  # Retourne une valeur depuis la fonction.
        upgrade_legacy_user_password(account["id_user"], password)  # Effectue une opération de traitement des données.

    role = normalize_role_code(account.get("role") or "Operat")  # Affecte une valeur à une variable.
    return role if role in AVAILABLE_ROLES else None  # Retourne une valeur depuis la fonction.


def create_registered_user(nom, prenom, identifiant, password, role):  # Définit la fonction create_registered_user.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        role_code = normalize_role_code(role)  # Affecte une valeur à une variable.
        if not role_code:  # Teste une condition.
            return False, "Rôle invalide."  # Retourne une valeur depuis la fonction.

        # Contrôle serveur obligatoire: empêche de contourner la validation HTML du formulaire.
        password_ok, password_message = validate_password_strength(password)  # Affecte une valeur à une variable.
        if not password_ok:  # Teste une condition.
            return False, password_message  # Retourne une valeur depuis la fonction.

        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)  # Affecte une valeur à une variable.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT id_user FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) LIMIT 1",  # Affecte une valeur à une variable.
            (identifiant,)  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        if cursor.fetchone() or identifiant.casefold() == BOOTSTRAP_ADMIN_LOGIN.casefold():  # Teste une condition.
            return False, "Cet identifiant existe déjà."  # Retourne une valeur depuis la fonction.

        hashed_password, salt = hash_password(password)  # Affecte une valeur à une variable.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"""
            INSERT INTO `{users_table_name}` (prenom, nom, login, password, salt)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (prenom, nom, identifiant, hashed_password, salt)  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        user_id = cursor.lastrowid  # Affecte une valeur à une variable.
        set_role_for_user(table_cursor, users_table_name, roles_table_name, user_id, role_code)  # Effectue une opération de traitement des données.
        conn.commit()  # Valide les changements effectués dans la base de données.
        return True, "Utilisateur créé avec succès !"  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def update_registered_user_role(identifiant, role):  # Définit la fonction update_registered_user_role.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        role_code = normalize_role_code(role)  # Affecte une valeur à une variable.
        if not role_code:  # Teste une condition.
            return False, "Rôle invalide."  # Retourne une valeur depuis la fonction.

        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)  # Affecte une valeur à une variable.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT id_user FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) LIMIT 1",  # Affecte une valeur à une variable.
            (identifiant,),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        user = cursor.fetchone()  # Affecte une valeur à une variable.
        if not user:  # Teste une condition.
            return False, "Utilisateur introuvable."  # Retourne une valeur depuis la fonction.

        set_role_for_user(table_cursor, users_table_name, roles_table_name, user["id_user"], role_code)  # Effectue une opération de traitement des données.
        conn.commit()  # Valide les changements effectués dans la base de données.
        return True, "Rôle mis à jour avec succès."  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def update_registered_user(original_identifiant, nom, prenom, identifiant, password, role):  # Définit la fonction update_registered_user.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        role_code = normalize_role_code(role)  # Affecte une valeur à une variable.
        if not role_code:  # Teste une condition.
            return False, "Rôle invalide."  # Retourne une valeur depuis la fonction.

        # On réapplique la même règle lors de la modification pour garder une politique homogène.
        password_ok, password_message = validate_password_strength(password)  # Affecte une valeur à une variable.
        if not password_ok:  # Teste une condition.
            return False, password_message  # Retourne une valeur depuis la fonction.

        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)  # Affecte une valeur à une variable.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT id_user FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) LIMIT 1",  # Affecte une valeur à une variable.
            (original_identifiant,),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        user = cursor.fetchone()  # Affecte une valeur à une variable.
        if not user:  # Teste une condition.
            return False, "Utilisateur introuvable."  # Retourne une valeur depuis la fonction.

        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT id_user FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) AND id_user <> %s LIMIT 1",  # Affecte une valeur à une variable.
            (identifiant, user["id_user"]),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        if cursor.fetchone() or identifiant.casefold() == BOOTSTRAP_ADMIN_LOGIN.casefold():  # Teste une condition.
            return False, "Cet identifiant existe déjà."  # Retourne une valeur depuis la fonction.

        hashed_password, salt = hash_password(password)  # Affecte une valeur à une variable.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"""
            UPDATE `{users_table_name}`
            SET prenom = %s, nom = %s, login = %s, password = %s, salt = %s
            WHERE id_user = %s
            """,
            (prenom, nom, identifiant, hashed_password, salt, user["id_user"]),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        set_role_for_user(table_cursor, users_table_name, roles_table_name, user["id_user"], role_code)  # Effectue une opération de traitement des données.
        conn.commit()  # Valide les changements effectués dans la base de données.
        return True, "Utilisateur mis à jour avec succès."  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.


def delete_registered_user(identifiant):  # Définit la fonction delete_registered_user.
    conn = get_db_connection()  # Affecte une valeur à une variable.
    cursor = conn.cursor(dictionary=True)  # Affecte une valeur à une variable.
    table_cursor = conn.cursor()  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        users_table_name, roles_table_name = ensure_user_management_tables(table_cursor)  # Affecte une valeur à une variable.
        users_columns = get_table_columns(table_cursor, users_table_name)  # Affecte une valeur à une variable.
        role_columns = get_table_columns(table_cursor, roles_table_name)  # Affecte une valeur à une variable.

        select_id_role = ", id_role" if "id_role" in users_columns else ""  # Affecte une valeur à une variable.
        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"SELECT id_user{select_id_role} FROM `{users_table_name}` WHERE LOWER(login) = LOWER(%s) LIMIT 1",  # Affecte une valeur à une variable.
            (identifiant,),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        user = cursor.fetchone()  # Affecte une valeur à une variable.
        if not user:  # Teste une condition.
            return False, "Utilisateur introuvable."  # Retourne une valeur depuis la fonction.

        if identifiant.casefold() == BOOTSTRAP_ADMIN_LOGIN.casefold():  # Teste une condition.
            return False, "Suppression du compte bootstrap interdite."  # Retourne une valeur depuis la fonction.

        if "id_user" in role_columns:  # Teste une condition.
            table_cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
                f"DELETE FROM `{roles_table_name}` WHERE id_user = %s",  # Affecte une valeur à une variable.
                (user["id_user"],),  # Effectue une opération de traitement des données.
            )  # Effectue une opération de traitement des données.

        cursor.execute(  # Exécute une requête SQL avec des paramètres sécurisés.
            f"DELETE FROM `{users_table_name}` WHERE id_user = %s",  # Affecte une valeur à une variable.
            (user["id_user"],),  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.
        conn.commit()  # Valide les changements effectués dans la base de données.
        return True, "Utilisateur supprimé avec succès."  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        table_cursor.close()  # Ferme le curseur SQL.
        cursor.close()  # Ferme le curseur SQL.
        conn.close()  # Ferme la connexion à la base de données.
 
@app.route("/", methods=["GET", "POST"])  # Déclare un décorateur ou une route Flask.
def login():  # Définit la fonction login.
    error = None  # Affecte une valeur à une variable.
    if request.method == "POST":  # Teste une condition.
        user = (request.form.get("username") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
        password = (request.form.get("password") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.

        # Flux de bootstrap: si aucun utilisateur n'existe encore,
        # le couple Admin/administrator ouvre la création du premier compte admin.
        # Dès qu'un utilisateur existe, ces identifiants sont rejetés.
        if user == BOOTSTRAP_ADMIN_LOGIN and password == BOOTSTRAP_ADMIN_PASSWORD:  # Teste une condition.
            try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
                if is_user_registry_empty():  # Teste une condition.
                    session.clear()  # Travaille avec la session utilisateur Flask.
                    # Jeton de session temporaire pour autoriser la page /bootstrap-admin.
                    session["bootstrap_admin_setup_allowed"] = True  # Affecte une valeur à une variable.
                    return redirect(url_for("bootstrap_admin_setup"))  # Retourne une valeur depuis la fonction.
                error = "Identifiants incorrects"  # Affecte une valeur à une variable.
            except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
                error = str(exc)  # Affecte une valeur à une variable.

        role = authenticate_user(user, password)  # Affecte une valeur à une variable.
 
        # 1. Vérification avec identifiants hachés
        if role:  # Teste une condition.
            
            session["logged_in"] = True  # Affecte une valeur à une variable.
            session["role"] = role  # Affecte une valeur à une variable.
            # 2. Redirection selon le rôle
            if role == "Respo":  # Teste une condition.
                return redirect(url_for("dashboard_op"))  # Retourne une valeur depuis la fonction.
            
            elif role == "Integ":  # Teste une autre condition si la précédente est fausse.
                return redirect(url_for("dashboard_op"))  # Retourne une valeur depuis la fonction.
            
            elif role == "Operat":  # Teste une autre condition si la précédente est fausse.
                return redirect(url_for("dashboard_op"))  # Retourne une valeur depuis la fonction.

            elif role == "Admin":  # Teste une autre condition si la précédente est fausse.
                return redirect(url_for("dashboard_op"))  # Retourne une valeur depuis la fonction.
        
        else:  # Prend le chemin alternatif si la condition précédente est fausse.
            error = "Identifiants incorrects"  # Affecte une valeur à une variable.
 
    # Rafraîchir immédiatement le statut OPC UA (au lieu de relire juste le cache statique)
    # Cela évite que le badge reste "Hors Ligne" longtemps après l'affichage de la page
    threshold_alert_message = None  # Affecte une valeur à une variable.
    threshold_alert_details = None  # Affecte une valeur à une variable.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        status = get_opcua_status_details()  # Affecte une valeur à une variable.
        _last_opcua_status["ok"] = status.get("ok")  # Affecte une valeur à une variable.
        _last_opcua_status["error"] = status.get("error")  # Affecte une valeur à une variable.
        _last_opcua_status["error_code"] = status.get("error_code")  # Affecte une valeur à une variable.

        if _last_opcua_status["ok"]:  # Teste une condition.
            thresholds_result = get_alert_thresholds_details()  # Affecte une valeur à une variable.
            alert_thresholds = None  # Affecte une valeur à une variable.
            if thresholds_result.get("ok") and thresholds_result.get("data"):  # Teste une condition.
                alert_thresholds = thresholds_result["data"]  # Affecte une valeur à une variable.
            else:  # Prend le chemin alternatif si la lecture OPC UA échoue.
                db_values = recuperer_derniers_seuils_alerte()  # Affecte une valeur à une variable.
                if db_values:  # Teste une condition.
                    alert_thresholds = {
                        "seuil_cpu": float(db_values["seuil_charge"] if db_values["seuil_charge"] is not None else db_values["charge"]),
                        "seuil_ram": float(db_values["seuil_ram"] if db_values["seuil_ram"] is not None else db_values["ram"]),
                        "seuil_temp": float(db_values["seuil_temperature"] if db_values["seuil_temperature"] is not None else db_values["temperature"]),
                    }  # Effectue une opération de traitement.

            if alert_thresholds:  # Teste une condition.
                automates, _ = _get_cached_automate_variables()  # Affecte une valeur à une variable.
                automate_values = (automates or {}).get("data") or {}  # Affecte une valeur à une variable.
                statuses = _build_alert_statuses(alert_thresholds, automate_values)  # Affecte une valeur à une variable.
                triggered = [  # Affecte une valeur à une variable.
                    key for key, state in statuses.items() if state == "Déclenchée"
                ]  # Effectue une opération de traitement.
                if triggered:  # Teste une condition.
                    label_map = {
                        "seuil_cpu": "CPU",  # Affecte une valeur à une variable.
                        "seuil_ram": "RAM",  # Affecte une valeur à une variable.
                        "seuil_temp": "Température",  # Affecte une valeur à une variable.
                    }  # Effectue une opération de traitement.
                    threshold_alert_message = "Alerte seuil : " + ", ".join(
                        label_map.get(key, key) for key in triggered
                    )  # Affecte une valeur à une variable.
                    threshold_alert_details = []  # Affecte une valeur à une variable.
                    current_map = {
                        "seuil_cpu": "cpu_load",  # Affecte une valeur à une variable.
                        "seuil_ram": "ram_usage",  # Affecte une valeur à une variable.
                        "seuil_temp": "temp_c",  # Affecte une valeur à une variable.
                    }  # Effectue une opération de traitement.
                    for key in triggered:  # Boucle sur une séquence d’éléments.
                        current_value = automate_values.get(current_map.get(key, ""), "?")
                        threshold_value = alert_thresholds.get(key, "?")
                        threshold_alert_details.append(
                            f"{label_map.get(key, key)} : {current_value} / {threshold_value}"
                        )  # Effectue une opération de traitement.
    except Exception as exc:  # Capture une exception et exécute un traitement adapté.
        _last_opcua_status["ok"] = False  # Affecte une valeur à une variable.
        _last_opcua_status["error"] = str(exc)  # Affecte une valeur à une variable.
        _last_opcua_status["error_code"] = type(exc).__name__  # Affecte une valeur à une variable.

    return render_template(  # Retourne une valeur depuis la fonction.
        "login.html",  # Effectue une opération de traitement des données.
        error=error,  # Affecte une valeur à une variable.
        automate_ok=_last_opcua_status["ok"],  # Affecte une valeur à une variable.
        automate_error=_last_opcua_status["error"],  # Affecte une valeur à une variable.
        automate_error_code=_last_opcua_status["error_code"],  # Affecte une valeur à une variable.
        threshold_alert_message=threshold_alert_message,  # Affecte une valeur à une variable.
        threshold_alert_details=threshold_alert_details,  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement des données.


@app.route("/bootstrap-admin", methods=["GET", "POST"])  # Déclare un décorateur ou une route Flask.
def bootstrap_admin_setup():  # Définit la fonction bootstrap_admin_setup.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        bootstrap_mode = is_user_registry_empty()  # Affecte une valeur à une variable.
    except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
        return render_template("bootstrap_admin.html", error=str(exc))  # Retourne une valeur depuis la fonction.

    if not bootstrap_mode:  # Teste une condition.
        session.pop("bootstrap_admin_setup_allowed", None)  # Travaille avec la session utilisateur Flask.
        return redirect(url_for("login"))  # Retourne une valeur depuis la fonction.

    # Protection: impossible d'accéder à la création du premier admin
    # sans être passé par le challenge bootstrap sur la page login.
    if not session.get("bootstrap_admin_setup_allowed"):  # Teste une condition.
        return redirect(url_for("login"))  # Retourne une valeur depuis la fonction.

    error = None  # Affecte une valeur à une variable.
    if request.method == "POST":  # Teste une condition.
        nom = (request.form.get("nom") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
        prenom = (request.form.get("prenom") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
        identifiant = (request.form.get("identifiant") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
        password = (request.form.get("mot_de_passe") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.

        if not nom or not prenom or not identifiant or not password:  # Teste une condition.
            error = "Tous les champs sont obligatoires."  # Affecte une valeur à une variable.
        else:  # Prend le chemin alternatif si la condition précédente est fausse.
            try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
                # Le premier entrant est forcé au rôle Admin.
                created, message = create_registered_user(nom, prenom, identifiant, password, "Admin")  # Affecte une valeur à une variable.
                if not created:  # Teste une condition.
                    error = message  # Affecte une valeur à une variable.
                else:  # Prend le chemin alternatif si la condition précédente est fausse.
                    session.pop("bootstrap_admin_setup_allowed", None)  # Travaille avec la session utilisateur Flask.
                    session["logged_in"] = True  # Affecte une valeur à une variable.
                    session["role"] = "Admin"  # Affecte une valeur à une variable.
                    return redirect(url_for("dashboard_op"))  # Retourne une valeur depuis la fonction.
            except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
                error = str(exc)  # Affecte une valeur à une variable.

    return render_template("bootstrap_admin.html", error=error)  # Retourne une valeur depuis la fonction.


@app.route("/logout", methods=["POST"])  # Déclare un décorateur ou une route Flask.
def logout():  # Définit la fonction logout.
    session.clear()  # Travaille avec la session utilisateur Flask.
    close_persistent_client()  # Effectue une opération de traitement des données.
    return redirect(url_for("login"))  # Retourne une valeur depuis la fonction.
 
@app.route("/dashboard")  # Déclare un décorateur ou une route Flask.
def dashboard_op():  # Définit la fonction dashboard_op.
    if not session.get("logged_in"):  # Teste une condition.
        return redirect(url_for("login"))  # Retourne une valeur depuis la fonction.
    interventions = recuperer_interventions()  # Affecte une valeur à une variable.
    
    # Rafraîchir immédiatement le statut OPC UA au sens lié (évite un badge "Hors Ligne" statique)
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        status = get_opcua_status_details()  # Affecte une valeur à une variable.
        _last_opcua_status["ok"] = status.get("ok")  # Affecte une valeur à une variable.
        _last_opcua_status["error"] = status.get("error")  # Affecte une valeur à une variable.
        _last_opcua_status["error_code"] = status.get("error_code")  # Affecte une valeur à une variable.
    except Exception as exc:  # Capture une exception et exécute un traitement adapté.
        _last_opcua_status["ok"] = False  # Affecte une valeur à une variable.
        _last_opcua_status["error"] = str(exc)  # Affecte une valeur à une variable.
        _last_opcua_status["error_code"] = type(exc).__name__  # Affecte une valeur à une variable.
    
    return render_template(  # Retourne une valeur depuis la fonction.
        "dashboard_operateur.html",  # Effectue une opération de traitement des données.
        interventions=interventions,  # Affecte une valeur à une variable.
        role=session.get("role"),  # Travaille avec la session utilisateur Flask.
        registered_users=fetch_registered_users(),  # Affecte une valeur à une variable.
        available_roles=AVAILABLE_ROLES,  # Affecte une valeur à une variable.
        automate_ok=_last_opcua_status["ok"],  # Affecte une valeur à une variable.
        automate_error=_last_opcua_status["error"],  # Affecte une valeur à une variable.
        automate_error_code=_last_opcua_status["error_code"],  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement des données.
 
 
@app.route("/planifier_maintenance", methods=["POST"])  # Déclare un décorateur ou une route Flask.
def planifier_maintenance():  # Définit la fonction planifier_maintenance.
    if not can_manage_maintenance():  # Teste une condition.
        return jsonify({"success": False, "message": "Accès refusé."}), 403  # Retourne une valeur depuis la fonction.

    date = (request.form.get("date_maintenance") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    commentaire = (request.form.get("commentaire") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
 
    if not date or not commentaire:  # Teste une condition.
        return jsonify({"success": False, "message": "Date et commentaire obligatoires."}), 400  # Retourne une valeur depuis la fonction.
 
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        horodatage = parse_horodatage(date)  # Affecte une valeur à une variable.
        enregistrer_intervention(commentaire, horodatage)  # Effectue une opération de traitement des données.
    except ValueError:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": "Format de date invalide."}), 400  # Retourne une valeur depuis la fonction.
    except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": str(exc)}), 500  # Retourne une valeur depuis la fonction.
 
    return jsonify({"success": True})  # Retourne une valeur depuis la fonction.


@app.route("/modifier_maintenance", methods=["POST"])  # Déclare un décorateur ou une route Flask.
def modifier_maintenance():  # Définit la fonction modifier_maintenance.
    if not can_manage_maintenance():  # Teste une condition.
        return jsonify({"success": False, "message": "Accès refusé."}), 403  # Retourne une valeur depuis la fonction.

    id_inter = (request.form.get("id_inter") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    date = (request.form.get("date_maintenance") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    commentaire = (request.form.get("commentaire") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.

    if not id_inter or not date or not commentaire:  # Teste une condition.
        return jsonify({"success": False, "message": "ID, date et commentaire obligatoires."}), 400  # Retourne une valeur depuis la fonction.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        id_inter_int = int(id_inter)  # Affecte une valeur à une variable.
    except ValueError:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": "ID intervention invalide."}), 400  # Retourne une valeur depuis la fonction.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        horodatage = parse_horodatage(date)  # Affecte une valeur à une variable.
        updated = modifier_intervention(id_inter_int, commentaire, horodatage)  # Affecte une valeur à une variable.
        if not updated:  # Teste une condition.
            return jsonify({"success": False, "message": "Intervention introuvable."}), 404  # Retourne une valeur depuis la fonction.
    except ValueError:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": "Format de date invalide."}), 400  # Retourne une valeur depuis la fonction.
    except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": str(exc)}), 500  # Retourne une valeur depuis la fonction.

    return jsonify({"success": True})  # Retourne une valeur depuis la fonction.


@app.route("/supprimer_maintenance", methods=["POST"])  # Déclare un décorateur ou une route Flask.
def supprimer_maintenance():  # Définit la fonction supprimer_maintenance.
    if not can_manage_maintenance():  # Teste une condition.
        return jsonify({"success": False, "message": "Accès refusé."}), 403  # Retourne une valeur depuis la fonction.

    id_inter = (request.form.get("id_inter") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    if not id_inter:  # Teste une condition.
        return jsonify({"success": False, "message": "ID intervention obligatoire."}), 400  # Retourne une valeur depuis la fonction.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        id_inter_int = int(id_inter)  # Affecte une valeur à une variable.
    except ValueError:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": "ID intervention invalide."}), 400  # Retourne une valeur depuis la fonction.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        deleted = supprimer_intervention(id_inter_int)  # Affecte une valeur à une variable.
        if not deleted:  # Teste une condition.
            return jsonify({"success": False, "message": "Intervention introuvable."}), 404  # Retourne une valeur depuis la fonction.
    except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": str(exc)}), 500  # Retourne une valeur depuis la fonction.

    return jsonify({"success": True})  # Retourne une valeur depuis la fonction.
 
@app.route("/get_interventions")  # Déclare un décorateur ou une route Flask.
def get_interventions_json():  # Définit la fonction get_interventions_json.
    if not session.get("logged_in"):  # Teste une condition.
        return jsonify({"success": False, "message": "Non authentifié."}), 401  # Retourne une valeur depuis la fonction.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        interventions = recuperer_interventions()  # Affecte une valeur à une variable.
    except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": str(exc)}), 500  # Retourne une valeur depuis la fonction.
    result = [  # Affecte une valeur à une variable.
        {  # Effectue une opération de traitement des données.
            "id_inter": row["id_inter"],  # Effectue une opération de traitement des données.
            "nom": row["nom"],  # Effectue une opération de traitement des données.
            "horodatage": row["horodatage"].strftime("%Y-%m-%d") if row["horodatage"] else "",  # Effectue une opération de traitement des données.
        }  # Effectue une opération de traitement des données.
        for row in interventions  # Boucle sur une séquence d éléments.
    ]  # Effectue une opération de traitement des données.
    return jsonify({"success": True, "interventions": result})  # Retourne une valeur depuis la fonction.


# Statut OPC UA en cache — mis à jour à chaque lecture de variable (cpu-temperature, suivi-consommation).
_last_opcua_status = {"ok": None, "error": None, "error_code": None}  # Affecte une valeur à une variable.


# ============================================================================
# CACHE OPC UA CÔTÉ SERVEUR — Réduit les appels répétés à l'automate
# ============================================================================
# TTL en secondes pour le cache OPC UA (défaut: 5s).
# Augmente si tu veux moins de requêtes OPC UA mais acceptes des données plus "vieilles".
OPCUA_CACHE_TTL = 10  # Affecte une valeur à une variable.

_opcua_variables_cache = {  # Affecte une valeur à une variable.
    "data": None,  # Effectue une opération de traitement des données.
    "timestamp": 0,  # Effectue une opération de traitement des données.
}  # Effectue une opération de traitement des données.


def _get_cached_automate_variables(force_refresh=False):  # Définit la fonction _get_cached_automate_variables.
    """
    Retourne les variables OPC UA depuis le cache si encore valide (< TTL),
    sinon refait une requête OPC UA et met à jour le cache.
    Réduit drastiquement les temps de chargement des graphiques.
    """
    global _opcua_variables_cache  # Effectue une opération de traitement des données.
    
    now = time.time()  # Affecte une valeur à une variable.
    age = now - _opcua_variables_cache["timestamp"]  # Affecte une valeur à une variable.
    
    # Si cache valide et pas de force_refresh, retourner le cache
    if not force_refresh and age < OPCUA_CACHE_TTL and _opcua_variables_cache["data"] is not None:  # Teste une condition.
        return _opcua_variables_cache["data"], False  # (données, was_refreshed)
    
    # Sinon, refaire la requête OPC UA
    result = get_automate_variables_details()  # Affecte une valeur à une variable.
    _opcua_variables_cache["data"] = result  # Affecte une valeur à une variable.
    _opcua_variables_cache["timestamp"] = now  # Affecte une valeur à une variable.
    
    return result, True  # (données, was_refreshed=True)


def _build_alert_statuses(seuils, automate_values):  # Définit la fonction _build_alert_statuses.
    """Construit le statut d'alerte à partir des valeurs live de l'automate."""
    def _status(current_value, threshold_value):  # Définit la fonction _status.
        if current_value is None or threshold_value is None:  # Teste une condition.
            return "Inconnu"  # Retourne une valeur depuis la fonction.
        return "Déclenchée" if float(current_value) >= float(threshold_value) else "Normale"  # Retourne une valeur depuis la fonction.

    return {  # Retourne une valeur depuis la fonction.
        "seuil_cpu": _status(automate_values.get("cpu_load"), seuils.get("seuil_cpu")),  # Effectue une opération de traitement des données.
        "seuil_ram": _status(automate_values.get("ram_usage"), seuils.get("seuil_ram")),  # Effectue une opération de traitement des données.
        "seuil_temp": _status(automate_values.get("temp_c"), seuils.get("seuil_temp")),  # Effectue une opération de traitement des données.
    }  # Effectue une opération de traitement des données.


# ============================================================================
@app.route("/api/automate-status")  # Déclare un décorateur ou une route Flask.
def api_automate_status():  # Définit la fonction api_automate_status.
    """Retourne le dernier statut OPC UA connu sans déclencher de connexion supplémentaire."""
    return jsonify(_last_opcua_status)  # Retourne une valeur depuis la fonction.


@app.route("/api/alert-thresholds", methods=["GET"])  # Déclare un décorateur ou une route Flask.
def api_get_alert_thresholds():  # Définit la fonction api_get_alert_thresholds.
    if not session.get("logged_in"):  # Teste une condition.
        return jsonify({"ok": False, "error": "Non authentifié."}), 401  # Retourne une valeur depuis la fonction.

    # Source prioritaire: valeurs courantes lues sur l'automate.
    opcua_result = get_alert_thresholds_details()  # Affecte une valeur à une variable.
    if opcua_result.get("ok") and opcua_result.get("data"):  # Teste une condition.
        values = opcua_result["data"]  # Affecte une valeur à une variable.
        payload = {  # Affecte une valeur à une variable.
            "seuil_cpu": float(values.get("seuil_cpu", 0)),  # Effectue une opération de traitement des données.
            "seuil_ram": float(values.get("seuil_ram", 0)),  # Effectue une opération de traitement des données.
            "seuil_temp": float(values.get("seuil_temp", 0)),  # Effectue une opération de traitement des données.
        }  # Effectue une opération de traitement des données.
        automate_values, _ = _get_cached_automate_variables()  # Affecte une valeur à une variable.
        statuses = _build_alert_statuses(payload, (automate_values or {}).get("data") or {})  # Affecte une valeur à une variable.
        _last_opcua_status["ok"] = True  # Affecte une valeur à une variable.
        _last_opcua_status["error"] = None  # Affecte une valeur à une variable.
        _last_opcua_status["error_code"] = None  # Affecte une valeur à une variable.
        try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
            # On garde aussi un snapshot DB pour afficher des valeurs en fallback.
            enregistrer_seuils_alerte(  # Effectue une opération de traitement des données.
                charge=payload["seuil_cpu"],  # Affecte une valeur à une variable.
                ram=payload["seuil_ram"],  # Affecte une valeur à une variable.
                temperature=payload["seuil_temp"],  # Affecte une valeur à une variable.
            )  # Effectue une opération de traitement des données.
        except Exception:  # Capture une exception et exécute un traitement adapté.
            pass  # Ne fait rien ici, c’est une instruction vide.
        return jsonify({"ok": True, "data": payload, "statuses": statuses, "source": "opcua"})  # Retourne une valeur depuis la fonction.

    # Fallback: dernières valeurs connues en base si l'OPC UA est indisponible.
    db_values = recuperer_derniers_seuils_alerte()  # Affecte une valeur à une variable.
    if db_values:  # Teste une condition.
        payload = {  # Affecte une valeur à une variable.
            "seuil_cpu": float(db_values["seuil_charge"] if db_values["seuil_charge"] is not None else db_values["charge"]),  # Effectue une opération de traitement des données.
            "seuil_ram": float(db_values["seuil_ram"] if db_values["seuil_ram"] is not None else db_values["ram"]),  # Effectue une opération de traitement des données.
            "seuil_temp": float(db_values["seuil_temperature"] if db_values["seuil_temperature"] is not None else db_values["temperature"]),  # Effectue une opération de traitement des données.
        }  # Effectue une opération de traitement des données.
        automate_values, _ = _get_cached_automate_variables()  # Affecte une valeur à une variable.
        statuses = _build_alert_statuses(payload, (automate_values or {}).get("data") or {})  # Affecte une valeur à une variable.
        return jsonify(  # Retourne une valeur depuis la fonction.
            {  # Effectue une opération de traitement des données.
                "ok": True,  # Effectue une opération de traitement des données.
                "data": payload,  # Effectue une opération de traitement des données.
                "statuses": statuses,  # Effectue une opération de traitement des données.
                "source": "database",  # Effectue une opération de traitement des données.
                "opcua_error": opcua_result.get("error"),  # Effectue une opération de traitement des données.
                "opcua_error_code": opcua_result.get("error_code"),  # Effectue une opération de traitement des données.
            }  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.

    return jsonify(  # Retourne une valeur depuis la fonction.
        {  # Effectue une opération de traitement des données.
            "ok": False,  # Effectue une opération de traitement des données.
            "error": opcua_result.get("error") or "Aucun seuil disponible",  # Effectue une opération de traitement des données.
            "error_code": opcua_result.get("error_code"),  # Effectue une opération de traitement des données.
        }  # Effectue une opération de traitement des données.
    ), 404  # Effectue une opération de traitement des données.


@app.route("/api/alert-thresholds", methods=["POST"])  # Déclare un décorateur ou une route Flask.
def api_set_alert_thresholds():  # Définit la fonction api_set_alert_thresholds.
    if not session.get("logged_in"):  # Teste une condition.
        return jsonify({"ok": False, "error": "Non authentifié."}), 401  # Retourne une valeur depuis la fonction.

    if session.get("role") not in ("Integ", "Admin"):  # Teste une condition.
        return jsonify({"ok": False, "error": "Accès refusé."}), 403  # Retourne une valeur depuis la fonction.

    payload = request.get_json(silent=True) or request.form  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        seuil_cpu = float((payload.get("seuil_cpu") or "").strip() if isinstance(payload.get("seuil_cpu"), str) else payload.get("seuil_cpu"))  # Affecte une valeur à une variable.
        seuil_ram = float((payload.get("seuil_ram") or "").strip() if isinstance(payload.get("seuil_ram"), str) else payload.get("seuil_ram"))  # Affecte une valeur à une variable.
        seuil_temp = float((payload.get("seuil_temp") or "").strip() if isinstance(payload.get("seuil_temp"), str) else payload.get("seuil_temp"))  # Affecte une valeur à une variable.
    except (TypeError, ValueError):  # Capture une exception et exécute un traitement adapté.
        return jsonify({"ok": False, "error": "Valeurs seuil invalides."}), 400  # Retourne une valeur depuis la fonction.

    # Ordre volontaire: écrire d'abord sur l'automate, puis persister en base.
    write_result = set_alert_thresholds_details(seuil_ram=seuil_ram, seuil_cpu=seuil_cpu, seuil_temp=seuil_temp)  # Affecte une valeur à une variable.
    if not write_result.get("ok"):  # Teste une condition.
        _last_opcua_status["ok"] = False  # Affecte une valeur à une variable.
        _last_opcua_status["error"] = write_result.get("error")  # Affecte une valeur à une variable.
        _last_opcua_status["error_code"] = write_result.get("error_code")  # Affecte une valeur à une variable.
        return jsonify({"ok": False, "error": write_result.get("error"), "error_code": write_result.get("error_code")}), 502  # Retourne une valeur depuis la fonction.

    _last_opcua_status["ok"] = True  # Affecte une valeur à une variable.
    _last_opcua_status["error"] = None  # Affecte une valeur à une variable.
    _last_opcua_status["error_code"] = None  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        enregistrer_seuils_alerte(charge=seuil_cpu, ram=seuil_ram, temperature=seuil_temp)  # Affecte une valeur à une variable.
    except Exception as exc:  # Capture une exception et exécute un traitement adapté.
        return jsonify(  # Retourne une valeur depuis la fonction.
            {  # Effectue une opération de traitement des données.
                "ok": True,  # Effectue une opération de traitement des données.
                "data": {  # Effectue une opération de traitement des données.
                    "seuil_cpu": seuil_cpu,  # Effectue une opération de traitement des données.
                    "seuil_ram": seuil_ram,  # Effectue une opération de traitement des données.
                    "seuil_temp": seuil_temp,  # Effectue une opération de traitement des données.
                },  # Effectue une opération de traitement des données.
                "warning": f"Seuils ecrits sur automate mais sauvegarde DB echouee: {exc}",  # Effectue une opération de traitement des données.
            }  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.

    return jsonify(  # Retourne une valeur depuis la fonction.
        {  # Effectue une opération de traitement des données.
            "ok": True,  # Effectue une opération de traitement des données.
            "data": {  # Effectue une opération de traitement des données.
                "seuil_cpu": seuil_cpu,  # Effectue une opération de traitement des données.
                "seuil_ram": seuil_ram,  # Effectue une opération de traitement des données.
                "seuil_temp": seuil_temp,  # Effectue une opération de traitement des données.
            },  # Effectue une opération de traitement des données.
        }  # Effectue une opération de traitement des données.
    )  # Effectue une opération de traitement des données.


@app.route("/api/cpu-temperature")  # Déclare un décorateur ou une route Flask.
def api_cpu_temperature():  # Définit la fonction api_cpu_temperature.
    """Affiche la dernière valeur de base et met à jour la base via OPC UA quand possible."""
    opcua_error = None  # Affecte une valeur à une variable.
    opcua_error_code = None  # Affecte une valeur à une variable.
    live_data = None  # Affecte une valeur à une variable.

    # 1) Tenter une lecture OPC UA pour enrichir la base, sans bloquer l'affichage.
    # OPTIMISATION: utiliser le cache OPC UA côté serveur au lieu de refaire une requête à chaque fois.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        variables, was_refreshed = _get_cached_automate_variables()  # Affecte une valeur à une variable.
        if variables.get("ok") and variables.get("data"):  # Teste une condition.
            data = variables["data"]  # Affecte une valeur à une variable.
            charge = data.get("cpu_load", 0)  # Affecte une valeur à une variable.
            ram = data.get("ram_usage", 0)  # Affecte une valeur à une variable.
            temp = data.get("temp_c", 0)  # Affecte une valeur à une variable.
            live_data = {  # Affecte une valeur à une variable.
                "charge": charge,  # Effectue une opération de traitement des données.
                "ram": ram,  # Effectue une opération de traitement des données.
                "temperature": temp,  # Effectue une opération de traitement des données.
                "horodatage": datetime.utcnow().isoformat() + "Z",  # Effectue une opération de traitement des données.
            }  # Effectue une opération de traitement des données.
            _last_opcua_status["ok"] = True  # Affecte une valeur à une variable.
            _last_opcua_status["error"] = None  # Affecte une valeur à une variable.
            _last_opcua_status["error_code"] = None  # Affecte une valeur à une variable.
            # Enregistrer en base que si on vient de refaire la requête OPC UA
            # (évite d'écrire en DB à chaque requête web)
            if was_refreshed:  # Teste une condition.
                try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
                    enregistrer_temperature(charge, ram, temp)  # Effectue une opération de traitement des données.
                except Exception:  # Capture une exception et exécute un traitement adapté.
                    # Si l'insertion échoue, on continue quand meme avec la lecture DB/fallback live.
                    pass  # Ne fait rien ici, c’est une instruction vide.
        else:  # Prend le chemin alternatif si la condition précédente est fausse.
            opcua_error = (variables or {}).get("error", "Lecture OPC UA impossible")  # Affecte une valeur à une variable.
            opcua_error_code = (variables or {}).get("error_code")  # Affecte une valeur à une variable.
            _last_opcua_status["ok"] = False  # Affecte une valeur à une variable.
            _last_opcua_status["error"] = opcua_error  # Affecte une valeur à une variable.
            _last_opcua_status["error_code"] = opcua_error_code  # Affecte une valeur à une variable.
    except Exception as exc:  # Capture une exception et exécute un traitement adapté.
        opcua_error = str(exc)  # Affecte une valeur à une variable.
        opcua_error_code = type(exc).__name__  # Affecte une valeur à une variable.
        _last_opcua_status["ok"] = False  # Affecte une valeur à une variable.
        _last_opcua_status["error"] = opcua_error  # Affecte une valeur à une variable.
        _last_opcua_status["error_code"] = opcua_error_code  # Affecte une valeur à une variable.

    # 2) Source principale: dernière valeur en base.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        dernier = recuperer_derniere_temperature()  # Affecte une valeur à une variable.
        if dernier:  # Teste une condition.
            return jsonify(  # Retourne une valeur depuis la fonction.
                {  # Effectue une opération de traitement des données.
                    "ok": True,  # Effectue une opération de traitement des données.
                    "source": "database",  # Effectue une opération de traitement des données.
                    "charge": dernier["charge"],  # Effectue une opération de traitement des données.
                    "ram": dernier["ram"],  # Effectue une opération de traitement des données.
                    "temperature": dernier["temperature"],  # Effectue une opération de traitement des données.
                    "alerte": dernier["alerte"],  # Effectue une opération de traitement des données.
                    "horodatage": dernier["horodatage"].isoformat() if dernier["horodatage"] else None,  # Effectue une opération de traitement des données.
                    "opcua_ok": opcua_error is None,  # Effectue une opération de traitement des données.
                    "opcua_error": opcua_error,  # Effectue une opération de traitement des données.
                    "opcua_error_code": opcua_error_code,  # Effectue une opération de traitement des données.
                }  # Effectue une opération de traitement des données.
            )  # Effectue une opération de traitement des données.
    except Exception as db_exc:  # Capture une exception et exécute un traitement adapté.
        # 3) Si la base échoue mais qu'on a une valeur live, on l'affiche quand meme.
        if live_data is not None:  # Teste une condition.
            return jsonify(  # Retourne une valeur depuis la fonction.
                {  # Effectue une opération de traitement des données.
                    "ok": True,  # Effectue une opération de traitement des données.
                    "source": "opcua_live",  # Effectue une opération de traitement des données.
                    "charge": live_data["charge"],  # Effectue une opération de traitement des données.
                    "ram": live_data["ram"],  # Effectue une opération de traitement des données.
                    "temperature": live_data["temperature"],  # Effectue une opération de traitement des données.
                    "alerte": None,  # Effectue une opération de traitement des données.
                    "horodatage": live_data["horodatage"],  # Effectue une opération de traitement des données.
                    "db_error": str(db_exc),  # Effectue une opération de traitement des données.
                    "opcua_ok": True,  # Effectue une opération de traitement des données.
                }  # Effectue une opération de traitement des données.
            )  # Effectue une opération de traitement des données.
        return jsonify({"ok": False, "error": str(db_exc)}), 500  # Retourne une valeur depuis la fonction.

    # 4) Si la base est vide mais qu'on a une valeur live OPC UA, on l'utilise.
    if live_data is not None:  # Teste une condition.
        return jsonify(  # Retourne une valeur depuis la fonction.
            {  # Effectue une opération de traitement des données.
                "ok": True,  # Effectue une opération de traitement des données.
                "source": "opcua_live",  # Effectue une opération de traitement des données.
                "charge": live_data["charge"],  # Effectue une opération de traitement des données.
                "ram": live_data["ram"],  # Effectue une opération de traitement des données.
                "temperature": live_data["temperature"],  # Effectue une opération de traitement des données.
                "alerte": None,  # Effectue une opération de traitement des données.
                "horodatage": live_data["horodatage"],  # Effectue une opération de traitement des données.
                "opcua_ok": True,  # Effectue une opération de traitement des données.
            }  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.

    return jsonify(  # Retourne une valeur depuis la fonction.
        {  # Effectue une opération de traitement des données.
            "ok": False,  # Effectue une opération de traitement des données.
            "error": "Aucune donnée CPU disponible",  # Effectue une opération de traitement des données.
            "opcua_error": opcua_error,  # Effectue une opération de traitement des données.
            "opcua_error_code": opcua_error_code,  # Effectue une opération de traitement des données.
        }  # Effectue une opération de traitement des données.
    ), 404  # Effectue une opération de traitement des données.


@app.route("/api/suivi-consommation-historique")  # Déclare un décorateur ou une route Flask.
def api_suivi_consommation_historique():  # Définit la fonction api_suivi_consommation_historique.
    """Retourne l'historique des données de consommation (derniers 60 enregistrements)."""
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        historique = recuperer_historique_suivi_conso(limit=60)  # Affecte une valeur à une variable.
        if not historique:  # Teste une condition.
            return jsonify({  # Retourne une valeur depuis la fonction.
                "ok": False,  # Effectue une opération de traitement des données.
                "message": "Aucune donnée d'historique disponible"  # Effectue une opération de traitement des données.
            }), 404  # Effectue une opération de traitement des données.
        
        result = [  # Affecte une valeur à une variable.
            {  # Effectue une opération de traitement des données.
                "courant": float(row["courant"]),  # Effectue une opération de traitement des données.
                "puissance": float(row["puissance"]),  # Effectue une opération de traitement des données.
                "energie": float(row["energie"]),  # Effectue une opération de traitement des données.
                "horodatage": row["horodatage"].isoformat() if row["horodatage"] else None,  # Effectue une opération de traitement des données.
            }  # Effectue une opération de traitement des données.
            for row in historique  # Boucle sur une séquence d éléments.
        ]  # Effectue une opération de traitement des données.
        return jsonify({  # Retourne une valeur depuis la fonction.
            "ok": True,  # Effectue une opération de traitement des données.
            "data": result,  # Effectue une opération de traitement des données.
            "count": len(result)  # Effectue une opération de traitement des données.
        })  # Effectue une opération de traitement des données.
    except Exception as e:  # Capture une exception et exécute un traitement adapté.
        return jsonify({  # Retourne une valeur depuis la fonction.
            "ok": False,  # Effectue une opération de traitement des données.
            "error": str(e)  # Effectue une opération de traitement des données.
        }), 500  # Effectue une opération de traitement des données.

@app.route("/api/suivi-consommation")  # Déclare un décorateur ou une route Flask.
def api_suivi_consommation():  # Définit la fonction api_suivi_consommation.
    """Mappe les variables énergétiques OPC UA vers suivi_conso et retourne la dernière ligne."""
    opcua_error = None  # Affecte une valeur à une variable.
    opcua_error_code = None  # Affecte une valeur à une variable.
    live_data = None  # Affecte une valeur à une variable.

    def _safe_float(value, default=0.0):  # Définit la fonction _safe_float.
        try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
            if value is None:  # Teste une condition.
                return default  # Retourne une valeur depuis la fonction.
            return float(value)  # Retourne une valeur depuis la fonction.
        except (TypeError, ValueError):  # Capture une exception et exécute un traitement adapté.
            return default  # Retourne une valeur depuis la fonction.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        # OPTIMISATION: utiliser le cache OPC UA côté serveur
        variables, was_refreshed = _get_cached_automate_variables()  # Affecte une valeur à une variable.
        if variables.get("ok") and variables.get("data"):  # Teste une condition.
            data = variables["data"]  # Affecte une valeur à une variable.
            courant = _safe_float(data.get("energ_act_l1"), 0.0)  # Affecte une valeur à une variable.
            puissance = _safe_float(data.get("energ_act_l2"), 0.0)  # Affecte une valeur à une variable.
            energie = _safe_float(data.get("energ_act_tot"), 0.0)  # Affecte une valeur à une variable.
            _last_opcua_status["ok"] = True  # Affecte une valeur à une variable.
            _last_opcua_status["error"] = None  # Affecte une valeur à une variable.
            _last_opcua_status["error_code"] = None  # Affecte une valeur à une variable.
            live_data = {  # Affecte une valeur à une variable.
                "courant": courant,  # Effectue une opération de traitement des données.
                "puissance": puissance,  # Effectue une opération de traitement des données.
                "energie": energie,  # Effectue une opération de traitement des données.
                "horodatage": datetime.utcnow().isoformat() + "Z",  # Effectue une opération de traitement des données.
            }  # Effectue une opération de traitement des données.
            # Enregistrer en base que si on vient de refaire la requête OPC UA
            if was_refreshed:  # Teste une condition.
                try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
                    enregistrer_suivi_conso(courant, puissance, energie)  # Effectue une opération de traitement des données.
                except Exception:  # Capture une exception et exécute un traitement adapté.
                    pass  # Ne fait rien ici, c’est une instruction vide.
        else:  # Prend le chemin alternatif si la condition précédente est fausse.
            opcua_error = (variables or {}).get("error", "Lecture OPC UA impossible")  # Affecte une valeur à une variable.
            opcua_error_code = (variables or {}).get("error_code")  # Affecte une valeur à une variable.
            _last_opcua_status["ok"] = False  # Affecte une valeur à une variable.
            _last_opcua_status["error"] = opcua_error  # Affecte une valeur à une variable.
            _last_opcua_status["error_code"] = opcua_error_code  # Affecte une valeur à une variable.
    except Exception as exc:  # Capture une exception et exécute un traitement adapté.
        opcua_error = str(exc)  # Affecte une valeur à une variable.
        opcua_error_code = type(exc).__name__  # Affecte une valeur à une variable.
        _last_opcua_status["ok"] = False  # Affecte une valeur à une variable.
        _last_opcua_status["error"] = opcua_error  # Affecte une valeur à une variable.
        _last_opcua_status["error_code"] = opcua_error_code  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        dernier = recuperer_dernier_suivi_conso()  # Affecte une valeur à une variable.
        if dernier:  # Teste une condition.
            return jsonify(  # Retourne une valeur depuis la fonction.
                {  # Effectue une opération de traitement des données.
                    "ok": True,  # Effectue une opération de traitement des données.
                    "source": "database",  # Effectue une opération de traitement des données.
                    "courant": float(dernier["courant"]),  # Effectue une opération de traitement des données.
                    "puissance": float(dernier["puissance"]),  # Effectue une opération de traitement des données.
                    "energie": float(dernier["energie"]),  # Effectue une opération de traitement des données.
                    "horodatage": dernier["horodatage"].isoformat() if dernier["horodatage"] else None,  # Effectue une opération de traitement des données.
                    "opcua_ok": opcua_error is None,  # Effectue une opération de traitement des données.
                    "opcua_error": opcua_error,  # Effectue une opération de traitement des données.
                    "opcua_error_code": opcua_error_code,  # Effectue une opération de traitement des données.
                }  # Effectue une opération de traitement des données.
            )  # Effectue une opération de traitement des données.
    except Exception as db_exc:  # Capture une exception et exécute un traitement adapté.
        if live_data is not None:  # Teste une condition.
            return jsonify(  # Retourne une valeur depuis la fonction.
                {  # Effectue une opération de traitement des données.
                    "ok": True,  # Effectue une opération de traitement des données.
                    "source": "opcua_live",  # Effectue une opération de traitement des données.
                    "courant": live_data["courant"],  # Effectue une opération de traitement des données.
                    "puissance": live_data["puissance"],  # Effectue une opération de traitement des données.
                    "energie": live_data["energie"],  # Effectue une opération de traitement des données.
                    "horodatage": live_data["horodatage"],  # Effectue une opération de traitement des données.
                    "db_error": str(db_exc),  # Effectue une opération de traitement des données.
                }  # Effectue une opération de traitement des données.
            )  # Effectue une opération de traitement des données.
        return jsonify({"ok": False, "error": str(db_exc)}), 500  # Retourne une valeur depuis la fonction.

    if live_data is not None:  # Teste une condition.
        return jsonify(  # Retourne une valeur depuis la fonction.
            {  # Effectue une opération de traitement des données.
                "ok": True,  # Effectue une opération de traitement des données.
                "source": "opcua_live",  # Effectue une opération de traitement des données.
                "courant": live_data["courant"],  # Effectue une opération de traitement des données.
                "puissance": live_data["puissance"],  # Effectue une opération de traitement des données.
                "energie": live_data["energie"],  # Effectue une opération de traitement des données.
                "horodatage": live_data["horodatage"],  # Effectue une opération de traitement des données.
            }  # Effectue une opération de traitement des données.
        )  # Effectue une opération de traitement des données.

    return jsonify(  # Retourne une valeur depuis la fonction.
        {  # Effectue une opération de traitement des données.
            "ok": False,  # Effectue une opération de traitement des données.
            "error": "Aucune donnée de consommation disponible",  # Effectue une opération de traitement des données.
            "opcua_error": opcua_error,  # Effectue une opération de traitement des données.
            "opcua_error_code": opcua_error_code,  # Effectue une opération de traitement des données.
        }  # Effectue une opération de traitement des données.
    ), 404  # Effectue une opération de traitement des données.


@app.route("/responsable")  # Déclare un décorateur ou une route Flask.
def dashboard_resp():  # Définit la fonction dashboard_resp.
    return render_template("dashboard_SB_respo.html")  # Retourne une valeur depuis la fonction.
 
@app.route("/integrateur")  # Déclare un décorateur ou une route Flask.
def dashboard_integ():  # Définit la fonction dashboard_integ.
    return render_template("dashboard_SB_integ.html")  # Retourne une valeur depuis la fonction.
 
# Route pour la page d'administration
@app.route("/admin", methods=["GET", "POST"])  # Déclare un décorateur ou une route Flask.
def admin():  # Définit la fonction admin.
    if not session.get("logged_in"):  # Teste une condition.
        return redirect(url_for("login"))  # Retourne une valeur depuis la fonction.
    return redirect(url_for("dashboard_op"))  # Retourne une valeur depuis la fonction.
 
# Route pour créer un nouvel utilisateur
@app.route("/create_user", methods=["POST"])  # Déclare un décorateur ou une route Flask.
def create_user():  # Définit la fonction create_user.
    if not session.get("logged_in") or session.get("role") != "Admin":  # Teste une condition.
        return jsonify({"success": False, "message": "Accès refusé."}), 403  # Retourne une valeur depuis la fonction.

    nom = (request.form.get("nom") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    prenom = (request.form.get("prenom") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    identifiant = (request.form.get("identifiant") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    password = (request.form.get("mot_de_passe") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    role = (request.form.get("role") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.

    if not nom or not prenom or not identifiant or not password or not role:  # Teste une condition.
        return jsonify({"success": False, "message": "Tous les champs sont obligatoires."}), 400  # Retourne une valeur depuis la fonction.

    if not normalize_role_code(role):  # Teste une condition.
        return jsonify({"success": False, "message": "Rôle invalide."}), 400  # Retourne une valeur depuis la fonction.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        created, message = create_registered_user(nom, prenom, identifiant, password, role)  # Affecte une valeur à une variable.
        if not created:  # Teste une condition.
            return jsonify({"success": False, "message": message}), 409  # Retourne une valeur depuis la fonction.
        users = fetch_registered_users()  # Affecte une valeur à une variable.
    except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": str(exc)}), 500  # Retourne une valeur depuis la fonction.

    return jsonify(  # Retourne une valeur depuis la fonction.
        {  # Effectue une opération de traitement des données.
            "success": True,  # Effectue une opération de traitement des données.
            "message": message,  # Effectue une opération de traitement des données.
            "users": users,  # Effectue une opération de traitement des données.
        }  # Effectue une opération de traitement des données.
    )  # Effectue une opération de traitement des données.


@app.route("/update_user_role", methods=["POST"])  # Déclare un décorateur ou une route Flask.
def update_user_role():  # Définit la fonction update_user_role.
    if not session.get("logged_in") or session.get("role") != "Admin":  # Teste une condition.
        return jsonify({"success": False, "message": "Accès refusé."}), 403  # Retourne une valeur depuis la fonction.

    identifiant = (request.form.get("identifiant") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    role = (request.form.get("role") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.

    if not identifiant or not role:  # Teste une condition.
        return jsonify({"success": False, "message": "Identifiant et rôle obligatoires."}), 400  # Retourne une valeur depuis la fonction.

    if not normalize_role_code(role):  # Teste une condition.
        return jsonify({"success": False, "message": "Rôle invalide."}), 400  # Retourne une valeur depuis la fonction.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        updated, message = update_registered_user_role(identifiant, role)  # Affecte une valeur à une variable.
        if not updated:  # Teste une condition.
            return jsonify({"success": False, "message": message}), 404  # Retourne une valeur depuis la fonction.
        users = fetch_registered_users()  # Affecte une valeur à une variable.
    except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": str(exc)}), 500  # Retourne une valeur depuis la fonction.

    return jsonify({"success": True, "message": message, "users": users})  # Retourne une valeur depuis la fonction.


@app.route("/update_user", methods=["POST"])  # Déclare un décorateur ou une route Flask.
def update_user():  # Définit la fonction update_user.
    if not session.get("logged_in") or session.get("role") != "Admin":  # Teste une condition.
        return jsonify({"success": False, "message": "Accès refusé."}), 403  # Retourne une valeur depuis la fonction.

    original_identifiant = (request.form.get("original_identifiant") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    nom = (request.form.get("nom") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    prenom = (request.form.get("prenom") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    identifiant = (request.form.get("identifiant") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    password = (request.form.get("mot_de_passe") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    role = (request.form.get("role") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.

    if not original_identifiant or not nom or not prenom or not identifiant or not password or not role:  # Teste une condition.
        return jsonify({"success": False, "message": "Tous les champs sont obligatoires."}), 400  # Retourne une valeur depuis la fonction.

    if not normalize_role_code(role):  # Teste une condition.
        return jsonify({"success": False, "message": "Rôle invalide."}), 400  # Retourne une valeur depuis la fonction.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        updated, message = update_registered_user(original_identifiant, nom, prenom, identifiant, password, role)  # Affecte une valeur à une variable.
        if not updated:  # Teste une condition.
            return jsonify({"success": False, "message": message}), 409  # Retourne une valeur depuis la fonction.
        users = fetch_registered_users()  # Affecte une valeur à une variable.
    except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": str(exc)}), 500  # Retourne une valeur depuis la fonction.

    return jsonify({"success": True, "message": message, "users": users})  # Retourne une valeur depuis la fonction.


@app.route("/delete_user", methods=["POST"])  # Déclare un décorateur ou une route Flask.
def delete_user():  # Définit la fonction delete_user.
    if not session.get("logged_in") or session.get("role") != "Admin":  # Teste une condition.
        return jsonify({"success": False, "message": "Accès refusé."}), 403  # Retourne une valeur depuis la fonction.

    identifiant = (request.form.get("identifiant") or "").strip()  # Récupère une valeur envoyée par le formulaire HTTP.
    if not identifiant:  # Teste une condition.
        return jsonify({"success": False, "message": "Identifiant obligatoire."}), 400  # Retourne une valeur depuis la fonction.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        deleted, message = delete_registered_user(identifiant)  # Affecte une valeur à une variable.
        if not deleted:  # Teste une condition.
            return jsonify({"success": False, "message": message}), 404  # Retourne une valeur depuis la fonction.
        users = fetch_registered_users()  # Affecte une valeur à une variable.
    except mysql.connector.Error as exc:  # Capture une exception et exécute un traitement adapté.
        return jsonify({"success": False, "message": str(exc)}), 500  # Retourne une valeur depuis la fonction.

    return jsonify({"success": True, "message": message, "users": users})  # Retourne une valeur depuis la fonction.
 
# --- TOUJOURS À LA FIN DU FICHIER ---
if __name__ == "__main__":  # Teste une condition.
    app.run(host='0.0.0.0', port=8180, debug=True)  # Affecte une valeur à une variable.
