import React, { memo } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import supersub from "remark-supersub";
import { ChartDataResponse, ChatMessage as ChatMessageType } from "../../types/AppTypes";
import ChatChart from "../ChatChart/ChatChart";
import Citations from "../Citations/Citations";

interface ChatMessageProps {
  message: ChatMessageType;
  index: number;
  isLastAssistantMessage: boolean;
  generatingResponse: boolean;
  parseCitationFromMessage: (citations: any) => any[];
}

const ChatMessage: React.FC<ChatMessageProps> = memo(({
  message,
  index,
  isLastAssistantMessage,
  generatingResponse,
  parseCitationFromMessage
}) => {
  const { t } = useTranslation();
  // Handle user messages
  if (message.role === "user" && typeof message.content === "string") {
    if (message.content === "show in a graph by default") return null;
    return (
      <div className="user-message">
        <span>{message.content}</span>
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

  // Handle error messages
  if (message.role === "error" && typeof message.content === "string") {
    return (
      <div className="assistant-message error-message">
        <p>{message.content}</p>
        <div className="answerDisclaimerContainer">
          <span className="answerDisclaimer">
            {t("message.aiDisclaimer")}
          </span>
        </div>
      </div>
    );
  }

  // Handle assistant messages - string content (text, lists, tables, or stringified charts)
  if (message.role === "assistant" && typeof message.content === "string") {
    // Extract Chart.js JSON from mixed text/JSON content
    const extractChartFromText = (content: string): { textPart: string; chartData: any | null } => {
      // Pattern to match Chart.js JSON object with type field
      // Matches: { "type": "bar", "data": {...}, "options": {...} }
      const chartJsonPattern = /\{\s*"type"\s*:\s*"(bar|pie|line|doughnut|horizontalBar|radar|polarArea|scatter|bubble)"[\s\S]*?"data"\s*:\s*\{[\s\S]*?"datasets"\s*:\s*\[[\s\S]*?\]\s*\}[\s\S]*?\}/;

      const match = content.match(chartJsonPattern);
      if (match) {
        const jsonStr = match[0];
        const textPart = content.replace(jsonStr, '').trim();
        try {
          const parsed = JSON.parse(jsonStr);
          if (parsed && typeof parsed === 'object' && 'data' in parsed && 'type' in parsed) {
            return { textPart, chartData: parsed };
          }
        } catch {
          // JSON parse failed, return original content
        }
      }
      return { textPart: content, chartData: null };
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
    const { textPart, chartData: extractedChart } = extractChartFromText(message.content);

    if (extractedChart) {
      // Render both text and chart
      const containsHTML = /<\/?[a-z][\s\S]*>/i.test(textPart);

      return (
        <div className="assistant-message">
          {/* Text content above the chart */}
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

          {/* Chart below the text */}
          <div className="chart-section" style={{ marginTop: textPart ? '16px' : '0' }}>
            <ChatChart chartContent={extractedChart} />
          </div>

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

    return (
      <div className="assistant-message">
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
      </div>
    );
  }

  // Fallback for unexpected content types
  return null;
});

ChatMessage.displayName = 'ChatMessage';

export default ChatMessage;
