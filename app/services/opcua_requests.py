import atexit  # Importe un module ou un package.
import os  # Importe un module ou un package.
import threading  # Importe un module ou un package.

try:  # OPC UA est optionnel pour permettre le démarrage de l'app sans l'automate.
    from opcua import Client as SyncClient  # Importe un élément spécifique depuis un module.
    from opcua import ua  # Importe un élément spécifique depuis un module.
    from opcua.crypto import security_policies  # Importe un élément spécifique depuis un module.
    OPCUA_IMPORT_ERROR = None
except ImportError as exc:
    SyncClient = None
    ua = None
    security_policies = None
    OPCUA_IMPORT_ERROR = exc

try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
    from connections.opcua import fetch_server_endpoints  # Importe un élément spécifique depuis un module.
except ImportError:  # Capture et traite une exception.
    from app.connections.opcua import fetch_server_endpoints  # Importe un élément spécifique depuis un module.


# Mapping des noms internes vers les noms réels sur le serveur OPC UA.
# Les variables sont localisées dans le "Jeu de symboles" (namespace 5).
# Ce mapping est utilisé pour découvrir les nodes lors de la connexion.
VARIABLE_NAME_MAP = {  # Affecte une valeur à une variable.
    "energ_act_l1": "EnergActL1",  # Affecte une valeur à une variable.
    "energ_act_l2": "EnergActL2",  # Affecte une valeur à une variable.
    "energ_act_tot": "EnergActTot",  # Affecte une valeur à une variable.
    "total_time": "TotalTime",  # Affecte une valeur à une variable.
    "start_time": "StartTime",  # Affecte une valeur à une variable.
    "end_time": "EndTime",  # Affecte une valeur à une variable.
    "qty_produced": "QtyProduced",  # Affecte une valeur à une variable.
    "qty_target": "QtyTarget",  # Affecte une valeur à une variable.
    "cpu_load": "rCpuLoad",  # Affecte une valeur à une variable.
    "ram_usage": "rRamUsage",  # Affecte une valeur à une variable.
    "temp_c": "rTempC",  # Affecte une valeur à une variable.
    "seuil_ram": "seuilRam",  # Affecte une valeur à une variable.
    "seuil_cpu": "seuilCpu",  # Affecte une valeur à une variable.
    "seuil_temp": "seuilTemp",  # Affecte une valeur à une variable.
    "plann_ent_preh": "plannEntPreh",  # Affecte une valeur à une variable.
    "plann_net_rob": "plannNetRob",  # Affecte une valeur à une variable.
}  # Effectue une opération de traitement.

AUTOMATE_NODE_IDS = VARIABLE_NAME_MAP  # Compatibilité avec le code existant  # Affecte une valeur à une variable.

ALERT_THRESHOLD_KEYS = ("seuil_ram", "seuil_cpu", "seuil_temp")  # Affecte une valeur à une variable.


_persistent_client = None  # Affecte une valeur à une variable.
_persistent_client_config = None  # Affecte une valeur à une variable.
_persistent_client_lock = threading.Lock()  # Affecte une valeur à une variable.
_symbol_set_cache = None  # Cache pour les variables du Jeu de symboles  # Affecte une valeur à une variable.
_symbol_set_lock = threading.Lock()  # Lock pour accès thread-safe au cache  # Affecte une valeur à une variable.

# python-opcua exposes security policy classes under opcua.crypto.security_policies
# (not under opcua.ua in recent versions).
SECURITY_POLICY_BASIC256SHA256 = (
    security_policies.SecurityPolicyBasic256Sha256 if security_policies else None
)  # Affecte une valeur à une variable.


def _require_opcua():  # Définit la fonction _require_opcua.
    if OPCUA_IMPORT_ERROR is not None:
        raise RuntimeError(
            "La dépendance python-opcua n'est pas installée dans cette image Docker."
        ) from OPCUA_IMPORT_ERROR


