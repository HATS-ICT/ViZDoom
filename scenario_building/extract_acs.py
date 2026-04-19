"""CLI: extract the ACS source (SCRIPTS lump) from a WAD.

Usage:
    python -m scenario_building.extract_acs WAD [--map MAP01] [--output FILE]

Prints the source to stdout if ``--output`` is omitted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scenario_building.acs_patch import extract_acs_source, list_maps
else:
    from .acs_patch import extract_acs_source, list_maps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("wad", help="Input WAD path.")
    parser.add_argument(
        "--map",
        dest="map_name",
        default=None,
        help="Map name inside the WAD. Auto-detected if the WAD has exactly one map.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination file. Defaults to stdout.",
    )
    parser.add_argument(
        "--list-maps",
        action="store_true",
        help="Print the WAD's map names and exit without extracting.",
    )
    args = parser.parse_args()

    if args.list_maps:
        for name in list_maps(args.wad):
            print(name)
        return

    source = extract_acs_source(args.wad, map_name=args.map_name)
    if args.output is None:
        sys.stdout.write(source)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(source, encoding="utf-8")
        print(f"[done] {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
