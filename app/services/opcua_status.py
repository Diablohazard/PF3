import os  # Importe un module ou un package.
import re  # Importe un module ou un package.

from dotenv import load_dotenv  # Importe un élément spécifique depuis un module.

try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
    from services.opcua_requests import (  # Importe un élément spécifique depuis un module.
        read_automate_variables_sync,  # Effectue une opération de traitement.
        read_alert_thresholds_sync,  # Effectue une opération de traitement.
        read_node_value_sync,  # Effectue une opération de traitement.
        server_accepts_anonymous,  # Effectue une opération de traitement.
        server_supports_sign_and_encrypt,  # Effectue une opération de traitement.
        write_alert_thresholds_sync,  # Effectue une opération de traitement.
    )  # Effectue une opération de traitement.
except ImportError:  # Capture et traite une exception.
    from app.services.opcua_requests import (  # Importe un élément spécifique depuis un module.
        read_automate_variables_sync,  # Effectue une opération de traitement.
        read_alert_thresholds_sync,  # Effectue une opération de traitement.
        read_node_value_sync,  # Effectue une opération de traitement.
        server_accepts_anonymous,  # Effectue une opération de traitement.
        server_supports_sign_and_encrypt,  # Effectue une opération de traitement.
        write_alert_thresholds_sync,  # Effectue une opération de traitement.
    )  # Effectue une opération de traitement.


load_dotenv()  # Effectue une opération de traitement.

DEFAULT_OPCUA_URL = "opc.tcp://172.30.30.10:4840"  # Affecte une valeur à une variable.
SERVER_STATUS_NODE_ID = "i=2259"  # Affecte une valeur à une variable.
DEFAULT_OPCUA_TIMEOUT = 10  # Affecte une valeur à une variable.


def _build_status(is_online, error_message=None, error_code=None):  # Définit la fonction _build_status.
    return {  # Retourne une valeur depuis la fonction.
        "ok": is_online,  # Effectue une opération de traitement.
        "error": error_message,  # Effectue une opération de traitement.
        "error_code": error_code,  # Effectue une opération de traitement.
    }  # Effectue une opération de traitement.


def _extract_error_code(exception):  # Définit la fonction _extract_error_code.
    exception_text = str(exception)  # Affecte une valeur à une variable.
    match = re.search(r"\(([A-Za-z][A-Za-z0-9_]+)\)", exception_text)  # Affecte une valeur à une variable.
    if match:  # Teste une condition.
        return match.group(1)  # Retourne une valeur depuis la fonction.

    match = re.search(r"\b(Bad[A-Za-z0-9_]+)\b", exception_text)  # Affecte une valeur à une variable.
    if match:  # Teste une condition.
        return match.group(1)  # Retourne une valeur depuis la fonction.

    return type(exception).__name__  # Retourne une valeur depuis la fonction.


def _get_opcua_config():  # Définit la fonction _get_opcua_config.
    timeout_value = os.getenv("OPCUA_TIMEOUT", str(DEFAULT_OPCUA_TIMEOUT)).strip()  # Affecte une valeur à une variable.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        timeout = max(1, int(timeout_value))  # Affecte une valeur à une variable.
    except ValueError:  # Capture et traite une exception.
        timeout = DEFAULT_OPCUA_TIMEOUT  # Affecte une valeur à une variable.
    cfg = {
        "url": os.getenv("OPCUA_URL", DEFAULT_OPCUA_URL).strip(),
        "username": (os.getenv("OPCUA_USERNAME") or "").strip(),
        "password": (os.getenv("OPCUA_PASSWORD") or "").strip(),
        "timeout": timeout,
        "security_config": {
            "mode": (os.getenv("OPCUA_SECURITY_MODE", "None") or "None").strip(),
            "client_cert": (os.getenv("OPCUA_CLIENT_CERT") or "").strip(),
            "client_key": (os.getenv("OPCUA_CLIENT_KEY") or "").strip(),
            "server_cert": (os.getenv("OPCUA_SERVER_CERT") or "").strip(),
        },
    }

    # Optional override: force anonymous connections when troubleshooting.
    force_anonymous = (os.getenv("OPCUA_FORCE_ANONYMOUS") or "").strip().lower() in ("1", "true", "yes", "on")
    if force_anonymous:
        cfg["username"] = ""
        cfg["password"] = ""
        cfg["security_config"] = {"mode": "None", "client_cert": "", "client_key": "", "server_cert": ""}

    return cfg


