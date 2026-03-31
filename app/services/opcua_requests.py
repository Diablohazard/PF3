from opcua import ua

try:
    from connections.opcua import create_async_client, fetch_server_endpoints
except ImportError:
    from app.connections.opcua import create_async_client, fetch_server_endpoints


AUTOMATE_NODE_IDS = {
    "energ_act_l1": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActL1",
    "energ_act_l2": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActL2",
    "energ_act_tot": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActTot",
    "plann_ent_preh": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.plannEntPreh",
    "plann_net_rob": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.plannNetRob",
    "cpu_load": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.rCpuLoad",
    "ram_usage": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.rRamUsage",
    "temp_c": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.rTempC",
    "seuil_cpu": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.seuilCpu",
    "seuil_ram": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.seuilRam",
    "seuil_temp": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.seuilTemp",
}


def server_accepts_anonymous(url, timeout=10):
    endpoints = fetch_server_endpoints(url, timeout=timeout)

    for endpoint in endpoints:
        for token in endpoint.UserIdentityTokens:
            if token.TokenType == ua.UserTokenType.Anonymous:
                return True

    return False


async def read_node_value(url, username, password, node_id, timeout=10):
    client = create_async_client(
        url=url,
        username=username,
        password=password,
        timeout=timeout,
    )

    async with client:
        node = client.get_node(node_id)
        return await node.read_value()


async def read_named_nodes(url, username, password, node_ids, timeout=10):
    client = create_async_client(
        url=url,
        username=username,
        password=password,
        timeout=timeout,
    )

    values = {}
    async with client:
        for name, node_id in node_ids.items():
            node = client.get_node(node_id)
            values[name] = await node.read_value()

    return values


async def read_automate_variables(url, username, password, timeout=10):
    return await read_named_nodes(
        url=url,
        username=username,
        password=password,
        node_ids=AUTOMATE_NODE_IDS,
        timeout=timeout,
    )
