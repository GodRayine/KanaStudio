package com.godrayine.kanastudio;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.res.ColorStateList;
import android.content.res.Configuration;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.InputType;
import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.text.TextWatcher;
import android.text.method.LinkMovementMethod;
import android.text.style.ClickableSpan;
import android.text.style.BackgroundColorSpan;
import android.text.style.ForegroundColorSpan;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.GridLayout;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.Charset;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Native, dependency-free Android UI. No network APIs or permissions. */
public class MainActivity extends Activity {
    static final String SAMPLE = "Тихо падает снег. Мама и папа читают книгу.\n\nЧистый лист ждёт новую историю. У окна стоит чашка чая, а рядом спит кот. Начни с нескольких слогов и читай в своём темпе.";
    static final String[] GROUPS = {"vowels", "k", "s", "t", "n", "h", "m", "y", "r", "w", "voiced", "contracted"};
    static final String[] GROUP_LABELS = {"Гласные", "К · ка ки ку кэ ко", "С · са си су сэ со", "Т / Ч · та чи цу тэ то", "Н · на ни ну нэ но", "Х · ха хи ху хэ хо", "М · ма ми му мэ мо", "Я · я ю ё", "Р · ра ри ру рэ ро", "В · ва во · н", "Звонкие и полузвонкие", "Сочетания · кя, сю, чо"};
    private static final int OPEN_TEXT = 11, SAVE_TEXT = 12;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private SharedPreferences prefs;
    private KanaEngine.Options options = new KanaEngine.Options();
    private KanaEngine.Result result;
    private boolean dark, highlight = true, readerControlsExpanded;
    private String draft = "", exportText = "";
    private int page, revision, textSize = 20;
    private Palette colors;
    private LinearLayout root, content, tabs;
    private FrameLayout host;
    private ScrollView scroller;
    private EditText editor;
    private TextView output, stats, selectionCount;
    private Button copyButton, saveButton, readingsButton;
    private final Runnable updateTask = () -> convertAsync(null);
    private final Runnable saveTask = () -> saveState();

