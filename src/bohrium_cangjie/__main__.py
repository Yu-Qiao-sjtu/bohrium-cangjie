"""Command line for adapting and installing Bohrium skill directories."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bohrium_cangjie.adapt import AdaptError, adapt_path
from bohrium_cangjie.install import install_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bohrium-cangjie")
    sub = parser.add_subparsers(dest="command", required=True)

    adapt = sub.add_parser("adapt", help="rewrite a Cangjie skill or pack into a new directory")
    adapt.add_argument("--source", type=Path, required=True)
    adapt.add_argument("--out", type=Path, required=True)

    install = sub.add_parser("install", help="copy adapted skills into a Bohrium skill root")
    install.add_argument("--source", type=Path, required=True)
    install.add_argument("--dest", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "adapt":
            reports = adapt_path(args.source, args.out)
        else:
            reports = install_path(args.source, args.dest)
    except AdaptError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    payload = [item.to_dict() for item in reports]
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    if any(item.status in {"rejected", "conflict"} for item in reports):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
