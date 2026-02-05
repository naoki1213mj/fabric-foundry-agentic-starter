import React, { memo } from "react";
import { ChartDataResponse, ChatMessage as ChatMessageType } from "../../types/AppTypes";
import { AssistantMessage } from "./AssistantMessage";
import { ChartMessage } from "./ChartMessage";
import { ErrorMessage } from "./ErrorMessage";
import { UserMessage } from "./UserMessage";

interface ChatMessageProps {
  message: ChatMessageType;
  index: number;
  isLastAssistantMessage: boolean;
  generatingResponse: boolean;
  parseCitationFromMessage: (citations: any) => any[];
}

const ChatMessageComponent: React.FC<ChatMessageProps> = memo(({
  message,
  index,
  isLastAssistantMessage,
  generatingResponse,
  parseCitationFromMessage
}) => {
  // Handle user messages
  if (message.role === "user" && typeof message.content === "string") {
    if (message.content === "show in a graph by default") return null;
    return (
      <UserMessage
        content={message.content}
        timestamp={message.date}
      />
    );
  }

  // Handle chart messages - object content
  if (message.role === "assistant" && typeof message.content === "object" && message.content !== null) {
    const content = message.content as Record<string, any>;
    if (("type" in content || "chartType" in content) && "data" in content) {
      try {
        return (
          <ChartMessage
            chartContent={content as ChartDataResponse}
            timestamp={message.date}
          />
        );
      } catch {
        return (
          <ChartMessage
            chartContent={{} as ChartDataResponse}
            errorMode={true}
          />
        );
      }
    }
  }

  // Handle error messages
  if (message.role === "error" && typeof message.content === "string") {
    return (
      <ErrorMessage
        content={message.content}
        timestamp={message.date}
      />
    );
  }

  // Handle assistant messages - string content (text, lists, tables, or stringified charts)
  if (message.role === "assistant" && typeof message.content === "string") {
    return (
      <AssistantMessage
        message={message}
        index={index}
        isLastAssistantMessage={isLastAssistantMessage}
        generatingResponse={generatingResponse}
        parseCitationFromMessage={parseCitationFromMessage}
      />
    );
  }

  // Fallback for unexpected content types
  return null;
});

ChatMessageComponent.displayName = 'ChatMessage';

export default ChatMessageComponent;
