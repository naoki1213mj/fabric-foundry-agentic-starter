import React, { Suspense, lazy, memo } from 'react';
import { useTranslation } from 'react-i18next';
import { ChartDataResponse } from '../../types/AppTypes';
import { formatTimestamp } from './messageUtils';

// Lazy load ChatChart component (includes heavy Chart.js library)
const ChatChart = lazy(() => import('../ChatChart/ChatChart'));

// Loading skeleton for chart - exported for reuse
export const ChartLoadingSkeleton: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div className="chart-loading-skeleton" style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '200px',
      backgroundColor: 'var(--bg-secondary, #f8fafc)',
      borderRadius: '8px',
      padding: '24px',
      gap: '12px'
    }}>
      <div className="skeleton-chart-icon" style={{
        width: '48px',
        height: '48px',
        borderRadius: '8px',
        background: 'linear-gradient(90deg, var(--bg-tertiary, #e2e8f0) 25%, var(--bg-secondary, #f1f5f9) 50%, var(--bg-tertiary, #e2e8f0) 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s infinite'
      }} />
      <div style={{
        color: 'var(--text-secondary, #64748b)',
        fontSize: '14px'
      }}>
        {t('chat.loadingChart') || 'チャートを読み込み中...'}
      </div>
      <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
};

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
      <Suspense fallback={<ChartLoadingSkeleton />}>
        <ChatChart chartContent={chartContent} />
      </Suspense>
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
