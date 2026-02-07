import React, { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";

interface CopyButtonProps {
  text: string;
  className?: string;
}

/**
 * Copy text to clipboard using multiple fallback methods
 */
const copyToClipboard = async (text: string): Promise<boolean> => {
  // Method 1: Clipboard API (modern browsers, requires HTTPS)
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      /* expected — clipboard API may fail, fall through to fallback */
    }
  }

  // Method 2: execCommand fallback (legacy, works in HTTP)
  try {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    textArea.style.top = "-9999px";
    textArea.style.opacity = "0";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    const successful = document.execCommand("copy");
    document.body.removeChild(textArea);
    return successful;
  } catch {
    return false;
  }
};

/**
 * Reusable copy to clipboard button
 */
export const CopyButton: React.FC<CopyButtonProps> = ({ text, className = "" }) => {
  const [copied, setCopied] = useState(false);
  const { t } = useTranslation();

  const handleCopy = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!text || text.trim() === "") {
      console.warn("CopyButton: No text to copy");
      return;
    }

    const success = await copyToClipboard(text);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } else {
      console.error("Failed to copy text to clipboard");
    }
  }, [text]);

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`copy-button ${className} ${copied ? "copied" : ""}`}
      title={copied ? t("message.copied") || "コピーしました" : t("message.copy") || "コピー"}
      aria-label={copied ? t("message.copied") || "コピーしました" : t("message.copy") || "コピー"}
    >
      {copied ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
      )}
    </button>
  );
};

export default CopyButton;
