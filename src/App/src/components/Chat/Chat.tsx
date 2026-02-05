import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ListImperativeAPI } from "react-window";
import {
  setSelectedConversationId,
  startNewConversation,
} from "../../store/appSlice";
import {
  clearChat,
  setUserMessage as setUserMessageAction,
} from "../../store/chatSlice";
import { clearCitation } from "../../store/citationSlice";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  type AgentMode,
  type ModelReasoningEffort,
  type ModelType,
  type ReasoningEffort,
  type ReasoningSummary,
  type ToolEvent
} from "../../types/AppTypes";
import "./Chat.css";
import { ChatHeader } from "./ChatHeader";
import { ChatInput } from "./ChatInput";
import { ChatMessageList } from "./ChatMessageList";
import { throttle } from "./chatUtils";
import { useChatAPI } from "./useChatAPI";

// Last updated: 2025-02-05 - Extracted API logic to useChatAPI hook

type ChatProps = {
  onHandlePanelStates: (name: string) => void;
  panels: Record<string, string>;
  panelShowStates: Record<string, boolean>;
};

const Chat: React.FC<ChatProps> = ({
  onHandlePanelStates,
  panelShowStates,
  panels,
}) => {
  const dispatch = useAppDispatch();
  const { userMessage, generatingResponse, messages, isStreamingInProgress } = useAppSelector((state) => state.chat);
  const selectedConversationId = useAppSelector((state) => state.app.selectedConversationId);
  const generatedConversationId = useAppSelector((state) => state.app.generatedConversationId);
  const { isFetchingConvMessages } = useAppSelector((state) => state.chatHistory);
  const questionInputRef = useRef<HTMLTextAreaElement>(null);
  const [isChartLoading, setIsChartLoading] = useState(false);
  const [agentMode, setAgentMode] = useState<AgentMode>("multi_tool");
  const [reasoningEffort, setReasoningEffort] = useState<ReasoningEffort>("low");
  const [modelType, setModelType] = useState<ModelType>("gpt-5");
  const [temperature, setTemperature] = useState<number>(0.7);
  const [modelReasoningEffort, setModelReasoningEffort] = useState<ModelReasoningEffort>("medium");
  const [reasoningSummary, setReasoningSummary] = useState<ReasoningSummary>("auto");
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const [reasoningContent, setReasoningContent] = useState<string>("");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const abortFuncs = useRef([] as AbortController[]);
  const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);
  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
  const autoScrollEnabledRef = useRef(true);
  const listApiRef = useRef<ListImperativeAPI | null>(null);

  // Memoized computed values
  const currentConversationId = useMemo(() =>
    selectedConversationId || generatedConversationId,
    [selectedConversationId, generatedConversationId]
  );

  const hasMessages = useMemo(() => messages.length > 0, [messages.length]);

  const filteredMessages = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return messages;

    return messages.filter((msg) => {
      if (typeof msg.content === "string") {
        return msg.content.toLowerCase().includes(term);
      }
      return false;
    });
  }, [messages, searchTerm]);

  const isInputDisabled = useMemo(() =>
    generatingResponse,
    [generatingResponse]
  );

  const isSendDisabled = useMemo(() =>
    generatingResponse || !userMessage.trim(),
    [generatingResponse, userMessage]
  );

  const scrollTargetIndex = useMemo(() => {
    // virtualItems: messages + thinking (conditional) + anchor
    // reasoning/tool は仮想化リストの外なのでカウントしない
    let count = messages.length;
    if ((generatingResponse && !isStreamingInProgress && !isChartLoading) || (isChartLoading && !isStreamingInProgress)) {
      count += 1; // thinking skeleton
    }
    count += 1; // anchor row
    return Math.max(0, count - 1);
  }, [messages.length, generatingResponse, isStreamingInProgress, isChartLoading]);

  // Scroll helpers - respect user scroll position
  const scrollChatToBottom = useCallback(() => {
    if (!autoScrollEnabled) return;

    if (listApiRef.current?.scrollToRow) {
      listApiRef.current.scrollToRow({ index: scrollTargetIndex, align: "end", behavior: "smooth" });
      return;
    }

    if (chatMessageStreamEnd.current) {
      setTimeout(() => {
        chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  }, [autoScrollEnabled, scrollTargetIndex]);

  const throttledScrollChatToBottom = useMemo(
    () => throttle(() => {
      if (chatMessageStreamEnd.current && autoScrollEnabled) {
        chatMessageStreamEnd.current.scrollIntoView({ behavior: "auto" });
      }
    }, 500),
    [autoScrollEnabled]
  );

  // Handle user scroll - disable auto-scroll when user scrolls up
  const handleScroll = useCallback(() => {
    // react-window の List 要素からスクロール位置を取得
    const element = listApiRef.current?.element ?? chatContainerRef.current;
    if (!element) return;
    const { scrollTop, scrollHeight, clientHeight } = element;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100; // 100px threshold
    if (autoScrollEnabledRef.current !== isAtBottom) {
      autoScrollEnabledRef.current = isAtBottom;
      setAutoScrollEnabled(isAtBottom);
    }
  }, []);

  // Re-enable auto-scroll when new message is sent
  const enableAutoScroll = useCallback(() => {
    autoScrollEnabledRef.current = true;
    setAutoScrollEnabled(true);
  }, []);

  // Tool events handler
  const handleToolEvents = useCallback((events: ToolEvent[]) => {
    if (events.length === 0) {
      setToolEvents([]);
    } else {
      setToolEvents((prev) => [...prev, ...events]);
    }
  }, []);

  // Reasoning content handler (GPT-5 thinking) - REPLACE with cumulative text from backend
  // Backend accumulates delta text and sends full cumulative text with throttling
  // We just replace state directly - no need for frontend throttle since backend handles it
  const handleReasoningContent = useCallback((content: string) => {
    setReasoningContent(content);  // Replace with accumulated text from backend
  }, []);

  // Use the custom API hook
  const { sendChatMessage: sendChatMessageRaw, abortCurrentRequest } = useChatAPI({
    agentMode,
    reasoningEffort,
    modelType,
    temperature,
    modelReasoningEffort,
    reasoningSummary,
    onToolEvents: handleToolEvents,
    onReasoningContent: handleReasoningContent,
    onChartLoadingChange: setIsChartLoading,
    scrollChatToBottom,
    throttledScrollChatToBottom,
  });

  // Wrap sendChatMessage to clear reasoning content on new query
  const sendChatMessage = useCallback((question: string, conversationId: string) => {
    setReasoningContent("");  // Clear previous reasoning content
    enableAutoScroll();  // Re-enable auto-scroll when sending new message
    return sendChatMessageRaw(question, conversationId);
  }, [sendChatMessageRaw, enableAutoScroll]);

  // Citation parser - handles both legacy and new formats
  const parseCitationFromMessage = useCallback((citations: any) => {
    if (!citations) return [];

    try {
      // If citations is already an array, use it directly
      if (Array.isArray(citations)) {
        return citations.filter((c: any) => c?.url?.trim() || c?.title?.trim());
      }

      // If citations is a JSON string, parse it
      if (typeof citations === "string") {
        // Try parsing as a JSON array (new format: "[{...}, {...}]")
        const parsed = JSON.parse(citations);
        if (Array.isArray(parsed)) {
          return parsed.filter((c: any) => c?.url?.trim() || c?.title?.trim());
        }

        // Legacy format: "citations": [...] inside a larger object
        if (parsed?.citations && Array.isArray(parsed.citations)) {
          return parsed.citations.filter((c: any) => c?.url?.trim() || c?.title?.trim());
        }
      }
    } catch {
      // Error parsing citations
    }
    return [];
  }, []);

  // Effects
  // Abort ongoing request when conversation changes (intentionally omit generatingResponse/isStreamingInProgress)
  // Track previous conversation ID to detect actual conversation switches vs. ID updates
  const prevConversationIdRef = useRef<string | null>(null);
  const prevGeneratedConversationIdRef = useRef<string | null>(null);

  // Helper to get conversation ID from URL
  const getConversationIdFromUrl = useCallback(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("conversation");
  }, []);

  // Helper to update URL with conversation ID
  const updateUrlWithConversationId = useCallback((conversationId: string | null) => {
    const url = new URL(window.location.href);
    if (conversationId) {
      url.searchParams.set("conversation", conversationId);
    } else {
      url.searchParams.delete("conversation");
    }
    window.history.replaceState({}, "", url.toString());
  }, []);

  // URL persistence - restore conversation from URL on mount
  useEffect(() => {
    const conversationIdFromUrl = getConversationIdFromUrl();
    if (conversationIdFromUrl && !selectedConversationId) {
      dispatch(setSelectedConversationId(conversationIdFromUrl));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- Only run on mount

  // URL persistence - update URL when conversation changes
  useEffect(() => {
    const conversationIdFromUrl = getConversationIdFromUrl();
    const activeConversationId = selectedConversationId || generatedConversationId;

    if (activeConversationId && conversationIdFromUrl !== activeConversationId) {
      updateUrlWithConversationId(activeConversationId);
    } else if (!activeConversationId && conversationIdFromUrl) {
      // Clear URL when no conversation
      updateUrlWithConversationId(null);
    }
  }, [selectedConversationId, generatedConversationId, getConversationIdFromUrl, updateUrlWithConversationId]);

  useEffect(() => {
    // Only clear tool events and reasoning content when switching to a DIFFERENT conversation
    // Not when the ID is updated for the SAME conversation (e.g., after saveToDB assigns an ID)
    const prevSelectedId = prevConversationIdRef.current;
    const prevGeneratedId = prevGeneratedConversationIdRef.current;

    const isIdPromotion =
      prevSelectedId === "" &&
      selectedConversationId !== "" &&
      prevGeneratedId === generatedConversationId;

    const isActualConversationSwitch =
      prevSelectedId !== null &&
      prevSelectedId !== selectedConversationId &&
      !isIdPromotion;

    if (isActualConversationSwitch) {
      // Clear tool events and reasoning content when switching conversations
      setToolEvents([]);
      setReasoningContent("");
    }

    // Update the previous ID references
    prevConversationIdRef.current = selectedConversationId;
    prevGeneratedConversationIdRef.current = generatedConversationId;

    if (isActualConversationSwitch && (generatingResponse || isStreamingInProgress)) {
      const chatAPISignal = abortFuncs.current.shift();
      if (chatAPISignal) {
        chatAPISignal.abort(
          "Chat Aborted due to switch to other conversation while generating"
        );
      }
    }
  }, [selectedConversationId, generatedConversationId, generatingResponse, isStreamingInProgress]);

  // 会話読み込み完了時のみスクロール（ユーザー操作時は発動しない）
  const prevIsFetchingRef = useRef(isFetchingConvMessages);
  useEffect(() => {
    // 読み込み中→完了への遷移時のみスクロール
    const wasLoading = prevIsFetchingRef.current;
    prevIsFetchingRef.current = isFetchingConvMessages;

    if (wasLoading && !isFetchingConvMessages && chatMessageStreamEnd.current) {
      if (autoScrollEnabledRef.current) {
        if (listApiRef.current?.scrollToRow) {
          listApiRef.current.scrollToRow({ index: scrollTargetIndex, align: "end", behavior: "auto" });
        } else {
          setTimeout(() => {
            chatMessageStreamEnd.current?.scrollIntoView({ behavior: "auto" });
          }, 100);
        }
      }
    }
  }, [isFetchingConvMessages, scrollTargetIndex]);

  // 応答生成開始時のみスクロール（生成中・終了時は発動しない）
  const prevGeneratingRef = useRef(generatingResponse);
  useEffect(() => {
    const wasNotGenerating = !prevGeneratingRef.current;
    prevGeneratingRef.current = generatingResponse;

    // 生成開始時（false→true）のみスクロール
    if (wasNotGenerating && generatingResponse && autoScrollEnabledRef.current) {
      scrollChatToBottom();
    }
  }, [generatingResponse, scrollChatToBottom]);

  const setUserMessage = useCallback((value: string) => {
    dispatch(setUserMessageAction(value));
  }, [dispatch]);

  const onNewConversation = useCallback(() => {
    dispatch(startNewConversation());
    dispatch(clearChat());
    dispatch(clearCitation());
    setToolEvents([]);  // Clear tool events when starting new conversation
    setReasoningContent("");  // Clear reasoning content when starting new conversation
    updateUrlWithConversationId(null);
    enableAutoScroll();
  }, [dispatch, updateUrlWithConversationId, enableAutoScroll]);

  const handleEditUserMessage = useCallback((content: string) => {
    if (generatingResponse) return;
    dispatch(setUserMessageAction(content));
    questionInputRef.current?.focus();
  }, [dispatch, generatingResponse]);

  const handleResendUserMessage = useCallback((content: string) => {
    if (generatingResponse || !content.trim()) return;
    sendChatMessage(content, currentConversationId);
  }, [generatingResponse, sendChatMessage, currentConversationId]);

  const downloadTextFile = useCallback((filename: string, content: string) => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }, []);

  const exportChatAsJson = useCallback(() => {
    if (messages.length === 0) return;
    const filename = `conversation-${currentConversationId || "new"}.json`;
    downloadTextFile(filename, JSON.stringify(messages, null, 2));
  }, [messages, currentConversationId, downloadTextFile]);

  const exportChatAsMarkdown = useCallback(() => {
    if (messages.length === 0) return;
    const filename = `conversation-${currentConversationId || "new"}.md`;
    const md = messages.map((msg) => {
      const role = msg.role === "assistant" ? "Assistant" : msg.role === "user" ? "User" : "System";
      const content = typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content, null, 2);
      return `## ${role}\n\n${content}\n`;
    }).join("\n");
    downloadTextFile(filename, md);
  }, [messages, currentConversationId, downloadTextFile]);

  // Event handlers
  // Keyboard shortcuts: Enter=send, Ctrl+Enter=send, Ctrl+K=new chat, Esc=stop
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl+K: New conversation
    if (e.ctrlKey && e.key === "k") {
      e.preventDefault();
      onNewConversation();
      return;
    }
    // Escape: Stop generating
    if (e.key === "Escape" && generatingResponse) {
      e.preventDefault();
      abortCurrentRequest();
      return;
    }
    // Enter or Ctrl+Enter: Send message
    if ((e.key === "Enter" && !e.shiftKey) || (e.ctrlKey && e.key === "Enter")) {
      e.preventDefault();
      if (isInputDisabled) {
        return;
      }
      if (userMessage) {
        sendChatMessage(userMessage, currentConversationId);
      }
      if (questionInputRef?.current) {
        questionInputRef?.current.focus();
      }
    }
  }, [isInputDisabled, userMessage, currentConversationId, sendChatMessage, generatingResponse, abortCurrentRequest, onNewConversation]);

  const onClickSend = useCallback(() => {
    if (isInputDisabled) {
      return;
    }
    if (userMessage) {
      sendChatMessage(userMessage, currentConversationId);
    }
    if (questionInputRef?.current) {
      questionInputRef?.current.focus();
    }
  }, [isInputDisabled, userMessage, currentConversationId, sendChatMessage]);

  const handleToggleHistory = useCallback(() => {
    onHandlePanelStates(panels.CHATHISTORY);
  }, [onHandlePanelStates, panels.CHATHISTORY]);

  return (
    <div className="chat-container">
      <ChatHeader
        onToggleHistory={handleToggleHistory}
        isHistoryVisible={panelShowStates?.[panels.CHATHISTORY]}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        onClearSearch={() => setSearchTerm("")}
        onExportJson={exportChatAsJson}
        onExportMarkdown={exportChatAsMarkdown}
        exportDisabled={messages.length === 0}
      />
      <ChatMessageList
        messages={filteredMessages}
        isFetchingMessages={isFetchingConvMessages}
        hasMessages={hasMessages}
        totalMessagesCount={messages.length}
        searchTerm={searchTerm}
        generatingResponse={generatingResponse}
        isStreamingInProgress={isStreamingInProgress}
        isChartLoading={isChartLoading}
        toolEvents={toolEvents}
        reasoningContent={reasoningContent}
        parseCitationFromMessage={parseCitationFromMessage}
        chatMessageStreamEndRef={chatMessageStreamEnd}
        listApiRef={listApiRef}
        containerRef={chatContainerRef}
        onScroll={handleScroll}
        onEditUserMessage={handleEditUserMessage}
        onResendUserMessage={handleResendUserMessage}
        onSendMessage={(question) => {
          if (!isInputDisabled && question) {
            sendChatMessage(question, currentConversationId);
          }
        }}
        disabled={isInputDisabled}
      />
      <ChatInput
        userMessage={userMessage}
        onUserMessageChange={setUserMessage}
        onSend={onClickSend}
        onKeyDown={handleKeyDown}
        onNewConversation={onNewConversation}
        isInputDisabled={isInputDisabled}
        isSendDisabled={isSendDisabled}
        questionInputRef={questionInputRef}
        agentMode={agentMode}
        onAgentModeChange={setAgentMode}
        reasoningEffort={reasoningEffort}
        onReasoningEffortChange={setReasoningEffort}
        modelType={modelType}
        onModelTypeChange={setModelType}
        temperature={temperature}
        onTemperatureChange={setTemperature}
        modelReasoningEffort={modelReasoningEffort}
        onModelReasoningEffortChange={setModelReasoningEffort}
        reasoningSummary={reasoningSummary}
        onReasoningSummaryChange={setReasoningSummary}
      />
    </div>
  );
};

export default Chat;
