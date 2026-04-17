"""Inspect a WAD with omgifol: list lumps, dump BEHAVIOR / SCRIPTS if present."""

import sys
from pathlib import Path

from omg import WAD


def inspect(wad_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    wad = WAD(str(wad_path))

    print(f"=== {wad_path.name} ===")
    groups = [
        ("sprites", wad.sprites),
        ("patches", wad.patches),
        ("flats", wad.flats),
        ("colormaps", wad.colormaps),
        ("ztextures", wad.ztextures),
        ("txdefs", wad.txdefs),
        ("music", wad.music),
        ("sounds", wad.sounds),
        ("graphics", wad.graphics),
        ("data", wad.data),
        ("maps", wad.maps),
        ("udmfmaps", getattr(wad, "udmfmaps", {})),
    ]
    for name, g in groups:
        keys = list(g.keys()) if hasattr(g, "keys") else []
        if keys:
            print(f"  {name} ({len(keys)}): {keys}")

    print()
    print("=== Map details ===")
    all_maps = [("doom", wad.maps)]
    if hasattr(wad, "udmfmaps"):
        all_maps.append(("udmf", wad.udmfmaps))

    for kind, map_container in all_maps:
        for map_name in map_container.keys():
            map_group = map_container[map_name]
            lump_names = list(map_group.keys())
            print(f"  [{kind}] {map_name}: {lump_names}")

            for lump_name in lump_names:
                lump = map_group[lump_name]
                data = lump.data
                size = len(data)
                out_path = out_dir / f"{kind}__{map_name}__{lump_name}.bin"
                out_path.write_bytes(data)
                print(f"    {lump_name}: {size} bytes -> {out_path.name}")

    print()
    print("=== Global data lumps ===")
    for key in wad.data.keys():
        lump = wad.data[key]
        data = lump.data
        out_path = out_dir / f"DATA__{key}.bin"
        out_path.write_bytes(data)
        print(f"  {key}: {len(data)} bytes -> {out_path.name}")


if __name__ == "__main__":
    wad_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("decompiled") / wad_path.stem
    inspect(wad_path, out_dir)
