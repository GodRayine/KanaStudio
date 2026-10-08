"""Package the signed Android APK with all tracked source and SHA-256 checksums."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "release/android/1.0.0"
APK = RELEASE / "KanaStudio-Android-1.0.0.apk"
source = RELEASE / "KanaStudio-Android-v1.0.0-source.zip"
if not APK.is_file():
    raise SystemExit("Run android/build.py first.")
paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().strip("\0").split("\0")
if "android/src/com/godrayine/kanastudio/MainActivity.java" not in paths:
    raise SystemExit("Stage the Android source files in Git before packaging.")
with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
    for name in sorted(paths):
        if any(part in {"build", ".venv", "__pycache__", ".git", "release"} for part in Path(name).parts) or name.endswith((".jks", ".keystore", ".password")):
            raise SystemExit("Unexpected private/generated file tracked: " + name)
        archive.write(ROOT / name, "KanaStudio-Android-v1.0.0-source/" + name)
with zipfile.ZipFile(source) as archive:
    assert archive.testzip() is None
report_path = RELEASE / "verification.json"
report = json.loads(report_path.read_text(encoding="utf-8"))
assert report["requested_permissions"] == []
assert report["sha256"] == hashlib.sha256(APK.read_bytes()).hexdigest()
report["desktop_parity_cases"] = sum(1 for _ in (ROOT / "android/tests/desktop-fixtures.tsv").open(encoding="utf-8"))
ui_report = ROOT / "android/build/ui-qa/report.json"
if ui_report.is_file():
    report["emulator_ui_checks"] = json.loads(ui_report.read_text())
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
files = [APK, source, report_path]
(RELEASE / "SHA256SUMS.txt").write_text("".join(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n" for path in files), encoding="utf-8")
for path in files:
    print(path)
