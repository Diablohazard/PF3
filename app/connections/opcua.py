from asyncua import Client as AsyncClient
from opcua import Client as SyncClient


def create_async_client(url, username="", password="", timeout=10):
    client = AsyncClient(url=url, timeout=timeout)
    if username:
        client.set_user(username)
        client.set_password(password)
    return client


def fetch_server_endpoints(url, timeout=10):
    client = SyncClient(url, timeout=timeout)
    return client.connect_and_get_server_endpoints()