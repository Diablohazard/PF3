#!/usr/bin/env python3
"""
Test spécifique des node IDs du code actuel pour voir lesquels existent
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.opcua_requests import _read_with_retry
from services.opcua_status import _get_opcua_config
from opcua.ua import NodeId

# Node IDs du code actuel
TEST_NODE_IDS = {
    "energ_act_l1": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActL1",
    "energ_act_l2": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActL2",
    "cpu_load": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.rCpuLoad",
}

# Also try with different namespaces
ALTERNATIVE_NODE_IDS = {
    "ns=2": "ns=2;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActL1",
    "ns=3": "ns=3;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActL1",
}

def test_node_exists(client, node_id_str):
    """Test if a node exists on the server"""
    try:
        node_id = NodeId.from_string(node_id_str)
        node = client.get_node(node_id)
        display_name = node.get_display_name().Text
        return f"✓ EXISTS: {display_name}"
    except Exception as e:
        error_str = str(e)
        if "BadNodeIdUnknown" in error_str:
            return f"✗ NOT FOUND (BadNodeIdUnknown)"
        else:
            return f"? ERROR: {error_str[:80]}"

def test_all_nodes(client):
    """Test all current node IDs"""
    print("=== Testant les node IDs du code actuel ===\n")
    for name, node_id_str in TEST_NODE_IDS.items():
        result = test_node_exists(client, node_id_str)
        print(f"{name:15} {node_id_str:55} → {result}")
    
    print("\n=== Testant namespace alternatifs ===\n")
    for name, node_id_str in ALTERNATIVE_NODE_IDS.items():
        result = test_node_exists(client, node_id_str)
        print(f"{name:15} {node_id_str:55} → {result}")
    
    print("\n=== Testant les namespaces 0,1,2,3,4 sur GVL_OPCUA ===\n")
    for ns in range(5):
        node_id_str = f"ns={ns};s=|var|172.30.30.10.Application.GVL_OPCUA"
        result = test_node_exists(client, node_id_str)
        print(f"ns={ns}  {node_id_str:55} → {result}")
    
    # Try simple object paths
    print("\n=== Testant des paths simples ===\n")
    simple_paths = [
        ("Root", "i=84"),
        ("Objects", "i=85"),
        ("Types", "i=86"),
        ("Views", "i=87"),
    ]
    for name, node_id in simple_paths:
        result = test_node_exists(client, node_id)
        print(f"{name:15} {node_id:55} → {result}")

def main():
    config = _get_opcua_config()
    print(f"Configuration: URL={config['url']}, User={config['username']}\n")
    
    def _test(client):
        test_all_nodes(client)
        return True
    
    try:
        _read_with_retry(
            _test,
            url=config["url"],
            username=config["username"],
            password=config["password"],
            timeout=config["timeout"],
            security_config=config.get("security_config"),
        )
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
