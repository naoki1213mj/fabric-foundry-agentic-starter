import React, { memo, useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import supersub from "remark-supersub";
import { ChartDataResponse, ChatMessage as ChatMessageType } from "../../types/AppTypes";
import ChatChart from "../ChatChart/ChatChart";
import Citations from "../Citations/Citations";

// Copy button component
const CopyButton: React.FC<{ text: string; className?: string }> = ({ text, className = "" }) => {
  const [copied, setCopied] = useState(false);
  const { t } = useTranslation();

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className={`copy-button ${className} ${copied ? "copied" : ""}`}
      title={copied ? t("message.copied") || "コピーしました" : t("message.copy") || "コピー"}
      aria-label={copied ? t("message.copied") || "コピーしました" : t("message.copy") || "コピー"}
    >
      {copied ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
      )}
    </button>
  );
};

interface ChatMessageProps {
  message: ChatMessageType;
  index: number;
  isLastAssistantMessage: boolean;
  generatingResponse: boolean;
  parseCitationFromMessage: (citations: any) => any[];
}

// Helper function to format timestamp
const formatTimestamp = (dateString: string | undefined): string => {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return '';
  }
};

const ChatMessage: React.FC<ChatMessageProps> = memo(({
  message,
  index,
  isLastAssistantMessage,
  generatingResponse,
  parseCitationFromMessage
}) => {
  const { t } = useTranslation();
  const timestamp = formatTimestamp(message.date);

  // Handle user messages
  if (message.role === "user" && typeof message.content === "string") {
    if (message.content === "show in a graph by default") return null;
    return (
      <div className="user-message">
        <div className="message-header">
          <CopyButton text={message.content} className="user-copy-button" />
        </div>
        <span>{message.content}</span>
        {timestamp && <div className="message-timestamp">{timestamp}</div>}
      </div>
    );
  }

  // Handle chart messages - object content
  if (message.role === "assistant" && typeof message.content === "object" && message.content !== null) {
    if (("type" in message.content || "chartType" in message.content) && "data" in message.content) {
      try {
        return (
          <div className="assistant-message chart-message">
            <ChatChart chartContent={message.content as ChartDataResponse} />
            <div className="answerDisclaimerContainer">
              <span className="answerDisclaimer">
                {t("message.aiDisclaimer")}
              </span>
            </div>
            {timestamp && <div className="message-timestamp">{timestamp}</div>}
          </div>
        );
      } catch {
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
    }
  }

  // Handle error messages
  if (message.role === "error" && typeof message.content === "string") {
    return (
      <div className="assistant-message error-message">
        <div className="error-icon">⚠️</div>
        <div className="error-content">
          <p className="error-text">{message.content}</p>
        </div>
        <div className="answerDisclaimerContainer">
          <span className="answerDisclaimer">
            {t("message.aiDisclaimer")}
          </span>
        </div>
        {timestamp && <div className="message-timestamp">{timestamp}</div>}
      </div>
    );
  }

  // Handle assistant messages - string content (text, lists, tables, or stringified charts)
  if (message.role === "assistant" && typeof message.content === "string") {
    const isStreaming = generatingResponse && isLastAssistantMessage;

    // Check if content contains chart JSON pattern
    const chartJsonPattern = /```json|"type"\s*:\s*"(bar|pie|line|doughnut|horizontalBar|radar|polarArea|scatter|bubble)"/i;
    const looksLikeChartJson = chartJsonPattern.test(message.content);

    // Check if chart JSON is complete (has matching closing braces/backticks)
    // During streaming with chart JSON: show available text + "generating chart" indicator
    // Keep showing indicator until streaming is complete to prevent flickering
    if (isStreaming && looksLikeChartJson) {
      // Extract text excluding the chart JSON (complete or incomplete)
      const extractTextExcludingChart = (content: string): string => {
        let textPart = content;

        // Remove ```json ... ``` blocks (complete or incomplete)
        textPart = textPart.replace(/```json[\s\S]*?(```|$)/g, '');

        // Remove raw JSON objects with chart type
        const rawJsonStart = textPart.match(/\{\s*"type"\s*:\s*"(bar|pie|line|doughnut|horizontalBar|radar|polarArea|scatter|bubble)"/i);
        if (rawJsonStart && rawJsonStart.index !== undefined) {
          const beforeJson = textPart.substring(0, rawJsonStart.index);
          const afterJsonStart = textPart.substring(rawJsonStart.index);
          // Find where JSON ends (or end of string if incomplete)
          let braceCount = 0;
          let jsonEndIndex = afterJsonStart.length; // default to end if incomplete
          for (let i = 0; i < afterJsonStart.length; i++) {
            if (afterJsonStart[i] === '{') braceCount++;
            else if (afterJsonStart[i] === '}') {
              braceCount--;
              if (braceCount === 0) {
                jsonEndIndex = i + 1;
                break;
              }
            }
          }
          const afterJson = afterJsonStart.substring(jsonEndIndex);
          textPart = (beforeJson + afterJson).trim();
        }

        // Clean up extra whitespace
        textPart = textPart.replace(/\n{3,}/g, '\n\n').trim();
        return textPart;
      };

      const availableText = extractTextExcludingChart(message.content);
      const containsHTML = availableText ? /<\/?[a-z][\s\S]*>/i.test(availableText) : false;

      return (
        <div className="assistant-message">
          {/* Show text content (before and after chart, excluding JSON) */}
          {availableText && (
            containsHTML ? (
              <div
                dangerouslySetInnerHTML={{ __html: availableText }}
                className="html-content"
              />
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm, supersub]}
                children={availableText}
              />
            )
          )}

          {/* Show "generating chart" indicator */}
          <div className="chart-generating-indicator" style={{ marginTop: availableText ? '16px' : '0' }}>
            <div className="typing-indicator">
              <span className="generating-text">{t("chat.generatingChart")}</span>
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        </div>
      );
    }

    // Extract Chart.js JSON(s) from mixed text/JSON content
    const extractChartsFromText = (content: string): { textPart: string; charts: any[] } => {
      const charts: any[] = [];
      let textPart = content;

      // STEP 1: First try to extract from Markdown code blocks (```json ... ```)
      const codeBlockPattern = /```json\s*([\s\S]*?)```/g;
      let codeBlockMatch;
      const codeBlockPositions: { start: number; end: number; json: any }[] = [];

      while ((codeBlockMatch = codeBlockPattern.exec(content)) !== null) {
        const jsonStr = codeBlockMatch[1].trim();
        try {
          const parsed = JSON.parse(jsonStr);
          if (parsed && parsed.data && parsed.type && parsed.data.datasets) {
            codeBlockPositions.push({
              start: codeBlockMatch.index,
              end: codeBlockMatch.index + codeBlockMatch[0].length,
              json: parsed
            });
          }
        } catch {
          // Invalid JSON in code block, skip
        }
      }

      // If found in code blocks, use those
      if (codeBlockPositions.length > 0) {
        for (let i = codeBlockPositions.length - 1; i >= 0; i--) {
          const pos = codeBlockPositions[i];
          charts.unshift(pos.json);
          textPart = textPart.substring(0, pos.start) + textPart.substring(pos.end);
        }
        textPart = textPart.replace(/\n{3,}/g, '\n\n').trim();
        // Deduplicate charts based on data content
        const uniqueCharts = deduplicateCharts(charts);
        return { textPart, charts: uniqueCharts };
      }

      // STEP 2: Fallback - Find raw JSON using bracket counting
      const chartTypePattern = /\{\s*"type"\s*:\s*"(bar|pie|line|doughnut|horizontalBar|radar|polarArea|scatter|bubble)"/g;
      const jsonPositions: { start: number; end: number; json: any }[] = [];

      let match;
      while ((match = chartTypePattern.exec(content)) !== null) {
        const startIndex = match.index;

        // Find the matching closing brace using bracket counting
        let braceCount = 0;
        let endIndex = -1;

        for (let i = startIndex; i < content.length; i++) {
          if (content[i] === '{') braceCount++;
          else if (content[i] === '}') {
            braceCount--;
            if (braceCount === 0) {
              endIndex = i;
              break;
            }
          }
        }

        if (endIndex !== -1) {
          const jsonStr = content.substring(startIndex, endIndex + 1);
          try {
            const parsed = JSON.parse(jsonStr);
            if (parsed && parsed.data && parsed.type && parsed.data.datasets) {
              jsonPositions.push({ start: startIndex, end: endIndex + 1, json: parsed });
            }
          } catch {
            // Invalid JSON, skip
          }
        }
      }

      // Remove JSON from text (in reverse order to maintain indices)
      for (let i = jsonPositions.length - 1; i >= 0; i--) {
        const pos = jsonPositions[i];
        charts.unshift(pos.json); // Add to beginning to maintain order
        textPart = textPart.substring(0, pos.start) + textPart.substring(pos.end);
      }

      // Clean up extra whitespace and "Chart.js（...）" labels
      textPart = textPart.replace(/Chart\.js（[^）]*）[^\n]*/g, '').trim();
      textPart = textPart.replace(/\n{3,}/g, '\n\n'); // Reduce multiple newlines

      // Deduplicate charts based on data content
      const uniqueCharts = deduplicateCharts(charts);
      return { textPart, charts: uniqueCharts };
    };

    // Helper function to deduplicate charts based on their data
    const deduplicateCharts = (charts: any[]): any[] => {
      const seen = new Set<string>();
      const unique: any[] = [];

      for (const chart of charts) {
        // Create a signature based on chart type and data labels/values
        let signature = '';
        try {
          const type = chart.type || chart.chartType || '';
          const labels = chart.data?.labels?.join(',') || '';
          const firstDataset = chart.data?.datasets?.[0];
          const data = firstDataset?.data?.join(',') || '';
          signature = `${type}|${labels}|${data}`;
        } catch {
          signature = JSON.stringify(chart);
        }

        if (!seen.has(signature)) {
          seen.add(signature);
          unique.push(chart);
        }
      }

      return unique;
    };

    // Try parsing entire content as JSON first (pure JSON case)
    let parsedContent = null;
    try {
      parsedContent = JSON.parse(message.content);
    } catch {
      // Not pure JSON - try to extract chart from mixed content
      parsedContent = null;
    }

    // If parsed successfully and it's a chart object
    if (parsedContent && typeof parsedContent === "object") {
      let chartData = null;

      // SCENARIO 1: Direct chart object {type, data, options}
      if (("type" in parsedContent || "chartType" in parsedContent) && "data" in parsedContent) {
        chartData = parsedContent;
      }
      // SCENARIO 2: Wrapped chart {"answer": {type, data, options}}
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
              <ChatChart chartContent={chartData} />
              <div className="answerDisclaimerContainer">
                <span className="answerDisclaimer">
                  {t("message.aiDisclaimer")}
                </span>
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

    // SCENARIO 3: Mixed text + JSON content (e.g., "説明テキスト... { "type": "bar", ... }")
    const { textPart, charts: extractedCharts } = extractChartsFromText(message.content);

    if (extractedCharts.length > 0) {
      // Render text + multiple charts
      const containsHTML = /<\/?[a-z][\s\S]*>/i.test(textPart);

      return (
        <div className="assistant-message">
          {/* Text content above the charts */}
          {textPart && (
            containsHTML ? (
              <div
                dangerouslySetInnerHTML={{ __html: textPart }}
                className="html-content"
              />
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm, supersub]}
                children={textPart}
              />
            )
          )}

          {/* Render all extracted charts */}
          {extractedCharts.map((chartData, chartIndex) => (
            <div
              key={chartIndex}
              className="chart-section"
              style={{ marginTop: chartIndex === 0 && textPart ? '16px' : '12px' }}
            >
              <ChatChart chartContent={chartData} />
            </div>
          ))}

          {/* Citations */}
          {!generatingResponse && (
            <Citations
              answer={{
                answer: textPart || message.content,
                citations:
                  message.role === "assistant"
                    ? parseCitationFromMessage(message.citations)
                    : [],
              }}
              index={index}
            />
          )}

          <div className="answerDisclaimerContainer">
            <span className="answerDisclaimer">
              {t("message.aiDisclaimer")}
            </span>
          </div>
        </div>
      );
    }

    // Plain text message (most common case)
    const containsHTML = /<\/?[a-z][\s\S]*>/i.test(message.content);

    // Extract plain text for copy (strip HTML tags if present)
    const plainTextForCopy = containsHTML
      ? message.content.replace(/<[^>]*>/g, '')
      : message.content;

    return (
      <div className="assistant-message">
        <div className="message-header">
          <CopyButton text={plainTextForCopy} className="assistant-copy-button" />
        </div>
        {containsHTML ? (
          <div
            dangerouslySetInnerHTML={{ __html: message.content }}
            className="html-content"
          />
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm, supersub]}
            children={message.content}
          />
        )}

        {/* Citation Loader: Show only while citations are fetching */}
        {isLastAssistantMessage && generatingResponse ? (
          <div className="typing-indicator">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </div>
        ) : (
          <Citations
            answer={{
              answer: message.content,
              citations:
                message.role === "assistant"
                  ? parseCitationFromMessage(message.citations)
                  : [],
            }}
            index={index}
          />
        )}

        <div className="answerDisclaimerContainer">
          <span className="answerDisclaimer">
            {t("message.aiDisclaimer")}
          </span>
        </div>
        {timestamp && <div className="message-timestamp">{timestamp}</div>}
      </div>
    );
  }

  // Fallback for unexpected content types
  return null;
});

ChatMessage.displayName = 'ChatMessage';

export default ChatMessage;
