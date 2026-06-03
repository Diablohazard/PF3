from asyncua import Client as AsyncClient
from opcua import Client as SyncClient


def create_async_client(url, username=None, password=None, timeout=10):
    client = AsyncClient(url=url, timeout=timeout)
    # If username is provided (non-empty), configure user/password.
    # Otherwise leave the client untouched to use anonymous identity.
    if username:
        client.set_user(username)
        client.set_password(password or "")
    return client


def fetch_server_endpoints(url, timeout=10):
    client = SyncClient(url, timeout=timeout)
    try:
        return client.connect_and_get_server_endpoints()
    finally:
        try:
            client.disconnect()
        except Exception:
            pass