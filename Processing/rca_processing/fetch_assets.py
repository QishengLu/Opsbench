"""Fetch only the pinned published shape checkpoint; no executable source download."""
import json
import urllib.request
from pathlib import Path

from .common import OPS_COMMIT, hash_file


def main():
    folder = Path(__file__).resolve().parents[1] / "assets"
    folder.mkdir(exist_ok=True)
    path = folder / "patterncla.pt"
    url = f"https://raw.githubusercontent.com/Johnn13/OpsAgent/{OPS_COMMIT}/patterncla.pt"
    if not path.exists():
        with urllib.request.urlopen(url, timeout=60) as response:
            raw = response.read(2 * 1024 * 1024)
        if len(raw) != 960802:
            raise ValueError("Unexpected checkpoint size")
        partial = path.with_suffix(".partial")
        partial.write_bytes(raw)
        partial.replace(path)
    record = {"url": url, "commit": OPS_COMMIT, "sha256": hash_file(path),
              "bytes": path.stat().st_size}
    if record["sha256"] != "71e257758e2becbe611fc489203407dce0ff114ea703d87ee7aca3eba1040753":
        raise ValueError("Pinned checkpoint checksum mismatch")
    manifest = folder / "patterncla.source.json"
    if manifest.exists() and json.loads(manifest.read_text()) != record:
        raise ValueError("Checkpoint provenance mismatch")
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
