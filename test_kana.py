import unittest
from kana import BASE_READINGS, KANA, Options, convert


class ConversionTests(unittest.TestCase):
    def test_chi_does_not_replace_ti_in_russian_words(self):
        for alphabet, sign in [("hiragana", "ち"), ("katakana", "チ"), ("mixed", "ち")]:
            with self.subTest(alphabet=alphabet):
                opts = Options(alphabet=alphabet, selected=frozenset({"чи"}))
                self.assertEqual(convert("тихо птица Чисто", opts).text, f"тихо птица {sign}сто")
                result = convert("тихо птица чисто", Options(alphabet=alphabet))
                for segment in result.segments:
                    if segment.reading == "чи": self.assertEqual(segment.original.lower(), "чи")
                self.assertFalse(any(s.reading == "чи" for s in convert("тихо").segments))

    def test_ch_contractions_preserve_t_consonants(self):
        opts = Options(selected=frozenset({"ча", "чу", "чо"}))
        self.assertEqual(convert("чаша чудо чоппер тя тю тё", opts).text, "ちゃша ちゅдо ちょппер тя тю тё")
        kata = Options(alphabet="katakana", selected=opts.selected)
        self.assertEqual(convert("ча чу чо", kata).text, "チャ チュ チョ")

    def test_base_table_and_both_alphabets(self):
        self.assertEqual(len(BASE_READINGS), 46)
        for k in KANA:
            self.assertEqual(convert(k.reading, Options(selected=frozenset({k.reading}))).text, k.hiragana)
            self.assertEqual(convert(k.reading.upper(), Options(alphabet="katakana", selected=frozenset({k.reading}))).text, k.katakana)

    def test_longest_syllable_precedes_vowel(self):
        opts = Options(selected=frozenset(k.reading for k in KANA))
        self.assertEqual(convert("КЯ кю кё ка", opts).text, "きゃ きゅ きょ か")

    def test_variants_and_optional_e(self):
        opts = Options(selected=frozenset(k.reading for k in KANA))
        self.assertEqual(convert("ши чи фу джи шю", opts).text, "し ち ふ じ しゅ")
        opts = Options(selected=frozenset({"э", "кэ"}), replace_e=True)
        self.assertEqual(convert("Е ке КЭ э", opts).text, "え け け え")
        self.assertEqual(convert("е ке", Options(selected=frozenset({"э", "кэ"}))).text, "е ке")

    def test_preserves_original_punctuation_spacing_and_foreign_text(self):
        original = "Кот!  <script>hello & world</script>\n\t🙂 123"
        result = convert(original, Options(selected=frozenset({"ко"})))
        self.assertEqual(result.text, "こт!  <script>hello & world</script>\n\t🙂 123")
        self.assertEqual(result.replacements, 1)
        self.assertEqual(result.segments[0].original, "Ко")

    def test_zero_and_empty_selection(self):
        for opts in [Options(density=0), Options(selected=frozenset())]:
            self.assertEqual(convert("Мама и папа", opts).text, "Мама и папа")
        self.assertEqual(convert("").text, "")
        self.assertEqual(convert("а б", Options(selected=frozenset(), wide_spaces=True)).text, "а\u3000б")

    def test_density_is_reproducible_and_proportional(self):
        text = "а " * 100
        result = convert(text, Options(density=35))
        self.assertEqual(result.replacements, 35)
        self.assertEqual(result, convert(text, Options(density=35)))

    def test_snowball_is_progressive_and_uses_density_ceiling(self):
        result = convert("а " * 1000, Options(snowball=True))
        chunks = [result.text[i:i + 500] for i in range(0, 2000, 500)]
        counts = [c.count("あ") for c in chunks]
        self.assertEqual(counts, sorted(counts))
        self.assertGreater(counts[-1], counts[0] * 3)
        self.assertAlmostEqual(result.replacements, 500, delta=2)
        reduced = convert("а " * 1000, Options(snowball=True, density=50))
        self.assertAlmostEqual(reduced.replacements, 250, delta=2)

    def test_mixed_alternates_and_counts_unique_syllables(self):
        result = convert("ка ка ка ка", Options(alphabet="mixed"))
        self.assertEqual(result.text, "か カ か カ")
        self.assertEqual(result.unique, 1)
        self.assertEqual(result.replacements, 4)


if __name__ == "__main__":
    unittest.main()