def _get_symbol_set_variables(client):  # Définit la fonction _get_symbol_set_variables.
    """
    Découvre dynamiquement les variables OPC UA depuis le 'Jeu de symboles'.
    Retourne un dictionnaire {nom_variable: node_object}.
    """
    try:  # Tente d'exécuter un bloc de code pouvant lever une exception.
        objects = client.get_node("i=85")  # Objects node  # Effectue une opération de traitement.
        children = objects.get_children()  # Récupère les enfants  # Effectue une opération de traitement.
        
        symbol_set_node = None  # Affecte une valeur à une variable.
        for child in children:  # Boucle sur une séquence d'éléments.
            child_dn = child.get_display_name()  # Effectue une opération de traitement.
            if child_dn and child_dn.Text == "Jeu de symboles":  # Teste une condition.
                symbol_set_node = child  # Affecte une valeur à une variable.
                break  # Effectue une opération de traitement.

        if symbol_set_node is not None:  # Teste une condition.
            variables = symbol_set_node.get_children()  # Récupère les variables  # Affecte une valeur à une variable.
            var_map = {}  # Affecte une valeur à une variable.
            for var_node in variables:  # Boucle sur une séquence d'éléments.
                var_dn = var_node.get_display_name()  # Effectue une opération de traitement.
                if var_dn:  # Teste une condition.
                    var_map[var_dn.Text] = var_node  # Affecte une valeur à une variable.
            return var_map  # Retourne une valeur depuis la fonction.
    except Exception as exc:  # Capture et traite une exception.
        print(f"⚠ Erreur lors de la découverte des variables OPC UA: {exc}")  # Effectue une opération de traitement.
    
    return {}  # Retourne une valeur depuis la fonction.


def _resolve_node_reference(node_ref, client):  # Définit la fonction _resolve_node_reference.
    """
    Résout un référence de noeud OPC UA.
    - Si c'est un identifiant de symbole (par exemple "seuilRam"), on cherche dans le Jeu de symboles.
    - Si c'est un node id standard (ns=...), on l'utilise directement.
    """
    if isinstance(node_ref, str) and not node_ref.startswith("ns="):
        symbol_set_vars = _get_symbol_set_variables(client)
        if node_ref in symbol_set_vars:
            return symbol_set_vars[node_ref]
    return client.get_node(node_ref)


def _fetch_server_certificate(url, timeout=10):  # Définit la fonction _fetch_server_certificate.
    """
    Récupère automatiquement le certificat serveur via GetEndpoints (standard OPC UA).
    Le serveur envoie son certificat DER dans chaque descripteur d'endpoint sécurisé,
    sans authentification requise.
    Retourne le chemin du fichier enregistré, ou None si échec.
    """
    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        endpoints = fetch_server_endpoints(url, timeout=timeout)  # Affecte une valeur à une variable.
    except Exception as exc:  # Capture et traite une exception.
        print(f"⚠ Impossible de contacter le serveur pour récupérer le cert: {exc}")  # Effectue une opération de traitement.
        return None  # Retourne une valeur depuis la fonction.

    server_cert_bytes = None  # Affecte une valeur à une variable.
    for endpoint in endpoints:  # Boucle sur une séquence d’éléments.
        cert = getattr(endpoint, "ServerCertificate", None)  # Affecte une valeur à une variable.
        if cert and len(cert) > 0:  # Teste une condition.
            server_cert_bytes = bytes(cert)  # Affecte une valeur à une variable.
            break  # Effectue une opération de traitement.

    if not server_cert_bytes:  # Teste une condition.
        print("⚠ Le serveur n'a pas fourni de certificat dans ses endpoints.")  # Effectue une opération de traitement.
        return None  # Retourne une valeur depuis la fonction.

    certs_dir = os.path.join(os.path.dirname(__file__), "..", "certs")  # Affecte une valeur à une variable.
    os.makedirs(certs_dir, exist_ok=True)  # Affecte une valeur à une variable.
    cert_path = os.path.normpath(os.path.join(certs_dir, "server_cert.der"))  # Affecte une valeur à une variable.

    try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
        with open(cert_path, "wb") as f:  # Effectue une opération de traitement.
            f.write(server_cert_bytes)  # Effectue une opération de traitement.
        print(f"✓ Certificat serveur capturé automatiquement: {cert_path}")  # Effectue une opération de traitement.
        return cert_path  # Retourne une valeur depuis la fonction.
    except Exception as exc:  # Capture et traite une exception.
        print(f"⚠ Impossible d'écrire le certificat serveur: {exc}")  # Effectue une opération de traitement.
        return None  # Retourne une valeur depuis la fonction.


