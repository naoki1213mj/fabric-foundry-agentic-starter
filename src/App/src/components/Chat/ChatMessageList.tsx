import { Body1, Subtitle2 } from "@fluentui/react-components";
import React from "react";
import { useTranslation } from "react-i18next";
import type { ChatMessage, ToolEvent } from "../../types/AppTypes";
import ChatMessageComponent from "../ChatMessage/ChatMessage";
import { MessageSkeleton, ThinkingSkeleton } from "../SkeletonLoader";
import { ToolStatusIndicator } from "../ToolStatusIndicator";

interface ChatMessageListProps {
  messages: ChatMessage[];
  isFetchingMessages: boolean;
  hasMessages: boolean;
  generatingResponse: boolean;
  isStreamingInProgress: boolean;
  isChartLoading: boolean;
  toolEvents: ToolEvent[];
  parseCitationFromMessage: (citations: any) => any[];
  chatMessageStreamEndRef: React.RefObject<HTMLDivElement>;
}

/**
 * Chat message list component
 * Displays messages, loading states, and tool status
 */
export const ChatMessageList: React.FC<ChatMessageListProps> = ({
  messages,
  isFetchingMessages,
  hasMessages,
  generatingResponse,
  isStreamingInProgress,
  isChartLoading,
  toolEvents,
  parseCitationFromMessage,
  chatMessageStreamEndRef,
}) => {
  const { t } = useTranslation();

  return (
    <div className="chat-messages">
      {/* Loading skeleton while fetching messages */}
      {Boolean(isFetchingMessages) && (
        <div className="loading-messages-skeleton">
          <MessageSkeleton />
          <MessageSkeleton isUser />
          <MessageSkeleton />
        </div>
      )}

      {/* Empty state */}
      {!isFetchingMessages && !hasMessages && (
        <div className="initial-msg">
          <h2>✨</h2>
          <Subtitle2>{t("chat.startChatting")}</Subtitle2>
          <Body1 style={{ textAlign: "center" }}>
            {t("chat.landingText")}
          </Body1>
        </div>
      )}

      {/* Message list */}
      {!isFetchingMessages &&
        messages.map((msg, index) => {
          const isLastAssistantMessage = msg.role === "assistant" && index === messages.length - 1;

          return (
            <div key={msg.id || index} className={`chat-message ${msg.role}`}>
              <ChatMessageComponent
                message={msg}
                index={index}
                isLastAssistantMessage={isLastAssistantMessage}
                generatingResponse={generatingResponse}
                parseCitationFromMessage={parseCitationFromMessage}
              />
            </div>
          );
        })}

      {/* Tool status indicator - show only after response completion */}
      {!generatingResponse && toolEvents.length > 0 && (
        <div className="tool-status-wrapper">
          <ToolStatusIndicator toolEvents={toolEvents} />
        </div>
      )}

      {/* Loading indicator for generating response or chart */}
      {((generatingResponse && !isStreamingInProgress && !isChartLoading) || (isChartLoading && !isStreamingInProgress)) && (
        <ThinkingSkeleton />
      )}

      {/* Scroll anchor */}
      <div data-testid="streamendref-id" ref={chatMessageStreamEndRef} />
    </div>
  );
};

export default ChatMessageList;
