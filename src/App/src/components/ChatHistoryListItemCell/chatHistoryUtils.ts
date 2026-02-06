import { DialogType } from "@fluentui/react";

// Last updated: 2025-02-05 - Extracted utilities from ChatHistoryListItemCell

/**
 * Delete confirmation dialog content props
 */
export const deleteDialogContentProps = {
  type: DialogType.close,
  title: "Are you sure you want to delete this item?",
  closeButtonAriaLabel: "Close",
  subText: "The history of this chat session will be permanently removed.",
};

/**
 * Delete confirmation dialog modal props
 */
export const deleteDialogModalProps = {
  titleAriaId: "labelId",
  subtitleAriaId: "subTextId",
  isBlocking: true,
  styles: { main: { maxWidth: 450 } },
};

/**
 * Truncate title to a maximum length
 */
export const truncateTitle = (title: string | undefined, maxLength = 28): string => {
  if (!title) return "";
  return title.length > maxLength ? `${title.substring(0, maxLength)} ...` : title;
};

/**
 * Format timestamp for display in Japan timezone
 * - Today: Show time only (e.g., "14:30")
 * - Other days: Show date and time (e.g., "1月 15日 14:30")
 */
export const formatTimestamp = (dateStr?: string): string => {
  if (!dateStr) return "";

  // Backend stores UTC via datetime.utcnow().isoformat() without 'Z' suffix,
  // so we need to treat no-TZ strings as UTC
  const dateStrFixed = /Z|[+-]\d{2}:\d{2}$/.test(dateStr) ? dateStr : dateStr + 'Z';
  const date = new Date(dateStrFixed);
  const now = new Date();

  // 日本時間で比較するためのオプション
  const japanOptions: Intl.DateTimeFormatOptions = { timeZone: "Asia/Tokyo" };
  const dateInJapan = date.toLocaleDateString("ja-JP", japanOptions);
  const nowInJapan = now.toLocaleDateString("ja-JP", japanOptions);
  const isToday = dateInJapan === nowInJapan;

  if (isToday) {
    return date.toLocaleTimeString("ja-JP", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Tokyo"
    });
  }

  return (
    date.toLocaleDateString("ja-JP", {
      month: "short",
      day: "numeric",
      timeZone: "Asia/Tokyo"
    }) +
    " " +
    date.toLocaleTimeString("ja-JP", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Tokyo"
    })
  );
};
