import React, { memo } from 'react';
import { CopyButton } from './CopyButton';
import { formatTimestamp } from './messageUtils';

export interface UserMessageProps {
  content: string;
  timestamp?: string;
}

export const UserMessage: React.FC<UserMessageProps> = memo(({ content, timestamp }) => {
  return (
    <div className="user-message">
      <div className="message-header">
        <CopyButton text={content} className="user-copy-button" />
      </div>
      <span>{content}</span>
      {timestamp && <div className="message-timestamp">{formatTimestamp(timestamp)}</div>}
    </div>
  );
});

UserMessage.displayName = 'UserMessage';
