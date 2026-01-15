import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { en } from "./locales/en";
import { ja } from "./locales/ja";

// ブラウザの言語設定を取得
const getBrowserLanguage = (): string => {
  const browserLang = navigator.language || (navigator as any).userLanguage;
  // 日本語の場合は 'ja'、それ以外は 'en' をデフォルトに
  return browserLang?.startsWith("ja") ? "ja" : "ja"; // デフォルトを日本語に設定
};

i18n.use(initReactI18next).init({
  resources: {
    ja,
    en,
  },
  lng: getBrowserLanguage(), // ブラウザ言語またはデフォルト
  fallbackLng: "en", // フォールバック言語
  interpolation: {
    escapeValue: false, // React は XSS を自動エスケープ
  },
  react: {
    useSuspense: false, // Suspense を無効化（レガシー互換性）
  },
});

export default i18n;

// 言語切り替え関数
export const changeLanguage = (lng: "ja" | "en") => {
  i18n.changeLanguage(lng);
  localStorage.setItem("preferredLanguage", lng);
};

// 現在の言語を取得
export const getCurrentLanguage = (): string => {
  return i18n.language || "ja";
};
