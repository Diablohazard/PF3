#!/usr/bin/env python3
"""
Liste les choix enfants d'Objects pour trouver la structure réelle
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.opcua_requests import _read_with_retry
from services.opcua_status import _get_opcua_config

def show_children(client):
    """Affiche les enfants directs d'Objects"""
    print("=== Enfants directs d'Objects (i=85) ===\n")
    
    try:
        objects_node = client.get_node("i=85")
        children = objects_node.get_children()
        
        print(f"Total: {len(children)} enfants\n")
        
        for i, child in enumerate(children):
            try:
                dn = child.get_display_name()
                node_id = str(child.nodeid)
                node_class = child.get_node_class()
                class_name = str(node_class).split('.')[-1] if node_class else "?"
                
                # Essaie de lire la valeur si c'est une variable
                value_str = ""
                try:
                    if "Variable" in class_name:
                        value = child.get_value()
                        value_str = f" = {value}"
                except:
                    pass
                
                print(f"[{i:2}] {dn.Text:40} [{class_name:15}] {node_id}{value_str}")
                
                # Si c'est un objet, affiche ses enfants aussi
                if "Object" in class_name:
                    try:
                        sub_children = child.get_children()
                        if sub_children:
                            print(f"      └─ {len(sub_children)} enfants:")
                            for j, sub_child in enumerate(sub_children[:5]):
                                try:
                                    sub_dn = sub_child.get_display_name()
                                    sub_id = str(sub_child.nodeid)
                                    print(f"        [{ j}] {sub_dn.Text:35} {sub_id}")
                                except:
                                    pass
                            if len(sub_children) > 5:
                                print(f"        ... + {len(sub_children) - 5} autres")
                    except:
                        pass
                
            except Exception as e:
                print(f"[{i}] Erreur: {e}")
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    return True

def main():
    config = _get_opcua_config()
    print(f"Serveur: {config['url']}\n")
    
    def _show(client):
        return show_children(client)
    
    try:
        _read_with_retry(
            _show,
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
