#!/usr/bin/env python3
"""
Script interactif pour explorer les nodes OPC UA du serveur et trouver les vrais IDs.
Utilise les mêmes connexions que le code principal.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from opcua import Client
from opcua.ua import NodeClass
import time

def browse_node(client, node, depth=0, max_depth=3, target_keywords=None):
    """Browse and display node tree"""
    if target_keywords is None:
        target_keywords = ["Energ", "Time", "Qty", "Cpu", "Ram", "Temp", "seuil", "plann", "GVL"]
    
    if depth > max_depth:
        return
    
    try:
        display_name = node.get_display_name().Text
        node_id = str(node.nodeid)
        
        # Check for keywords
        has_keyword = any(kw.lower() in display_name.lower() for kw in target_keywords)
        marker = "✓ " if has_keyword else ""
        
        indent = "  " * depth
        print(f"{indent}{marker}{display_name} → {node_id}")
        
        # Browse children if not too deep
        if depth < max_depth:
            try:
                children = node.get_children()
                if children:
                    for child in children[:20]:  # Limit to first 20 children
                        browse_node(client, child, depth + 1, max_depth, target_keywords)
            except:
                pass
                
    except Exception as e:
        pass

def main():
    print("=== Explorateur OPC UA Server ===\n")
    
    # Configuration
    url = "opc.tcp://172.30.30.10:4840"
    username = "admin"
    password = "wago"
    
    client = Client(url)
    # Set credentials BEFORE connect
    client.set_user(username)
    client.set_password(password)
    
    try:
        print(f"Connexion à {url}...\n")
        # Créer la connexion avec credentials
        # Try to establish connection with credentials
        client.connect()
        
        print("✓ Connexion établie\n")
        print("=== Exploration de la structure ===\n")
        
        # Get root and explore
        root = client.get_root_node()
        objects = client.get_objects_node()
        browse_node(client, objects, depth=0, max_depth=4)
        
        print("\n\n=== Recherche directe de GVL_OPCUA ===")
        # Try browsing from objects directly
        try:
            print("\nTentative via OPC UA Browse...")
            refs = objects.get_references()
            for ref in refs[:5]:
                try:
                    child = ref.target_node
                    if child:
                        print(f"  - {child.get_display_name().Text}")
                except:
                    pass
        except Exception as e:
            print(f"  Erreur: {e}")
            
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            client.close_session()
        except:
            pass
        try:
            client.disconnect()
        except:
            pass

if __name__ == "__main__":
    main()
