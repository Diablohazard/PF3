#!/usr/bin/env python3
"""
Script simple pour établir une connexion OPC UA et explorer les nodes disponibles.
Utilise directement les fonctions de secours du code.
"""
import sys
import os

# Ajoute le chemin app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Maintenant on peut importer
from services.opcua_requests import _ensure_persistent_client, _read_with_retry
from services.opcua_status import _get_opcua_config
from opcua import Client
from opcua.ua import NodeClass

def explore_and_list_nodes(client, start_node_id="i=85", depth=0, max_depth=4, results=None):
    """
    Explore OPC UA server and list all nodes with their paths.
    start_node_id="i=85" is the Objects folder by default.
    """
    if results is None:
        results = []
    
    if depth > max_depth:
        return results
    
    indent = "  " * depth
    
    try:
        node = client.get_node(start_node_id)
        display_name = node.get_display_name().Text
        node_id_str = str(node.nodeid)
        
        # Check for variables with interesting keywords
        keywords = ["Energ", "Time", "Qty", "Cpu", "Ram", "Temp", "seuil", "plann", "GVL", "Application"]
        found = any(kw.lower() in display_name.lower() for kw in keywords)
        
        marker = "✓ " if found else ""
        entry = f"{indent}{marker}{display_name} → {node_id_str}"
        results.append(entry)
        print(entry)
        
        # Iterate through children
        if depth < max_depth:
            try:
                children = node.get_children()
                for child in children[:30]:  # Limit children
                    child_id = str(child.nodeid)
                    explore_and_list_nodes(client, child_id, depth + 1, max_depth, results)
            except Exception as e:
                pass
    except Exception as e:
        pass
    
    return results

def main():
    config = _get_opcua_config()
    print(f"Configuration: URL={config['url']}, User={config['username']}\n")
    
    # Use the same connection mechanism as the application
    def _explore(client):
        print("=== Exploration des nodes OPC UA ===\n")
        explore_and_list_nodes(client, start_node_id="i=85", depth=0, max_depth=5)
        print("\n\n=== Recherche spécifique des nodes avec 'GVL' ou 'Application' ===")
        return True
    
    try:
        _read_with_retry(
            _explore,
            url=config["url"],
            username=config["username"],
            password=config["password"],
            timeout=config["timeout"],
            security_config=config.get("security_config"),
        )
        print("\n✓ Exploration complétée")
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
