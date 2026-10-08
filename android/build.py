"""Build and sign a dependency-free Android APK with official SDK tools (no Gradle)."""
import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
VERSION = "1.0.0"


def run(*args, **kwargs):
    result = subprocess.run([str(a) for a in args], check=True, **kwargs)
    return result.stdout if kwargs.get("capture_output") else None


def compile_apk(sources, manifest, name, sdk, jdk, build, assets=None, classpath=None):
    tools = sdk / "build-tools/36.0.0"
    framework = sdk / "platforms/android-36/android.jar"
    work = build / name
    for folder in ["generated", "classes", "dex"]:
        (work / folder).mkdir(parents=True, exist_ok=True)
    resources = work / "resources.zip"
    run(tools / "aapt2.exe", "compile", "--dir", ROOT / "res", "-o", resources)
    unsigned = work / "unsigned.apk"
    arguments = [tools / "aapt2.exe", "link", "-I", framework, "--manifest", manifest,
        "--java", work / "generated", "-o", unsigned, "--auto-add-overlay", resources]
    if assets:
        arguments += ["-A", assets]
    run(*arguments)
    java_files = sorted(sources.rglob("*.java")) + sorted((work / "generated").rglob("*.java"))
    # Argument files handle spaces and non-ASCII paths on Windows.
    javac_args = work / "javac.args"
    cp = str(framework) + (os.pathsep + str(classpath) if classpath else "")
    javac_args.write_text("\n".join('"' + str(p).replace("\\", "/") + '"' for p in java_files), encoding="utf-8")
    run(jdk / "bin/javac.exe", "-encoding", "UTF-8", "--release", "8", "-classpath", cp, "-d", work / "classes", "@" + str(javac_args))
    bytecode = work / "classes.jar"
    with zipfile.ZipFile(bytecode, "w") as archive:
        for path in sorted((work / "classes").rglob("*.class")):
            archive.write(path, path.relative_to(work / "classes").as_posix())
    d8_args = [jdk / "bin/java.exe", "-cp", tools / "lib/d8.jar", "com.android.tools.r8.D8", "--min-api", "26", "--lib", framework, "--output", work / "dex"]
    if classpath:
        d8_args += ["--classpath", classpath.parent / "classes.jar"]
    run(*d8_args, bytecode)
    with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((work / "dex").glob("*.dex")):
            archive.write(path, path.name)
    aligned = work / "aligned.apk"
    run(tools / "zipalign.exe", "-f", "-p", "4", unsigned, aligned)
    return aligned, work / "classes"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, default=Path(os.environ.get("ANDROID_HOME", str(Path.home() / "AppData/Local/KanaStudioDevelopment/sdk"))))
    parser.add_argument("--jdk", type=Path, default=Path(os.environ.get("JAVA_HOME", ".")))
    parser.add_argument("--signing-dir", type=Path, default=Path.home() / ".codex/secrets/KanaStudio-android")
    parser.add_argument("--initialize-signing-key", action="store_true")
    parser.add_argument("--with-device-tests", action="store_true")
    args = parser.parse_args()
    sdk, jdk = args.sdk.resolve(), args.jdk.resolve()
    if not (jdk / "bin/javac.exe").is_file():
        raise SystemExit("Pass --jdk <JDK 21 directory> or set JAVA_HOME.")
    tools = sdk / "build-tools/36.0.0"
    if not (tools / "aapt2.exe").is_file() or not (sdk / "platforms/android-36/android.jar").is_file():
        raise SystemExit("Install platforms;android-36 and build-tools;36.0.0; pass --sdk.")
    build = ROOT / "build/runs" / uuid.uuid4().hex
    build.mkdir(parents=True, exist_ok=True)
    # Cross-platform algorithm tests run on the host JVM without Android dependencies.
    tests = build / "engine-tests"
    tests.mkdir(exist_ok=True)
    source = ROOT / "src/com/godrayine/kanastudio"
    run(jdk / "bin/javac.exe", "-encoding", "UTF-8", "--release", "8", "-d", tests,
        source / "KanaEngine.java", source / "KanaTable.java", ROOT / "tests/EngineTest.java")
    run(jdk / "bin/java.exe", "-cp", tests, "com.godrayine.kanastudio.EngineTest", ROOT / "tests/desktop-fixtures.tsv")
    assets = build / "assets"
    assets.mkdir(exist_ok=True)
    for name in ["LICENSE", "COPYRIGHT"]:
        shutil.copyfile(PROJECT / name, assets / name)
    signing = args.signing_dir.resolve()
    key, password = signing / "release.jks", signing / "release.password"
    if not key.exists():
        if not args.initialize_signing_key:
            raise SystemExit("Signing key missing. Pass --initialize-signing-key for the FIRST build only. Keep this private key for future updates.")
        signing.mkdir(parents=True, exist_ok=True)
        password.write_text(secrets.token_urlsafe(40), encoding="ascii")
        run(jdk / "bin/keytool.exe", "-genkeypair", "-keystore", key, "-storetype", "PKCS12", "-alias", "kanastudio",
            "-keyalg", "RSA", "-keysize", "3072", "-validity", "10000", "-dname", "CN=GodRayine, OU=Kana Studio, O=GodRayine",
            "-storepass:file", password, "-keypass:file", password)
    if not password.is_file():
        raise SystemExit("Signing password file missing; restore it with the original key.")
    release = PROJECT / "release/android" / VERSION
    release.mkdir(parents=True, exist_ok=True)
    aligned, classes = compile_apk(ROOT / "src", ROOT / "AndroidManifest.xml", "app", sdk, jdk, build, assets)
    apk = release / f"KanaStudio-Android-{VERSION}.apk"
    signer = [jdk / "bin/java.exe", "-jar", tools / "lib/apksigner.jar"]
    def sign(input_apk, target):
        run(*signer, "sign", "--ks", key, "--ks-key-alias", "kanastudio", "--ks-pass", "file:" + str(password),
            "--v4-signing-enabled", "false", "--out", target, input_apk)
        return run(*signer, "verify", "--verbose", "--print-certs", target, text=True, capture_output=True)
    certificate = sign(aligned, apk)
    permissions = run(tools / "aapt2.exe", "dump", "permissions", apk, text=True, capture_output=True)
    if "uses-permission" in permissions:
        raise SystemExit("Unexpected permission in compiled APK: " + permissions)
    manifest = run(tools / "aapt2.exe", "dump", "xmltree", "--file", "AndroidManifest.xml", apk, text=True, capture_output=True)
    report = {"version": VERSION, "apk": apk.name, "sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "requested_permissions": [], "signature_verification": certificate, "compiled_manifest": manifest}
    (release / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (release / "SHA256SUMS.txt").write_text(report["sha256"] + "  " + apk.name + "\n", encoding="utf-8")
    print("Release:", apk, flush=True)
    if args.with_device_tests:
        test_apk, _ = compile_apk(ROOT / "tests/device", ROOT / "tests/AndroidManifest.xml", "device-tests", sdk, jdk, build, classpath=classes)
        device_apk = ROOT / "build/KanaStudio-device-tests.apk"
        sign(test_apk, device_apk)
        print("Device tests:", device_apk, flush=True)


if __name__ == "__main__":
    main()
