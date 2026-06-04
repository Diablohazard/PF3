import os
import re

from dotenv import load_dotenv

try:
    from services.opcua_requests import (
        read_automate_variables_sync,
        read_alert_thresholds_sync,
        read_node_value_sync,
        read_cpu_metrics_sync,
        OpcuaNodeReadError,
        server_accepts_anonymous,
        server_supports_sign_and_encrypt,
        write_alert_thresholds_sync,
    )
except ImportError:
    from app.services.opcua_requests import (
        read_automate_variables_sync,
        read_alert_thresholds_sync,
        read_node_value_sync,
        read_cpu_metrics_sync,
        OpcuaNodeReadError,
        server_accepts_anonymous,
        server_supports_sign_and_encrypt,
        write_alert_thresholds_sync,
    )


load_dotenv()

DEFAULT_OPCUA_URL = "opc.tcp://172.30.30.10:4840"
SERVER_STATUS_NODE_ID = "i=2259"
DEFAULT_OPCUA_TIMEOUT = 10


def _build_status(is_online, error_message=None, error_code=None):
    return {
        "ok": is_online,
        "error": error_message,
        "error_code": error_code,
    }


def _extract_error_code(exception):
    exception_text = str(exception)
    match = re.search(r"\(([A-Za-z][A-Za-z0-9_]+)\)", exception_text)
    if match:
        return match.group(1)

    match = re.search(r"\b(Bad[A-Za-z0-9_]+)\b", exception_text)
    if match:
        return match.group(1)

    return type(exception).__name__


def _get_opcua_config():
    timeout_value = os.getenv("OPCUA_TIMEOUT", str(DEFAULT_OPCUA_TIMEOUT)).strip()
    try:
        timeout = max(1, int(timeout_value))
    except ValueError:
        timeout = DEFAULT_OPCUA_TIMEOUT

    auth_mode = (os.getenv("OPCUA_AUTH") or "").strip().lower()
    username = (os.getenv("OPCUA_USERNAME") or "").strip()
    password = (os.getenv("OPCUA_PASSWORD") or "").strip()
    if auth_mode == "anonymous":
        username = ""
        password = ""

    return {
        "url": os.getenv("OPCUA_URL", DEFAULT_OPCUA_URL).strip(),
        "username": username,
        "password": password,
        "timeout": timeout,
        "security_config": {
            "mode": (os.getenv("OPCUA_SECURITY_MODE", "None") or "None").strip(),
            "client_cert": (os.getenv("OPCUA_CLIENT_CERT") or "").strip(),
            "client_key": (os.getenv("OPCUA_CLIENT_KEY") or "").strip(),
            "server_cert": (os.getenv("OPCUA_SERVER_CERT") or "").strip(),
        },
    }


def _check_connection(url, username, password, timeout, security_config=None):
    try:
        valeur = read_node_value_sync(
            url=url,
            username=username,
            password=password,
            node_id=SERVER_STATUS_NODE_ID,
            timeout=timeout,
            security_config=security_config,
        )
        print(f"Etat serveur OPCUA : {valeur}")
        return _build_status(True)

    except Exception as exc:
        error_message = f"Erreur de connexion Automate: {exc}"
        print(error_message)
        return _build_status(False, error_message, _extract_error_code(exc))


def get_opcua_status_details():
    config = _get_opcua_config()

    security_mode = (config.get("security_config") or {}).get("mode", "None")
    if security_mode == "None":
        try:
            anonymous_allowed = server_accepts_anonymous(
                config["url"],
                timeout=config["timeout"],
            )
            if not config["username"] and not anonymous_allowed:
                error_message = (
                    "Connexion OPC UA refusee: l'endpoint None est joignable, "
                    "mais le serveur n'annonce pas de token Anonymous."
                )
                print(error_message)
                return _build_status(False, error_message, "AnonymousNotAllowed")
        except Exception as exc:
            print(f"Info: verification Anonymous via GetEndpoints impossible: {exc}")

        return _check_connection(
            config["url"],
            config["username"],
            config["password"],
            config["timeout"],
            config.get("security_config"),
        )

    # If credentials are provided, test authenticated connectivity directly.
    # This avoids false negatives when GetEndpoints is slow/unavailable.
    try:
        anonymous_allowed = server_accepts_anonymous(
            config["url"],
            timeout=config["timeout"],
        )

        if security_mode == "SignAndEncrypt":
            secure_endpoint_available = server_supports_sign_and_encrypt(
                config["url"],
                timeout=config["timeout"],
            )
            if not secure_endpoint_available:
                error_message = (
                    "Connexion OPC UA refusee: aucun endpoint serveur compatible "
                    "avec Basic256Sha256 + SignAndEncrypt."
                )
                print(error_message)
                return _build_status(False, error_message, "SecureEndpointUnavailable")

    except Exception as exc:
        error_message = f"Erreur lors de la lecture des endpoints OPC UA: {exc}"
        print(error_message)
        return _build_status(False, error_message, _extract_error_code(exc))

    if not config["username"] and not anonymous_allowed:
        error_message = (
            "Connexion OPC UA refusée: le serveur n'accepte pas l'accès anonyme. "
            "Renseignez OPCUA_USERNAME et OPCUA_PASSWORD dans l'environnement."
        )
        print(error_message)
        return _build_status(False, error_message, "AnonymousNotAllowed")

    return _check_connection(
        config["url"],
        config["username"],
        config["password"],
        config["timeout"],
        config.get("security_config"),
    )