    @Override public void onCreate(Bundle state) {
        prefs = getSharedPreferences("kana-studio", MODE_PRIVATE);
        dark = prefs.getBoolean("dark", (getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES);
        setTheme(dark ? R.style.AppThemeDark : R.style.AppTheme);
        super.onCreate(state);
        draft = prefs.getString("draft", "");
        options.selected = new HashSet<>(prefs.getStringSet("selected", KanaEngine.baseReadings()));
        options.alphabet = prefs.getString("alphabet", "hiragana");
        options.density = Math.max(0, Math.min(100, prefs.getInt("density", 100)));
        options.snowball = prefs.getBoolean("snowball", false);
        options.replaceE = prefs.getBoolean("replace-e", false);
        options.wideSpaces = prefs.getBoolean("wide-spaces", false);
        highlight = prefs.getBoolean("highlight", true);
        textSize = Math.max(16, Math.min(32, prefs.getInt("text-size", 20)));
        if (state != null) { page = state.getInt("page", 0); readerControlsExpanded = state.getBoolean("reader-controls", false); }
        Session previous = (Session)getLastNonConfigurationInstance();
        if (previous != null) { draft = previous.draft; options = previous.options; exportText = previous.exportText; page = previous.page; }
        if (Build.VERSION.SDK_INT >= 33) getOnBackInvokedDispatcher().registerOnBackInvokedCallback(0, this::navigateBack);
        buildUI();
    }

    private void buildUI() {
        colors = new Palette(dark);
        editor = null; output = null; stats = null; selectionCount = null;
        copyButton = null; saveButton = null; readingsButton = null;
        root = vertical(); root.setBackgroundColor(colors.background);
        root.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS);
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                android.graphics.Insets ime = insets.getInsets(WindowInsets.Type.ime());
                root.setPadding(bars.left, bars.top, bars.right, Math.max(bars.bottom, ime.bottom));
                return insets;
            });
        }
        getWindow().setStatusBarColor(colors.background);
        getWindow().setNavigationBarColor(colors.surface);
        if (Build.VERSION.SDK_INT >= 29) {
            getWindow().setNavigationBarContrastEnforced(false);
            getWindow().setStatusBarContrastEnforced(false);
        }
        LinearLayout header = horizontal(); header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(20), dp(8), dp(12), dp(8));
        TextView title = text("Kana Studio", 22, true); if (Build.VERSION.SDK_INT >= 28) title.setAccessibilityHeading(true);
        header.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
        ImageButton theme = iconButton(dark ? "sun" : "moon", dark ? "Включить светлую тему" : "Включить тёмную тему", () -> {
            captureDraft(); dark = !dark; saveState();
            setTheme(dark ? R.style.AppThemeDark : R.style.AppTheme); buildUI();
        });
        header.addView(theme, new LinearLayout.LayoutParams(dp(48), dp(48)));
        ImageButton help = iconButton("help", "Как пользоваться", this::showHelp);
        LinearLayout.LayoutParams helpParams = new LinearLayout.LayoutParams(dp(48), dp(48)); helpParams.leftMargin = dp(8);
        header.addView(help, helpParams); root.addView(header);
        host = new FrameLayout(this); root.addView(host, new LinearLayout.LayoutParams(-1, 0, 1));
        tabs = horizontal(); tabs.setPadding(dp(12), dp(8), dp(12), dp(8)); tabs.setBackgroundColor(colors.surface);
        String[] labels = {"Текст", "Чтение", "Слоги"};
        for (int i = 0; i < labels.length; i++) {
            final int target = i;
            Button tab = button(labels[i], () -> switchPage(target), page == target);
            tab.setSelected(page == i); tab.setContentDescription(labels[i] + (page == i ? ", открытая вкладка" : ", вкладка"));
            addWeighted(tabs, tab);
        }
        root.addView(tabs); setContentView(root); root.requestApplyInsets();
        updateSystemBars(); root.post(this::updateSystemBars);
        showPage();
    }

    private void updateSystemBars() {
        getWindow().getDecorView().setSystemUiVisibility(dark ? 0 : View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        if (Build.VERSION.SDK_INT >= 30) {
            int appearance = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
            getWindow().getInsetsController().setSystemBarsAppearance(dark ? 0 : appearance, appearance);
        }
    }

    private void switchPage(int target) {
        if (target == page) return;
        captureDraft(); saveState();
        View focus = getCurrentFocus();
        if (focus != null) ((InputMethodManager) getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(focus.getWindowToken(), 0);
        page = target; buildUI();
    }

    private void showPage() {
        host.removeAllViews();
        scroller = new ScrollView(this); scroller.setFillViewport(true); scroller.setClipToPadding(false);
        content = vertical();
        int width = getResources().getConfiguration().screenWidthDp;
        int gutter = Math.max(16, (width - 720) / 2);
        content.setPadding(dp(gutter), dp(8), dp(gutter), dp(24));
        scroller.addView(content, new ScrollView.LayoutParams(-1, -2));
        host.addView(scroller, new FrameLayout.LayoutParams(-1, -1));
        if (page == 0) showEditor(); else if (page == 1) showReader(); else showSelection();
    }

    private void heading(String title, String subtitle) {
        TextView heading = text(title, 28, true); if (Build.VERSION.SDK_INT >= 28) heading.setAccessibilityHeading(true); content.addView(heading);
        if (!subtitle.isEmpty()) { TextView sub = text(subtitle, 15, false); sub.setTextColor(colors.muted); add(content, sub, 6); }
    }

    private void showEditor() {
        heading("Знакомый текст,\nновые знаки", "Добавь текст и выбери, какие слоги изучать.");
        LinearLayout card = card(); add(content, card, 24);
        TextView label = text("Русский текст", 16, true); card.addView(label);
        editor = new EditText(this);
        editor.setTextColor(colors.text); editor.setHintTextColor(colors.muted); editor.setTextSize(17);
        editor.setGravity(Gravity.TOP | Gravity.START); editor.setMinHeight(dp(208)); editor.setMaxLines(14);
        editor.setPadding(0, dp(12), 0, dp(12)); editor.setBackgroundColor(Color.TRANSPARENT);
        editor.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        editor.setImeOptions(EditorInfo.IME_FLAG_NO_EXTRACT_UI | EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING);
        editor.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        editor.setSaveEnabled(false); // Avoid duplicating large drafts in Binder saved state.
        editor.setHint("Вставь русский текст или открой пример");
        editor.setContentDescription("Русский текст для замены слогов");
        editor.setText(draft); card.addView(editor, new LinearLayout.LayoutParams(-1, -2));
        editor.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                draft = s.toString(); revision++;
                handler.removeCallbacks(saveTask); handler.postDelayed(saveTask, 500);
            }
            public void afterTextChanged(Editable editable) {}
        });
        LinearLayout actions = horizontal();
        addWeighted(actions, button("Пример", () -> replaceDraft(SAMPLE), false));
        addWeighted(actions, button("Открыть TXT", this::openText, false));
        add(card, actions, 8);
        Button clear = button("Очистить текст", () -> {
            if (draft.isEmpty()) return;
            new AlertDialog.Builder(this).setTitle("Очистить текст?").setMessage("Текущий черновик будет удалён.")
                .setNegativeButton("Отмена", null).setPositiveButton("Очистить", (dialog, which) -> setDraft("")).show();
        }, false);
        add(card, clear, 8);
        LinearLayout alphabet = card(); add(content, alphabet, 16);
        alphabet.addView(text("Азбука", 16, true)); addAlphabetButtons(alphabet);
        Button read = button("Читать текст", () -> switchPage(1), true); add(content, read, 20);
    }

    private void addAlphabetButtons(LinearLayout parent) {
        boolean large = getResources().getConfiguration().fontScale > 1.3f;
        LinearLayout row = large ? vertical() : horizontal();
        String[] names = {"Хирагана", "Катакана", "Обе"}; String[] values = {"hiragana", "katakana", "mixed"};
        for (int i = 0; i < names.length; i++) {
            final String value = values[i];
            Button choice = button(names[i], () -> { captureDraft(); options.alphabet = value; saveState(); buildUI(); }, options.alphabet.equals(value));
            choice.setSelected(options.alphabet.equals(value));
            choice.setContentDescription(names[i] + (options.alphabet.equals(value) ? ", выбрано" : ""));
            if (large) add(row, choice, 8); else addWeighted(row, choice);
        }
        add(parent, row, 12);
    }

    private void showReader() {
        heading("Читай в своём темпе", "Нажми на знак каны, чтобы увидеть чтение.");
        LinearLayout settingsCard = card(); add(content, settingsCard, 24);
        LinearLayout controls = vertical();
        Button settingsButton = button((readerControlsExpanded ? "Свернуть настройки · " : "Настроить чтение · ") + options.density + "%", null, false);
        settingsButton.setOnClickListener(view -> {
            readerControlsExpanded = !readerControlsExpanded;
            controls.setVisibility(readerControlsExpanded ? View.VISIBLE : View.GONE);
            settingsButton.setText((readerControlsExpanded ? "Свернуть настройки · " : "Настроить чтение · ") + options.density + "%");
            if (Build.VERSION.SDK_INT >= 30) settingsButton.setStateDescription(readerControlsExpanded ? "Развёрнуто" : "Свёрнуто");
        });
        settingsCard.addView(settingsButton); add(settingsCard, controls, 12);
        controls.setVisibility(readerControlsExpanded ? View.VISIBLE : View.GONE);
        controls.addView(text("Количество замен", 16, true));
        LinearLayout densityRow = horizontal(); densityRow.setGravity(Gravity.CENTER_VERTICAL);
        Button less = button("−", () -> setDensity(options.density - 10), false); less.setContentDescription("Уменьшить количество замен на 10 процентов");
        Button more = button("+", () -> setDensity(options.density + 10), false); more.setContentDescription("Увеличить количество замен на 10 процентов");
        TextView percent = text(options.density + "%", 20, true); percent.setGravity(Gravity.CENTER);
        densityRow.addView(less, new LinearLayout.LayoutParams(dp(48), -2));
        densityRow.addView(percent, new LinearLayout.LayoutParams(0, -2, 1));
        densityRow.addView(more, new LinearLayout.LayoutParams(dp(48), -2)); add(controls, densityRow, 12);
        SeekBar density = new SeekBar(this); density.setMax(100); density.setProgress(options.density);
        density.setProgressTintList(ColorStateList.valueOf(colors.accent)); density.setThumbTintList(ColorStateList.valueOf(colors.accent));
        density.setContentDescription("Количество замен в процентах"); density.setMinimumHeight(dp(48));
        density.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onProgressChanged(SeekBar bar, int value, boolean user) {
                if (user) { options.density = value; percent.setText(value + "%"); settingsButton.setText("Свернуть настройки · " + value + "%"); changed(); }
            }
            public void onStartTrackingTouch(SeekBar bar) {}
            public void onStopTrackingTouch(SeekBar bar) { saveState(); }
        }); controls.addView(density, new LinearLayout.LayoutParams(-1, dp(48)));
        CheckBox snow = checkbox("Снежный ком", options.snowball);
        snow.setOnCheckedChangeListener((button, checked) -> { options.snowball = checked; changed(); }); controls.addView(snow);
        TextView snowHint = text("Замен становится больше к концу текста", 14, false); snowHint.setTextColor(colors.muted); controls.addView(snowHint);
        LinearLayout readingCard = card(); add(content, readingCard, 16);
        stats = text("Обновляю текст…", 14, false); stats.setTextColor(colors.muted); readingCard.addView(stats);
        output = text("", textSize, false); output.setLineSpacing(dp(6), 1.15f); output.setTextIsSelectable(true);
        output.setHighlightColor(colors.highlight); output.setLinkTextColor(colors.accent);
        add(readingCard, output, 16);
        LinearLayout sizes = horizontal();
        Button smaller = button("А−", () -> setTextSize(textSize - 2), false); smaller.setContentDescription("Уменьшить размер текста");
        Button larger = button("А+", () -> setTextSize(textSize + 2), false); larger.setContentDescription("Увеличить размер текста");
        addWeighted(sizes, smaller); addWeighted(sizes, larger);
        readingsButton = button("Чтения", this::showReadings, false); addWeighted(sizes, readingsButton); add(readingCard, sizes, 16);
        LinearLayout actions = horizontal();
        copyButton = button("Скопировать", () -> convertAsync(current -> {
            if (current.text.isEmpty()) return;
            ((ClipboardManager) getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("Текст с каной", current.text));
            if (Build.VERSION.SDK_INT < 33) notifyUser("Текст скопирован");
        }), true);
        saveButton = button("Сохранить TXT", () -> convertAsync(current -> {
            if (!current.text.isEmpty()) { exportText = current.text; saveText(); }
        }), false);
        addWeighted(actions, copyButton); addWeighted(actions, saveButton); add(content, actions, 16);
        CheckBox highlighted = checkbox("Подсвечивать кану", highlight);
        highlighted.setOnCheckedChangeListener((button, checked) -> { highlight = checked; saveState(); if (result != null) renderResult(result); });
        add(content, highlighted, 12);
        convertAsync(null);
    }

    private void showSelection() {
        heading("Что изучаем", "Выбирай группы или отдельные знаки.");
        selectionCount = text("", 15, false); selectionCount.setTextColor(colors.muted); add(content, selectionCount, 8); updateSelectionCount();
        boolean large = getResources().getConfiguration().fontScale > 1.3f;
        LinearLayout presets = large ? vertical() : horizontal();
        Button basic = button("Базовые", () -> setSelected(KanaEngine.baseReadings()), false);
        Button all = button("Все", () -> {
            Set<String> readings = new HashSet<>(); for (KanaEngine.Kana kana : KanaTable.ALL) readings.add(kana.reading); setSelected(readings);
        }, false);
        Button none = button("Ни одного", () -> setSelected(new HashSet<>()), false);
        if (large) { add(presets, basic, 0); add(presets, all, 8); add(presets, none, 8); }
        else { addWeighted(presets, basic); addWeighted(presets, all); addWeighted(presets, none); }
        add(content, presets, 16);
        LinearLayout alphabet = card(); alphabet.addView(text("Азбука", 16, true)); addAlphabetButtons(alphabet); add(content, alphabet, 16);
        for (int groupIndex = 0; groupIndex < GROUPS.length; groupIndex++) {
            final String group = GROUPS[groupIndex];
            List<KanaEngine.Kana> entries = new ArrayList<>();
            for (KanaEngine.Kana kana : KanaTable.ALL) if (kana.group.equals(group)) entries.add(kana);
            LinearLayout groupCard = card(); add(content, groupCard, 12);
            final CheckBox groupToggle = checkbox(GROUP_LABELS[groupIndex], allSelected(entries));
            TextView groupStatus = text("", 14, false); groupStatus.setTextColor(colors.muted);
            Button expand = button("Выбрать отдельно", null, false);
            GridLayout grid = new GridLayout(this); grid.setVisibility(View.GONE);
            int columns = Math.max(2, Math.min(5, (getResources().getConfiguration().screenWidthDp - 64) / (getResources().getConfiguration().fontScale > 1.3f ? 116 : 76)));
            grid.setColumnCount(columns);
            Map<String, Button> choices = new LinkedHashMap<>();
            Runnable update = () -> {
                int count = 0;
                for (KanaEngine.Kana kana : entries) { if (options.selected.contains(kana.reading)) count++; styleChoice(choices.get(kana.reading), options.selected.contains(kana.reading)); }
                groupStatus.setText(count + " из " + entries.size() + " выбрано");
                groupToggle.setOnCheckedChangeListener(null); groupToggle.setChecked(count == entries.size());
                groupToggle.setOnCheckedChangeListener((button, checked) -> {
                    for (KanaEngine.Kana kana : entries) { if (checked) options.selected.add(kana.reading); else options.selected.remove(kana.reading); }
                    updateGroup(choices, entries, groupStatus); updateSelectionCount(); changed();
                });
            };
            for (KanaEngine.Kana kana : entries) {
                String sign = options.alphabet.equals("katakana") ? kana.katakana : kana.hiragana;
                Button choice = button(sign + "\n" + kana.reading, () -> {
                    if (!options.selected.remove(kana.reading)) options.selected.add(kana.reading);
                    update.run(); updateSelectionCount(); changed();
                }, options.selected.contains(kana.reading));
                choice.setTextSize(18); choice.setContentDescription(sign + ", " + kana.reading);
                choice.setMinHeight(dp(72)); choices.put(kana.reading, choice);
                GridLayout.LayoutParams params = new GridLayout.LayoutParams();
                params.width = 0; params.height = -2; params.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f);
                params.setMargins(dp(4), dp(4), dp(4), dp(4)); grid.addView(choice, params);
            }
            expand.setOnClickListener(view -> {
                boolean opened = grid.getVisibility() != View.VISIBLE; grid.setVisibility(opened ? View.VISIBLE : View.GONE);
                expand.setText(opened ? "Свернуть знаки" : "Выбрать отдельно");
                if (Build.VERSION.SDK_INT >= 30) expand.setStateDescription(opened ? "Развёрнуто" : "Свёрнуто");
            });
            groupCard.addView(groupToggle); groupCard.addView(groupStatus); add(groupCard, expand, 8); add(groupCard, grid, 8); update.run();
        }
        LinearLayout extra = card(); add(content, extra, 16); extra.addView(text("Дополнительно", 18, true));
        CheckBox e = checkbox("Заменять е как э", options.replaceE); e.setOnCheckedChangeListener((button, checked) -> { options.replaceE = checked; changed(); }); extra.addView(e);
        CheckBox spaces = checkbox("Японские широкие пробелы", options.wideSpaces); spaces.setOnCheckedChangeListener((button, checked) -> { options.wideSpaces = checked; changed(); }); extra.addView(spaces);
    }

    private boolean allSelected(List<KanaEngine.Kana> entries) {
        for (KanaEngine.Kana kana : entries) if (!options.selected.contains(kana.reading)) return false;
        return true;
    }
    private void updateGroup(Map<String, Button> choices, List<KanaEngine.Kana> entries, TextView status) {
        int count = 0;
        for (KanaEngine.Kana kana : entries) { boolean selected = options.selected.contains(kana.reading); if (selected) count++; styleChoice(choices.get(kana.reading), selected); }
        status.setText(count + " из " + entries.size() + " выбрано");
    }
    private void styleChoice(Button choice, boolean selected) {
        if (choice == null) return;
        choice.setSelected(selected); choice.setTextColor(selected ? colors.onAccent : colors.text);
        choice.setBackground(ripple(selected ? colors.accent : colors.field, 12));
        if (Build.VERSION.SDK_INT >= 30) choice.setStateDescription(selected ? "Выбрано" : "Не выбрано");
    }
    private void updateSelectionCount() {
        if (selectionCount != null) selectionCount.setText("Выбрано " + options.selected.size() + " из " + KanaTable.ALL.length + " знаков");
    }
    private void setSelected(Set<String> selected) { options.selected = new HashSet<>(selected); changed(); buildUI(); }
    private void setDensity(int value) { options.density = Math.max(0, Math.min(100, value)); changed(); buildUI(); }
    private void setTextSize(int value) { textSize = Math.max(16, Math.min(32, value)); saveState(); if (output != null) output.setTextSize(textSize); }
    private void changed() { revision++; saveState(); handler.removeCallbacks(updateTask); if (page == 1) handler.postDelayed(updateTask, 150); }

    private interface ResultAction { void run(KanaEngine.Result result); }
    private void convertAsync(ResultAction action) {
        final String source = draft; final KanaEngine.Options snapshot = options.copy(); final int generation = revision;
        if (stats != null) stats.setText("Обновляю текст…");
        worker.execute(() -> {
            try {
                KanaEngine.Result converted = KanaEngine.convert(source, snapshot);
                handler.post(() -> {
                    if (isFinishing() || isDestroyed()) return;
                    if (generation != revision) { if (action != null) convertAsync(action); return; }
                    result = converted; if (page == 1 && output != null) renderResult(converted);
                    if (action != null) action.run(converted);
                });
            } catch (RuntimeException error) { handler.post(() -> notifyUser("Не удалось обработать текст")); }
        });
    }
    private void renderResult(KanaEngine.Result converted) {
        if (output == null) return;
        if (draft.isEmpty()) {
            output.setText("Добавь текст на вкладке «Текст», чтобы начать чтение."); output.setTextColor(colors.muted); stats.setText("Пока нет текста");
        } else {
            output.setTextColor(colors.text);
            SpannableStringBuilder rich = new SpannableStringBuilder();
            boolean hints = converted.text.length() <= 120_000;
            for (KanaEngine.Segment segment : converted.segments) {
                int start = rich.length(); rich.append(segment.text);
                if (!segment.reading.isEmpty() && hints) {
                    if (highlight) rich.setSpan(new BackgroundColorSpan(colors.highlight), start, rich.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                    rich.setSpan(new ClickableSpan() {
                        @Override public void onClick(View widget) {
                            new AlertDialog.Builder(MainActivity.this).setTitle(segment.text + " · " + segment.reading)
                                .setMessage("Исходный слог: «" + segment.original + "».\nРусское чтение приблизительное.").setPositiveButton("Понятно", null).show();
                        }
                        @Override public void updateDrawState(android.text.TextPaint paint) { paint.setColor(colors.text); paint.setUnderlineText(false); }
                    }, start, rich.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                }
            }
            output.setText(rich); output.setMovementMethod(LinkMovementMethod.getInstance());
            stats.setText("Замен: " + converted.replacements + " · разных слогов: " + converted.unique);
        }
        boolean hasText = !converted.text.isEmpty(); setEnabled(copyButton, hasText); setEnabled(saveButton, hasText); setEnabled(readingsButton, converted.replacements > 0);
    }
    private void setEnabled(Button button, boolean enabled) { if (button != null) { button.setEnabled(enabled); button.setAlpha(enabled ? 1 : .45f); } }

    private void showReadings() {
        if (result == null) return;
        Set<String> seen = new HashSet<>(); StringBuilder readings = new StringBuilder();
        for (KanaEngine.Segment segment : result.segments) if (!segment.reading.isEmpty() && seen.add(segment.text + segment.reading))
            readings.append(segment.text).append("  —  ").append(segment.reading).append('\n');
        ScrollView scroll = new ScrollView(this); TextView text = text(readings.toString().trim(), 20, false); text.setPadding(dp(24), dp(12), dp(24), dp(24)); scroll.addView(text);
        new AlertDialog.Builder(this).setTitle("Чтения в этом тексте").setView(scroll).setPositiveButton("Закрыть", null).show();
    }
    private void captureDraft() { if (editor != null) draft = editor.getText().toString(); }
    private void saveState() {
        if (prefs == null) return;
        prefs.edit().putBoolean("dark", dark).putString("draft", draft.length() <= 200_000 ? draft : "")
            .putStringSet("selected", new HashSet<>(options.selected)).putString("alphabet", options.alphabet).putInt("density", options.density)
            .putBoolean("snowball", options.snowball).putBoolean("replace-e", options.replaceE).putBoolean("wide-spaces", options.wideSpaces)
            .putBoolean("highlight", highlight).putInt("text-size", textSize).apply();
    }
    private void setDraft(String text) {
        draft = text; revision++; saveState();
        if (editor != null) editor.setText(text); else buildUI();
    }
    private void replaceDraft(String text) {
        captureDraft();
        if (draft.trim().isEmpty()) { setDraft(text); return; }
        new AlertDialog.Builder(this).setTitle("Заменить текст?").setMessage("Текущий черновик будет заменён.")
            .setNegativeButton("Отмена", null).setPositiveButton("Заменить", (dialog, which) -> setDraft(text)).show();
    }
    private void openText() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("text/*").addCategory(Intent.CATEGORY_OPENABLE);
        intent.putExtra(Intent.EXTRA_LOCAL_ONLY, true);
        try { startActivityForResult(intent, OPEN_TEXT); } catch (android.content.ActivityNotFoundException error) { notifyUser("На устройстве нет приложения для выбора файлов"); }
    }
    private void saveText() {
        final String pending = exportText;
        worker.execute(() -> {
            try (OutputStream file = openFileOutput("pending-export.txt", MODE_PRIVATE)) {
                file.write(pending.getBytes(StandardCharsets.UTF_8));
                handler.post(() -> { if (!isDestroyed()) launchSavePicker(); });
            } catch (Exception error) { handler.post(() -> notifyUser("Не удалось подготовить TXT")); }
        });
    }
    private void launchSavePicker() {
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("text/plain").addCategory(Intent.CATEGORY_OPENABLE);
        intent.putExtra(Intent.EXTRA_TITLE, "Текст с каной.txt"); intent.putExtra(Intent.EXTRA_LOCAL_ONLY, true);
        try { startActivityForResult(intent, SAVE_TEXT); } catch (android.content.ActivityNotFoundException error) { notifyUser("На устройстве нет приложения для сохранения файлов"); }
    }
    @Override protected void onActivityResult(int request, int status, Intent data) {
        super.onActivityResult(request, status, data);
        if (status != RESULT_OK || data == null || data.getData() == null) { if (request == SAVE_TEXT) deleteFile("pending-export.txt"); return; }
        Uri uri = data.getData();
        if (request == OPEN_TEXT) {
            worker.execute(() -> {
                try (InputStream input = getContentResolver().openInputStream(uri); ByteArrayOutputStream buffer = new ByteArrayOutputStream()) {
                    if (input == null) throw new java.io.IOException();
                    byte[] bytes = new byte[8192]; int length;
                    while ((length = input.read(bytes)) != -1) { if (buffer.size() + length > 2_000_000) throw new IllegalArgumentException("Выбери TXT размером до 2 МБ"); buffer.write(bytes, 0, length); }
                    String imported = decodeText(buffer.toByteArray()).replace("\r\n", "\n").replace('\r', '\n');
                    if (imported.indexOf('\0') >= 0) throw new IllegalArgumentException("Это не текстовый файл. Сохрани документ как TXT.");
                    handler.post(() -> { if (!isDestroyed()) replaceDraft(imported); });
                } catch (Exception error) { handler.post(() -> notifyUser(error instanceof IllegalArgumentException ? error.getMessage() : "Не удалось открыть TXT")); }
            });
        } else if (request == SAVE_TEXT) {
            worker.execute(() -> {
                try (InputStream pending = openFileInput("pending-export.txt"); OutputStream output = getContentResolver().openOutputStream(uri, "wt")) {
                    if (output == null) throw new java.io.IOException();
                    byte[] bytes = new byte[8192]; int length; while ((length = pending.read(bytes)) != -1) output.write(bytes, 0, length);
                    handler.post(() -> notifyUser("TXT сохранён"));
                } catch (Exception error) { handler.post(() -> notifyUser("Не удалось сохранить TXT")); }
                finally { deleteFile("pending-export.txt"); }
            });
        }
    }
    static String decodeText(byte[] bytes) throws CharacterCodingException {
        if (bytes.length >= 2 && ((bytes[0] == (byte)0xff && bytes[1] == (byte)0xfe) || (bytes[0] == (byte)0xfe && bytes[1] == (byte)0xff)))
            return StandardCharsets.UTF_16.newDecoder().onMalformedInput(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
        try {
            String decoded = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
            return decoded.startsWith("\ufeff") ? decoded.substring(1) : decoded;
        } catch (CharacterCodingException error) { return Charset.forName("windows-1251").newDecoder().decode(ByteBuffer.wrap(bytes)).toString(); }
    }
    private void showHelp() {
        ScrollView scroll = new ScrollView(this);
        TextView help = text("1. Добавь текст\nВставь русский текст, открой TXT из памяти телефона или нажми «Пример».\n\n2. Выбери слоги\nНа вкладке «Слоги» включай группы и отдельные знаки. ち / チ заменяет «чи», а не «ти».\n\n3. Читай\nПолзунок регулирует количество замен. «Снежный ком» делает замены редкими в начале и частыми к концу. Нажми на знак или кнопку «Чтения» для подсказки.\n\n4. Сохрани\nСкопируй результат или сохрани TXT в память телефона. Черновик и настройки сохраняются внутри приложения. Тексты свыше 200 000 символов нужно сохранять вручную. Для длинных текстов свыше 120 000 символов подсветка отключается.\n\nЛокальная работа\nПриложение не имеет сетевых разрешений, не содержит рекламы, аналитики и внешних сервисов. Облачное резервное копирование и перенос данных отключены. Системный выбор файлов ограничен локальными документами. Буфер обмена используется только после нажатия «Скопировать».\n\nЭто приблизительная учебная замена слогов, а не перевод.\n\nKana Studio для Android · 1.0.0\nCopyright (C) 2026 GodRayine. GNU GPL v3 или более поздняя. Без гарантий. Идея метода — Илья Виноградов; оригинальная «Кананизация» — Алексей Сергеев.", 16, false);
        help.setPadding(dp(24), dp(16), dp(24), dp(24)); help.setLineSpacing(dp(4), 1.05f); scroll.addView(help);
        new AlertDialog.Builder(this).setTitle("Как пользоваться").setView(scroll).setNegativeButton("Закрыть", null)
            .setPositiveButton("Лицензия", (dialog, which) -> showLicense()).show();
    }
    private void showLicense() {
        worker.execute(() -> {
            try (InputStream input = getAssets().open("LICENSE"); ByteArrayOutputStream buffer = new ByteArrayOutputStream()) {
                byte[] bytes = new byte[8192]; int length; while ((length = input.read(bytes)) != -1) buffer.write(bytes, 0, length);
                String license = new String(buffer.toByteArray(), StandardCharsets.UTF_8);
                handler.post(() -> {
                    if (isDestroyed()) return;
                    ScrollView scroll = new ScrollView(this); TextView text = text(license, 14, false); text.setPadding(dp(24), dp(16), dp(24), dp(24)); scroll.addView(text);
                    new AlertDialog.Builder(this).setTitle("GNU GPL v3+").setView(scroll).setPositiveButton("Закрыть", null).show();
                });
            } catch (Exception error) { handler.post(() -> notifyUser("Не удалось открыть лицензию")); }
        });
    }
    private void navigateBack() { if (page != 0) switchPage(0); else finish(); }
    @Override public void onBackPressed() { navigateBack(); }
    @Override protected void onSaveInstanceState(Bundle state) { captureDraft(); saveState(); state.putInt("page", page); state.putBoolean("reader-controls", readerControlsExpanded); super.onSaveInstanceState(state); }
    @Override public Object onRetainNonConfigurationInstance() { captureDraft(); return new Session(draft, exportText, options.copy(), page); }
    @Override protected void onPause() { captureDraft(); saveState(); if (draft.length() > 200_000) notifyUser("Большой черновик не сохранён. Сохрани текст как TXT."); super.onPause(); }
    @Override protected void onDestroy() { handler.removeCallbacks(updateTask); handler.removeCallbacks(saveTask); worker.shutdown(); super.onDestroy(); }
    private void notifyUser(String message) { if (!isDestroyed()) Toast.makeText(this, message, Toast.LENGTH_SHORT).show(); }

    private static class Session {
        final String draft, exportText; final KanaEngine.Options options; final int page;
        Session(String draft, String exportText, KanaEngine.Options options, int page) { this.draft = draft; this.exportText = exportText; this.options = options; this.page = page; }
    }

    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private LinearLayout vertical() { LinearLayout layout = new LinearLayout(this); layout.setOrientation(LinearLayout.VERTICAL); return layout; }
    private LinearLayout horizontal() { LinearLayout layout = new LinearLayout(this); layout.setOrientation(LinearLayout.HORIZONTAL); return layout; }
    private TextView text(String value, int size, boolean bold) {
        TextView view = new TextView(this); view.setText(value); view.setTextSize(size); view.setTextColor(colors.text);
        view.setFontFeatureSettings("kern"); if (bold) view.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL)); return view;
    }
    private LinearLayout card() {
        LinearLayout layout = vertical(); layout.setPadding(dp(16), dp(16), dp(16), dp(16));
        layout.setBackground(shape(colors.surface, 20)); return layout;
    }
    private GradientDrawable shape(int color, int radius) { GradientDrawable drawable = new GradientDrawable(); drawable.setColor(color); drawable.setCornerRadius(dp(radius)); return drawable; }
    private RippleDrawable ripple(int color, int radius) {
        return new RippleDrawable(ColorStateList.valueOf(dark ? 0x30ffffff : 0x18000000), shape(color, radius), shape(Color.WHITE, radius));
    }
    private Button button(String label, Runnable action, boolean primary) {
        Button button = new Button(this); button.setText(label); button.setAllCaps(false); button.setTextSize(14);
        button.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL)); button.setTextColor(primary ? colors.onAccent : colors.text);
        button.setMinHeight(dp(48)); button.setMinimumHeight(dp(48)); button.setMinWidth(0); button.setMinimumWidth(0);
        button.setPadding(dp(8), dp(10), dp(8), dp(10)); button.setBackground(ripple(primary ? colors.accent : colors.field, 12));
        button.setStateListAnimator(null); button.setElevation(0);
        if (action != null) button.setOnClickListener(view -> action.run()); return button;
    }
    private CheckBox checkbox(String label, boolean checked) {
        CheckBox check = new CheckBox(this); check.setText(label); check.setTextColor(colors.text); check.setTextSize(16); check.setMinHeight(dp(48));
        check.setPadding(0, dp(4), dp(4), dp(4)); check.setButtonTintList(ColorStateList.valueOf(colors.accent)); check.setChecked(checked); return check;
    }
    private void add(LinearLayout parent, View child, int margin) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1, -2); params.topMargin = dp(margin); parent.addView(child, params);
    }
    private void addWeighted(LinearLayout row, View child) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, -2, 1); if (row.getChildCount() > 0) params.leftMargin = dp(8); row.addView(child, params);
    }
    private ImageButton iconButton(String icon, String description, Runnable action) {
        ImageButton button = new ImageButton(this); button.setImageDrawable(new Icon(icon, colors.text)); button.setContentDescription(description);
        button.setBackground(ripple(colors.background, 12)); button.setPadding(dp(12), dp(12), dp(12), dp(12)); button.setOnClickListener(view -> action.run()); return button;
    }
    private static class Palette {
        final int background, surface, field, text, muted, accent, onAccent, highlight;
        Palette(boolean dark) {
            background = Color.parseColor(dark ? "#141C18" : "#F2F6F3"); surface = Color.parseColor(dark ? "#202C25" : "#FFFFFF");
            field = Color.parseColor(dark ? "#33453A" : "#E5EEE7"); text = Color.parseColor(dark ? "#EDF5EF" : "#233B2E");
            muted = Color.parseColor(dark ? "#B1C5B8" : "#526559"); accent = Color.parseColor(dark ? "#A4D8BC" : "#285D47");
            onAccent = Color.parseColor(dark ? "#14291C" : "#FFFFFF"); highlight = Color.parseColor(dark ? "#365641" : "#D9EDDF");
        }
    }
    private static class Icon extends Drawable {
        final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG); final String type;
        Icon(String type, int color) { this.type = type; paint.setColor(color); paint.setStyle(Paint.Style.STROKE); paint.setStrokeWidth(1.8f); paint.setStrokeCap(Paint.Cap.ROUND); }
        @Override public void draw(Canvas canvas) {
            Rect bounds = getBounds(); canvas.save(); canvas.translate(bounds.left, bounds.top); canvas.scale(bounds.width() / 24f, bounds.height() / 24f);
            if (type.equals("sun")) {
                canvas.drawCircle(12, 12, 4, paint);
                for (int i = 0; i < 8; i++) { double angle = i * Math.PI / 4; canvas.drawLine(12 + (float)Math.cos(angle) * 7, 12 + (float)Math.sin(angle) * 7, 12 + (float)Math.cos(angle) * 10, 12 + (float)Math.sin(angle) * 10, paint); }
            } else if (type.equals("moon")) {
                android.graphics.Path path = new android.graphics.Path(); path.moveTo(19.5f, 14); path.cubicTo(11, 17, 7, 8, 11, 3); path.cubicTo(2, 4, 1, 15, 9, 20); path.cubicTo(14, 23, 19, 19, 19.5f, 14); canvas.drawPath(path, paint);
            } else {
                canvas.drawCircle(12, 12, 9, paint); android.graphics.Path path = new android.graphics.Path(); path.moveTo(9.5f, 8.5f); path.cubicTo(10, 5, 16, 6, 15, 9.5f); path.cubicTo(14.5f, 11, 12, 10.5f, 12, 13); canvas.drawPath(path, paint); canvas.drawPoint(12, 16.5f, paint);
            }
            canvas.restore();
        }
        @Override public void setAlpha(int alpha) { paint.setAlpha(alpha); }
        @Override public void setColorFilter(android.graphics.ColorFilter filter) { paint.setColorFilter(filter); }
        @Override public int getOpacity() { return android.graphics.PixelFormat.TRANSLUCENT; }
    }
}
