"""Inspect and patch ACS scripts inside ViZDoom scenario WAD files.

Public surface:
    list_maps(wad)                         -> list[str]
    extract_acs_source(wad, map_name=None) -> str
    build_patched_wad(base_wad, acs_source, output_wad, map_name=None) -> Path
    locate_acc()                           -> tuple[Path, Path]

Map name is auto-detected when the WAD carries exactly one map (the common case
for scenarios shipped with ViZDoom). Pass `map_name` explicitly for multi-map
WADs.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Union

__all__ = [
    "AccNotFoundError",
    "AcsCompileError",
    "build_patched_wad",
    "extract_acs_source",
    "list_maps",
    "locate_acc",
]

ACS_MAGICS = {b"ACS\x00", b"ACSE", b"ACSe"}


class AccNotFoundError(RuntimeError):
    """Raised when the acc binary cannot be located."""


class AcsCompileError(RuntimeError):
    """Raised when acc fails to compile an ACS source."""


def _import_omg():
    try:
        from omg import WAD, Lump
    except ImportError as exc:
        raise ImportError(
            "scenario_building requires omgifol. Install with "
            "'pip install omgifol' or 'pip install vizdoom[scenario_building]'."
        ) from exc
    return WAD, Lump


def locate_acc() -> tuple[Path, Path]:
    """Return ``(acc_binary, include_dir)``.

    Lookup order:
      1. ``$VIZDOOM_ACC`` + ``$VIZDOOM_ACC_INCLUDES`` env vars (caller override).
      2. Next to the installed ``vizdoom`` package (shipped by setup.py).
      3. ViZDoom repo ``bin/`` dir (walking up from this file — dev mode).
      4. System ``PATH``.
    """
    env_bin = os.environ.get("VIZDOOM_ACC")
    env_inc = os.environ.get("VIZDOOM_ACC_INCLUDES")
    if env_bin and env_inc:
        return Path(env_bin), Path(env_inc)

    candidates: list[tuple[Path, Path]] = []

    try:
        import vizdoom

        pkg_dir = Path(vizdoom.__file__).parent
        candidates.append((pkg_dir / "acc", pkg_dir / "acc_includes"))
    except Exception:
        pass

    here = Path(__file__).resolve()
    for ancestor in [here.parent, *here.parents]:
        bin_dir = ancestor / "bin"
        if (bin_dir / "acc").is_file():
            candidates.append((bin_dir / "acc", bin_dir / "acc_includes"))
            break

    system_acc = shutil.which("acc")
    if system_acc:
        candidates.append((Path(system_acc), Path(system_acc).parent))

    for acc_bin, acc_inc in candidates:
        if acc_bin.is_file() and acc_inc.is_dir():
            return acc_bin, acc_inc

    raise AccNotFoundError(
        "Could not locate acc. Rebuild ViZDoom with BUILD_ACC=ON, or set "
        "VIZDOOM_ACC and VIZDOOM_ACC_INCLUDES env vars."
    )


def _load_wad(wad_path: Path):
    WAD, _ = _import_omg()
    if not wad_path.is_file():
        raise FileNotFoundError(f"WAD does not exist: {wad_path}")
    return WAD(str(wad_path))


def _all_map_names(wad) -> list[str]:
    return list(wad.maps.keys()) + list(getattr(wad, "udmfmaps", {}).keys())


def _get_map_container(wad, map_name: str):
    if map_name in wad.maps:
        return wad.maps[map_name]
    udmf = getattr(wad, "udmfmaps", {})
    if map_name in udmf:
        return udmf[map_name]
    raise KeyError(
        f"Map '{map_name}' not found in WAD. Available maps: {_all_map_names(wad)}"
    )


def _resolve_map_name(wad, map_name: Optional[str]) -> str:
    if map_name is not None:
        return map_name
    names = _all_map_names(wad)
    if len(names) == 1:
        return names[0]
    if not names:
        raise ValueError("WAD contains no maps.")
    raise ValueError(
        f"WAD contains multiple maps; pass map_name explicitly. Found: {names}"
    )


def list_maps(wad_path: Union[str, Path]) -> list[str]:
    """Return every map name found in the WAD (Doom-format and UDMF)."""
    return _all_map_names(_load_wad(Path(wad_path)))


def extract_acs_source(
    wad_path: Union[str, Path],
    map_name: Optional[str] = None,
) -> str:
    """Return the SCRIPTS (ACS source) lump for ``map_name`` as UTF-8 text.

    If the WAD has exactly one map, ``map_name`` may be omitted.
    """
    wad = _load_wad(Path(wad_path))
    name = _resolve_map_name(wad, map_name)
    container = _get_map_container(wad, name)
    if "SCRIPTS" not in container:
        raise KeyError(
            f"Map '{name}' has no SCRIPTS lump (lumps: {list(container.keys())})."
        )
    return container["SCRIPTS"].data.decode("utf-8", errors="replace")


def _run_acc(acc_bin: Path, acc_inc: Path, acs_src: Path, out_obj: Path) -> None:
    result = subprocess.run(
        [str(acc_bin), "-i", str(acc_inc), str(acs_src), str(out_obj)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AcsCompileError(
            f"acc failed (exit {result.returncode}).\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if not out_obj.is_file() or out_obj.stat().st_size == 0:
        raise AcsCompileError("acc reported success but produced no output bytecode.")
    magic = out_obj.read_bytes()[:4]
    if magic not in ACS_MAGICS:
        raise AcsCompileError(
            f"acc output does not look like ACS bytecode (magic={magic!r})."
        )


def build_patched_wad(
    base_wad: Union[str, Path],
    acs_source: Union[str, bytes],
    output_wad: Union[str, Path],
    map_name: Optional[str] = None,
) -> Path:
    """Compile ``acs_source`` and embed it into a copy of ``base_wad``.

    The base WAD is never mutated; the result is written to ``output_wad``.
    Returns the resolved absolute path of the written WAD.
    """
    base = Path(base_wad).expanduser().resolve()
    out = Path(output_wad).expanduser().resolve()
    if out == base:
        raise ValueError("Refusing to overwrite the base WAD; output_wad must differ.")
    if out.exists() and not out.is_file():
        raise ValueError(f"output_wad exists and is not a regular file: {out}")

    wad = _load_wad(base)
    name = _resolve_map_name(wad, map_name)
    container = _get_map_container(wad, name)
    if "BEHAVIOR" not in container or "SCRIPTS" not in container:
        raise KeyError(
            f"Map '{name}' is missing SCRIPTS or BEHAVIOR lumps "
            f"(lumps: {list(container.keys())}). "
            "This tool only patches maps that already carry both."
        )

    _, Lump = _import_omg()
    acs_bytes = acs_source.encode("utf-8") if isinstance(acs_source, str) else acs_source
    acc_bin, acc_inc = locate_acc()

    with tempfile.TemporaryDirectory(prefix="acs_patch_") as td:
        td_path = Path(td)
        acs_file = td_path / "source.acs"
        obj_file = td_path / "source.o"
        acs_file.write_bytes(acs_bytes)
        _run_acc(acc_bin, acc_inc, acs_file, obj_file)
        bytecode = obj_file.read_bytes()

    container["SCRIPTS"] = Lump(acs_bytes)
    container["BEHAVIOR"] = Lump(bytecode)

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=out.parent, delete=False, suffix=".wad.tmp"
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        wad.to_file(str(tmp_path))
        os.replace(tmp_path, out)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return out
