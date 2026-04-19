"""CLI: compile an edited ACS source and embed it into a new WAD.

Usage:
    python -m scenario_building.compile_and_embed BASE.wad EDITED.acs OUT.wad [--map MAP01]

Thin wrapper over ``scenario_building.acs_patch.build_patched_wad``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scenario_building.acs_patch import build_patched_wad
else:
    from .acs_patch import build_patched_wad


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base_wad", help="Source WAD to patch (not modified).")
    parser.add_argument("acs_file", help="Edited ACS source file.")
    parser.add_argument("output_wad", help="Where to write the patched WAD.")
    parser.add_argument(
        "--map",
        dest="map_name",
        default=None,
        help="Map name inside the WAD. Auto-detected if the WAD has exactly one map.",
    )
    args = parser.parse_args()

    acs_text = Path(args.acs_file).read_text(encoding="utf-8")
    out = build_patched_wad(
        args.base_wad,
        acs_text,
        args.output_wad,
        map_name=args.map_name,
    )
    print(f"[done] {out}")


if __name__ == "__main__":
    main()