def get_opcua_status():
    return get_opcua_status_details()["ok"]


def get_automate_variables_details():
    config = _get_opcua_config()
    try:
        values = read_automate_variables_sync(
            url=config["url"],
            username=config["username"],
            password=config["password"],
            timeout=config["timeout"],
            security_config=config.get("security_config"),
        )
        return {
            "ok": True,
            "data": values,
            "error": None,
            "error_code": None,
        }
    except Exception as exc:
        error_message = f"Erreur de lecture des variables OPC UA: {exc}"
        print(error_message)
        return {
            "ok": False,
            "data": None,
            "error": error_message,
            "error_code": _extract_error_code(exc),
        }


def get_cpu_metrics_details():
    config = _get_opcua_config()
    try:
        values = read_cpu_metrics_sync(
            url=config["url"],
            username=config["username"],
            password=config["password"],
            timeout=config["timeout"],
            security_config=config.get("security_config"),
        )
        return {
            "ok": True,
            "data": values,
            "error": None,
            "error_code": None,
        }
    except Exception as exc:
        if isinstance(exc, OpcuaNodeReadError) and _extract_error_code(exc) == "BadNodeIdUnknown":
            error_message = (
                "Erreur de lecture des variables CPU OPC UA: les NodeIds CPU/RAM/Temp "
                "ne correspondent pas a l'espace d'adressage expose par l'automate."
            )
            print(f"{error_message} {exc.errors}")
            return {
                "ok": False,
                "data": None,
                "error": error_message,
                "error_code": "BadNodeIdUnknown",
                "node_errors": exc.errors,
            }

        error_message = f"Erreur de lecture des variables CPU OPC UA: {exc}"
        print(error_message)
        return {
            "ok": False,
            "data": None,
            "error": error_message,
            "error_code": _extract_error_code(exc),
        }


def get_alert_thresholds_details():
    # Wrapper service: centralise la résolution de config (URL, auth, sécurité)
    # puis délègue la lecture des seuils au service OPC UA.
    config = _get_opcua_config()
    try:
        values = read_alert_thresholds_sync(
            url=config["url"],
            username=config["username"],
            password=config["password"],
            timeout=config["timeout"],
            security_config=config.get("security_config"),
        )
        return {
            "ok": True,
            "data": values,
            "error": None,
            "error_code": None,
        }
    except Exception as exc:
        if isinstance(exc, OpcuaNodeReadError) and _extract_error_code(exc) == "BadNodeIdUnknown":
            error_message = (
                "Erreur de lecture des seuils OPC UA: les NodeIds seuil_ram/seuil_cpu/seuil_temp "
                "ne correspondent pas a l'espace d'adressage expose par l'automate."
            )
            print(f"{error_message} {exc.errors}")
            return {
                "ok": False,
                "data": None,
                "error": error_message,
                "error_code": "BadNodeIdUnknown",
                "node_errors": exc.errors,
            }

        error_message = f"Erreur de lecture des seuils OPC UA: {exc}"
        print(error_message)
        return {
            "ok": False,
            "data": None,
            "error": error_message,
            "error_code": _extract_error_code(exc),
        }


def set_alert_thresholds_details(seuil_ram, seuil_cpu, seuil_temp):
    # Normalise d'abord les entrées UI en float avant écriture OPC UA.
    config = _get_opcua_config()
    payload = {
        "seuil_ram": float(seuil_ram),
        "seuil_cpu": float(seuil_cpu),
        "seuil_temp": float(seuil_temp),
    }

    try:
        result = write_alert_thresholds_sync(
            url=config["url"],
            username=config["username"],
            password=config["password"],
            thresholds=payload,
            timeout=config["timeout"],
            security_config=config.get("security_config"),
        )
        return {
            "ok": True,
            "data": payload,
            "write_result": result,
            "error": None,
            "error_code": None,
        }
    except Exception as exc:
        error_message = f"Erreur d'ecriture des seuils OPC UA: {exc}"
        print(error_message)
        return {
            "ok": False,
            "data": None,
            "error": error_message,
            "error_code": _extract_error_code(exc),
        }