def _check_connection(url, username, password, timeout, security_config=None):  # Définit la fonction _check_connection.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        valeur = read_node_value_sync(  # Affecte une valeur à une variable.
            url=url,  # Affecte une valeur à une variable.
            username=username,  # Affecte une valeur à une variable.
            password=password,  # Affecte une valeur à une variable.
            node_id=SERVER_STATUS_NODE_ID,  # Affecte une valeur à une variable.
            timeout=timeout,  # Affecte une valeur à une variable.
            security_config=security_config,  # Affecte une valeur à une variable.
        )  # Effectue une opération de traitement.
        print(f"Etat serveur OPCUA : {valeur}")  # Effectue une opération de traitement.
        return _build_status(True)  # Retourne une valeur depuis la fonction.

    except Exception as exc:  # Capture et traite une exception.
        error_message = f"Erreur de connexion Automate: {exc}"  # Affecte une valeur à une variable.
        print(error_message)  # Effectue une opération de traitement.
        return _build_status(False, error_message, _extract_error_code(exc))  # Retourne une valeur depuis la fonction.


def get_opcua_status_details():  # Définit la fonction get_opcua_status_details.
    config = _get_opcua_config()  # Affecte une valeur à une variable.

    security_mode = (config.get("security_config") or {}).get("mode", "None")  # Affecte une valeur à une variable.

    # If credentials are provided, test authenticated connectivity directly.
    # This avoids false negatives when GetEndpoints is slow/unavailable.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        anonymous_allowed = server_accepts_anonymous(  # Affecte une valeur à une variable.
            config["url"],  # Effectue une opération de traitement.
            timeout=config["timeout"],  # Affecte une valeur à une variable.
        )  # Effectue une opération de traitement.

        if security_mode == "SignAndEncrypt":  # Teste une condition.
            secure_endpoint_available = server_supports_sign_and_encrypt(  # Affecte une valeur à une variable.
                config["url"],  # Effectue une opération de traitement.
                timeout=config["timeout"],  # Affecte une valeur à une variable.
            )  # Effectue une opération de traitement.
            if not secure_endpoint_available:  # Teste une condition.
                warning = (  # Affecte une valeur à une variable.
                    "Connexion OPC UA SignAndEncrypt non disponible sur le serveur. "  # Effectue une opération de traitement.
                    "Tentative de fallback en anonymous (best-effort)."  # Effectue une opération de traitement.
                )  # Effectue une opération de traitement.
                print(warning)  # Effectue une opération de traitement.

    except Exception as exc:  # Capture et traite une exception.
        error_message = f"Erreur lors de la lecture des endpoints OPC UA: {exc}"  # Affecte une valeur à une variable.
        print(error_message)  # Effectue une opération de traitement.
        return _build_status(False, error_message, _extract_error_code(exc))  # Retourne une valeur depuis la fonction.

    if not config["username"]:  # Teste une condition.
        print("⚠ Aucun `OPCUA_USERNAME` fourni: tentative de connexion anonymous (best-effort).")  # Effectue une opération de traitement.

    return _check_connection(  # Retourne une valeur depuis la fonction.
        config["url"],  # Effectue une opération de traitement.
        config["username"],  # Effectue une opération de traitement.
        config["password"],  # Effectue une opération de traitement.
        config["timeout"],  # Effectue une opération de traitement.
        config.get("security_config"),  # Effectue une opération de traitement.
    )  # Effectue une opération de traitement.


def get_opcua_status():  # Définit la fonction get_opcua_status.
    return get_opcua_status_details()["ok"]  # Retourne une valeur depuis la fonction.


def get_automate_variables_details():  # Définit la fonction get_automate_variables_details.
    config = _get_opcua_config()  # Affecte une valeur à une variable.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        values = read_automate_variables_sync(  # Affecte une valeur à une variable.
            url=config["url"],  # Affecte une valeur à une variable.
            username=config["username"],  # Affecte une valeur à une variable.
            password=config["password"],  # Affecte une valeur à une variable.
            timeout=config["timeout"],  # Affecte une valeur à une variable.
            security_config=config.get("security_config"),  # Affecte une valeur à une variable.
        )  # Effectue une opération de traitement.
        return {  # Retourne une valeur depuis la fonction.
            "ok": True,  # Effectue une opération de traitement.
            "data": values,  # Effectue une opération de traitement.
            "error": None,  # Effectue une opération de traitement.
            "error_code": None,  # Effectue une opération de traitement.
        }  # Effectue une opération de traitement.
    except Exception as exc:  # Capture et traite une exception.
        error_message = f"Erreur de lecture des variables OPC UA: {exc}"  # Affecte une valeur à une variable.
        print(error_message)  # Effectue une opération de traitement.
        return {  # Retourne une valeur depuis la fonction.
            "ok": False,  # Effectue une opération de traitement.
            "data": None,  # Effectue une opération de traitement.
            "error": error_message,  # Effectue une opération de traitement.
            "error_code": _extract_error_code(exc),  # Effectue une opération de traitement.
        }  # Effectue une opération de traitement.


