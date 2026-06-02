#!/usr/bin/env python3
"""
Génère le mapping correct des node IDs depuis le Jeu de symboles.
Cet output peut être utilisé pour mettre à day le code.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.opcua_requests import _read_with_retry
from services.opcua_status import _get_opcua_config

def get_symbol_set_variables(client):
    """Retourne toutes les variables du Jeu de symboles"""
    try:
        objects = client.get_node("i=85")
        children = objects.get_children()
        
        # Le Jeu de symboles est le 5e enfant (index 4)
        if len(children) > 4:
            symbol_set = children[4]
            variables = symbol_set.get_children()
            
            var_map = {}
            for var in variables:
                dn = var.get_display_name()
                var_map[dn.Text] = var
            
            return var_map
        return {}
    except Exception as e:
        print(f"Erreur: {e}")
        return {}

def get_node_id_string(node):
    """Convertit un node OPC UA en string NodeId"""
    return str(node.nodeid)

def main():
    config = _get_opcua_config()
    
    def _get_vars(client):
        var_map = get_symbol_set_variables(client)
        
        print("# Mapping des variables réelles du serveur OPC UA")
        print("# Copier dans opcua_requests.py en remplaçant AUTOMATE_NODE_IDS")
        print()
        print("AUTOMATE_NODE_IDS = {")
        
        # Mapping des noms attendus par le code vers les noms réels du serveur
        name_mapping = {
            "energ_act_l1": "EnergActL1",
            "energ_act_l2": "EnergActL2",
            "energ_act_tot": "EnergActTot",
            "total_time": "TotalTime",
            "start_time": "StartTime",
            "end_time": "EndTime",
            "qty_produced": "QtyProduced",
            "qty_target": "QtyTarget",
            "cpu_load": "rCpuLoad",
            "ram_usage": "rRamUsage",
            "temp_c": "rTempC",
            "seuil_ram": "seuilRam",
            "seuil_cpu": "seuilCpu",
            "seuil_temp": "seuilTemp",
            "plann_ent_preh": "plannEntPreh",
            "plann_net_rob": "plannNetRob",
        }
        
        for code_name, server_name in name_mapping.items():
            if server_name in var_map:
                node_id_str = get_node_id_string(var_map[server_name])
                print(f'    "{code_name}": "{node_id_str}",  # {server_name}')
            else:
                print(f'    # "{code_name}": NOT_FOUND,  # {server_name}')
        
        print("}")
        
        # Affiche aussi les variables trouvées
        print("\n# Variables trouvées sur le serveur:")
        for i, (name, node) in enumerate(var_map.items()):
            try:
                value = node.get_value()
                print(f"#  {i:2}. {name:20} = {value}")
            except:
                print(f"#  {i:2}. {name:20} = (erreur lecture)")
        
        return True
    
    try:
        _read_with_retry(
            _get_vars,
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
