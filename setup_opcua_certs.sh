#!/bin/bash

# Script de setup des certificats OPC UA SignAndEncrypt
# Usage: ./setup_opcua_certs.sh [OPCUA_SERVER_URL]

OPCUA_SERVER="${1:-172.30.30.10:4840}"
OPCUA_HOST=$(echo "$OPCUA_SERVER" | cut -d: -f1)
CERTS_DIR="app/certs"

echo "=== Setup certificats OPC UA SignAndEncrypt ==="
echo "Serveur OPC UA: $OPCUA_SERVER"
echo "Répertoire certs: $CERTS_DIR"

# Créer le répertoire certs s'il n'existe pas
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

# ============================================================================
# ÉTAPE 1: Récupérer le certificat serveur depuis le serveur OPC UA
# ============================================================================
echo ""
echo "[1/3] Récupération du certificat serveur..."

if timeout 5 openssl s_client -connect "$OPCUA_SERVER" -tls1_2 2>/dev/null </dev/null | \
   openssl x509 -outform DER -out server_cert.der 2>/dev/null; then
    echo "✓ Certificat serveur récupéré: server_cert.der"
else
    echo "⚠ Impossible de récupérer le cert serveur via TLS"
    echo "  Tentative via endpoint discovery OPC UA..."
    
    # Alternative: script Python pour extraire le cert via OPC UA
    python3 << 'PYTHON_SCRIPT'
import socket
import sys
import subprocess

OPCUA_HOST = sys.argv[1] if len(sys.argv) > 1 else "172.30.30.10"
OPCUA_PORT = 4840

try:
    # Connexion socket pour récupérer le cert
    sock = socket.create_connection((OPCUA_HOST, OPCUA_PORT), timeout=5)
    # Lecture du hello OPC UA (les certs peuvent être dedans)
    data = sock.recv(1024)
    sock.close()
    print("Connexion établie, mais extraction manuelle nécessaire")
except Exception as e:
    print(f"Erreur: {e}")
PYTHON_SCRIPT
    
    echo "  → Télécharge manuellement le cert du serveur WAGO via son interface web"
    echo "  → Place-le dans $CERTS_DIR/server_cert.der"
fi

# ============================================================================
# ÉTAPE 2: Générer la clé privée client
# ============================================================================
echo ""
echo "[2/3] Génération de la clé privée client..."

if [ ! -f "client_key.pem" ]; then
    openssl genrsa -out client_key.pem 2048 2>/dev/null
    echo "✓ Clé privée client générée: client_key.pem"
else
    echo "✓ Clé privée existante: client_key.pem"
fi

# ============================================================================
# ÉTAPE 3: Générer le certificat client auto-signé
# ============================================================================
echo ""
echo "[3/3] Génération du certificat client..."

if [ ! -f "client_cert.der" ]; then
    # Générer un CSR
    openssl req -new \
        -key client_key.pem \
        -out client.csr \
        -subj "/CN=opcua_client/O=PF3/C=FR" 2>/dev/null
    
    # Auto-signer le certificat
    openssl x509 -req -days 3650 \
        -in client.csr \
        -signkey client_key.pem \
        -out client_cert.der \
        -outform DER 2>/dev/null
    
    rm -f client.csr
    echo "✓ Certificat client généré: client_cert.der"
else
    echo "✓ Certificat client existant: client_cert.der"
fi

# ============================================================================
# Afficher le résumé
# ============================================================================
cd - > /dev/null

echo ""
echo "=== Résumé ===" 
echo "Fichiers créés:"
ls -lh "$CERTS_DIR"/"*.der" "$CERTS_DIR"/"*.pem" 2>/dev/null || echo "Aucun fichier trouvé"

echo ""
echo "Configuration .env requise:"
echo "  OPCUA_SECURITY_MODE=SignAndEncrypt"
echo "  OPCUA_CLIENT_CERT=app/certs/client_cert.der"
echo "  OPCUA_CLIENT_KEY=app/certs/client_key.pem"
echo "  OPCUA_SERVER_CERT=app/certs/server_cert.der"

echo ""
echo "✓ Setup terminé!"