def get_alert_thresholds_details():  # Définit la fonction get_alert_thresholds_details.
    # Wrapper service: centralise la résolution de config (URL, auth, sécurité)
    # puis délègue la lecture des seuils au service OPC UA.
    config = _get_opcua_config()  # Affecte une valeur à une variable.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        values = read_alert_thresholds_sync(  # Affecte une valeur à une variable.
            url=config["url"],  # Affecte une valeur à une variable.
            username=config["username"],  # Affecte une valeur à une variable.
            password=config["password"],  # Affecte une valeur à une variable.
            timeout=config["timeout"],  # Affecte une valeur à une variable.
            security_config=config.get("security_config"),  # Affecte une valeur à une variable.
        )  # Effectue une opération de traitement.
        return {  # Retourne une valeur depuis la fonction.
            "ok": True,  # Effectue une opération de traitement.
            "data": values,  # Effectue une opération de traitement.
            "error": None,  # Effectue une opération de traitement.
            "error_code": None,  # Effectue une opération de traitement.
        }  # Effectue une opération de traitement.
    except Exception as exc:  # Capture et traite une exception.
        error_message = f"Erreur de lecture des seuils OPC UA: {exc}"  # Affecte une valeur à une variable.
        print(error_message)  # Effectue une opération de traitement.
        return {  # Retourne une valeur depuis la fonction.
            "ok": False,  # Effectue une opération de traitement.
            "data": None,  # Effectue une opération de traitement.
            "error": error_message,  # Effectue une opération de traitement.
            "error_code": _extract_error_code(exc),  # Effectue une opération de traitement.
        }  # Effectue une opération de traitement.


def set_alert_thresholds_details(seuil_ram, seuil_cpu, seuil_temp):  # Définit la fonction set_alert_thresholds_details.
    # Normalise d'abord les entrées UI en float avant écriture OPC UA.
    config = _get_opcua_config()  # Affecte une valeur à une variable.
    payload = {  # Affecte une valeur à une variable.
        "seuil_ram": float(seuil_ram),  # Effectue une opération de traitement.
        "seuil_cpu": float(seuil_cpu),  # Effectue une opération de traitement.
        "seuil_temp": float(seuil_temp),  # Effectue une opération de traitement.
    }  # Effectue une opération de traitement.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        result = write_alert_thresholds_sync(  # Affecte une valeur à une variable.
            url=config["url"],  # Affecte une valeur à une variable.
            username=config["username"],  # Affecte une valeur à une variable.
            password=config["password"],  # Affecte une valeur à une variable.
            thresholds=payload,  # Affecte une valeur à une variable.
            timeout=config["timeout"],  # Affecte une valeur à une variable.
            security_config=config.get("security_config"),  # Affecte une valeur à une variable.
        )  # Effectue une opération de traitement.
        return {  # Retourne une valeur depuis la fonction.
            "ok": True,  # Effectue une opération de traitement.
            "data": payload,  # Effectue une opération de traitement.
            "write_result": result,  # Effectue une opération de traitement.
            "error": None,  # Effectue une opération de traitement.
            "error_code": None,  # Effectue une opération de traitement.
        }  # Effectue une opération de traitement.
    except Exception as exc:  # Capture et traite une exception.
        error_message = f"Erreur d'ecriture des seuils OPC UA: {exc}"  # Affecte une valeur à une variable.
        print(error_message)  # Effectue une opération de traitement.
        return {  # Retourne une valeur depuis la fonction.
            "ok": False,  # Effectue une opération de traitement.
            "data": None,  # Effectue une opération de traitement.
            "error": error_message,  # Effectue une opération de traitement.
            "error_code": _extract_error_code(exc),  # Effectue une opération de traitement.
        }  # Effectue une opération de traitement.
