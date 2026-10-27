"""Package the complete Windows folder and record build provenance."""

import ast
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    bundle = ROOT / "dist" / "IEC104-Reader"
    if not (bundle / "IEC104-Reader.exe").is_file() or not (bundle / "_internal").is_dir():
        raise SystemExit("Expected the complete PyInstaller onedir bundle.")
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    version = next(
        ast.literal_eval(node.value) for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "APP_VERSION" for target in node.targets)
    )
    for name in ("LICENSE", "README.md"):
        shutil.copyfile(ROOT / name, bundle / name)
    source_paths = [ROOT / "app.py", *sorted((ROOT / "iec104").glob("*.py")),
                    ROOT / "IEC104-Reader.spec", ROOT / "requirements-build.txt",
                    ROOT / "windows-version-info.txt"]
    info = {
        "application": "IEC104 Reader", "version": version,
        "build_time_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "pyinstaller": importlib.metadata.version("pyinstaller"),
        "packaging": "onedir", "upx": False, "authenticode_signed": False,
        "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"):
                          hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
    }
    (bundle / "BUILD-INFO.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    checksums = "".join(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  "
        + path.relative_to(bundle).as_posix() + "\n"
        for path in sorted(bundle.rglob("*"))
        if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    (bundle / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
    archive = ROOT / "dist" / f"IEC104-Reader-{version}-Windows-portable.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                output.write(path, Path("IEC104-Reader") / path.relative_to(bundle))
    checksum_file = ROOT / "dist" / f"SHA256SUMS-{version}.txt"
    checksum_file.write_text(hashlib.sha256(archive.read_bytes()).hexdigest()
                             + "  " + archive.name + "\n", encoding="utf-8")
    print(archive)


if __name__ == "__main__":
    main()
