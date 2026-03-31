from opcua import ua

try:
    from connections.opcua import create_async_client, fetch_server_endpoints
except ImportError:
    from app.connections.opcua import create_async_client, fetch_server_endpoints


def server_accepts_anonymous(url):
    endpoints = fetch_server_endpoints(url)

    for endpoint in endpoints:
        for token in endpoint.UserIdentityTokens:
            if token.TokenType == ua.UserTokenType.Anonymous:
                return True

    return False


async def read_node_value(url, username, password, node_id, timeout=2):
    client = create_async_client(
        url=url,
        username=username,
        password=password,
        timeout=timeout,
    )

    async with client:
        node = client.get_node(node_id)
        return await node.read_value()
