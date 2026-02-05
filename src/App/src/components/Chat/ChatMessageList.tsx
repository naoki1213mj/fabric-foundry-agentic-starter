import { Body1, Subtitle2 } from "@fluentui/react-components";
import React from "react";
import { useTranslation } from "react-i18next";
import type { ChatMessage, ToolEvent } from "../../types/AppTypes";
import ChatMessageComponent from "../ChatMessage/ChatMessage";
import { ReasoningIndicator } from "../ReasoningIndicator";
import { MessageSkeleton, ThinkingSkeleton } from "../SkeletonLoader";
import { SuggestedQuestions } from "../SuggestedQuestions/SuggestedQuestions";
import { ToolStatusIndicator } from "../ToolStatusIndicator";

interface ChatMessageListProps {
  messages: ChatMessage[];
  isFetchingMessages: boolean;
  hasMessages: boolean;
  totalMessagesCount: number;
  searchTerm: string;
  generatingResponse: boolean;
  isStreamingInProgress: boolean;
  isChartLoading: boolean;
  toolEvents: ToolEvent[];
  reasoningContent: string;  // Concatenated reasoning text (streaming delta)
  parseCitationFromMessage: (citations: any) => any[];
  chatMessageStreamEndRef: React.RefObject<HTMLDivElement>;
  containerRef?: React.RefObject<HTMLDivElement>;
  onScroll?: () => void;
  onSendMessage?: (message: string) => void;
  onEditUserMessage?: (content: string) => void;
  onResendUserMessage?: (content: string) => void;
  disabled?: boolean;
}

/**
 * Chat message list component
 * Displays messages, loading states, and tool status
 */
export const ChatMessageList: React.FC<ChatMessageListProps> = ({
  messages,
  isFetchingMessages,
  hasMessages,
  totalMessagesCount,
  searchTerm,
  generatingResponse,
  isStreamingInProgress,
  isChartLoading,
  toolEvents,
  reasoningContent,
  parseCitationFromMessage,
  chatMessageStreamEndRef,
  containerRef,
  onScroll,
  onSendMessage,
  onEditUserMessage,
  onResendUserMessage,
  disabled = false,
}) => {
  const { t } = useTranslation();

  return (
    <div
      className="chat-messages"
      ref={containerRef}
      onScroll={onScroll}
    >
      {/* Loading skeleton while fetching messages */}
      {Boolean(isFetchingMessages) && (
        <div className="loading-messages-skeleton">
          <MessageSkeleton />
          <MessageSkeleton isUser />
          <MessageSkeleton />
        </div>
      )}

      {/* Empty state with suggested questions */}
      {!isFetchingMessages && !hasMessages && (
        <div className="initial-msg">
          <h2>✨</h2>
          <Subtitle2>{t("chat.startChatting")}</Subtitle2>
          <Body1 style={{ textAlign: "center" }}>
            {t("chat.landingText")}
          </Body1>
          {onSendMessage && (
            <SuggestedQuestions
              onSelectQuestion={onSendMessage}
              disabled={disabled}
            />
          )}
        </div>
      )}

      {/* No results state when searching */}
      {!isFetchingMessages && totalMessagesCount > 0 && messages.length === 0 && searchTerm.trim() && (
        <div className="initial-msg">
          <Subtitle2>{t("chat.noSearchResultsTitle")}</Subtitle2>
          <Body1 style={{ textAlign: "center" }}>
            {t("chat.noSearchResultsBody", { query: searchTerm })}
          </Body1>
        </div>
      )}

      {/* Message list */}
      {!isFetchingMessages &&
        messages.map((msg, index) => {
          const isLastAssistantMessage =
            msg.role === "assistant" && index === messages.length - 1;

          return (
            <div key={msg.id || index} className={`chat-message ${msg.role}`}>
              <ChatMessageComponent
                message={msg}
                index={index}
                isLastAssistantMessage={isLastAssistantMessage}
                generatingResponse={generatingResponse}
                parseCitationFromMessage={parseCitationFromMessage}
                onEditUserMessage={onEditUserMessage}
                onResendUserMessage={onResendUserMessage}
              />
            </div>
          );
        })}

      {/* Reasoning indicator - GPT-5 thinking process */}
      {reasoningContent && (
        <div className="reasoning-status-wrapper">
          <ReasoningIndicator
            reasoningContent={reasoningContent}
            isGenerating={generatingResponse}
          />
        </div>
      )}

      {/* Tool status indicator - show during and after generation */}
      {toolEvents.length > 0 && (
        <div className="tool-status-wrapper">
          <ToolStatusIndicator
            toolEvents={toolEvents}
            isGenerating={generatingResponse}
          />
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
