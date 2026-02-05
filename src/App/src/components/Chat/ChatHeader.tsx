import { Button, Subtitle2 } from "@fluentui/react-components";
import React from "react";
import { useTranslation } from "react-i18next";

interface ChatHeaderProps {
  onToggleHistory: () => void;
  isHistoryVisible: boolean;
}

/**
 * Chat header component with title and history toggle button
 */
export const ChatHeader: React.FC<ChatHeaderProps> = ({
  onToggleHistory,
  isHistoryVisible,
}) => {
  const { t } = useTranslation();

  return (
    <div className="chat-header">
      <Subtitle2>{t("chat.title")}</Subtitle2>
      <span>
        <Button
          appearance="outline"
          onClick={onToggleHistory}
          className="hide-chat-history"
        >
          {isHistoryVisible ? t("chat.hideHistory") : t("chat.showHistory")}
        </Button>
      </span>
    </div>
  );
};

export default ChatHeader;
