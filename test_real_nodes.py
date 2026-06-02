#!/usr/bin/env python3
"""
Test de lecture avec les vrais node IDs du Jeu de symboles
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.opcua_requests import _read_with_retry
from services.opcua_status import _get_opcua_config
from opcua.ua import NodeId

def test_read_variables(client):
    """Test la lecture des variables via le Jeu de symboles"""
    print("=== Test de lecture des variables ===\n")
    
    try:
        # Récupère le noeud Jeu de symboles
        objects_node = client.get_node("i=85")
        children = objects_node.get_children()
        symbol_set_node = children[4]  # Le "Jeu de symboles"
        
        # Récupère les enfants (les variables)
        variables = symbol_set_node.get_children()
        
        test_vars = ["EnergActL1", "rCpuLoad", "rTempC", "QtyProduced", "seuilRam"]
        
        for var_name in test_vars:
            # Cherche la variable par nom
            for var_node in variables:
                dn = var_node.get_display_name()
                if dn.Text == var_name:
                    try:
                        value = var_node.get_value()
                        print(f"✓ {var_name:20} = {value}")
                    except Exception as read_err:
                        print(f"✗ {var_name:20} LECTURE ERREUR: {read_err}")
                    break
            else:
                print(f"✗ {var_name:20} NON TROUVÉ")
        
        print("\n✓ Lecture réussie via le Jeu de symboles!")
        return True
    
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    config = _get_opcua_config()
    print(f"Serveur: {config['url']}\n")
    
    def _test(client):
        return test_read_variables(client)
    
    try:
        result = _read_with_retry(
            _test,
            url=config["url"],
            username=config["username"],
            password=config["password"],
            timeout=config["timeout"],
            security_config=config.get("security_config"),
        )
        print(f"\nRésultat: {result}")
    except Exception as e:
        print(f"✗ Erreur globale: {e}")

if __name__ == "__main__":
    main()
