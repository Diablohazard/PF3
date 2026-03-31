import asyncio
import os

from asyncua import Client
from dotenv import load_dotenv
from opcua import Client as SyncClient
from opcua import ua


load_dotenv()

DEFAULT_OPCUA_URL = "opc.tcp://172.30.30.10:4840"
SERVER_STATUS_NODE_ID = "i=2259"


def _build_status(is_online, error_message=None):
    return {
        "ok": is_online,
        "error": error_message,
    }


def _get_opcua_config():
    return {
        "url": os.getenv("OPCUA_URL", DEFAULT_OPCUA_URL).strip(),
        "username": (os.getenv("OPCUA_USERNAME") or "").strip(),
        "password": (os.getenv("OPCUA_PASSWORD") or "").strip(),
    }


def _server_accepts_anonymous(url):
    client = SyncClient(url)

    try:
        endpoints = client.connect_and_get_server_endpoints()
    except Exception as exc:
        error_message = f"Erreur lors de la lecture des endpoints OPC UA: {exc}"
        print(error_message)
        return False, error_message

    for endpoint in endpoints:
        for token in endpoint.UserIdentityTokens:
            if token.TokenType == ua.UserTokenType.Anonymous:
                return True, None

    return False, None


async def _check_connection_async(url, username, password):
    try:
        client = Client(url=url, timeout=2)

        if username:
            client.set_user(username)
            client.set_password(password)

        async with client:
            node = client.get_node(SERVER_STATUS_NODE_ID)
            valeur = await node.read_value()
            print(f"Etat serveur OPCUA : {valeur}")
            return _build_status(True)

    except Exception as exc:
        error_message = f"Erreur de connexion Automate: {exc}"
        print(error_message)
        return _build_status(False, error_message)


def get_opcua_status_details():
    config = _get_opcua_config()
    anonymous_allowed, discovery_error = _server_accepts_anonymous(config["url"])

    if discovery_error:
        return _build_status(False, discovery_error)

    if not config["username"] and not anonymous_allowed:
        error_message = (
            "Connexion OPC UA refusée: le serveur n'accepte pas l'accès anonyme. "
            "Renseignez OPCUA_USERNAME et OPCUA_PASSWORD dans l'environnement."
        )
        print(error_message)
        return _build_status(False, error_message)

    return asyncio.run(
        _check_connection_async(
            config["url"],
            config["username"],
            config["password"],
        )
    )


def get_opcua_status():
    return get_opcua_status_details()["ok"]