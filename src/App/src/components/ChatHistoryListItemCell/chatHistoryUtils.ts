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
 * Format timestamp for display
 * - Today: Show time only (e.g., "14:30")
 * - Other days: Show date and time (e.g., "1月 15日 14:30")
 */
export const formatTimestamp = (dateStr?: string): string => {
  if (!dateStr) return "";

  const date = new Date(dateStr);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  if (isToday) {
    return date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
  }

  return (
    date.toLocaleDateString("ja-JP", { month: "short", day: "numeric" }) +
    " " +
    date.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })
  );
};
