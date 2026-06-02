#!/usr/bin/env python3
"""
Script de diagnostic OPC UA pour explorer la structure du serveur
et trouver les vrais node IDs des variables.
"""
import sys
sys.path.insert(0, './app')

from opcua import Client
from opcua.ua import NodeClass

def explore_node(node, depth=0, max_depth=4, parent_path=""):
    """Explore récursivement les nœuds OPC UA"""
    if depth > max_depth:
        return
    
    try:
        # Récupère les informations du nœud
        display_name = node.get_display_name().Text
        node_id = node.nodeid
        node_class = node.get_node_class()
        
        # Format affichage
        indent = "  " * depth
        class_name = str(node_class).split('.')[-1] if node_class else "?"
        print(f"{indent}├─ [{class_name}] {display_name} → {node_id}")
        
        # Cherche les variables contenant les noms attendus
        search_terms = ["Energ", "Time", "Qty", "Cpu", "Ram", "Temp", "seuil", "plann"]
        for term in search_terms:
            if term.lower() in display_name.lower():
                print(f"{indent}   ✓ MATCH: {display_name} = {node_id}")
        
        # Explore les enfants si c'est un objet/dossier
        if node_class in [NodeClass.Object, NodeClass.Variable]:
            try:
                children = node.get_children()
                for child in children:
                    explore_node(child, depth + 1, max_depth, parent_path + "/" + display_name)
            except:
                pass
    except Exception as e:
        pass

def main():
    try:
        from app.services.opcua_status import _get_opcua_config
    except ImportError:
        from services.opcua_status import _get_opcua_config
    
    config = _get_opcua_config()
    print(f"Configuration OPC UA: {config}\n")
    
    client = Client(config['url'])
    try:
        # Essaie d'abord SANS credentials
        print("Tentative de connexion ANONYME (sans credentials)...")
        client.connect()
        print("✓ Connecté au serveur OPC UA (anonyme)\n")
        
        # Récupère le root node
        root = client.get_root_node()
        print("=== Structure du serveur OPC UA ===\n")
        
        # Explore depuis les nœuds objects standard
        try:
            objects = client.get_objects_node()
            print("📁 Objects:")
            explore_node(objects, depth=1, max_depth=3)
        except Exception as e:
            print(f"Erreur lors de l'exploration: {e}")
        
        print("\n=== Recherche spécifique des variables ===\n")
        # Essaie de trouver GVL_OPCUA directement
        expected_node_ids = [
            "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA",
            "ns=3;s=|var|172.30.30.10.Application.GVL_OPCUA",
            "ns=2;s=|var|172.30.30.10.Application.GVL_OPCUA",
        ]
        
        for node_id_str in expected_node_ids:
            try:
                from opcua.ua import NodeId
                node_id = NodeId.from_string(node_id_str)
                node = client.get_node(node_id)
                print(f"✓ Trouvé: {node_id_str}")
                # Explore les enfants
                explore_node(node, depth=1, max_depth=2)
            except:
                pass
        
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            client.disconnect()
        except:
            pass

if __name__ == "__main__":
    main()
