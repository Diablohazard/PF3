import atexit
import os
import threading

from opcua import Client as SyncClient
from opcua import ua
from opcua.crypto import security_policies

try:
    from connections.opcua import fetch_server_endpoints
except ImportError:
    from app.connections.opcua import fetch_server_endpoints


AUTOMATE_NODE_IDS = {
    "energ_act_l1": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActL1",
    "energ_act_l2": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActL2",
    "energ_act_tot": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EnergActTot",
    "total_time": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.TotalTime",
    "start_time": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.StartTime",
    "end_time": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.EndTime",
    "qty_produced": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.QtyProduced",
    "qty_target": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.QtyTarget",
    "cpu_load": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.rCpuLoad",
    "ram_usage": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.rRamUsage",
    "temp_c": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.rTempC",
    "seuil_ram": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.seuilRam",
    "seuil_cpu": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.seuilCpu",
    "seuil_temp": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.seuilTemp",
    "plann_ent_preh": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.plannEntPreh",
    "plann_net_rob": "ns=4;s=|var|172.30.30.10.Application.GVL_OPCUA.plannNetRob",
}

ALERT_THRESHOLD_KEYS = ("seuil_ram", "seuil_cpu", "seuil_temp")


_persistent_client = None
_persistent_client_config = None
_persistent_client_lock = threading.Lock()

# python-opcua exposes security policy classes under opcua.crypto.security_policies
# (not under opcua.ua in recent versions).
SECURITY_POLICY_BASIC256SHA256 = security_policies.SecurityPolicyBasic256Sha256


def _fetch_server_certificate(url, timeout=10):
    """
    Récupère automatiquement le certificat serveur via GetEndpoints (standard OPC UA).
    Le serveur envoie son certificat DER dans chaque descripteur d'endpoint sécurisé,
    sans authentification requise.
    Retourne le chemin du fichier enregistré, ou None si échec.
    """
    try:
        endpoints = fetch_server_endpoints(url, timeout=timeout)
    except Exception as exc:
        print(f"⚠ Impossible de contacter le serveur pour récupérer le cert: {exc}")
        return None

    server_cert_bytes = None
    for endpoint in endpoints:
        cert = getattr(endpoint, "ServerCertificate", None)
        if cert and len(cert) > 0:
            server_cert_bytes = bytes(cert)
            break

    if not server_cert_bytes:
        print("⚠ Le serveur n'a pas fourni de certificat dans ses endpoints.")
        return None

    certs_dir = os.path.join(os.path.dirname(__file__), "..", "certs")
    os.makedirs(certs_dir, exist_ok=True)
    cert_path = os.path.normpath(os.path.join(certs_dir, "server_cert.der"))

    try:
        with open(cert_path, "wb") as f:
            f.write(server_cert_bytes)
        print(f"✓ Certificat serveur capturé automatiquement: {cert_path}")
        return cert_path
    except Exception as exc:
        print(f"⚠ Impossible d'écrire le certificat serveur: {exc}")
        return None


def _validate_security_config(security_config):
    if not security_config:
        return

    mode = (security_config.get("mode") or "None").strip()
    if mode == "None":
        return

    if mode != "SignAndEncrypt":
        raise ValueError(f"Mode de securite OPC UA non supporte: {mode}")

    required_fields = ("client_cert", "client_key")
    missing = [field for field in required_fields if not (security_config.get(field) or "").strip()]
    if missing:
        raise ValueError(
            f"Configuration OPC UA incomplete pour SignAndEncrypt: champs manquants {missing}"
        )

    for field in required_fields:
        path = (security_config.get(field) or "").strip()
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"Fichier de securite OPC UA introuvable pour {field}: {path}"
            )


def _create_sync_client(url, username, password, timeout, security_config=None):
    _validate_security_config(security_config)

    client = SyncClient(url, timeout=timeout)
    if username:
        client.set_user(username)
        client.set_password(password)

    if (security_config or {}).get("mode") == "SignAndEncrypt":
        server_cert = (security_config.get("server_cert") or "").strip()

        # Si le cert serveur est absent, le capturer automatiquement via GetEndpoints
        if not server_cert or not os.path.isfile(server_cert):
            print("ⓘ Certificat serveur manquant, tentative de capture automatique...")
            captured = _fetch_server_certificate(url, timeout)
            if captured:
                server_cert = captured
            else:
                raise FileNotFoundError(
                    "Certificat serveur OPC UA introuvable et capture automatique échouée. "
                    f"Placez manuellement le certificat dans {security_config.get('server_cert', 'app/certs/server_cert.der')}"
                )

        client.set_security(
            SECURITY_POLICY_BASIC256SHA256,
            security_config["client_cert"],
            security_config["client_key"],
            server_cert,
            ua.MessageSecurityMode.SignAndEncrypt,
        )

    return client


def _disconnect_persistent_client():
    global _persistent_client, _persistent_client_config
    if _persistent_client is not None:
        try:
            _persistent_client.disconnect()
        except Exception:
            pass
        finally:
            _persistent_client = None
            _persistent_client_config = None


def close_persistent_client():
    with _persistent_client_lock:
        _disconnect_persistent_client()


def _ensure_persistent_client(url, username, password, timeout, security_config=None):
    global _persistent_client, _persistent_client_config

    desired_config = {
        "url": url,
        "username": username,
        "password": password,
        "timeout": timeout,
        "security": security_config,
    }

    # Reconnect if configuration changed (URL/credentials/timeout).
    if _persistent_client is not None and _persistent_client_config != desired_config:
        _disconnect_persistent_client()

    if _persistent_client is None:
        _persistent_client = _create_sync_client(url, username, password, timeout, security_config)
        _persistent_client.connect()
        _persistent_client_config = desired_config

    return _persistent_client


