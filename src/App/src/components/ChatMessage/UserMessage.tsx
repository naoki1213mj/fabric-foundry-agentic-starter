import React, { memo } from 'react';
import { useTranslation } from "react-i18next";
import { CopyButton } from './CopyButton';
import { formatTimestamp } from './messageUtils';

export interface UserMessageProps {
  content: string;
  timestamp?: string;
  onEdit?: (content: string) => void;
  onResend?: (content: string) => void;
}

export const UserMessage: React.FC<UserMessageProps> = memo(({ content, timestamp, onEdit, onResend }) => {
  const { t } = useTranslation();

  return (
    <div className="user-message">
      <div className="message-header">
        <CopyButton text={content} className="user-copy-button" />
        {onEdit && (
          <button
            type="button"
            className="message-action-button"
            onClick={() => onEdit(content)}
            aria-label={t("chat.editMessage")}
          >
            {t("chat.editMessage")}
          </button>
        )}
        {onResend && (
          <button
            type="button"
            className="message-action-button"
            onClick={() => onResend(content)}
            aria-label={t("chat.resendMessage")}
          >
            {t("chat.resendMessage")}
          </button>
        )}
      </div>
      <span>{content}</span>
      {timestamp && <div className="message-timestamp">{formatTimestamp(timestamp)}</div>}
    </div>
  );
});

UserMessage.displayName = 'UserMessage';
