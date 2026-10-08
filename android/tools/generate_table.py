"""Refresh the mobile table and golden fixtures from the original desktop converter."""
import base64
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from kana import KANA, Options, convert

MOBILE = ROOT / "android"
quote = lambda value: json.dumps(value, ensure_ascii=False)
rows = ["package com.godrayine.kanastudio;", "", "// Generated from kana.py. Run android/tools/generate_table.py after table changes.",
        "public final class KanaTable {", "    public static final KanaEngine.Kana[] ALL = {"]
for k in KANA:
    rows.append("        new KanaEngine.Kana(" + ", ".join(quote(v) for v in (k.reading, k.hiragana, k.katakana, k.group, *k.aliases)) + "),")
rows += ["    };", "}", ""]
(MOBILE / "src/com/godrayine/kanastudio/KanaTable.java").write_text("\n".join(rows), encoding="utf-8")

cases = []
all_readings = frozenset(k.reading for k in KANA)
for k in KANA:
    for spelling in (k.reading, *k.aliases):
        for alphabet in ("hiragana", "katakana", "mixed"):
            cases.append((spelling.upper(), Options(alphabet=alphabet, selected=frozenset({k.reading}))))
rng = random.Random(42026)
texts = ["тихо птица чисто чаша чудо чоппер тя тю тё", "КЯ кю кё КЕ э Е", "<script>Ка & 🙂 ка</script>\n\tки  カ", "Мама и папа читают книгу", "", "а " * 1000, "🙂а 🙂 а " * 150]
for _ in range(350):
    text = rng.choice(texts)
    selected = frozenset(rng.sample(sorted(all_readings), rng.randrange(105)))
    cases.append((text, Options(alphabet=rng.choice(["hiragana", "katakana", "mixed"]), selected=selected,
        density=rng.choice([0, 1, 35, 50, 99, 100]), snowball=rng.choice([False, True]),
        replace_e=rng.choice([False, True]), wide_spaces=rng.choice([False, True]))))
encode = lambda value: base64.b64encode(value.encode()).decode()
lines = []
for text, options in cases:
    result = convert(text, options)
    segments = "".join(s.text + "\x01" + s.original + "\x01" + s.reading + "\x02" for s in result.segments)
    lines.append("\t".join(map(str, [encode(text), options.alphabet, options.density, int(options.snowball), int(options.replace_e), int(options.wide_spaces),
        encode(",".join(sorted(options.selected))), encode(result.text), result.replacements, result.possible, result.unique, encode(segments)])))
(MOBILE / "tests/desktop-fixtures.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Generated {len(KANA)} kana and {len(cases)} desktop parity cases.")