def _read_with_retry(read_operation, url, username, password, timeout, security_config=None):
    with _persistent_client_lock:
        try:
            client = _ensure_persistent_client(url, username, password, timeout, security_config)
            return read_operation(client)
        except Exception:
            # Force reconnect once, then retry the same operation.
            _disconnect_persistent_client()
            client = _ensure_persistent_client(url, username, password, timeout, security_config)
            return read_operation(client)


def server_accepts_anonymous(url, timeout=10):
    endpoints = fetch_server_endpoints(url, timeout=timeout)

    for endpoint in endpoints:
        for token in endpoint.UserIdentityTokens:
            if token.TokenType == ua.UserTokenType.Anonymous:
                return True

    return False


def server_supports_sign_and_encrypt(url, timeout=10):
    endpoints = fetch_server_endpoints(url, timeout=timeout)

    for endpoint in endpoints:
        if (
            endpoint.SecurityMode == ua.MessageSecurityMode.SignAndEncrypt
            and endpoint.SecurityPolicyUri == SECURITY_POLICY_BASIC256SHA256.URI
        ):
            return True

    return False


def read_node_value_sync(url, username, password, node_id, timeout=10, security_config=None):
    def _operation(client):
        node = client.get_node(node_id)
        return node.get_value()

    return _read_with_retry(
        _operation,
        url=url,
        username=username,
        password=password,
        timeout=timeout,
        security_config=security_config,
    )


def read_named_nodes_sync(url, username, password, node_ids, timeout=10, security_config=None):
    def _operation(client):
        values = {}
        errors = {}
        for name, node_id in node_ids.items():
            try:
                node = client.get_node(node_id)
                values[name] = node.get_value()
            except Exception as exc:
                values[name] = None
                errors[name] = str(exc)

        # Si rien n'est lisible, on remonte une erreur claire au code appelant.
        if errors and len(errors) == len(node_ids):
            raise RuntimeError(f"Aucune variable OPC UA lisible: {errors}")

        return values

    return _read_with_retry(
        _operation,
        url=url,
        username=username,
        password=password,
        timeout=timeout,
        security_config=security_config,
    )



def read_automate_variables_sync(url, username, password, timeout=10, security_config=None):
    return read_named_nodes_sync(
        url=url,
        username=username,
        password=password,
        node_ids=AUTOMATE_NODE_IDS,
        timeout=timeout,
        security_config=security_config,
    )


def _coerce_value_for_variant_type(value, variant_type):
    if variant_type in (
        ua.VariantType.SByte,
        ua.VariantType.Byte,
        ua.VariantType.Int16,
        ua.VariantType.UInt16,
        ua.VariantType.Int32,
        ua.VariantType.UInt32,
        ua.VariantType.Int64,
        ua.VariantType.UInt64,
    ):
        return int(float(value))

    if variant_type in (ua.VariantType.Float, ua.VariantType.Double):
        return float(value)

    if variant_type == ua.VariantType.Boolean:
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)

    return value


def _set_node_value_with_node_type(node, value):
    variant_type = node.get_data_type_as_variant_type()
    typed_value = _coerce_value_for_variant_type(value, variant_type)
    node.set_value(ua.Variant(typed_value, variant_type))
    return variant_type


def write_node_value_sync(url, username, password, node_id, value, timeout=10, security_config=None):
    # Ecrit une valeur sur un noeud OPC UA en réutilisant la même session persistante.
    def _operation(client):
        node = client.get_node(node_id)
        _set_node_value_with_node_type(node, value)
        return True

    return _read_with_retry(
        _operation,
        url=url,
        username=username,
        password=password,
        timeout=timeout,
        security_config=security_config,
    )


def write_named_nodes_sync(url, username, password, node_values, timeout=10, security_config=None):
    # Ecriture groupée: on suit les succès/erreurs par clé pour faciliter le diagnostic.
    def _operation(client):
        results = {}
        errors = {}
        for name, payload in node_values.items():
            try:
                node = client.get_node(payload["node_id"])
                _set_node_value_with_node_type(node, payload["value"])
                results[name] = True
            except Exception as exc:
                results[name] = False
                errors[name] = str(exc)

        if errors and len(errors) == len(node_values):
            raise RuntimeError(f"Aucun seuil OPC UA ecrit: {errors}")

        return {"ok": True, "results": results, "errors": errors}

    return _read_with_retry(
        _operation,
        url=url,
        username=username,
        password=password,
        timeout=timeout,
        security_config=security_config,
    )


def read_alert_thresholds_sync(url, username, password, timeout=10, security_config=None):
    # Lecture ciblée des seuils d'alerte (RAM/CPU/TEMP) pour l'UI de paramétrage.
    node_ids = {key: AUTOMATE_NODE_IDS[key] for key in ALERT_THRESHOLD_KEYS}
    return read_named_nodes_sync(
        url=url,
        username=username,
        password=password,
        node_ids=node_ids,
        timeout=timeout,
        security_config=security_config,
    )


def write_alert_thresholds_sync(url, username, password, thresholds, timeout=10, security_config=None):
    # Conversion du payload fonctionnel -> mapping noeud OPC UA / valeur.
    node_values = {}
    for key in ALERT_THRESHOLD_KEYS:
        if key not in thresholds:
            continue
        node_values[key] = {
            "node_id": AUTOMATE_NODE_IDS[key],
            "value": float(thresholds[key]),
        }

    if not node_values:
        raise ValueError("Aucun seuil a ecrire")

    return write_named_nodes_sync(
        url=url,
        username=username,
        password=password,
        node_values=node_values,
        timeout=timeout,
        security_config=security_config,
    )


atexit.register(close_persistent_client)
