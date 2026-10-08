package com.godrayine.kanastudio;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Local converter matching the desktop implementation, including Unicode positions. */
public final class KanaEngine {
    public static final class Kana {
        public final String reading, hiragana, katakana, group;
        public final String[] aliases;
        public Kana(String reading, String hiragana, String katakana, String group, String... aliases) {
            this.reading = reading; this.hiragana = hiragana; this.katakana = katakana;
            this.group = group; this.aliases = aliases;
        }
    }

    public static final class Options {
        public String alphabet = "hiragana";
        public Set<String> selected = baseReadings();
        public int density = 100;
        public boolean snowball, replaceE, wideSpaces;
        public Options copy() {
            Options copy = new Options();
            copy.alphabet = alphabet; copy.selected = new HashSet<>(selected); copy.density = density;
            copy.snowball = snowball; copy.replaceE = replaceE; copy.wideSpaces = wideSpaces;
            return copy;
        }
    }

    public static final class Segment {
        public final String text, original, reading;
        public Segment(String text, String original, String reading) {
            this.text = text; this.original = original; this.reading = reading;
        }
    }

    public static final class Result {
        public final String text;
        public final List<Segment> segments;
        public final int replacements, possible, unique;
        Result(List<Segment> segments, int replacements, int possible, int unique) {
            this.segments = Collections.unmodifiableList(segments);
            this.replacements = replacements; this.possible = possible; this.unique = unique;
            StringBuilder output = new StringBuilder();
            for (Segment segment : segments) output.append(segment.text);
            text = output.toString();
        }
    }

    public static Set<String> baseReadings() {
        Set<String> result = new HashSet<>();
        for (Kana kana : KanaTable.ALL)
            if (!kana.group.equals("voiced") && !kana.group.equals("contracted")) result.add(kana.reading);
        return result;
    }

    public static Result convert(String text, Options options) {
        if (!options.alphabet.equals("hiragana") && !options.alphabet.equals("katakana") && !options.alphabet.equals("mixed"))
            throw new IllegalArgumentException("Unknown alphabet");
        if (options.density < 0 || options.density > 100) throw new IllegalArgumentException("Invalid density");
        Map<String, Kana> lookup = new HashMap<>();
        for (Kana kana : KanaTable.ALL) {
            if (!options.selected.contains(kana.reading)) continue;
            List<String> spellings = new ArrayList<>();
            spellings.add(kana.reading);
            Collections.addAll(spellings, kana.aliases);
            for (String spelling : spellings) {
                lookup.put(spelling, kana);
                if (options.replaceE && spelling.contains("э")) lookup.put(spelling.replace('э', 'е'), kana);
            }
        }
        List<Segment> segments = new ArrayList<>();
        if (lookup.isEmpty()) {
            segments.add(new Segment(options.wideSpaces ? text.replace(' ', '\u3000') : text, "", ""));
            return new Result(segments, 0, 0, 0);
        }
        List<String> keys = new ArrayList<>(lookup.keySet());
        Collections.sort(keys, (a, b) -> a.length() == b.length() ? a.compareTo(b) : b.length() - a.length());
        StringBuilder regex = new StringBuilder();
        for (String key : keys) { if (regex.length() > 0) regex.append('|'); regex.append(Pattern.quote(key)); }
        Matcher matcher = Pattern.compile(regex.toString(), Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE).matcher(text);
        int last = 0, replaced = 0, possible = 0;
        int characters = Math.max(text.codePointCount(0, text.length()), 1);
        int codePointsAtEnd = 0, previousEnd = 0;
        double quota = 0;
        Set<String> used = new HashSet<>();
        while (matcher.find()) {
            possible++;
            double chance = options.density / 100.0;
            if (options.snowball) {
                codePointsAtEnd += text.codePointCount(previousEnd, matcher.end());
                previousEnd = matcher.end();
                chance *= (double) codePointsAtEnd / characters;
            }
            quota += chance;
            if (quota + 1e-9 < 1) continue;
            quota -= 1;
            Kana kana = lookup.get(matcher.group().toLowerCase(Locale.ROOT));
            if (matcher.start() > last) segments.add(new Segment(text.substring(last, matcher.start()), "", ""));
            boolean kata = options.alphabet.equals("katakana") || (options.alphabet.equals("mixed") && replaced % 2 == 1);
            segments.add(new Segment(kata ? kana.katakana : kana.hiragana, matcher.group(), kana.reading));
            used.add(kana.reading); replaced++; last = matcher.end();
        }
        if (last < text.length()) segments.add(new Segment(text.substring(last), "", ""));
        if (options.wideSpaces) {
            List<Segment> spaced = new ArrayList<>();
            for (Segment segment : segments) spaced.add(new Segment(segment.text.replace(' ', '\u3000'), segment.original, segment.reading));
            segments = spaced;
        }
        return new Result(segments, replaced, possible, used.size());
    }
}
