#!/usr/bin/env python3
"""Safely preview, apply, or restore the KULT: Heretic Kingdoms UI workaround."""

import argparse
import hashlib
import os
import shutil
import struct
import tempfile
from pathlib import Path


SOURCE_FORMAT = 0x02
TARGET_FORMAT = 0x15  # D3DFMT_A8R8G8B8
INDEX_RECORD_SIZE = 124

RESOURCES = {
    "main": {
        "entries": 1649,
        "format2": 405,
        "index": "8af6b4295654936e91bb0fae6f724fff29c76a4b184bea26ef5cf973ec344d39",
        "original": "d7f6de2031284c36af3ea74eb0bc26be32e2b74916ba630ecec1853ee03c0607",
        "patched": "dce788e86aafeb768161f62d6026c5cca55eefd911ead521863880025e763a73",
    },
    "main_br": {
        "entries": 1605,
        "format2": 361,
        "index": "025160e20ce24ffcbb6e8fc6becde9591a703a109f9f5bcd466aa400b8c58964",
        "original": "b4ad67cfc81708198c718d7999c011a965aaf322027497fb1949e4076cde2b00",
        "patched": "ef761c97cfdb7f63e7fb402373ee4b4575374b66619d8ec1a5a7ed0d3e0210cb",
    },
    "main_ch": {
        "entries": 1605,
        "format2": 361,
        "index": "025160e20ce24ffcbb6e8fc6becde9591a703a109f9f5bcd466aa400b8c58964",
        "original": "c0f6ad60dd8aa90f16c7a77e5b654fcb14b6e2a93a7f00e085106a171e018555",
        "patched": "d27a8e3ad0c3916dc481f6f0ffdadd313e715e16b4bbd1e31f6c084716d2228c",
    },
    "main_de": {
        "entries": 1649,
        "format2": 405,
        "index": "8af6b4295654936e91bb0fae6f724fff29c76a4b184bea26ef5cf973ec344d39",
        "original": "d7f6de2031284c36af3ea74eb0bc26be32e2b74916ba630ecec1853ee03c0607",
        "patched": "dce788e86aafeb768161f62d6026c5cca55eefd911ead521863880025e763a73",
    },
    "main_eng": {
        "entries": 1637,
        "format2": 393,
        "index": "9cc9b91ab2e3e5a38c39897acb160a5e7660cd70c909283d8b6ac891b557c1db",
        "original": "e2fd4796fba675d2824f651967d2d7a50bf6600363fcda7c1b54e3017f64b7ec",
        "patched": "71495be5808f968a10c24e7a7045da5723a46f1c4cad86f0ca56bcb297f3ea3c",
    },
    "main_es": {
        "entries": 1649,
        "format2": 405,
        "index": "03d82611b24b9cdc88f08a2de2f32e12bf9aa16346fdc78551c0af04bbe5a059",
        "original": "8268af3204da4dfc016086cd9c2d595d12993179f7846b6822a5a939d78135d5",
        "patched": "91b523de93dd7656af3e647a17527e6c968e805bb937de8b5756fd2231ffed86",
    },
    "main_fr": {
        "entries": 1649,
        "format2": 405,
        "index": "4021a5d46f1db70ef6666e54c96d88cd9aff22a4900f68738ea255d5c7f16eed",
        "original": "e738a2225809d7570aebf1347e534b8942b8ee83d0bbf5bfcf349897e76b7eab",
        "patched": "254a7972b231062a8442d4196e60ba636e4cf56967afc1abc3a3cd82d42b5842",
    },
    "main_it": {
        "entries": 1649,
        "format2": 405,
        "index": "be0c0deabc703ef92022958505c9bc0ac42140b446a8991b3ab10c19ce11b26e",
        "original": "f65e427f47a5293810e996ddb015752fe08d1b91648c997c79e2af07e523f158",
        "patched": "5da8ce20f34e671a460016e63c8193edaf0c504195c42d44a262d484f6292d23",
    },
    "main_ru": {
        "entries": 1649,
        "format2": 407,
        "index": "44f9c3a413ed39566af787157664f0178b9686d5fdc7acf3fbc10371b918d9ff",
        "original": "3b593a5078707de28acc49539d63a031b1949b12e5f8a241e8284fd24359e7cb",
        "patched": "d274ef18e5b126a7220ff075036120f7686ff4658a21e242aceeba72ee97fddb",
    },
}

LANGUAGE_CODES = ("br", "ch", "de", "eng", "es", "fr", "it", "ru")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configured_resource(game_dir: Path) -> str:
    config_path = game_dir / "config.cfg"
    if not config_path.is_file():
        return "main"
    for line in config_path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip().lower() == "language":
            code = value.split("#", 1)[0].strip().lower()
            return f"main_{code}" if code else "main"
    return "main"


