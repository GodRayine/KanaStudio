"""Independent, deterministic Russian-to-kana learning text converter."""
from dataclasses import dataclass
from functools import lru_cache
import re


@dataclass(frozen=True)
class Kana:
    reading: str
    hiragana: str
    katakana: str
    group: str
    aliases: tuple[str, ...] = ()


GROUP_NAMES = {
    "vowels": "Гласные", "k": "К · ка ки ку кэ ко", "s": "С · са си су сэ со",
    "t": "Т / Ч · та чи цу тэ то", "n": "Н · на ни ну нэ но", "h": "Х · ха хи ху хэ хо",
    "m": "М · ма ми му мэ мо", "y": "Я · я ю ё", "r": "Р · ра ри ру рэ ро",
    "w": "В · ва во · н", "voiced": "Звонкие · га, дза, ба…", "contracted": "Сочетания · кя, сю, чо…",
}
READING_MIGRATIONS = {"ти": "чи", "тя": "ча", "тю": "чу", "тё": "чо"}


def _make_kana():
    rows = [
        ("vowels", "а и у э о", "あいうえお", "アイウエオ"),
        ("k", "ка ки ку кэ ко", "かきくけこ", "カキクケコ"),
        ("s", "са си су сэ со", "さしすせそ", "サシスセソ"),
        ("t", "та чи цу тэ то", "たちつてと", "タチツテト"),
        ("n", "на ни ну нэ но", "なにぬねの", "ナニヌネノ"),
        ("h", "ха хи ху хэ хо", "はひふへほ", "ハヒフヘホ"),
        ("m", "ма ми му мэ мо", "まみむめも", "マミムメモ"),
        ("y", "я ю ё", "やゆよ", "ヤユヨ"),
        ("r", "ра ри ру рэ ро", "らりるれろ", "ラリルレロ"),
        ("w", "ва во н", "わをん", "ワヲン"),
        ("voiced", "га ги гу гэ го дза дзи дзу дзэ дзо да ди ду дэ до ба би бу бэ бо па пи пу пэ по",
         "がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ", "ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ"),
    ]
    aliases = {"си": ("ши",), "цу": ("тсу",), "ху": ("фу",),
               "дза": ("за",), "дзи": ("зи", "джи"), "дзу": ("зу",), "дзэ": ("зэ",), "дзо": ("зо",)}
    result = []
    for group, readings, hira, kata in rows:
        for ru, hi, ka in zip(readings.split(), hira, kata, strict=True):
            result.append(Kana(ru, hi, ka, group, aliases.get(ru, ())))
    for prefix, hi, ka in [("к", "き", "キ"), ("с", "し", "シ"), ("ч", "ち", "チ"),
                           ("н", "に", "ニ"), ("х", "ひ", "ヒ"), ("м", "み", "ミ"),
                           ("р", "り", "リ"), ("г", "ぎ", "ギ"), ("дз", "じ", "ジ"),
                           ("б", "び", "ビ"), ("п", "ぴ", "ピ")]:
        for vowel, small_hi, small_ka in zip("яюё", "ゃゅょ", "ャュョ", strict=True):
            ru = prefix + vowel
            extra = ()
            if prefix == "с": extra = ("ш" + vowel,)
            if prefix == "ч":
                ru = {"я": "ча", "ю": "чу", "ё": "чо"}[vowel]
                extra = ("ч" + vowel,)
            if prefix == "дз": extra = ("з" + vowel, "дж" + vowel)
            result.append(Kana(ru, hi + small_hi, ka + small_ka, "contracted", extra))
    return tuple(result)


KANA = _make_kana()
BY_READING = {k.reading: k for k in KANA}
BASE_READINGS = frozenset(k.reading for k in KANA if k.group not in {"voiced", "contracted"})


@dataclass(frozen=True)
class Options:
    alphabet: str = "hiragana"
    selected: frozenset[str] = BASE_READINGS
    density: int = 100
    snowball: bool = False
    replace_e: bool = False
    wide_spaces: bool = False


@dataclass(frozen=True)
class Segment:
    text: str
    original: str = ""
    reading: str = ""


@dataclass(frozen=True)
class Result:
    text: str
    segments: tuple[Segment, ...]
    replacements: int
    possible: int
    unique: int


@lru_cache(maxsize=64)
def _matcher(selected, replace_e):
    lookup = {}
    for k in KANA:
        if k.reading not in selected: continue
        for spelling in (k.reading, *k.aliases):
            lookup[spelling] = k
            if replace_e and "э" in spelling:
                lookup[spelling.replace("э", "е")] = k
    if not lookup: return None, lookup
    pattern = re.compile("|".join(re.escape(s) for s in sorted(lookup, key=lambda s: (-len(s), s))), re.IGNORECASE)
    return pattern, lookup


def convert(text: str, options: Options = Options()) -> Result:
    if options.alphabet not in {"hiragana", "katakana", "mixed"}:
        raise ValueError("Unknown alphabet")
    if not 0 <= options.density <= 100:
        raise ValueError("Density must be between 0 and 100")
    pattern, lookup = _matcher(frozenset(options.selected), options.replace_e)
    if not pattern:
        output = text.replace(" ", "\u3000") if options.wide_spaces else text
        return Result(output, (Segment(output),), 0, 0, 0)
    segments, used = [], set()
    last, replaced, possible, quota = 0, 0, 0, 0.0
    for match in pattern.finditer(text):
        possible += 1
        chance = options.density / 100
        if options.snowball:
            chance *= match.end() / max(len(text), 1)
        quota += chance
        if quota + 1e-9 < 1: continue
        quota -= 1
        k = lookup[match.group().lower()]
        if match.start() > last:
            segments.append(Segment(text[last:match.start()]))
        # Alternation makes mixed mode reproducible across previews and exports.
        kata = options.alphabet == "katakana" or (options.alphabet == "mixed" and replaced % 2 == 1)
        segments.append(Segment(k.katakana if kata else k.hiragana, match.group(), k.reading))
        used.add(k.reading)
        replaced += 1
        last = match.end()
    if last < len(text): segments.append(Segment(text[last:]))
    if options.wide_spaces:
        segments = [Segment(s.text.replace(" ", "\u3000"), s.original, s.reading) for s in segments]
    return Result("".join(s.text for s in segments), tuple(segments), replaced, possible, len(used))
