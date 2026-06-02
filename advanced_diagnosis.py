#!/usr/bin/env python3
"""
Diagnostic avancé : teste les accès et cherche les variables d'autres façons
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.opcua_requests import _read_with_retry
from services.opcua_status import _get_opcua_config
from opcua.ua import NodeId
import random

def test_node_access(client, node_id_str):
    """Teste l'accès à un node"""
    try:
        node = client.get_node(node_id_str)
        dn = node.get_display_name()
        return f"✓ {dn.Text if dn else '(no name)'}"
    except Exception as e:
        return f"✗ {str(e)[:60]}"

def browse_and_read(client):
    """Teste plusieurs approches"""
    print("=== 1. Test d'accès aux nodes de base ===\n")
    basic_nodes = {
        "Root (i=84)": "i=84",
        "Objects (i=85)": "i=85",
        "Types (i=86)": "i=86",
        "Views (i=87)": "i=87",
        "Server (i=2253)": "i=2253",
    }
    
    for name, nid in basic_nodes.items():
        print(f"  {name:30} {test_node_access(client, nid)}")
    
    print("\n=== 2. Test des références depuis Objects ===\n")
    try:
        objects_node = client.get_node("i=85")
        # Get children via BrowseNode
        refs = objects_node.get_references()
        print(f"  Nombre de références: {len(refs)}")
        
        for i, ref in enumerate(refs[:10]):
            try:
                target = ref.target_node
                if target:
                    dn = target.get_display_name()
                    print(f"    [{i}] {dn.Text if dn else '?'} → {target.nodeid}")
            except:
                pass
        
        if len(refs) > 10:
            print(f"    ... + {len(refs) - 10} références")
    except Exception as e:
        print(f"  Erreur: {e}")
    
    print("\n=== 3. Test des ReadValueId / GetEndpoints info ===\n")
    try:
        # Essaie de lister les endpoints discou
        endpoints = client.uaclient.get_endpoints()
        print(f"  Endpoints disponibles: {len(endpoints)}")
        for ep in endpoints[:3]:
            print(f"    - URL: {ep.EndpointUrl}")
            print(f"      SecurityMode: {ep.SecurityMode}")
    except Exception as e:
        print(f"  Erreur endpoints: {e}")
    
    print("\n=== 4. Test alternativaves de recherche de variables ===\n")
    
    # Essaie des formats différents
    test_variants = [
        "ns=0;s=GVL_OPCUA",
        "ns=0;s=/GVL_OPCUA",
        "ns=0;s=Application",
        "ns=0;s=/Application",
        "ns=1;s=GVL_OPCUA",
        "ns=1;s=/GVL_OPCUA",
    ]
    
    for variant in test_variants:
        print(f"  {variant:40} {test_node_access(client, variant)}")
    
    print("\n=== 5. Énumération des Namespaces ===\n")
    try:
        # Get namespace array from Server object
        server = client.get_node("i=2253")
        ns_array = server.get_child(["0:NamespaceArray"])
        namespaces = ns_array.get_value()
        print(f"  Namespaces disponibles:")
        for i, ns in enumerate(namespaces):
            print(f"    ns={i}: {ns}")
    except Exception as e:
        print(f"  Erreur: {e}")
    
    return True

def main():
    config = _get_opcua_config()
    print(f"Serveur: {config['url']}\n")
    
    def _test(client):
        return browse_and_read(client)
    
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
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