def _validate_security_config(security_config):  # Définit la fonction _validate_security_config.
    if not security_config:  # Teste une condition.
        return  # Retourne une valeur depuis la fonction.

    mode = (security_config.get("mode") or "None").strip()  # Affecte une valeur à une variable.
    if mode == "None":  # Teste une condition.
        return  # Retourne une valeur depuis la fonction.

    if mode != "SignAndEncrypt":  # Teste une condition.
        raise ValueError(f"Mode de securite OPC UA non supporte: {mode}")  # Effectue une opération de traitement.

    required_fields = ("client_cert", "client_key")  # Affecte une valeur à une variable.
    missing = [field for field in required_fields if not (security_config.get(field) or "").strip()]  # Affecte une valeur à une variable.
    if missing:  # Teste une condition.
        raise ValueError(  # Effectue une opération de traitement.
            f"Configuration OPC UA incomplete pour SignAndEncrypt: champs manquants {missing}"  # Effectue une opération de traitement.
        )  # Effectue une opération de traitement.

    for field in required_fields:  # Boucle sur une séquence d’éléments.
        path = (security_config.get(field) or "").strip()  # Affecte une valeur à une variable.
        if not os.path.isfile(path):  # Teste une condition.
            raise FileNotFoundError(  # Effectue une opération de traitement.
                f"Fichier de securite OPC UA introuvable pour {field}: {path}"  # Effectue une opération de traitement.
            )  # Effectue une opération de traitement.


def _is_sign_and_encrypt_config(security_config):  # Définit la fonction _is_sign_and_encrypt_config.
    return (security_config or {}).get("mode") == "SignAndEncrypt"  # Retourne une valeur depuis la fonction.


def _create_sync_client(url, username, password, timeout, security_config=None):  # Définit la fonction _create_sync_client.
    _require_opcua()
    _validate_security_config(security_config)  # Effectue une opération de traitement.

    client = SyncClient(url, timeout=timeout)  # Affecte une valeur à une variable.
    if username:  # Teste une condition.
        client.set_user(username)  # Effectue une opération de traitement.
        client.set_password(password)  # Effectue une opération de traitement.

    if (security_config or {}).get("mode") == "SignAndEncrypt":  # Teste une condition.
        server_cert = (security_config.get("server_cert") or "").strip()  # Affecte une valeur à une variable.

        # Si le cert serveur est absent, le capturer automatiquement via GetEndpoints
        if not server_cert or not os.path.isfile(server_cert):  # Teste une condition.
            print("ⓘ Certificat serveur manquant, tentative de capture automatique...")  # Effectue une opération de traitement.
            captured = _fetch_server_certificate(url, timeout)  # Affecte une valeur à une variable.
            if captured:  # Teste une condition.
                server_cert = captured  # Affecte une valeur à une variable.
            else:  # Traite le cas alternatif.
                raise FileNotFoundError(  # Effectue une opération de traitement.
                    "Certificat serveur OPC UA introuvable et capture automatique échouée. "  # Effectue une opération de traitement.
                    f"Placez manuellement le certificat dans {security_config.get('server_cert', 'app/certs/server_cert.der')}"  # Effectue une opération de traitement.
                )  # Effectue une opération de traitement.

        client.set_security(  # Effectue une opération de traitement.
            SECURITY_POLICY_BASIC256SHA256,  # Effectue une opération de traitement.
            security_config["client_cert"],  # Effectue une opération de traitement.
            security_config["client_key"],  # Effectue une opération de traitement.
            server_cert,  # Effectue une opération de traitement.
            ua.MessageSecurityMode.SignAndEncrypt,  # Effectue une opération de traitement.
        )  # Effectue une opération de traitement.

    return client  # Retourne une valeur depuis la fonction.


