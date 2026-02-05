import { Body1, Subtitle2 } from "@fluentui/react-components";
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { AutoSizer } from "react-virtualized-auto-sizer";
import {
  List,
  useDynamicRowHeight,
  type DynamicRowHeight,
  type ListImperativeAPI,
  type RowComponentProps,
} from "react-window";
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
  containerRef?: React.MutableRefObject<HTMLDivElement | null>;
  listApiRef?: React.MutableRefObject<ListImperativeAPI | null>;
  onScroll?: () => void;
  onSendMessage?: (message: string) => void;
  onEditUserMessage?: (content: string) => void;
  onResendUserMessage?: (content: string) => void;
  disabled?: boolean;
}

type VirtualItem =
  | { type: "message"; message: ChatMessage; messageIndex: number }
  | { type: "reasoning" }
  | { type: "tool" }
  | { type: "thinking" }
  | { type: "anchor" };

type ChatRowProps = {
  items: VirtualItem[];
  lastAssistantIndex: number;
  generatingResponse: boolean;
  parseCitationFromMessage: (citations: any) => any[];
  onEditUserMessage?: (content: string) => void;
  onResendUserMessage?: (content: string) => void;
  reasoningContent: string;
  toolEvents: ToolEvent[];
  dynamicRowHeight: DynamicRowHeight;
  chatMessageStreamEndRef: React.RefObject<HTMLDivElement>;
  isReasoningExpanded: boolean;
  onReasoningToggle: (expanded: boolean) => void;
  isToolExpanded: boolean;
  onToolToggle: (expanded: boolean) => void;
};

