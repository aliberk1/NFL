"""Create, verify and restore backups of the database and usage counters.

Stop the application before restoring.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from app.config import DB, STATE_DIR


def targets():
    return {
        "nfl.duckdb": DB,
        "catalog.json": DB.parent / "catalog.json",
        "quality_report.json": DB.parent / "quality_report.json",
        "usage.sqlite": STATE_DIR / "usage.sqlite",
    }


def _sqlite_bytes(path):
    """Consistent copy even while the application is running."""
    with tempfile.TemporaryDirectory() as folder:
        copy = Path(folder) / "copy.sqlite"
        source, destination = sqlite3.connect(path), sqlite3.connect(copy)
        try:
            source.backup(destination)
        finally:
            source.close()
            destination.close()
        return copy.read_bytes()


def create(archive):
    archive = Path(archive)
    if archive.exists():
        raise ValueError(f"{archive} zaten var; üzerine yazılmadı.")
    if not DB.exists():
        raise ValueError(f"Veritabanı yok: {DB}")
    archive.parent.mkdir(parents=True, exist_ok=True)
    contents = {name: _sqlite_bytes(path) if name == "usage.sqlite" else path.read_bytes()
                for name, path in targets().items() if path.exists()}
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    partial = archive.with_name(archive.name + ".partial")
    try:
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("manifest.json", json.dumps(manifest, indent=2))
            for name, data in contents.items():
                bundle.writestr(name, data)
        verify(partial)
        os.replace(partial, archive)
    finally:
        partial.unlink(missing_ok=True)
    print(f"Backup created and verified: {archive}", flush=True)


def verify(archive):
    try:
        with zipfile.ZipFile(archive) as bundle:
            files = json.loads(bundle.read("manifest.json"))["files"]
            names = set(bundle.namelist()) - {"manifest.json"}
            if names != set(files) or not names <= set(targets()) or "nfl.duckdb" not in names:
                raise ValueError("Yedek içeriği beklenen dosya listesiyle eşleşmiyor.")
            contents = {name: bundle.read(name) for name in files}
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Yedek dosyası bozuk veya eksik.") from exc
    for name, data in contents.items():
        if hashlib.sha256(data).hexdigest() != files[name]:
            raise ValueError(f"Yedekteki {name} bütünlük kontrolünden geçmedi.")
    with tempfile.TemporaryDirectory() as folder:
        copy = Path(folder) / "check.duckdb"
        copy.write_bytes(contents["nfl.duckdb"])
        with duckdb.connect(str(copy), read_only=True) as con:
            con.execute("SELECT count(*) FROM players").fetchone()
    return contents


def restore(archive):
    contents = verify(archive)  # Nothing is touched unless the whole archive is valid.
    staged = []
    for name, path in targets().items():
        if name in contents:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + ".restoring")
            temporary.write_bytes(contents[name])
            staged.append((temporary, path))
    for temporary, path in staged:
        os.replace(temporary, path)
    for name, path in targets().items():
        # A leftover report would describe a different database.
        if name in ("catalog.json", "quality_report.json") and name not in contents:
            path.unlink(missing_ok=True)
    print(f"Restored: {archive}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "verify", "restore"))
    parser.add_argument("archive")
    args = parser.parse_args()
    try:
        {"create": create, "verify": verify, "restore": restore}[args.command](args.archive)
    except (OSError, ValueError, duckdb.Error) as exc:
        raise SystemExit(f"Hata: {exc}") from exc
    if args.command == "verify":
        print("Backup is valid.")


if __name__ == "__main__":
    main()