def _disconnect_persistent_client():  # Définit la fonction _disconnect_persistent_client.
    global _persistent_client, _persistent_client_config  # Effectue une opération de traitement.
    if _persistent_client is not None:  # Teste une condition.
        try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
            _persistent_client.disconnect()  # Effectue une opération de traitement.
        except Exception:  # Capture et traite une exception.
            pass  # Effectue une opération de traitement.
        finally:  # Exécute ce bloc quoi qu’il arrive.
            _persistent_client = None  # Affecte une valeur à une variable.
            _persistent_client_config = None  # Affecte une valeur à une variable.


def close_persistent_client():  # Définit la fonction close_persistent_client.
    with _persistent_client_lock:  # Effectue une opération de traitement.
        _disconnect_persistent_client()  # Effectue une opération de traitement.


def _ensure_persistent_client(url, username, password, timeout, security_config=None):  # Définit la fonction _ensure_persistent_client.
    global _persistent_client, _persistent_client_config  # Effectue une opération de traitement.

    desired_config = {  # Affecte une valeur à une variable.
        "url": url,  # Effectue une opération de traitement.
        "username": username,  # Effectue une opération de traitement.
        "password": password,  # Effectue une opération de traitement.
        "timeout": timeout,  # Effectue une opération de traitement.
        "security": security_config,  # Effectue une opération de traitement.
    }  # Effectue une opération de traitement.

    # Reconnect if configuration changed (URL/credentials/timeout).
    if _persistent_client is not None and _persistent_client_config != desired_config:  # Teste une condition.
        _disconnect_persistent_client()  # Effectue une opération de traitement.

    if _persistent_client is None:  # Teste une condition.
        try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
            _persistent_client = _create_sync_client(url, username, password, timeout, security_config)  # Affecte une variable.
            _persistent_client.connect()  # Effectue une opération de traitement.
            _persistent_client_config = desired_config  # Affecte une valeur à une variable.
        except Exception as exc:  # Capture et traite une exception.
            if _is_sign_and_encrypt_config(security_config):  # Teste une condition.
                # Ensure any partial/failed secure channel is fully disconnected
                _disconnect_persistent_client()
                # First try fallback: username/password over an unsecured endpoint
                try:
                    if username:  # If credentials provided, prefer username/password fallback
                        print("⚠ Connexion SignAndEncrypt échouée, tentative de fallback vers UserName (no security)...")
                        _persistent_client = _create_sync_client(url, username, password, timeout, security_config=None)
                        _persistent_client.connect()
                        _persistent_client_config = {
                            "url": url,
                            "username": username,
                            "password": password,
                            "timeout": timeout,
                            "security": None,
                        }
                        return _persistent_client
                    else:
                        # no username: try anonymous as last resort
                        print("⚠ Connexion SignAndEncrypt échouée, tentative de fallback vers anonymous (best-effort)...")
                        _persistent_client = _create_sync_client(url, "", "", timeout, security_config=None)
                        _persistent_client.connect()
                        _persistent_client_config = {
                            "url": url,
                            "username": "",
                            "password": "",
                            "timeout": timeout,
                            "security": None,
                        }
                        return _persistent_client
                except Exception as fallback_exc:  # Capture et traite une exception.
                    print(f"⚠ Fallback impossible: {fallback_exc}")  # Effectue une opération de traitement.
            raise exc  # Effectue une opération de traitement.

    return _persistent_client  # Retourne une valeur depuis la fonction.


