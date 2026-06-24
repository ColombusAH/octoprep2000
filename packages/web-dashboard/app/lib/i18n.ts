/**
 * Interface-language preference (FR-011, US3/P3) — a persisted, per-browser cookie,
 * independent of any session's speech_language/deck_language. See
 * specs/20260624-hebrew-rtl-support/data-model.md "Persisted UI Preference".
 */
import type { Language } from "./api";

export const UI_LANG_COOKIE = "octoprep_ui_lang";

export function getUiLanguage(): Language {
  if (typeof document === "undefined") return "en";
  const match = document.cookie.match(new RegExp(`${UI_LANG_COOKIE}=(en|he)`));
  return (match?.[1] as Language) ?? "en";
}

export function setUiLanguage(lang: Language): void {
  if (typeof document === "undefined") return;
  document.cookie = `${UI_LANG_COOKIE}=${lang}; path=/; max-age=31536000; SameSite=Lax`;
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "he" ? "rtl" : "ltr";
}

/** Inlined into <head> so lang/dir are correct before first paint — no flash. */
export const UI_LANG_INIT_SCRIPT = `
(function () {
  var m = document.cookie.match(/${UI_LANG_COOKIE}=(en|he)/);
  var lang = m ? m[1] : "en";
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "he" ? "rtl" : "ltr";
})();
`;
