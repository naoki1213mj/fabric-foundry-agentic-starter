import React, { Suspense, lazy, memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import supersub from 'remark-supersub';
import { ChartDataResponse, ChatMessage as ChatMessageType } from '../../types/AppTypes';
import Citations from '../Citations/Citations';
import { ChartLoadingSkeleton, StreamingChartIndicator } from './ChartMessage';
import { CopyButton } from './CopyButton';
import { MessageReactions } from './MessageReactions';
import {
    containsHtml,
    extractChartsFromText,
    extractTextExcludingChart,
    formatTimestamp,
    looksLikeChartJson,
    stripHtmlTags
} from './messageUtils';

// Lazy load ChatChart component (includes heavy Chart.js library)
const ChatChart = lazy(() => import('../ChatChart/ChatChart'));

export interface AssistantMessageProps {
  message: ChatMessageType;
  index: number;
  isLastAssistantMessage: boolean;
  generatingResponse: boolean;
  parseCitationFromMessage: (citations: any) => any[];
}

export const AssistantMessage: React.FC<AssistantMessageProps> = memo(({
  message,
  index,
  isLastAssistantMessage,
  generatingResponse,
  parseCitationFromMessage
}) => {
  const { t } = useTranslation();
  const timestamp = formatTimestamp(message.date);
  const content = message.content as string;

  // Cache remarkPlugins array to prevent re-creation on every render
  const remarkPlugins = useMemo(() => [remarkGfm, supersub], []);

  const isStreaming = generatingResponse && isLastAssistantMessage;
  const hasChartJson = looksLikeChartJson(content);

  // During streaming with chart JSON: show available text + "generating chart" indicator
  if (isStreaming && hasChartJson) {
    const availableText = extractTextExcludingChart(content);
    const hasHTML = availableText ? containsHtml(availableText) : false;
    const plainTextForCopy = availableText ? (hasHTML ? stripHtmlTags(availableText) : availableText) : '';

    return (
      <div className="assistant-message">
        {plainTextForCopy && (
          <div className="message-header">
            <CopyButton text={plainTextForCopy} className="assistant-copy-button" />
          </div>
        )}

        {availableText && (
          hasHTML ? (
            <div dangerouslySetInnerHTML={{ __html: availableText }} className="html-content" />
          ) : (
            <ReactMarkdown remarkPlugins={remarkPlugins} children={availableText} />
          )
        )}

        <StreamingChartIndicator textContent={availableText} containsHTML={hasHTML} />
      </div>
    );
  }

  // Try parsing entire content as JSON first (pure JSON case)
  let parsedContent = null;
  try {
    parsedContent = JSON.parse(content);
  } catch {
    parsedContent = null;
  }

  // If parsed successfully and it's a chart object
  if (parsedContent && typeof parsedContent === "object") {
    let chartData = null;

    // Direct chart object {type, data, options}
    if (("type" in parsedContent || "chartType" in parsedContent) && "data" in parsedContent) {
      chartData = parsedContent;
    }
    // Wrapped chart {"answer": {type, data, options}}
    else if ("answer" in parsedContent) {
      const answer = parsedContent.answer;
      if (answer && typeof answer === "object" && ("type" in answer || "chartType" in answer) && "data" in answer) {
        chartData = answer;
      }
    }

    // Render chart if valid chartData was found
    if (chartData && ("type" in chartData || "chartType" in chartData) && "data" in chartData) {
      try {
        return (
          <div className="assistant-message chart-message">
            <Suspense fallback={<ChartLoadingSkeleton />}>
              <ChatChart chartContent={chartData as ChartDataResponse} />
            </Suspense>
            <div className="answerDisclaimerContainer">
              <span className="answerDisclaimer">{t("message.aiDisclaimer")}</span>
            </div>
          </div>
        );
      } catch {
        return (
          <div className="assistant-message error-message">
            ⚠️ {t("error.chartDisplay")}
          </div>
        );
      }
    }
  }

  // Mixed text + JSON content (e.g., "説明テキスト... { "type": "bar", ... }")
  const { textPart, charts: extractedCharts } = extractChartsFromText(content);

  if (extractedCharts.length > 0) {
    const hasHTML = containsHtml(textPart);
    const plainTextForCopy = textPart ? (hasHTML ? stripHtmlTags(textPart) : textPart) : '';

    return (
      <div className="assistant-message">
        {plainTextForCopy && (
          <div className="message-header">
            <CopyButton text={plainTextForCopy} className="assistant-copy-button" />
          </div>
        )}

        {textPart && (
          hasHTML ? (
            <div dangerouslySetInnerHTML={{ __html: textPart }} className="html-content" />
          ) : (
            <ReactMarkdown remarkPlugins={remarkPlugins} children={textPart} />
          )
        )}

        {extractedCharts.map((chartData, chartIndex) => (
          <div
            key={chartIndex}
            className="chart-section"
            style={{ marginTop: chartIndex === 0 && textPart ? '16px' : '12px' }}
          >
            <Suspense fallback={<ChartLoadingSkeleton />}>
              <ChatChart chartContent={chartData} />
            </Suspense>
          </div>
        ))}

        {!generatingResponse && (
          <Citations
            answer={{
              answer: textPart || content,
              citations: message.role === "assistant" ? parseCitationFromMessage(message.citations) : [],
            }}
            index={index}
          />
        )}

        <div className="answerDisclaimerContainer">
          <span className="answerDisclaimer">{t("message.aiDisclaimer")}</span>
        </div>
      </div>
    );
  }

  // Plain text message (most common case)
  const hasHTML = containsHtml(content);
  const plainTextForCopy = hasHTML ? stripHtmlTags(content) : content;

  return (
    <div className="assistant-message">
      <div className="message-header">
        <CopyButton text={plainTextForCopy} className="assistant-copy-button" />
        <MessageReactions messageId={message.id} />
      </div>

      {hasHTML ? (
        <div dangerouslySetInnerHTML={{ __html: content }} className="html-content" />
      ) : (
        <ReactMarkdown remarkPlugins={remarkPlugins} children={content} />
      )}

      {isLastAssistantMessage && generatingResponse ? (
        <div className="typing-indicator">
          <span className="dot"></span>
          <span className="dot"></span>
          <span className="dot"></span>
        </div>
      ) : (
        <Citations
          answer={{
            answer: content,
            citations: message.role === "assistant" ? parseCitationFromMessage(message.citations) : [],
          }}
          index={index}
        />
      )}

      <div className="answerDisclaimerContainer">
        <span className="answerDisclaimer">{t("message.aiDisclaimer")}</span>
      </div>

      {timestamp && <div className="message-timestamp">{timestamp}</div>}
    </div>
  );
});

AssistantMessage.displayName = 'AssistantMessage';