def _read_with_retry(read_operation, url, username, password, timeout, security_config=None):  # Définit la fonction _read_with_retry.
    with _persistent_client_lock:  # Effectue une opération de traitement.
        try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
            client = _ensure_persistent_client(url, username, password, timeout, security_config)  # Affecte une valeur à une variable.
            return read_operation(client)  # Retourne une valeur depuis la fonction.
        except Exception:  # Capture et traite une exception.
            # Force reconnect once, then retry the same operation.
            _disconnect_persistent_client()  # Effectue une opération de traitement.
            client = _ensure_persistent_client(url, username, password, timeout, security_config)  # Affecte une valeur à une variable.
            return read_operation(client)  # Retourne une valeur depuis la fonction.


def server_accepts_anonymous(url, timeout=10):  # Définit la fonction server_accepts_anonymous.
    _require_opcua()
    endpoints = fetch_server_endpoints(url, timeout=timeout)  # Affecte une valeur à une variable.

    for endpoint in endpoints:  # Boucle sur une séquence d’éléments.
        for token in endpoint.UserIdentityTokens:  # Boucle sur une séquence d’éléments.
            if token.TokenType == ua.UserTokenType.Anonymous:  # Teste une condition.
                return True  # Retourne une valeur depuis la fonction.

    return False  # Retourne une valeur depuis la fonction.


def server_supports_sign_and_encrypt(url, timeout=10):  # Définit la fonction server_supports_sign_and_encrypt.
    _require_opcua()
    endpoints = fetch_server_endpoints(url, timeout=timeout)  # Affecte une valeur à une variable.

    for endpoint in endpoints:  # Boucle sur une séquence d’éléments.
        if (  # Teste une condition.
            endpoint.SecurityMode == ua.MessageSecurityMode.SignAndEncrypt  # Affecte une valeur à une variable.
            and endpoint.SecurityPolicyUri == SECURITY_POLICY_BASIC256SHA256.URI  # Affecte une valeur à une variable.
        ):  # Effectue une opération de traitement.
            return True  # Retourne une valeur depuis la fonction.

    return False  # Retourne une valeur depuis la fonction.


