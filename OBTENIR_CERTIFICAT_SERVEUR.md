# Guide: Obtenir le certificat serveur WAGO pour SignAndEncrypt

## Option A: Via l'interface web du WAGO (RECOMMANDÉ)

1. Accède à l'interface web du WAGO: http://172.30.30.10 (ou https:// selon config)
2. Va dans "Paramètres > Sécurité > Certificats" (ou équivalent selon version)
3. Localise le certificat OPC UA ou du serveur
4. Télécharge-le en format DER (ou .cer, puis convertis-le)
5. Place-le dans: `app/certs/server_cert.der`

## Option B: Via SSH sur le WAGO

```bash
# Connexion SSH au WAGO
ssh admin@172.30.30.10

# Chercher les certificats (emplacements courants WAGO)
find /etc -name "*.der" -o -name "*.pem" 2>/dev/null
find /opt -name "*.der" -o -name "*.pem" 2>/dev/null
find /var -name "*.der" -o -name "*.pem" 2>/dev/null

# Copier le certificat (exemple)
scp admin@172.30.30.10:/chemin/vers/server.der app/certs/server_cert.der
```

Emplacements typiques WAGO:
- `/etc/ssl/certs/`
- `/opt/codesys/certs/`
- `/home/admin/.opcua/`
- Le WAGO WebServer (si HTTPS)

## Option C: Si le serveur est configuré OPC UA UA avec certificats

Utilise cet outil Python pour extraire automatiquement le cert du serveur:

```python
from opcua import Client
import ssl
import os

client = Client("opc.tcp://172.30.30.10:4840")
# Sans sécurité pour juste récupérer l'endpoint
try:
    client.connect()
    # Récupérer endpoint info
    endpoints = client.get_endpoints()
    for ep in endpoints:
        if ep.SecurityPolicyUri == "http://opcfoundation.org/UA/SecurityPolicy#Basic256Sha256":
            print(f"Endpoint trouvé: {ep}")
    client.disconnect()
except Exception as e:
    print(f"Erreur: {e}")
```

## Vérifier les certificats générés

```bash
# Afficher info client cert
openssl x509 -inform DER -in app/certs/client_cert.der -text -noout

# Afficher info clé privée
openssl pkey -in app/certs/client_key.pem -text -noout

# Afficher info serveur cert (une fois en place)
openssl x509 -inform DER -in app/certs/server_cert.der -text -noout
```

## Une fois le cert serveur en place

1. Place le fichier `server_cert.der` dans `app/certs/`
2. Dans le `.env`, mets: `OPCUA_SECURITY_MODE=SignAndEncrypt`
3. Redémarre l'application
4. Test: les logs doivent montrer "Connexion OPC UA sécurisée"