const ChatMessageRow = ({
  index,
  style,
  ariaAttributes,
  ...rowProps
}: RowComponentProps<ChatRowProps>): React.ReactElement | null => {
  const {
    items,
    lastAssistantIndex,
    generatingResponse,
    parseCitationFromMessage,
    onEditUserMessage,
    onResendUserMessage,
    reasoningContent,
    toolEvents,
    dynamicRowHeight,
    chatMessageStreamEndRef,
    isReasoningExpanded,
    onReasoningToggle,
    isToolExpanded,
    onToolToggle,
  } = rowProps;

  const item = items[index];
  const rowRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    if (!rowRef.current) return;
    return dynamicRowHeight.observeRowElements([rowRef.current]);
  }, [dynamicRowHeight]);

  if (!item) return null;

  if (item.type === "message") {
    const isLastAssistantMessage = item.messageIndex === lastAssistantIndex;
    const isStreaming = isLastAssistantMessage && generatingResponse;

    return (
      <div style={{ ...style, width: "100%" }} {...ariaAttributes}>
        <div ref={rowRef}>
          <div className={`chat-message ${item.message.role} ${generatingResponse ? "no-animate" : ""}`.trim()}>
            <ChatMessageComponent
              message={item.message}
              index={item.messageIndex}
              isLastAssistantMessage={isLastAssistantMessage}
              generatingResponse={isStreaming}
              parseCitationFromMessage={parseCitationFromMessage}
              onEditUserMessage={onEditUserMessage}
              onResendUserMessage={onResendUserMessage}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ ...style, width: "100%" }} {...ariaAttributes}>
      <div ref={rowRef}>
        {item.type === "thinking" && (
          <ThinkingSkeleton />
        )}

        {item.type === "anchor" && (
          <div style={{ height: 1 }}>
            <div data-testid="streamendref-id" ref={chatMessageStreamEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};

const MemoizedChatMessageRow = React.memo(ChatMessageRow) as (
  props: RowComponentProps<ChatRowProps>
) => React.ReactElement | null;

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
  listApiRef: listApiRefProp,
  onScroll,
  onSendMessage,
  onEditUserMessage,
  onResendUserMessage,
  disabled = false,
}) => {
  const { t } = useTranslation();

  const internalListApiRef = useRef<ListImperativeAPI | null>(null);
  const listApiRef = listApiRefProp ?? internalListApiRef;
  const dynamicRowHeight = useDynamicRowHeight({ defaultRowHeight: 120, key: messages.length });

  const lastAssistantIndex = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "assistant") return i;
    }
    return -1;
  }, [messages]);

  const virtualItems = useMemo<VirtualItem[]>(() => {
    const items: VirtualItem[] = messages.map((message, messageIndex) => ({
      type: "message",
      message,
      messageIndex,
    }));

    // reasoning/tool は仮想化リストの外に配置するため、ここでは追加しない
    if ((generatingResponse && !isStreamingInProgress && !isChartLoading) || (isChartLoading && !isStreamingInProgress)) {
      items.push({ type: "thinking" });
    }
    items.push({ type: "anchor" });

    return items;
  }, [messages, generatingResponse, isStreamingInProgress, isChartLoading]);

  useEffect(() => {
    if (!containerRef) return;
    containerRef.current = listApiRef.current?.element ?? null;
  }, [containerRef, listApiRef, messages.length]);

  // 推論/ツール全体の折りたたみ状態
  const [isFooterCollapsed, setIsFooterCollapsed] = useState(false);
  const [isReasoningExpanded, setIsReasoningExpanded] = useState(false);
  const [isToolExpanded, setIsToolExpanded] = useState(false);

  useEffect(() => {
    if (!reasoningContent) setIsReasoningExpanded(false);
  }, [reasoningContent]);

  useEffect(() => {
    if (toolEvents.length === 0) setIsToolExpanded(false);
  }, [toolEvents.length]);

  const rowProps = useMemo<ChatRowProps>(() => ({
    items: virtualItems,
    lastAssistantIndex,
    generatingResponse,
    parseCitationFromMessage,
    onEditUserMessage,
    onResendUserMessage,
    reasoningContent,
    toolEvents,
    dynamicRowHeight,
    chatMessageStreamEndRef,
    isReasoningExpanded,
    onReasoningToggle: setIsReasoningExpanded,
    isToolExpanded,
    onToolToggle: setIsToolExpanded,
  }), [virtualItems, lastAssistantIndex, generatingResponse, parseCitationFromMessage, onEditUserMessage, onResendUserMessage, reasoningContent, toolEvents, dynamicRowHeight, chatMessageStreamEndRef, isReasoningExpanded, isToolExpanded]);

  if (!hasMessages) {
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
        {!isFetchingMessages && (
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
      </div>
    );
  }

  if (!isFetchingMessages && totalMessagesCount > 0 && messages.length === 0 && searchTerm.trim()) {
    return (
      <div
        className="chat-messages"
        ref={containerRef}
        onScroll={onScroll}
      >
        <div className="initial-msg">
          <Subtitle2>{t("chat.noSearchResultsTitle")}</Subtitle2>
          <Body1 style={{ textAlign: "center" }}>
            {t("chat.noSearchResultsBody", { query: searchTerm })}
          </Body1>
        </div>
      </div>
    );
  }

  // 推論/ツールの高さを考慮した残り高さを計算
  const hasReasoningOrTool = Boolean(reasoningContent) || toolEvents.length > 0;

  return (
    <div style={{ height: "100%", width: "100%", display: "flex", flexDirection: "column" }}>
      {/* 仮想化されたメッセージリスト */}
      <div style={{ flex: 1, minHeight: 0 }}>
        <AutoSizer
          renderProp={({ height, width }) => {
            if (!height || !width) return null;
            return (
              <List
                className="chat-messages"
                style={{ height, width }}
                rowCount={virtualItems.length}
                rowHeight={dynamicRowHeight}
                rowComponent={MemoizedChatMessageRow}
                rowProps={rowProps}
                listRef={listApiRef}
                overscanCount={3}
                onScroll={() => onScroll?.()}
              />
            );
          }}
        />
      </div>

      {/* 推論/ツール表示は仮想化リストの外に配置 - 全体をトグル可能 */}
      {hasReasoningOrTool && (
        <div className="reasoning-tool-footer" style={{ flexShrink: 0 }}>
          {/* 折りたたみヘッダー */}
          <button
            className="footer-collapse-toggle"
            onClick={() => setIsFooterCollapsed(!isFooterCollapsed)}
            aria-expanded={!isFooterCollapsed}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              width: "100%",
              padding: "8px 16px",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: "inherit",
              fontSize: "13px",
              fontWeight: 500,
            }}
          >
            <span style={{ transition: "transform 0.2s", transform: isFooterCollapsed ? "rotate(-90deg)" : "rotate(0)" }}>
              ▼
            </span>
            <span>
              {generatingResponse ? "処理中..." : "処理詳細"}
              {reasoningContent && " (推論)"}
              {toolEvents.length > 0 && ` (ツール: ${new Set(toolEvents.map(e => e.tool)).size}種類)`}
            </span>
          </button>

          {/* 折りたたみコンテンツ */}
          {!isFooterCollapsed && (
            <div style={{ maxHeight: isReasoningExpanded || isToolExpanded ? "40vh" : "auto", overflowY: "auto", padding: "0 16px 8px" }}>
              {reasoningContent && (
                <div className={`reasoning-status-wrapper ${generatingResponse ? "no-animate" : ""}`.trim()}>
                  <ReasoningIndicator
                    reasoningContent={reasoningContent}
                    isGenerating={generatingResponse}
                    isExpanded={isReasoningExpanded}
                    onToggle={setIsReasoningExpanded}
                  />
                </div>
              )}
              {toolEvents.length > 0 && (
                <div className={`tool-status-wrapper ${generatingResponse ? "no-animate" : ""}`.trim()}>
                  <ToolStatusIndicator
                    toolEvents={toolEvents}
                    isGenerating={generatingResponse}
                    isExpanded={isToolExpanded}
                    onToggle={setIsToolExpanded}
                  />
                </div>
              )}
            </div>
          )}
          <div ref={chatMessageStreamEndRef} />
        </div>
      )}
    </div>
  );
};

export default ChatMessageList;
