import React, { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { CopyButton } from './CopyButton';
import { formatTimestamp } from './messageUtils';

export interface ErrorMessageProps {
  content: string;
  timestamp?: string;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = memo(({ content, timestamp }) => {
  const { t } = useTranslation();

  return (
    <div className="assistant-message error-message" role="alert">
      <div className="error-icon">⚠️</div>
      <div className="error-content">
        <p className="error-text">{content}</p>
      </div>
      <CopyButton text={content} className="assistant-copy-button" />
      <div className="answerDisclaimerContainer">
        <span className="answerDisclaimer">
          {t('message.aiDisclaimer')}
        </span>
      </div>
      {timestamp && <div className="message-timestamp">{formatTimestamp(timestamp)}</div>}
    </div>
  );
});

ErrorMessage.displayName = 'ErrorMessage';
