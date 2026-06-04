#!/usr/bin/env python3
import os
import socket
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT_DIR, "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from services.opcua_requests import (  # noqa: E402
    fetch_server_endpoints,
    read_cpu_metrics_sync,
    read_node_value_sync,
    server_accepts_anonymous,
)
from services.opcua_status import (  # noqa: E402
    SERVER_STATUS_NODE_ID,
    _get_opcua_config,
    get_opcua_status_details,
)


def _print_result(label, callback):
    print(f"\n[{label}]")
    try:
        result = callback()
        if isinstance(result, dict) and result.get("ok") is False:
            print("ECHEC")
            print(result)
            return False
        print("OK")
        if result is not None:
            print(result)
        return True
    except Exception as exc:
        print("ECHEC")
        print(f"{type(exc).__name__}: {exc}")
        return False


def _tcp_check(url, timeout):
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 4840
    with socket.create_connection((host, port), timeout=timeout):
        return f"{host}:{port} accessible"


def _describe_endpoints(url, timeout):
    endpoints = fetch_server_endpoints(url, timeout=timeout)
    lines = []
    for idx, endpoint in enumerate(endpoints, start=1):
        lines.append(f"Endpoint {idx}:")
        lines.append(f"  Url:      {endpoint.EndpointUrl}")
        lines.append(f"  Mode:     {endpoint.SecurityMode}")
        lines.append(f"  Policy:   {endpoint.SecurityPolicyUri}")
        if not endpoint.UserIdentityTokens:
            lines.append("  Tokens:   <aucun>")
        for token in endpoint.UserIdentityTokens:
            lines.append(
                "  Token:    "
                f"type={token.TokenType} "
                f"policy_id={token.PolicyId!r} "
                f"security_policy={token.SecurityPolicyUri!r}"
            )
    return "\n".join(lines)


def main():
    load_dotenv(os.path.join(ROOT_DIR, ".env"))
    config = _get_opcua_config()
    security_config = config.get("security_config") or {}

    print("Diagnostic OPC UA")
    print(f"URL:       {config['url']}")
    print(f"Auth:      {'anonymous' if not config['username'] else 'username/password'}")
    print(f"Username:  {config['username'] or '<vide>'}")
    print(f"Security:  {security_config.get('mode', 'None')}")
    print(f"Timeout:   {config['timeout']}s")

    _print_result("TCP", lambda: _tcp_check(config["url"], config["timeout"]))

    _print_result(
        "Endpoints annonces par le serveur",
        lambda: _describe_endpoints(config["url"], config["timeout"]),
    )

    _print_result(
        "Statut applicatif",
        lambda: get_opcua_status_details(),
    )

    _print_result(
        "GetEndpoints anonymous",
        lambda: f"anonymous accepte: {server_accepts_anonymous(config['url'], config['timeout'])}",
    )

    _print_result(
        f"Lecture noeud serveur {SERVER_STATUS_NODE_ID}",
        lambda: read_node_value_sync(
            url=config["url"],
            username=config["username"],
            password=config["password"],
            node_id=SERVER_STATUS_NODE_ID,
            timeout=config["timeout"],
            security_config=security_config,
        ),
    )

    _print_result(
        "Lecture CPU/RAM/Temp",
        lambda: read_cpu_metrics_sync(
            url=config["url"],
            username=config["username"],
            password=config["password"],
            timeout=config["timeout"],
            security_config=security_config,
        ),
    )


if __name__ == "__main__":
    main()
