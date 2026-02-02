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
        return { textPart, charts };
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

      return { textPart, charts };
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
