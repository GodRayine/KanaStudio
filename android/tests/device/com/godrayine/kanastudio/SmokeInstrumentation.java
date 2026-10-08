package com.godrayine.kanastudio;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;

/** Runs ONLY on a disposable emulator: changes its app draft and settings. */
public class SmokeInstrumentation extends Instrumentation {
    private int checks;
    private void check(boolean condition, String description) { if (!condition) throw new AssertionError(description); checks++; }
    private View find(View root, String text) {
        if (root instanceof TextView && ((TextView)root).getText().toString().equals(text)) return root;
        if (root instanceof ViewGroup) for (int i = 0; i < ((ViewGroup)root).getChildCount(); i++) { View found = find(((ViewGroup)root).getChildAt(i), text); if (found != null) return found; }
        return null;
    }
    private Object field(Activity activity, String name) throws Exception { Field field = MainActivity.class.getDeclaredField(name); field.setAccessible(true); return field.get(activity); }
    private void click(Activity activity, String label) { View view = find(activity.getWindow().getDecorView(), label); if (view == null) throw new AssertionError("Missing button " + label); view.performClick(); }
    @Override public void onCreate(Bundle arguments) { super.onCreate(arguments); start(); }
    @Override public void onStart() {
        Bundle result = new Bundle(); Activity activity = null;
        try {
            PackageInfo info = getTargetContext().getPackageManager().getPackageInfo("com.godrayine.kanastudio", android.content.pm.PackageManager.GET_PERMISSIONS);
            check(info.requestedPermissions == null || info.requestedPermissions.length == 0, "APK requests permissions");
            check((info.applicationInfo.flags & ApplicationInfo.FLAG_ALLOW_BACKUP) == 0, "Backup enabled");
            check(MainActivity.decodeText("\ufeffПривет".getBytes(StandardCharsets.UTF_8)).equals("Привет"), "UTF8 BOM");
            check(MainActivity.decodeText("Привет".getBytes(StandardCharsets.UTF_16)).equals("Привет"), "UTF16");
            check(MainActivity.decodeText("Привет".getBytes(java.nio.charset.Charset.forName("windows-1251"))).equals("Привет"), "CP1251");
            Intent intent = new Intent().setClassName("com.godrayine.kanastudio", "com.godrayine.kanastudio.MainActivity").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            activity = startActivitySync(intent); final Activity app = activity;
            runOnMainSync(() -> {
                try {
                    EditText editor = (EditText)field(app, "editor");
                    check(editor != null, "Editor opens"); editor.setText("тихо птица чисто ка ка 🙂");
                    click(app, "Читать текст");
                } catch (Exception error) { throw new RuntimeException(error); }
            });
            Thread.sleep(800); waitForIdleSync();
            runOnMainSync(() -> {
                try {
                    KanaEngine.Result converted = (KanaEngine.Result)field(app, "result");
                    check(converted != null && converted.replacements > 0, "Conversion rendered");
                    for (KanaEngine.Segment segment : converted.segments) check(!segment.reading.equals("чи") || segment.original.equals("чи"), "TI incorrectly replaced with CHI");
                    check(((TextView)field(app, "output")).getText().toString().equals(converted.text), "Rendered text equals conversion");
                    click(app, "Скопировать"); click(app, "Слоги");
                    click(app, "Ни одного"); check(((KanaEngine.Options)field(app, "options")).selected.isEmpty(), "Clear selection");
                    click(app, "Базовые"); check(((KanaEngine.Options)field(app, "options")).selected.size() == 46, "Basic selection");
                    click(app, "Все"); check(((KanaEngine.Options)field(app, "options")).selected.size() == 104, "All selection");
                    click(app, "Катакана"); check(((KanaEngine.Options)field(app, "options")).alphabet.equals("katakana"), "Alphabet control");
                    click(app, "Базовые"); click(app, "Текст");
                    check(((EditText)field(app, "editor")).getText().toString().equals("тихо птица чисто ка ка 🙂"), "Draft preserved across tabs");
                    View decor = app.getWindow().getDecorView(); toggleTheme(decor);
                    check(((EditText)field(app, "editor")).getText().toString().equals("тихо птица чисто ка ка 🙂"), "Draft preserved across theme");
                    toggleTheme(app.getWindow().getDecorView()); click(app, "Читать текст");
                } catch (Exception error) { throw new RuntimeException(error); }
            });
            Thread.sleep(500); waitForIdleSync();
            runOnMainSync(() -> {
                try {
                    Button copy = (Button)find(app.getWindow().getDecorView(), "Скопировать");
                    check(copy.isEnabled(), "Copy enabled with text");
                    check(copy.getHeight() / getTargetContext().getResources().getDisplayMetrics().density >= 48, "Copy touch target");
                    check(!((KanaEngine.Result)field(app, "result")).text.isEmpty(), "Katakana output");
                } catch (Exception error) { throw new RuntimeException(error); }
            });
            result.putString("stream", "PASS: " + checks + " device checks; no permissions, backup disabled, encodings, conversion, controls, themes, draft, touch targets.\n");
            finish(Activity.RESULT_OK, result);
        } catch (Throwable error) {
            result.putString("stream", "FAIL: " + error + "\n"); finish(Activity.RESULT_CANCELED, result);
        }
    }
    private boolean toggleTheme(View view) {
        CharSequence description = view.getContentDescription();
        if (description != null && description.toString().contains("тему")) { view.performClick(); return true; }
        if (view instanceof ViewGroup) for (int i = 0; i < ((ViewGroup)view).getChildCount(); i++) if (toggleTheme(((ViewGroup)view).getChildAt(i))) return true;
        return false;
    }
}
