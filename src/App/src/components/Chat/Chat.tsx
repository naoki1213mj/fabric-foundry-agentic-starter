import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { generateUUIDv4 } from "../../configs/Utils";
import {
  setSelectedConversationId,
  startNewConversation,
} from "../../store/appSlice";
import {
  addNewConversation,
  updateConversation,
} from "../../store/chatHistorySlice";
import {
  addMessages,
  clearChat,
  sendMessage,
  setGeneratingResponse,
  setStreamingFlag,
  setUserMessage as setUserMessageAction,
  updateMessageById,
} from "../../store/chatSlice";
import { clearCitation } from "../../store/citationSlice";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  type AgentMode,
  type ChartDataResponse,
  type ChatMessage,
  type Conversation,
  type ConversationRequest,
  type ParsedChunk,
  type ReasoningEffort,
  type ToolEvent,
  ToolMessageContent,
} from "../../types/AppTypes";
import {
  isMalformedChartJSON,
  parseChartContent,
} from "../../utils/jsonUtils";
import { ChatHeader } from "./ChatHeader";
import { ChatInput } from "./ChatInput";
import { ChatMessageList } from "./ChatMessageList";
import { isChartQuery, parseToolEvents, throttle } from "./chatUtils";
import "./Chat.css";

// Last updated: 2025-02-05 - Refactored into sub-components

