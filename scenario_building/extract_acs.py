"""Extract ACS source (SCRIPTS) and compiled bytecode (BEHAVIOR) from a WAD.

Walks both Doom-format and UDMF maps and also dumps any global ACS / LOADACS
lumps. SCRIPTS is written as a .acs source file; BEHAVIOR as a .o bytecode file.
"""

import sys
from pathlib import Path

from omg import WAD

ACS_LUMPS = {"SCRIPTS", "BEHAVIOR", "ACS", "LOADACS"}


def dump_lump(lump, out_path: Path) -> int:
    data = lump.data
    out_path.write_bytes(data)
    return len(data)


def extract(wad_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    wad = WAD(str(wad_path))

    print(f"[wad] {wad_path.name}")

    for kind, container in (("doom", wad.maps), ("udmf", getattr(wad, "udmfmaps", {}))):
        for map_name in container.keys():
            map_group = container[map_name]
            for lump_name in map_group.keys():
                if lump_name not in ACS_LUMPS:
                    continue
                ext = ".acs" if lump_name == "SCRIPTS" else ".o"
                out_path = out_dir / f"{map_name}_{lump_name}{ext}"
                size = dump_lump(map_group[lump_name], out_path)
                print(f"  [{kind}] {map_name}/{lump_name}: {size} B -> {out_path.name}")

    for lump_name in wad.data.keys():
        if lump_name not in ACS_LUMPS:
            continue
        ext = ".acs" if lump_name == "SCRIPTS" else ".o"
        out_path = out_dir / f"GLOBAL_{lump_name}{ext}"
        size = dump_lump(wad.data[lump_name], out_path)
        print(f"  [global] {lump_name}: {size} B -> {out_path.name}")


if __name__ == "__main__":
    wad_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("acs") / wad_path.stem
    extract(wad_path, out_dir)
