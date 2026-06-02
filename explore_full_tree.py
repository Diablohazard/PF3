#!/usr/bin/env python3
"""
Explore tous les nodes sous Objects pour trouver la structure réelle du serveur
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.opcua_requests import _read_with_retry
from services.opcua_status import _get_opcua_config

def explore_tree(client, start_id="i=85", depth=0, max_depth=6, visited=None, breadth_limit=50):
    """Explore la structure complète du serveur"""
    if visited is None:
        visited = set()
    
    # Évite les boucles infinies
    if start_id in visited or depth > max_depth:
        return
    visited.add(start_id)
    
    indent = "  " * depth
    
    try:
        node = client.get_node(start_id)
        display_name = node.get_display_name().Text
        node_class = node.get_node_class()
        
        # Affiche le nœud
        class_name = str(node_class).split('.')[-1] if node_class else "?"
        print(f"{indent}[{class_name}] {display_name}")
        
        # Explore les enfants
        try:
            children = node.get_children()
            for i, child in enumerate(children):
                if i >= breadth_limit:
                    print(f"{indent}  ... ({len(children) - breadth_limit} autres enfants)")
                    break
                child_id = str(child.nodeid)
                explore_tree(client, child_id, depth + 1, max_depth, visited, breadth_limit)
        except:
            pass
    except Exception as e:
        pass

def main():
    config = _get_opcua_config()
    print(f"Serveur: {config['url']}\n")
    print("=== Structure complète du serveur OPC UA ===\n")
    
    def _explore(client):
        explore_tree(client, "i=85", depth=0, max_depth=6, breadth_limit=100)
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
    except Exception as e:
        print(f"✗ Erreur: {e}")

if __name__ == "__main__":
    main()
