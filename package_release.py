"""Package EXE, portable/source archives and checksums for GitHub Releases."""
import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path
from version import VERSION

ROOT = Path(__file__).resolve().parent
SOURCES = [
    ".gitignore", "app.py", "kana.py", "version.py", "version_info.txt",
    "test_app.py", "test_kana.py", "requirements.txt", "build.ps1",
    "package_release.py", "icon.ico", "README.md", "CHANGELOG.md",
    "LICENSE", "COPYRIGHT", "THIRD-PARTY.md", "ИНСТРУКЦИЯ.txt",
]
NOTICES = ["README.md", "CHANGELOG.md", "ИНСТРУКЦИЯ.txt", "LICENSE", "COPYRIGHT", "THIRD-PARTY.md"]


def add_directory(archive, folder, prefix):
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            archive.write(path, prefix + path.relative_to(ROOT).as_posix())


def main(output_dir=None):
    release = Path(output_dir).resolve() if output_dir else ROOT / "release" / VERSION
    exe = release / "KanaStudio.exe"
    if not exe.is_file():
        raise SystemExit("Build KanaStudio.exe first")
    for name in NOTICES:
        shutil.copyfile(ROOT / name, release / name)
    shutil.copytree(ROOT / "licenses", release / "licenses", dirs_exist_ok=True)
    portable = release / "KanaStudio-win-x64.zip"
    with zipfile.ZipFile(portable, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ["KanaStudio.exe", *NOTICES]:
            archive.write(release / name, "KanaStudio/" + name)
        add_directory(archive, ROOT / "licenses", "KanaStudio/")
    source = release / f"KanaStudio-v{VERSION}-source.zip"
    prefix = f"KanaStudio-v{VERSION}-source/"
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in SOURCES:
            archive.write(ROOT / name, prefix + name)
        for folder in ["assets", "licenses", "docs"]:
            add_directory(archive, ROOT / folder, prefix)
    artifacts = [exe, portable, source]
    sums = release / "SHA256SUMS.txt"
    sums.write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in artifacts
    ), encoding="utf-8")
    for path in [*artifacts, sums]:
        print(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    main(parser.parse_args().output_dir)
