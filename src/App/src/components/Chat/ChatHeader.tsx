import { Button, Input, Subtitle2 } from "@fluentui/react-components";
import React from "react";
import { useTranslation } from "react-i18next";

interface ChatHeaderProps {
  onToggleHistory: () => void;
  isHistoryVisible: boolean;
  searchTerm: string;
  onSearchChange: (value: string) => void;
  onClearSearch: () => void;
  onExportJson: () => void;
  onExportMarkdown: () => void;
  exportDisabled: boolean;
}

/**
 * Chat header component with title and history toggle button
 */
export const ChatHeader: React.FC<ChatHeaderProps> = ({
  onToggleHistory,
  isHistoryVisible,
  searchTerm,
  onSearchChange,
  onClearSearch,
  onExportJson,
  onExportMarkdown,
  exportDisabled,
}) => {
  const { t } = useTranslation();

  return (
    <div className="chat-header">
      <Subtitle2>{t("chat.title")}</Subtitle2>
      <div className="chat-header-actions">
        <Input
          className="chat-search-input"
          placeholder={t("chat.searchPlaceholder")}
          aria-label={t("chat.searchPlaceholder")}
          value={searchTerm}
          onChange={(_, data) => onSearchChange(data.value)}
          size="small"
          contentAfter={
            searchTerm ? (
              <Button
                appearance="subtle"
                size="small"
                onClick={onClearSearch}
                className="chat-search-clear"
                aria-label={t("chat.clearSearch")}
              >
                {t("chat.clearSearch")}
              </Button>
            ) : null
          }
        />
        <Button
          appearance="subtle"
          onClick={onExportMarkdown}
          disabled={exportDisabled}
          className="chat-export-button"
          aria-label={t("chat.exportMarkdown")}
        >
          {t("chat.exportMarkdown")}
        </Button>
        <Button
          appearance="subtle"
          onClick={onExportJson}
          disabled={exportDisabled}
          className="chat-export-button"
          aria-label={t("chat.exportJson")}
        >
          {t("chat.exportJson")}
        </Button>
        <Button
          appearance="outline"
          onClick={onToggleHistory}
          className="hide-chat-history"
          aria-label={isHistoryVisible ? t("chat.hideHistory") : t("chat.showHistory")}
          aria-expanded={isHistoryVisible}
        >
          {isHistoryVisible ? t("chat.hideHistory") : t("chat.showHistory")}
        </Button>
      </div>
    </div>
  );
};

export default ChatHeader;