def texture_format_offsets(index_path: Path, data_path: Path, resource: dict) -> list[int]:
    index = index_path.read_bytes()
    entry_count = struct.unpack_from("<I", index)[0]
    if entry_count != resource["entries"]:
        raise RuntimeError(
            f"Unexpected index entry count {entry_count}; expected {resource['entries']}"
        )
    if len(index) != 4 + entry_count * INDEX_RECORD_SIZE:
        raise RuntimeError(f"Unexpected index size: {len(index)} bytes")

    data_size = data_path.stat().st_size
    offsets = []
    with data_path.open("rb") as stream:
        for entry in range(entry_count):
            record = 4 + entry * INDEX_RECORD_SIZE
            data_offset = struct.unpack_from("<I", index, record + 120)[0]
            if data_offset + 16 > data_size:
                raise RuntimeError(f"Index entry {entry} points outside the data file")

            stream.seek(data_offset)
            header = stream.read(16)
            if len(header) != 16:
                raise RuntimeError(f"Truncated texture header at offset {data_offset}")
            width, height, format_code, stride = struct.unpack("<IIII", header)
            if format_code != SOURCE_FORMAT:
                continue
            if (
                width == 0
                or height == 0
                or stride != width * 4
                or data_offset + 16 + height * stride > data_size
            ):
                raise RuntimeError(
                    f"Unexpected format-2 texture layout at offset {data_offset}"
                )
            offsets.append(data_offset + 8)

    if len(offsets) != resource["format2"]:
        raise RuntimeError(
            f"Found {len(offsets)} format-2 textures; expected {resource['format2']}"
        )
    return offsets


def atomic_copy(source: Path, destination: Path) -> None:
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def write_patched_copy(source: Path, offsets: list[int], expected_hash: str) -> Path:
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{source.name}.", suffix=".tmp", dir=source.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    verified = False
    try:
        shutil.copy2(source, temporary)
        with temporary.open("r+b") as stream:
            for offset in offsets:
                stream.seek(offset)
                stream.write(struct.pack("<I", TARGET_FORMAT))
            stream.flush()
            os.fsync(stream.fileno())
        if sha256(temporary) != expected_hash:
            raise RuntimeError("Patched checksum differs from the verified result")
        verified = True
        return temporary
    finally:
        if not verified:
            temporary.unlink(missing_ok=True)


def run(game_dir: Path, stem: str, action: str) -> None:
    resource = RESOURCES[stem]
    levels_dir = game_dir / "data" / "levels"
    data_path = levels_dir / f"{stem}.dat"
    index_path = levels_dir / f"{stem}.idx"
    backup_path = levels_dir / f"{stem}.dat.kult-compat.bak"

    if not data_path.is_file() or not index_path.is_file():
        raise RuntimeError(f"Missing resource pair for {stem} in {levels_dir}")
    if sha256(index_path) != resource["index"]:
        raise RuntimeError(f"Unrecognized resource index: {index_path}")
    current_hash = sha256(data_path)

    if action == "restore":
        if not backup_path.is_file():
            raise RuntimeError(f"Original backup not found: {backup_path}")
        if sha256(backup_path) != resource["original"]:
            raise RuntimeError("Backup checksum mismatch; refusing to restore it")
        if current_hash == resource["original"]:
            print(f"{stem}: already restored.")
            return
        if current_hash != resource["patched"]:
            raise RuntimeError("Current data checksum is unexpected; refusing restore")
        atomic_copy(backup_path, data_path)
        if sha256(data_path) != resource["original"]:
            raise RuntimeError("Restored file checksum verification failed")
        print(f"{stem}: restored original from {backup_path}")
        return

    if current_hash == resource["patched"]:
        print(f"{stem}: already patched; verified checksum matches.")
        return
    if current_hash != resource["original"]:
        raise RuntimeError(f"Unrecognized data file checksum; refusing to patch {data_path}")

    offsets = texture_format_offsets(index_path, data_path, resource)
    print(f"Resource: {stem}.dat ({resource['format2']} format fields)")
    print(f"Change: 0x{SOURCE_FORMAT:02x} -> 0x{TARGET_FORMAT:02x} (A8R8G8B8)")
    print(f"SHA-256: {resource['original']} -> {resource['patched']}")
    if action == "preview":
        print("Preview only; no files changed. Add --apply to write the fix.")
        return

    if backup_path.exists():
        if sha256(backup_path) != resource["original"]:
            raise RuntimeError(f"Existing backup checksum mismatch: {backup_path}")
    else:
        atomic_copy(data_path, backup_path)
        if sha256(backup_path) != resource["original"]:
            raise RuntimeError("Backup checksum verification failed")

    patched = write_patched_copy(data_path, offsets, resource["patched"])
    try:
        os.replace(patched, data_path)
    finally:
        patched.unlink(missing_ok=True)
    if sha256(data_path) != resource["patched"]:
        raise RuntimeError("Patched file checksum verification failed")
    print(f"{stem}: patched; original backup: {backup_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game-dir",
        type=Path,
        required=True,
        help="KULT installation directory containing config.cfg and data/levels",
    )
    parser.add_argument(
        "--language",
        choices=("main", *LANGUAGE_CODES),
        help="override config.cfg language (default: detect it; use 'main' for unsuffixed files)",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="apply the patch")
    action.add_argument("--restore", action="store_true", help="restore the saved original")
    args = parser.parse_args()

    game_dir = args.game_dir.expanduser()
    code = args.language
    if code is None:
        stem = configured_resource(game_dir)
    elif code == "main":
        stem = "main"
    else:
        stem = f"main_{code}"
    if stem not in RESOURCES:
        parser.error(f"Unsupported language/resource '{stem}'; no files were changed")

    action_name = "restore" if args.restore else "apply" if args.apply else "preview"
    try:
        run(game_dir, stem, action_name)
    except (OSError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