def read_node_value_sync(url, username, password, node_id, timeout=10, security_config=None):  # Définit la fonction read_node_value_sync.
    def _operation(client):  # Définit la fonction _operation.
        node = client.get_node(node_id)  # Affecte une valeur à une variable.
        return node.get_value()  # Retourne une valeur depuis la fonction.

    return _read_with_retry(  # Retourne une valeur depuis la fonction.
        _operation,  # Effectue une opération de traitement.
        url=url,  # Affecte une valeur à une variable.
        username=username,  # Affecte une valeur à une variable.
        password=password,  # Affecte une valeur à une variable.
        timeout=timeout,  # Affecte une valeur à une variable.
        security_config=security_config,  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement.


def read_named_nodes_sync(url, username, password, node_ids, timeout=10, security_config=None):  # Définit la fonction read_named_nodes_sync.
    def _operation(client):  # Définit la fonction _operation.
        values = {}  # Affecte une valeur à une variable.
        errors = {}  # Affecte une valeur à une variable.

        # Découvre les variables depuis le "Jeu de symboles" si node_ids contient des noms au lieu d'IDs
        symbol_set_vars = _get_symbol_set_variables(client)  # Affecte une valeur à une variable.

        for name, node_ref in node_ids.items():  # Boucle sur une séquence d’éléments.
            try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
                if isinstance(node_ref, str) and not node_ref.startswith("ns="):  # Teste une condition.
                    if node_ref in symbol_set_vars:  # Teste une condition.
                        node = symbol_set_vars[node_ref]  # Affecte une valeur à une variable.
                    else:  # Effectue une opération de traitement.
                        raise RuntimeError(f"Variable '{node_ref}' non trouvée dans le Jeu de symboles")  # Effectue une opération de traitement.
                else:  # Effectue une opération de traitement.
                    node = client.get_node(node_ref)  # Affecte une valeur à une variable.

                values[name] = node.get_value()  # Affecte une valeur à une variable.
            except Exception as exc:  # Capture et traite une exception.
                values[name] = None  # Affecte une valeur à une variable.
                errors[name] = str(exc)  # Affecte une valeur à une variable.

        # Si rien n'est lisible, on remonte une erreur claire au code appelant.
        if errors and len(errors) == len(node_ids):  # Teste une condition.
            raise RuntimeError(f"Aucune variable OPC UA lisible: {errors}")  # Effectue une opération de traitement.

        return values  # Retourne une valeur depuis la fonction.

    return _read_with_retry(  # Retourne une valeur depuis la fonction.
        _operation,  # Effectue une opération de traitement.
        url=url,  # Affecte une valeur à une variable.
        username=username,  # Affecte une valeur à une variable.
        password=password,  # Affecte une valeur à une variable.
        timeout=timeout,  # Affecte une valeur à une variable.
        security_config=security_config,  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement.



def read_automate_variables_sync(url, username, password, timeout=10, security_config=None):  # Définit la fonction read_automate_variables_sync.
    return read_named_nodes_sync(  # Retourne une valeur depuis la fonction.
        url=url,  # Affecte une valeur à une variable.
        username=username,  # Affecte une valeur à une variable.
        password=password,  # Affecte une valeur à une variable.
        node_ids=AUTOMATE_NODE_IDS,  # Affecte une valeur à une variable.
        timeout=timeout,  # Affecte une valeur à une variable.
        security_config=security_config,  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement.


def _coerce_value_for_variant_type(value, variant_type):  # Définit la fonction _coerce_value_for_variant_type.
    _require_opcua()
    if variant_type in (  # Teste une condition.
        ua.VariantType.SByte,  # Effectue une opération de traitement.
        ua.VariantType.Byte,  # Effectue une opération de traitement.
        ua.VariantType.Int16,  # Effectue une opération de traitement.
        ua.VariantType.UInt16,  # Effectue une opération de traitement.
        ua.VariantType.Int32,  # Effectue une opération de traitement.
        ua.VariantType.UInt32,  # Effectue une opération de traitement.
        ua.VariantType.Int64,  # Effectue une opération de traitement.
        ua.VariantType.UInt64,  # Effectue une opération de traitement.
    ):  # Effectue une opération de traitement.
        return int(float(value))  # Retourne une valeur depuis la fonction.

    if variant_type in (ua.VariantType.Float, ua.VariantType.Double):  # Teste une condition.
        return float(value)  # Retourne une valeur depuis la fonction.

    if variant_type == ua.VariantType.Boolean:  # Teste une condition.
        if isinstance(value, str):  # Teste une condition.
            return value.strip().lower() in ("1", "true", "yes", "on")  # Retourne une valeur depuis la fonction.
        return bool(value)  # Retourne une valeur depuis la fonction.

    return value  # Retourne une valeur depuis la fonction.


def _set_node_value_with_node_type(node, value):  # Définit la fonction _set_node_value_with_node_type.
    variant_type = node.get_data_type_as_variant_type()  # Affecte une valeur à une variable.
    typed_value = _coerce_value_for_variant_type(value, variant_type)  # Affecte une valeur à une variable.
    node.set_value(ua.Variant(typed_value, variant_type))  # Effectue une opération de traitement.
    return variant_type  # Retourne une valeur depuis la fonction.


def write_node_value_sync(url, username, password, node_id, value, timeout=10, security_config=None):  # Définit la fonction write_node_value_sync.
    # Ecrit une valeur sur un noeud OPC UA en réutilisant la même session persistante.
    def _operation(client):  # Définit la fonction _operation.
        node = _resolve_node_reference(node_id, client)  # Affecte une valeur à une variable.
        _set_node_value_with_node_type(node, value)  # Effectue une opération de traitement.
        return True  # Retourne une valeur depuis la fonction.

    return _read_with_retry(  # Retourne une valeur depuis la fonction.
        _operation,  # Effectue une opération de traitement.
        url=url,  # Affecte une valeur à une variable.
        username=username,  # Affecte une valeur à une variable.
        password=password,  # Affecte une valeur à une variable.
        timeout=timeout,  # Affecte une valeur à une variable.
        security_config=security_config,  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement.


def write_named_nodes_sync(url, username, password, node_values, timeout=10, security_config=None):  # Définit la fonction write_named_nodes_sync.
    # Ecriture groupée: on suit les succès/erreurs par clé pour faciliter le diagnostic.
    def _operation(client):  # Définit la fonction _operation.
        results = {}  # Affecte une valeur à une variable.
        errors = {}  # Affecte une valeur à une variable.
        for name, payload in node_values.items():  # Boucle sur une séquence d’éléments.
            try:  # Tente d’exécuter un bloc de code pouvant lever une exception.
                node = _resolve_node_reference(payload["node_id"], client)  # Affecte une valeur à une variable.
                _set_node_value_with_node_type(node, payload["value"])  # Effectue une opération de traitement.
                results[name] = True  # Affecte une valeur à une variable.
            except Exception as exc:  # Capture et traite une exception.
                results[name] = False  # Affecte une valeur à une variable.
                errors[name] = str(exc)  # Affecte une valeur à une variable.

        if errors and len(errors) == len(node_values):  # Teste une condition.
            raise RuntimeError(f"Aucun seuil OPC UA ecrit: {errors}")  # Effectue une opération de traitement.

        return {"ok": True, "results": results, "errors": errors}  # Retourne une valeur depuis la fonction.

    return _read_with_retry(  # Retourne une valeur depuis la fonction.
        _operation,  # Effectue une opération de traitement.
        url=url,  # Affecte une valeur à une variable.
        username=username,  # Affecte une valeur à une variable.
        password=password,  # Affecte une valeur à une variable.
        timeout=timeout,  # Affecte une valeur à une variable.
        security_config=security_config,  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement.


def read_alert_thresholds_sync(url, username, password, timeout=10, security_config=None):  # Définit la fonction read_alert_thresholds_sync.
    # Lecture ciblée des seuils d'alerte (RAM/CPU/TEMP) pour l'UI de paramétrage.
    node_ids = {key: AUTOMATE_NODE_IDS[key] for key in ALERT_THRESHOLD_KEYS}  # Affecte une valeur à une variable.
    return read_named_nodes_sync(  # Retourne une valeur depuis la fonction.
        url=url,  # Affecte une valeur à une variable.
        username=username,  # Affecte une valeur à une variable.
        password=password,  # Affecte une valeur à une variable.
        node_ids=node_ids,  # Affecte une valeur à une variable.
        timeout=timeout,  # Affecte une valeur à une variable.
        security_config=security_config,  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement.


def write_alert_thresholds_sync(url, username, password, thresholds, timeout=10, security_config=None):  # Définit la fonction write_alert_thresholds_sync.
    # Conversion du payload fonctionnel -> mapping noeud OPC UA / valeur.
    node_values = {}  # Affecte une valeur à une variable.
    for key in ALERT_THRESHOLD_KEYS:  # Boucle sur une séquence d’éléments.
        if key not in thresholds:  # Teste une condition.
            continue  # Effectue une opération de traitement.
        node_values[key] = {  # Affecte une valeur à une variable.
            "node_id": AUTOMATE_NODE_IDS[key],  # Effectue une opération de traitement.
            "value": float(thresholds[key]),  # Effectue une opération de traitement.
        }  # Effectue une opération de traitement.

    if not node_values:  # Teste une condition.
        raise ValueError("Aucun seuil a ecrire")  # Effectue une opération de traitement.

    return write_named_nodes_sync(  # Retourne une valeur depuis la fonction.
        url=url,  # Affecte une valeur à une variable.
        username=username,  # Affecte une valeur à une variable.
        password=password,  # Affecte une valeur à une variable.
        node_values=node_values,  # Affecte une valeur à une variable.
        timeout=timeout,  # Affecte une valeur à une variable.
        security_config=security_config,  # Affecte une valeur à une variable.
    )  # Effectue une opération de traitement.


atexit.register(close_persistent_client)  # Effectue une opération de traitement.
