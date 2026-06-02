#!/usr/bin/env python3
"""
Explore le node "Jeu de symboles" pour trouver les vraies variables
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.opcua_requests import _read_with_retry
from services.opcua_status import _get_opcua_config

def explore_symbols(client):
    """Explore le Symbol Set pour trouver les variables"""
    print("=== Exploration du 'Jeu de symboles' ===\n")
    
    # Le ByteStringNodeId du Jeu de symboles
    symbol_set_id = "nl=2;s=b'\x01\x00\x00\x00\xa6\xe1*q\x8a\xf73:\xa3\xe654\x8d\xe6`g\x90\xee\"{\\xe63\x14'"
    # Ou plus simplement, on peut parcourir Objects et prendre le 5e enfant
    
    try:
        objects_node = client.get_node("i=85")
        children = objects_node.get_children()
        
        if len(children) > 4:
            symbol_set_node = children[4]  # Le "Jeu de symboles"
            dn = symbol_set_node.get_display_name()
            print(f"Nœud trouvé: {dn.Text}\n")
            
            # Explore les enfants du Jeu de symboles
            sub_children = symbol_set_node.get_children()
            print(f"Enfants du Jeu de symboles: {len(sub_children)}\n")
            
            for i, child in enumerate(sub_children):
                try:
                    child_dn = child.get_display_name()
                    child_id = str(child.nodeid)
                    node_class = child.get_node_class()
                    class_name = str(node_class).split('.')[-1] if node_class else "?"
                    
                    print(f"[{i:3}] {child_dn.Text:50} [{class_name:15}] {child_id}")
                    
                    # Si c'est un objet, affiche aussi ses enfants jusqu'à 3 niveaux
                    if "Object" in class_name or "Variable" not in class_name:
                        try:
                            subsub_children = child.get_children()
                            if subsub_children:
                                for j, subsub in enumerate(subsub_children[:10]):
                                    try:
                                        subsub_dn = subsub.get_display_name()
                                        subsub_id = str(subsub.nodeid)
                                        subsub_class = subsub.get_node_class()
                                        subsub_cls_name = str(subsub_class).split('.')[-1] if subsub_class else "?"
                                        print(f"  └─[{j:2}] {subsub_dn.Text:45} [{subsub_cls_name:15}] {subsub_id}")
                                        
                                        # Check if this has keywords
                                        keywords = ["Energ", "Time", "Qty", "Cpu", "Ram", "Temp", "seuil", "plann", "GVL", "Application"]
                                        if any(kw.lower() in subsub_dn.Text.lower() for kw in keywords):
                                            print(f"     ✓✓✓ MATCH: {subsub_id}")
                                    except:
                                        pass
                                if len(subsub_children) > 10:
                                    print(f"    ... + { len(subsub_children) - 10} autres")
                        except:
                            pass
                    
                    # Check for keywords
                    keywords = ["Energ", "Time",  "Qty", "Cpu", "Ram", "Temp", "seuil", "plann", "GVL", "Application"]
                    if any(kw.lower() in child_dn.Text.lower() for kw in keywords):
                        print(f"✓✓✓ MATCH KEYWORD: {child_id}")
                        
                except Exception as e:
                    print(f"[{i}] Erreur: {e}")
        else:
            print("✗ Pas assez d'enfants sous Objects")
        
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    return True

def main():
    config = _get_opcua_config()
    print(f"Serveur: {config['url']}\n")
    
    def _explore(client):
        return explore_symbols(client)
    
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
