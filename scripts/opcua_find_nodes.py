#!/usr/bin/env python3
import argparse
import os
import sys
from collections import deque

from dotenv import load_dotenv
from opcua import ua

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT_DIR, "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from services.opcua_requests import _create_sync_client  # noqa: E402
from services.opcua_status import _get_opcua_config  # noqa: E402


DEFAULT_TERMS = ("cpu", "ram", "temp", "load", "usage", "gvl", "opcua")


def _text(value):
    if value is None:
        return ""
    return str(value)


def _browse_name(node):
    try:
        return _text(node.get_browse_name())
    except Exception:
        return ""


def _display_name(node):
    try:
        return _text(node.get_display_name().Text)
    except Exception:
        return ""


def _node_id(node):
    try:
        return _text(node.nodeid.to_string())
    except Exception:
        return ""


def _data_type(node):
    try:
        return _text(node.get_data_type_as_variant_type())
    except Exception:
        return ""


def _value_preview(node):
    try:
        return repr(node.get_value())
    except Exception:
        return ""


def _matches(node, terms):
    haystack = " ".join((_browse_name(node), _display_name(node), _node_id(node))).lower()
    return any(term.lower() in haystack for term in terms)


def find_nodes(client, terms, limit, max_depth):
    root = client.get_objects_node()
    queue = deque([(root, 0)])
    visited = set()
    matches = []

    while queue and len(visited) < limit:
        node, depth = queue.popleft()
        node_id = _node_id(node)
        if node_id in visited:
            continue
        visited.add(node_id)

        if _matches(node, terms):
            matches.append(node)

        if depth >= max_depth:
            continue

        try:
            children = node.get_children()
        except Exception:
            children = []

        for child in children:
            queue.append((child, depth + 1))

    return matches, len(visited)


def main():
    parser = argparse.ArgumentParser(description="Find matching OPC UA nodes.")
    parser.add_argument("terms", nargs="*", default=DEFAULT_TERMS)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--max-depth", type=int, default=8)
    args = parser.parse_args()

    load_dotenv(os.path.join(ROOT_DIR, ".env"))
    config = _get_opcua_config()

    client = _create_sync_client(
        config["url"],
        config["username"],
        config["password"],
        config["timeout"],
        config.get("security_config"),
    )

    print(f"Connexion: {config['url']}")
    print(f"Utilisateur: {'anonymous' if not config['username'] else config['username']}")
    print(f"Securite: {(config.get('security_config') or {}).get('mode', 'None')}")
    print(f"Termes: {', '.join(args.terms)}")

    try:
        client.connect()

        try:
            namespaces = client.get_namespace_array()
            print("\nNamespaces:")
            for idx, namespace in enumerate(namespaces):
                print(f"  ns={idx}: {namespace}")
        except Exception as exc:
            print(f"\nNamespaces indisponibles: {exc}")

        matches, visited_count = find_nodes(client, args.terms, args.limit, args.max_depth)
        print(f"\nNoeuds parcourus: {visited_count}")
        print(f"Correspondances: {len(matches)}\n")

        for node in matches:
            print(f"- node_id: {_node_id(node)}")
            print(f"  browse:  {_browse_name(node)}")
            print(f"  display: {_display_name(node)}")
            print(f"  type:    {_data_type(node)}")
            preview = _value_preview(node)
            if preview:
                print(f"  value:   {preview}")
            print()
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
