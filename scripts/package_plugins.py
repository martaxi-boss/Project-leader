#!/usr/bin/env python3
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
PLUGINS = ("project-leader", "recovery-guardian")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_plugin(plugin_dir, output_zip):
    plugin_dir = Path(plugin_dir)
    output_zip = Path(output_zip)
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in plugin_dir.rglob("*") if p.is_file()):
            arcname = path.relative_to(plugin_dir).as_posix()
            info = zipfile.ZipInfo(arcname, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output_zip


def build(root, output_dir):
    root = Path(root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = []

    for name in PLUGINS:
        plugin_dir = root / "plugins" / name
        metadata = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
        archive = package_plugin(plugin_dir, output_dir / f"{name}.zip")
        entries.append(
            {
                "name": name,
                "version": metadata["version"],
                "file": archive.name,
                "sha256": sha256_file(archive),
                "size": archive.stat().st_size,
            }
        )

    manifest = {"schema_version": "1.0", "plugins": entries}
    (output_dir / "plugin-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{entry['sha256']}  {entry['file']}\n" for entry in entries),
        encoding="utf-8",
    )
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    build(args.root, args.output_dir)


if __name__ == "__main__":
    main()
