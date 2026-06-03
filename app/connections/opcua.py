def create_async_client(url, username="", password="", timeout=10):  # Définit la fonction create_async_client.
    from asyncua import Client as AsyncClient  # Importe un élément spécifique depuis un module.

    client = AsyncClient(url=url, timeout=timeout)  # Affecte une valeur à une variable.
    if username:  # Teste une condition.
        client.set_user(username)  # Effectue une opération de traitement.
        client.set_password(password)  # Effectue une opération de traitement.
    return client  # Retourne une valeur depuis la fonction.


def fetch_server_endpoints(url, timeout=10):  # Définit la fonction fetch_server_endpoints.
    from opcua import Client as SyncClient  # Importe un élément spécifique depuis un module.

    client = SyncClient(url, timeout=timeout)  # Affecte une valeur à une variable.
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        return client.connect_and_get_server_endpoints()  # Retourne une valeur depuis la fonction.
    finally:  # Exécute ce bloc quoi qu’il arrive.
        try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
            client.disconnect()  # Effectue une opération de traitement.
        except Exception:  # Capture et traite une exception.
            pass  # Effectue une opération de traitement.
