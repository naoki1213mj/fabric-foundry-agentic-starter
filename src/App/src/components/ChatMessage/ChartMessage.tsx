import React, { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { ChartDataResponse } from '../../types/AppTypes';
import ChatChart from '../ChatChart/ChatChart';
import { formatTimestamp } from './messageUtils';

export interface ChartMessageProps {
  chartContent: ChartDataResponse;
  timestamp?: string;
  errorMode?: boolean;
}

export const ChartMessage: React.FC<ChartMessageProps> = memo(({
  chartContent,
  timestamp,
  errorMode = false
}) => {
  const { t } = useTranslation();

  if (errorMode) {
    return (
      <div className="assistant-message error-message">
        <div className="error-icon">⚠️</div>
        <div className="error-content">
          <span className="error-title">{t("error.chartDisplayTitle") || "チャート表示エラー"}</span>
          <span className="error-description">{t("error.chartDisplay")}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="assistant-message chart-message">
      <ChatChart chartContent={chartContent} />
      <div className="answerDisclaimerContainer">
        <span className="answerDisclaimer">
          {t("message.aiDisclaimer")}
        </span>
      </div>
      {timestamp && <div className="message-timestamp">{formatTimestamp(timestamp)}</div>}
    </div>
  );
});

ChartMessage.displayName = 'ChartMessage';

export interface StreamingChartIndicatorProps {
  textContent?: string;
  containsHTML?: boolean;
}

export const StreamingChartIndicator: React.FC<StreamingChartIndicatorProps> = memo(({
  textContent,
  containsHTML = false
}) => {
  const { t } = useTranslation();

  return (
    <div className="chart-generating-indicator" style={{ marginTop: textContent ? '16px' : '0' }}>
      <div className="typing-indicator">
        <span className="generating-text">{t("chat.generatingChart")}</span>
        <span className="dot"></span>
        <span className="dot"></span>
        <span className="dot"></span>
      </div>
    </div>
  );
});

StreamingChartIndicator.displayName = 'StreamingChartIndicator';
