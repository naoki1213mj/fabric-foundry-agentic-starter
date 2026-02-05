import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
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
    type ReasoningEffort,
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
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);
  const abortFuncs = useRef([] as AbortController[]);
  const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

  // Memoized computed values
  const currentConversationId = useMemo(() =>
    selectedConversationId || generatedConversationId,
    [selectedConversationId, generatedConversationId]
  );

  const hasMessages = useMemo(() => messages.length > 0, [messages.length]);

  const isInputDisabled = useMemo(() =>
    generatingResponse,
    [generatingResponse]
  );

  const isSendDisabled = useMemo(() =>
    generatingResponse || !userMessage.trim(),
    [generatingResponse, userMessage]
  );

  // Scroll helpers
  const scrollChatToBottom = useCallback(() => {
    if (chatMessageStreamEnd.current) {
      setTimeout(() => {
        chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const throttledScrollChatToBottom = useMemo(
    () => throttle(() => {
      if (chatMessageStreamEnd.current) {
        chatMessageStreamEnd.current.scrollIntoView({ behavior: "auto" });
      }
    }, 500),
    []
  );

  // Tool events handler
  const handleToolEvents = useCallback((events: ToolEvent[]) => {
    if (events.length === 0) {
      setToolEvents([]);
    } else {
      setToolEvents((prev) => [...prev, ...events]);
    }
  }, []);

  // Use the custom API hook
  const { sendChatMessage, abortCurrentRequest } = useChatAPI({
    agentMode,
    reasoningEffort,
    onToolEvents: handleToolEvents,
    onChartLoadingChange: setIsChartLoading,
    scrollChatToBottom,
    throttledScrollChatToBottom,
  });

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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (generatingResponse || isStreamingInProgress) {
      const chatAPISignal = abortFuncs.current.shift();
      if (chatAPISignal) {
        chatAPISignal.abort(
          "Chat Aborted due to switch to other conversation while generating"
        );
      }
    }
  }, [selectedConversationId]);

  useEffect(() => {
    if (
      !isFetchingConvMessages &&
      chatMessageStreamEnd.current
    ) {
      setTimeout(() => {
        chatMessageStreamEnd.current?.scrollIntoView({ behavior: "auto" });
      }, 100);
    }
  }, [isFetchingConvMessages]);

  useEffect(() => {
    scrollChatToBottom();
  }, [generatingResponse, scrollChatToBottom]);

  const setUserMessage = useCallback((value: string) => {
    dispatch(setUserMessageAction(value));
  }, [dispatch]);

  const onNewConversation = useCallback(() => {
    dispatch(startNewConversation());
    dispatch(clearChat());
    dispatch(clearCitation());
    setToolEvents([]);  // Clear tool events when starting new conversation
  }, [dispatch]);

  // Event handlers
  // Keyboard shortcuts: Enter=send, Ctrl+Enter=send, Ctrl+K=new chat, Esc=stop
  // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // eslint-disable-next-line react-hooks/exhaustive-deps
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
      />
      <ChatMessageList
        messages={messages}
        isFetchingMessages={isFetchingConvMessages}
        hasMessages={hasMessages}
        generatingResponse={generatingResponse}
        isStreamingInProgress={isStreamingInProgress}
        isChartLoading={isChartLoading}
        toolEvents={toolEvents}
        parseCitationFromMessage={parseCitationFromMessage}
        chatMessageStreamEndRef={chatMessageStreamEnd}
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
      />
    </div>
  );
};

export default Chat;
