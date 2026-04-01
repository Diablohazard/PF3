import atexit
import threading

from opcua import Client as SyncClient
from opcua import ua

try:
    from connections.opcua import fetch_server_endpoints
except ImportError:
    from app.connections.opcua import fetch_server_endpoints


AUTOMATE_NODE_IDS = {
    "energ_act_l1": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActL1",
    "energ_act_l2": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActL2",
    "energ_act_tot": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActTot",
    "total_time": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.TotalTime",
    "start_time": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.StartTime",
    "end_time": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EndTime",
    "qty_produced": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.QtyProduced",
    "qty_target": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.QtyTarget",
    "cpu_load": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.rCpuLoad",
    "ram_usage": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.rRamUsage",
    "temp_c": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.rTempC",
    "seuil_ram": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.seuilRam",
    "seuil_cpu": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.seuilCpu",
    "seuil_temp": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.seuilTemp",
    "plann_ent_preh": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.plannEntPreh",
    "plann_net_rob": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.plannNetRob",
}


_persistent_client = None
_persistent_client_config = None
_persistent_client_lock = threading.Lock()


def _create_sync_client(url, username, password, timeout):
    client = SyncClient(url, timeout=timeout)
    if username:
        client.set_user(username)
        client.set_password(password)
    return client


def _disconnect_persistent_client():
    global _persistent_client
    if _persistent_client is not None:
        try:
            _persistent_client.disconnect()
        except Exception:
            pass
        finally:
            _persistent_client = None


def close_persistent_client():
    with _persistent_client_lock:
        _disconnect_persistent_client()


def _ensure_persistent_client(url, username, password, timeout):
    global _persistent_client, _persistent_client_config

    desired_config = {
        "url": url,
        "username": username,
        "password": password,
        "timeout": timeout,
    }

    # Reconnect if configuration changed (URL/credentials/timeout).
    if _persistent_client is not None and _persistent_client_config != desired_config:
        _disconnect_persistent_client()

    if _persistent_client is None:
        _persistent_client = _create_sync_client(url, username, password, timeout)
        _persistent_client.connect()
        _persistent_client_config = desired_config

    return _persistent_client


def _read_with_retry(read_operation, url, username, password, timeout):
    with _persistent_client_lock:
        try:
            client = _ensure_persistent_client(url, username, password, timeout)
            return read_operation(client)
        except Exception:
            # Force reconnect once, then retry the same operation.
            _disconnect_persistent_client()
            client = _ensure_persistent_client(url, username, password, timeout)
            return read_operation(client)


def server_accepts_anonymous(url, timeout=10):
    endpoints = fetch_server_endpoints(url, timeout=timeout)

    for endpoint in endpoints:
        for token in endpoint.UserIdentityTokens:
            if token.TokenType == ua.UserTokenType.Anonymous:
                return True

    return False


def read_node_value_sync(url, username, password, node_id, timeout=10):
    def _operation(client):
        node = client.get_node(node_id)
        return node.get_value()

    return _read_with_retry(
        _operation,
        url=url,
        username=username,
        password=password,
        timeout=timeout,
    )


def read_named_nodes_sync(url, username, password, node_ids, timeout=10):
    def _operation(client):
        values = {}
        for name, node_id in node_ids.items():
            node = client.get_node(node_id)
            values[name] = node.get_value()

        return values

    return _read_with_retry(
        _operation,
        url=url,
        username=username,
        password=password,
        timeout=timeout,
    )



def read_automate_variables_sync(url, username, password, timeout=10):
    return read_named_nodes_sync(
        url=url,
        username=username,
        password=password,
        node_ids=AUTOMATE_NODE_IDS,
        timeout=timeout,
    )


atexit.register(close_persistent_client)