const [ASSISTANT, ERROR, USER] = ["assistant", "error", "user"];

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
  const { t } = useTranslation();
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

  // Save to database helper
  const saveToDB = useCallback(async (newMessages: ChatMessage[], convId: string, reqType: string = "Text") => {
    if (!convId || !newMessages.length) {
      return;
    }
    const isNewConversation = reqType !== "graph" ? !selectedConversationId : false;

    try {
      const result = await dispatch(updateConversation({ conversationId: convId, messages: newMessages })).unwrap();

      if (isNewConversation && result?.success) {
        const newConversation: Conversation = {
          id: result?.data?.conversation_id,
          title: result?.data?.title,
          messages: messages,
          date: result?.data?.date,
          updatedAt: result?.data?.date,
        };
        dispatch(addNewConversation(newConversation));
        dispatch(setSelectedConversationId(result?.data?.conversation_id));
      }
    } catch {
      // Error saving data to database
    } finally {
      dispatch(setGeneratingResponse(false));
    }
  }, [selectedConversationId, messages, dispatch]);

  // Citation parser
  const parseCitationFromMessage = useCallback((message: string) => {
    try {
      message = "{" + message;
      const toolMessage = JSON.parse(message as string) as ToolMessageContent;

      if (toolMessage?.citations?.length) {
        return toolMessage.citations.filter(
          (c) => c.url?.trim() || c.title?.trim()
        );
      }
    } catch {
      // Error parsing tool content
    }
    return [];
  }, []);

  // Helper function to create and dispatch a message
  const createAndDispatchMessage = useCallback((role: string, content: string | ChartDataResponse, shouldScroll: boolean = true): ChatMessage => {
    const message: ChatMessage = {
      id: generateUUIDv4(),
      role,
      content,
      date: new Date().toISOString(),
    };

    dispatch(addMessages([message]));

    if (shouldScroll) scrollChatToBottom();

    return message;
  }, [dispatch, scrollChatToBottom]);

  // Helper function to extract chart data from response
  const extractChartData = useCallback((chartResponse: ChartDataResponse | string): ChartDataResponse | string => {
    if (typeof chartResponse === "object" && "answer" in chartResponse) {
      return !chartResponse.answer ||
             (typeof chartResponse.answer === "object" && Object.keys(chartResponse.answer).length === 0)
        ? "Chart can not be generated, please try again."
        : chartResponse.answer;
    }

    if (typeof chartResponse === "string") {
      try {
        const parsed = JSON.parse(chartResponse);
        if (parsed && typeof parsed === "object" && "answer" in parsed) {
          return !parsed.answer ||
                 (typeof parsed.answer === "object" && Object.keys(parsed.answer).length === 0)
            ? "Chart can not be generated, please try again."
            : parsed.answer;
        }
      } catch {
        // Fall through to default
      }
      return "Chart can not be generated, please try again.";
    }

    return chartResponse;
  }, []);

  // Effects
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

  // API request for chart
  const makeApiRequestForChart = async (
    question: string,
    conversationId: string
  ) => {
    if (generatingResponse || !question.trim()) return;

    const newMessage: ChatMessage = {
      id: generateUUIDv4(),
      role: USER,
      content: question,
      date: new Date().toISOString()
    };

    dispatch(setGeneratingResponse(true));
    dispatch(addMessages([newMessage]));
    dispatch(setUserMessageAction(questionInputRef?.current?.value || ""));
    scrollChatToBottom();

    const abortController = new AbortController();
    abortFuncs.current.unshift(abortController);

    const request: ConversationRequest = {
      id: conversationId,
      query: question,
      agentMode: agentMode,
      reasoningEffort: reasoningEffort
    };

    let updatedMessages: ChatMessage[] = [];

    try {
      const result = await dispatch(sendMessage({ request, abortSignal: abortController.signal }));
      if (!sendMessage.fulfilled.match(result)) {
        throw new Error("Failed to send message");
      }
      const response = result.payload;

      if (response?.body) {
        const reader = response.body.getReader();
        let runningText = "";
        let hasError = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = new TextDecoder("utf-8").decode(value);
          try {
            const textObj = JSON.parse(text);
            if (textObj?.object?.data) {
              runningText = text;
            }
            if (textObj?.error) {
              hasError = true;
              runningText = text;
            }
          } catch {
            // Non-JSON chunk, continue
          }
        }

        if (hasError) {
          const errorMsg = JSON.parse(runningText).error;
          const errorMessage = createAndDispatchMessage(ERROR, errorMsg);
          updatedMessages = [newMessage, errorMessage];
        } else if (isChartQuery(question)) {
          try {
            const parsedResponse = JSON.parse(runningText);

            if ((parsedResponse?.object?.type || parsedResponse?.object?.chartType) && parsedResponse?.object?.data) {
              const chartMessage = createAndDispatchMessage(
                ASSISTANT,
                parsedResponse.object as unknown as ChartDataResponse
              );
              updatedMessages = [newMessage, chartMessage];
            } else if (parsedResponse.error || parsedResponse?.object?.message) {
              const errorMsg = parsedResponse.error || parsedResponse.object.message;
              const errorMessage = createAndDispatchMessage(ERROR, errorMsg);
              updatedMessages = [newMessage, errorMessage];
            }
          } catch {
            // Error parsing chart response
          }
        }
      }

      if (updatedMessages.length > 0) {
        saveToDB(updatedMessages, conversationId, "graph");
      }
    } catch (e) {
      if (abortController.signal.aborted) {
        updatedMessages = [newMessage];
        saveToDB(updatedMessages, conversationId, "graph");
      } else if (e instanceof Error) {
        alert(e.message);
      } else {
        alert(t("error.tryAgainLater") + " " + t("error.contactAdmin"));
      }
    } finally {
      dispatch(setGeneratingResponse(false));
      dispatch(setStreamingFlag(false));
      setIsChartLoading(false);
      abortController.abort();
    }
  };

  // Main API request
  const makeApiRequestWithCosmosDB = async (
    question: string,
    conversationId: string
  ) => {
    if (generatingResponse || !question.trim()) return;

    const isChart = isChartQuery(userMessage);
    const isChatReq = isChart ? "graph" : "Text";
    const newMessage: ChatMessage = {
      id: generateUUIDv4(),
      role: USER,
      content: question,
      date: new Date().toISOString(),
    };

    dispatch(setGeneratingResponse(true));
    if (isChart) {
      setIsChartLoading(true);
    }
    setToolEvents([]);

    dispatch(addMessages([newMessage]));
    dispatch(setUserMessageAction(""));
    scrollChatToBottom();

    const abortController = new AbortController();
    abortFuncs.current.unshift(abortController);

    const request: ConversationRequest = {
      id: conversationId,
      query: userMessage,
      agentMode: agentMode,
      reasoningEffort: reasoningEffort
    };

    const streamMessage: ChatMessage = {
      id: generateUUIDv4(),
      date: new Date().toISOString(),
      role: ASSISTANT,
      content: "",
      citations: "",
    };

    let updatedMessages: ChatMessage[] = [];

    try {
      const result = await dispatch(sendMessage({ request, abortSignal: abortController.signal }));
      if (!sendMessage.fulfilled.match(result)) {
        throw new Error("Failed to send message");
      }
      const response = result.payload;

      if (response?.body) {
        let isChartResponseReceived = false;
        const reader = response.body.getReader();
        let runningText = "";
        let hasError = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          let text = new TextDecoder("utf-8").decode(value);

          // Parse and extract tool events from the stream
          const { events: newToolEvents, cleanedText } = parseToolEvents(text);
          if (newToolEvents.length > 0) {
            setToolEvents((prev) => [...prev, ...newToolEvents]);
            text = cleanedText;
          }

          try {
            const textObj = JSON.parse(text);
            if (textObj?.object?.data || textObj?.object?.message) {
              runningText = text;
              isChartResponseReceived = true;
            }
            if (textObj?.error) {
              hasError = true;
              runningText = text;
            }
          } catch {
            // Not JSON, continue processing as stream
          }

          if (!isChartResponseReceived) {
            const objects = text.split("\n").filter((val) => val !== "");

            objects.forEach((textValue) => {
              if (!textValue || textValue === "{}") return;

              try {
                const parsed: ParsedChunk = JSON.parse(textValue);

                if (parsed?.error && !hasError) {
                  hasError = true;
                  runningText = parsed?.error;
                } else if (typeof parsed === "object" && !hasError) {
                  const responseContent = parsed?.choices?.[0]?.messages?.[0]?.content;
                  const responseCitations = parsed?.choices?.[0]?.messages?.[0]?.citations;

                  if (responseContent) {
                    streamMessage.content = responseContent;
                    streamMessage.role = parsed?.choices?.[0]?.messages?.[0]?.role || ASSISTANT;

                    if (responseCitations) {
                      streamMessage.citations = responseCitations;
                    }

                    dispatch(updateMessageById({ ...streamMessage }));
                    throttledScrollChatToBottom();
                    runningText = responseContent;
                  }
                }
              } catch {
                // Skip malformed chunks
              }
            });

            if (hasError) break;
          }
        }

        // Process final response
        if (hasError) {
          const parsedError = JSON.parse(runningText);
          const errorMsg = parsedError.error === "Attempted to access streaming response content, without having called `read()`."
            ? "An error occurred. Please try again later."
            : parsedError.error;

          const errorMessage = createAndDispatchMessage(ERROR, errorMsg);
          updatedMessages = [newMessage, errorMessage];
        } else if (isChartQuery(userMessage)) {
          if (streamMessage.content) {
            updatedMessages = [newMessage, streamMessage];
          } else {
            try {
              const splitRunningText = runningText.split("}{");
              const parsedChartResponse = JSON.parse("{" + splitRunningText[splitRunningText.length - 1]);

              const rawChartContent = parsedChartResponse?.choices[0]?.messages[0]?.content;

              let chartResponse = typeof rawChartContent === "string"
                ? parseChartContent(rawChartContent)
                : rawChartContent || "Chart can not be generated, please try again.";

              chartResponse = extractChartData(chartResponse);

              if ((chartResponse?.type || chartResponse?.chartType) && chartResponse?.data) {
                const chartMessage = createAndDispatchMessage(
                  ASSISTANT,
                  chartResponse as unknown as ChartDataResponse
                );
                updatedMessages = [newMessage, chartMessage];
              } else if (parsedChartResponse?.error || parsedChartResponse?.choices[0]?.messages[0]?.content) {
                let content = parsedChartResponse?.choices[0]?.messages[0]?.content;
                let displayContent = content;

                try {
                  const parsed = typeof content === "string" ? JSON.parse(content) : content;
                  if (parsed && typeof parsed === "object" && "answer" in parsed) {
                    displayContent = parsed.answer;
                  }
                } catch {
                  displayContent = content;
                }

                let errorMsg = parsedChartResponse?.error || displayContent;

                if (isMalformedChartJSON(errorMsg, !!parsedChartResponse?.error)) {
                  errorMsg = "Chart can not be generated, please try again later";
                }

                const errorMessage = createAndDispatchMessage(ERROR, errorMsg);
                updatedMessages = [newMessage, errorMessage];
              }
            } catch {
              // Error parsing chart response
            }
          }
        } else if (!isChartResponseReceived) {
          updatedMessages = [newMessage, streamMessage];
        }
      }

      if (updatedMessages.length > 0 && updatedMessages[updatedMessages.length - 1]?.role !== ERROR) {
        saveToDB(updatedMessages, conversationId, isChatReq);
      }
    } catch (e) {
      if (abortController.signal.aborted) {
        updatedMessages = streamMessage.content
          ? [newMessage, streamMessage]
          : [newMessage];

        saveToDB(updatedMessages, conversationId, "error");
      } else if (e instanceof Error) {
        alert(e.message);
      } else {
        alert(t("error.tryAgainLater") + " " + t("error.contactAdmin"));
      }
    } finally {
      dispatch(setGeneratingResponse(false));
      dispatch(setStreamingFlag(false));
      setIsChartLoading(false);
      abortController.abort();
    }
  };

  // Event handlers
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (isInputDisabled) {
        return;
      }
      if (userMessage) {
        makeApiRequestWithCosmosDB(userMessage, currentConversationId);
      }
      if (questionInputRef?.current) {
        questionInputRef?.current.focus();
      }
    }
  }, [isInputDisabled, userMessage, currentConversationId]);

  const onClickSend = useCallback(() => {
    if (isInputDisabled) {
      return;
    }
    if (userMessage) {
      makeApiRequestWithCosmosDB(userMessage, currentConversationId);
    }
    if (questionInputRef?.current) {
      questionInputRef?.current.focus();
    }
  }, [isInputDisabled, userMessage, currentConversationId]);

  const setUserMessage = useCallback((value: string) => {
    dispatch(setUserMessageAction(value));
  }, [dispatch]);

  const onNewConversation = useCallback(() => {
    dispatch(startNewConversation());
    dispatch(clearChat());
    dispatch(clearCitation());
  }, [dispatch]);

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
