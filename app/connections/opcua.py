# 1. Installer la bibliothèque : pip install opcua
from opcua import Client

# 2. Définir l'URL du serveur OPCUA de l'automate Wago CC100
url = "opc.tcp://192.168.0.100:4840"  # Remplace par l'adresse IP de ton automate

# 3. Créer le client et se connecter
client = Client(url)
try:
    client.connect()
    print("Connecté au serveur OPCUA Wago CC100")

    # 4. Lire une variable (exemple)
    node_id = "ns=2;s=MyVariable"  # Remplace par l'identifiant de ta variable
    node = client.get_node(node_id)
    value = node.get_value()
    print(f"Valeur lue : {value}")

    # 5. Écrire une variable (exemple)
    # node.set_value(42)  # Décommente et adapte pour écrire une valeur

finally:
    client.disconnect()
    print("Déconnecté du serveur OPCUA")