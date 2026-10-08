"""UI checks on a disposable emulator ONLY. Resets its Kana Studio draft/settings."""
import argparse
import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--adb", type=Path, required=True)
parser.add_argument("--serial", default="emulator-5580")
args = parser.parse_args()
if not args.serial.startswith("emulator-"):
    raise SystemExit("This destructive QA setup is restricted to emulators.")
OUTPUT = ROOT / "android/build/ui-qa"
OUTPUT.mkdir(parents=True, exist_ok=True)


def adb(*arguments):
    return subprocess.check_output([str(args.adb), "-s", args.serial, *arguments])


def tree():
    adb("shell", "uiautomator", "dump", "/sdcard/kana-ui.xml")
    return ET.fromstring(adb("shell", "cat", "/sdcard/kana-ui.xml"))


def tap(text=None, description=None):
    for _ in range(5):
        for node in tree().iter("node"):
            if (text is not None and node.get("text", "").casefold() == text.casefold()) or (description is not None and node.get("content-desc") == description):
                left, top, right, bottom = map(int, re.findall(r"\d+", node.get("bounds")))
                adb("shell", "input", "tap", str((left + right) // 2), str((top + bottom) // 2))
                time.sleep(.3)
                return
        size = adb("shell", "wm", "size").decode()
        matches = re.findall(r"(\d+)x(\d+)", size)
        width, height = map(int, matches[-1])
        adb("shell", "input", "swipe", str(width//2), str(height*3//4), str(width//2), str(height//3), "200")
    raise AssertionError("Missing UI control: " + str(text or description))


def capture(name):
    (OUTPUT / (name + ".png")).write_bytes(adb("exec-out", "screencap", "-p"))
    (OUTPUT / (name + ".xml")).write_bytes(ET.tostring(tree(), encoding="utf-8"))
    print("Captured", name, flush=True)


def start():
    adb("shell", "am", "start", "-n", "com.godrayine.kanastudio/.MainActivity")
    time.sleep(.5)


adb("shell", "am", "force-stop", "com.godrayine.kanastudio")
adb("shell", "pm", "clear", "com.godrayine.kanastudio")
adb("shell", "settings", "put", "global", "airplane_mode_on", "1")
adb("shell", "svc", "wifi", "disable")
adb("shell", "svc", "data", "disable")
adb("shell", "settings", "put", "global", "window_animation_scale", "0")
adb("shell", "settings", "put", "global", "transition_animation_scale", "0")
adb("shell", "settings", "put", "global", "animator_duration_scale", "0")
adb("shell", "settings", "put", "system", "font_scale", "1.0")
adb("shell", "wm", "size", "1080x2160")
adb("shell", "wm", "density", "460")
adb("shell", "wm", "user-rotation", "lock", "0")
start(); tap("Пример"); capture("editor-light")
tap("Чтение"); tap("Настроить чтение · 100%"); tap("−"); tap("−"); tap("−"); tap("−"); tap("−"); tap("Свернуть настройки · 50%"); capture("reader-light")
tap(description="Включить тёмную тему"); capture("reader-dark")
tap("Чтения"); capture("reading-hints"); tap("Закрыть")
tap("Слоги"); tap("Выбрать отдельно"); capture("selection-dark")
tap("Текст"); capture("editor-dark")
adb("shell", "am", "force-stop", "com.godrayine.kanastudio"); start()
nodes = list(tree().iter("node"))
assert any("Тихо падает снег" in n.get("text", "") for n in nodes), "Draft not restored"
assert any(n.get("content-desc") == "Включить светлую тему" for n in nodes), "Dark theme not restored"
tap("Чтение"); capture("restored-reader")
adb("shell", "settings", "put", "system", "font_scale", "2.0"); time.sleep(.5); capture("large-font")
tap("Слоги"); capture("large-font-selection")
adb("shell", "wm", "user-rotation", "lock", "1"); time.sleep(.6); capture("landscape-large-font")
adb("shell", "settings", "put", "system", "font_scale", "1.0")
adb("shell", "wm", "user-rotation", "lock", "0")
adb("shell", "wm", "size", "1536x2048"); adb("shell", "wm", "density", "240"); time.sleep(.6)
tap("Чтение"); capture("tablet-dark")
adb("shell", "wm", "size", "1080x2160"); adb("shell", "wm", "density", "460"); time.sleep(.6)
tap("Текст")
report = {"emulator": args.serial, "platform": adb("shell", "getprop", "ro.build.version.release").decode().strip(),
    "airplane_mode": adb("shell", "settings", "get", "global", "airplane_mode_on").decode().strip(),
    "cases": ["375dp portrait, light/dark", "tap reading hints", "syllable expansion", "draft/theme restored after process stop", "200% font", "landscape at 200% font", "1024dp tablet", "animations disabled"]}
(OUTPUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("PASS: offline UI scenarios; screenshots need visual review.")
