import { Body1, Subtitle2 } from "@fluentui/react-components";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { AutoSizer } from "react-virtualized-auto-sizer";
import {
    List,
    useDynamicRowHeight,
    type ListImperativeAPI,
    type RowComponentProps,
} from "react-window";
import type { ChatMessage, Citation, ToolEvent } from "../../types/AppTypes";
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
  conversationId?: string | null;
  isHistoryPanelOpen?: boolean;
  generatingResponse: boolean;
  isStreamingInProgress: boolean;
  isChartLoading: boolean;
  toolEvents: ToolEvent[];
  reasoningContent: string;  // Concatenated reasoning text (streaming delta)
  parseCitationFromMessage: (citations: string | Citation[] | undefined) => Citation[];
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
  parseCitationFromMessage: (citations: string | Citation[] | undefined) => Citation[];
  onEditUserMessage?: (content: string) => void;
  onResendUserMessage?: (content: string) => void;
  reasoningContent: string;
  toolEvents: ToolEvent[];
  chatMessageStreamEndRef: React.RefObject<HTMLDivElement>;
  isReasoningExpanded: boolean;
  onReasoningToggle: (expanded: boolean) => void;
  isToolExpanded: boolean;
  onToolToggle: (expanded: boolean) => void;
  totalItemCount: number;
};

const ROW_PADDING_X = 24; // horizontal padding for each row (replaces List-level padding)

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
    chatMessageStreamEndRef,
    totalItemCount,
  } = rowProps;

  const item = items[index];
  if (!item) return null;

  // Add top padding to first row, bottom padding to last row (replaces List container padding)
  const isFirst = index === 0;
  const isLast = index === totalItemCount - 1;
  const rowStyle: React.CSSProperties = {
    ...style,
    width: "100%",
    boxSizing: "border-box" as const,
    paddingLeft: ROW_PADDING_X,
    paddingRight: ROW_PADDING_X,
    ...(isFirst ? { paddingTop: ROW_PADDING_X } : {}),
    ...(isLast ? { paddingBottom: ROW_PADDING_X } : {}),
  };

  if (item.type === "message") {
    const isLastAssistantMessage = item.messageIndex === lastAssistantIndex;
    const isStreaming = isLastAssistantMessage && generatingResponse;

    return (
      <div style={rowStyle} {...ariaAttributes}>
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
    );
  }

  return (
    <div style={rowStyle} {...ariaAttributes}>
      {item.type === "thinking" && (
        <ThinkingSkeleton />
      )}

      {item.type === "anchor" && (
        <div style={{ height: 1 }}>
          <div data-testid="streamendref-id" ref={chatMessageStreamEndRef} />
        </div>
      )}
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
  conversationId,
  isHistoryPanelOpen = false,
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
  const rowHeightKey = useMemo(() => {
    const firstId = messages[0]?.id ?? "none";
    const lastId = messages[messages.length - 1]?.id ?? "none";
    return `${conversationId ?? "new"}:${messages.length}:${firstId}:${lastId}:${isHistoryPanelOpen ? "panel" : "full"}`;
  }, [conversationId, messages, isHistoryPanelOpen]);
  const dynamicRowHeight = useDynamicRowHeight({ defaultRowHeight: 120, key: rowHeightKey });

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

  // 履歴パネル開閉後、AutoSizer再マウント完了後にスクロール位置を復元
  useEffect(() => {
    // AutoSizer key変更による再マウント後、少し遅延させてスクロール
    const timer = setTimeout(() => {
      if (listApiRef.current?.scrollToRow && messages.length > 0) {
        const lastIdx = virtualItems.length - 1;
        listApiRef.current.scrollToRow({ index: Math.max(0, lastIdx), align: "end", behavior: "auto" });
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [isHistoryPanelOpen]); // eslint-disable-line react-hooks/exhaustive-deps

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
    chatMessageStreamEndRef,
    isReasoningExpanded,
    onReasoningToggle: setIsReasoningExpanded,
    isToolExpanded,
    onToolToggle: setIsToolExpanded,
    totalItemCount: virtualItems.length,
  }), [virtualItems, lastAssistantIndex, generatingResponse, parseCitationFromMessage, onEditUserMessage, onResendUserMessage, reasoningContent, toolEvents, chatMessageStreamEndRef, isReasoningExpanded, isToolExpanded]);

  if (!hasMessages) {
    return (
      <div
        className="chat-messages"
        ref={containerRef}
        onScroll={onScroll}
        style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "var(--spacing-lg, 24px)" }}
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
        style={{ padding: "var(--spacing-lg, 24px)" }}
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
    <div
      style={{
        flex: 1,
        minHeight: 0,
        width: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* 仮想化されたメッセージリスト */}
      <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
        <AutoSizer
          key={`autosizer-${isHistoryPanelOpen ? "panel" : "full"}`}
          renderProp={({ height, width }) => {
            if (!height || !width) return null;
            return (
              <List
                key={`message-list-${conversationId ?? "new"}`}
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
              {generatingResponse ? t("chat.processing") : t("chat.processingDetails")}
              {reasoningContent && ` (${t("chat.reasoning")})`}
              {toolEvents.length > 0 && ` (${t("chat.toolCount", { count: new Set(toolEvents.map(e => e.tool)).size })})`}
            </span>
          </button>

          {/* 折りたたみコンテンツ */}
          {!isFooterCollapsed && (
            <div style={{ maxHeight: isReasoningExpanded || isToolExpanded ? "25vh" : "auto", overflowY: "auto", padding: "0 16px 8px" }}>
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
