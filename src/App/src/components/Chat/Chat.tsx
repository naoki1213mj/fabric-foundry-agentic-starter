import { DefaultButton, Spinner, SpinnerSize } from "@fluentui/react";
import {
    Body1,
    Button,
    Dropdown,
    Option,
    Subtitle2,
    Textarea,
} from "@fluentui/react-components";
import { ChatAdd24Regular } from "@fluentui/react-icons";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { getChatLandingText } from "../../config";
import { generateUUIDv4 } from "../../configs/Utils";
import {
    setSelectedConversationId,
    startNewConversation,
} from "../../store/appSlice";
import {
    addNewConversation,
    updateConversation, // eslint-disable-line @typescript-eslint/no-unused-vars
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
    ToolMessageContent,
} from "../../types/AppTypes";
import {
    isMalformedChartJSON,
    parseChartContent,
} from "../../utils/jsonUtils";
import ChatMessageComponent from "../ChatMessage/ChatMessage";
import "./Chat.css";

// Throttle utility for scroll during streaming
const throttle = <T extends (...args: Parameters<T>) => void>(fn: T, delay: number) => {
  let lastCall = 0;
  return (...args: Parameters<T>) => {
    const now = Date.now();
    if (now - lastCall >= delay) {
      lastCall = now;
      fn(...args);
    }
  };
};

type ChatProps = {
  onHandlePanelStates: (name: string) => void;
  panels: Record<string, string>;
  panelShowStates: Record<string, boolean>;
};

const [ASSISTANT, ERROR, USER] = ["assistant", "error", "user"];

const chatLandingText = getChatLandingText();

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
  const { isFetchingConvMessages, isHistoryUpdateAPIPending } = useAppSelector((state) => state.chatHistory);
  const questionInputRef = useRef<HTMLTextAreaElement>(null);
  const [isChartLoading, setIsChartLoading] = useState(false)
  const [agentMode, setAgentMode] = useState<AgentMode>("multi_tool");
  const abortFuncs = useRef([] as AbortController[]);
  const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

  // Agent mode options
  const agentModeOptions: { value: AgentMode; label: string; description: string }[] = [
    { value: "sql_only", label: "SQL Only", description: "高速・SQLクエリのみ" },
    { value: "multi_tool", label: "Multi Tool (推奨)", description: "全ツール使用・バランス型" },
    { value: "handoff", label: "Handoff", description: "専門家エージェント委譲" },
    { value: "magentic", label: "Magentic", description: "複雑な計画・マネージャー型" },
  ];

  // Memoized computed values
  const currentConversationId = useMemo(() =>
    selectedConversationId || generatedConversationId,
    [selectedConversationId, generatedConversationId]
  );

  const hasMessages = useMemo(() => messages.length > 0, [messages.length]);

  const isInputDisabled = useMemo(() =>
    generatingResponse || isHistoryUpdateAPIPending,
    [generatingResponse, isHistoryUpdateAPIPending]
  );

  const isSendDisabled = useMemo(() =>
    generatingResponse || !userMessage.trim() || isHistoryUpdateAPIPending,
    [generatingResponse, userMessage, isHistoryUpdateAPIPending]
  );

  const saveToDB = useCallback(async (newMessages: ChatMessage[], convId: string, reqType: string = 'Text') => {
    if (!convId || !newMessages.length) {
      return;
    }
    const isNewConversation = reqType !== 'graph' ? !selectedConversationId : false;

    if (false) {  // Disabled: chart display default
      setIsChartLoading(true);
      setTimeout(()=>{
        makeApiRequestForChart('show in a graph by default', convId)
      },5000)

    }

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
  const parseCitationFromMessage = useCallback((message: string) => {
  try {
    message = '{' + message;
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

  const isChartQuery = useCallback((query: string) => {
    const chartKeywords = [
      "chart",
      "graph",
      "visualize",
      "plot",
      "グラフ",
      "チャート",
      "可視化",
      "図",
      "棒グラフ",
      "円グラフ",
      "折れ線",
      "折れ線グラフ",
    ];

    // Convert to lowercase for case-insensitive matching
    const lowerCaseQuery = query.toLowerCase();

    // Use word boundary regex to match whole words only
    return chartKeywords.some((keyword) => {
      // 英語は単語境界、日本語は部分一致
      if (/^[a-z]+$/i.test(keyword)) {
        return new RegExp(`\\b${keyword}\\b`).test(lowerCaseQuery);
      }
      return lowerCaseQuery.includes(keyword);
    });
  }, []);

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

  const scrollChatToBottom = useCallback(() => {
    if (chatMessageStreamEnd.current) {
      setTimeout(() => {
        chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  }, []);

  // Throttled version for streaming - only scroll every 500ms to prevent flickering
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const throttledScrollChatToBottom = useMemo(
    () => throttle(() => {
      if (chatMessageStreamEnd.current) {
        chatMessageStreamEnd.current.scrollIntoView({ behavior: "auto" });
      }
    }, 500),
    []
  );

  useEffect(() => {
    scrollChatToBottom();
  }, [generatingResponse, scrollChatToBottom]);

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
    if (typeof chartResponse === 'object' && 'answer' in chartResponse) {
      return !chartResponse.answer ||
             (typeof chartResponse.answer === "object" && Object.keys(chartResponse.answer).length === 0)
        ? "Chart can't be generated, please try again."
        : chartResponse.answer;
    }

    if (typeof chartResponse === 'string') {
      try {
        const parsed = JSON.parse(chartResponse);
        if (parsed && typeof parsed === 'object' && 'answer' in parsed) {
          return !parsed.answer ||
                 (typeof parsed.answer === "object" && Object.keys(parsed.answer).length === 0)
            ? "Chart can't be generated, please try again."
            : parsed.answer;
        }
      } catch {
        // Fall through to default
      }
      return "Chart can't be generated, please try again.";
    }

    return chartResponse;
  }, []);

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
      agentMode: agentMode
    };

    let updatedMessages: ChatMessage[] = [];

    try {
      const result = await dispatch(sendMessage({ request, abortSignal: abortController.signal }));
      if (!sendMessage.fulfilled.match(result)) {
        throw new Error('Failed to send message');
      }
      const response = result.payload;

      if (response?.body) {
        const reader = response.body.getReader();
        let runningText = "";
        let hasError = false;

        // Read stream
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
          } catch (e) {
            // Non-JSON chunk, continue
          }
        }

        // Process response
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
        saveToDB(updatedMessages, conversationId, 'graph');
      }
    } catch (e) {
      // Error in chart API request

      if (abortController.signal.aborted) {
        updatedMessages = [newMessage];
        saveToDB(updatedMessages, conversationId, 'graph');
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
    // Set chart loading state for graph queries to show loading indicator
    if (isChart) {
      setIsChartLoading(true);
    }

    dispatch(addMessages([newMessage]));

    dispatch(setUserMessageAction(""));

    scrollChatToBottom();

    const abortController = new AbortController();
    abortFuncs.current.unshift(abortController);

    const request: ConversationRequest = {
      id: conversationId,
      query: userMessage,
      agentMode: agentMode
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
        throw new Error('Failed to send message');
      }
      const response = result.payload;

      if (response?.body) {
        let isChartResponseReceived = false;
        const reader = response.body.getReader();
        let runningText = "";
        let hasError = false;

        // Read and process stream
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = new TextDecoder("utf-8").decode(value);

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
          } catch (e) {
            // Not JSON, continue processing as stream
          }

          if (!isChartResponseReceived) {
            // Text-based streaming response
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
                    // Backend sends accumulated content, so we use it directly
                    // Create a new object to ensure Redux detects the change
                    streamMessage.content = responseContent;
                    streamMessage.role = parsed?.choices?.[0]?.messages?.[0]?.role || ASSISTANT;

                    // Handle citations (Bing terms compliance)
                    if (responseCitations) {
                      streamMessage.citations = responseCitations;
                    }

                    // Dispatch with a new object reference to trigger re-render
                    dispatch(updateMessageById({ ...streamMessage }));
                    // Use throttled scroll during streaming to prevent flickering
                    throttledScrollChatToBottom();
                    // Keep latest content for fallback parsing if needed
                    runningText = responseContent;
                  }
                }
              } catch (e) {
                // Skip malformed chunks
              }
            });

            if (hasError) break;
          }
        }

        // END OF STREAMING - Process final response
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
            // Fallback: attempt to parse chart-only responses
            try {
              const splitRunningText = runningText.split("}{");
              const parsedChartResponse = JSON.parse("{" + splitRunningText[splitRunningText.length - 1]);

              const rawChartContent = parsedChartResponse?.choices[0]?.messages[0]?.content;

              // **OPTIMIZED: Use helper function for parsing**
              let chartResponse = typeof rawChartContent === "string"
                ? parseChartContent(rawChartContent)
                : rawChartContent || "Chart can't be generated, please try again.";

              chartResponse = extractChartData(chartResponse);

              // Validate and create chart message
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
      // Error in API request

      if (abortController.signal.aborted) {
        updatedMessages = streamMessage.content
          ? [newMessage, streamMessage]
          : [newMessage];

        saveToDB(updatedMessages, conversationId, 'error');
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
  return (
    <div className="chat-container">
      <div className="chat-header">
        <Subtitle2>{t("chat.title")}</Subtitle2>
        <span>
          <Button
            appearance="outline"
            onClick={() => onHandlePanelStates(panels.CHATHISTORY)}
            className="hide-chat-history"
          >
            {panelShowStates?.[panels.CHATHISTORY] ? t("chat.hideHistory") : t("chat.showHistory")}
          </Button>
        </span>
      </div>
      <div className="chat-messages">
        {Boolean(isFetchingConvMessages) && (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
            minHeight: '300px'
          }}>
            <Spinner
              size={SpinnerSize.medium}
              aria-label={t("loading.fetchingMessages")}
            />
          </div>
        )}
        {!isFetchingConvMessages && !hasMessages && (
          <div className="initial-msg">
            <h2>✨</h2>
            <Subtitle2>{t("chat.startChatting")}</Subtitle2>
            <Body1 style={{ textAlign: "center" }}>
              {t("chat.landingText")}
            </Body1>
          </div>
        )}
        {!isFetchingConvMessages &&
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
        {/* Show loading indicator: 
            - "回答を生成中" when waiting for response (generatingResponse && !isStreamingInProgress && !isChartLoading)
            - "チャート生成中" when chart is loading AND not streaming (to avoid duplicate with ChatMessage)
        */}
        {((generatingResponse && !isStreamingInProgress && !isChartLoading) || (isChartLoading && !isStreamingInProgress)) && (
          <div className="assistant-message loading-indicator">
            <div className="typing-indicator">
              <span className="generating-text">{isChartLoading ? t("chat.generatingChart") : t("chat.generating")} </span>
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}
        <div data-testid="streamendref-id" ref={chatMessageStreamEnd} />
      </div>
      <div className="chat-footer">
        <div className="agent-mode-selector">
          <Dropdown
            placeholder="Agent Mode"
            value={agentModeOptions.find(opt => opt.value === agentMode)?.label || "Multi Tool"}
            selectedOptions={[agentMode]}
            onOptionSelect={(_, data) => setAgentMode(data.optionValue as AgentMode)}
            disabled={isInputDisabled}
            style={{ minWidth: "160px" }}
          >
            {agentModeOptions.map((option) => (
              <Option key={option.value} value={option.value} text={option.label}>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontWeight: 500 }}>{option.label}</span>
                  <span style={{ fontSize: "11px", color: "#666" }}>{option.description}</span>
                </div>
              </Option>
            ))}
          </Dropdown>
        </div>
        <Button
          className="btn-create-conv"
          shape="circular"
          appearance="primary"
          icon={<ChatAdd24Regular />}
          onClick={onNewConversation}
          title={t("chat.createNewConversation")}
          disabled={isInputDisabled}
        />
        <div className="text-area-container">
          <Textarea
            className="textarea-field"
            value={userMessage}
            onChange={(e, data) => setUserMessage(data.value || "")}
            placeholder={t("chat.placeholder")}
            onKeyDown={handleKeyDown}
            ref={questionInputRef}
            rows={2}
            style={{ resize: "none" }}
            appearance="outline"
          />
          <DefaultButton
            iconProps={{ iconName: "Send" }}
            role="button"
            onClick={onClickSend}
            disabled={isSendDisabled}
            className="send-button"
            aria-disabled={isSendDisabled}
            title={t("chat.sendQuestion")}
          />
        </div>
      </div>
    </div>
  );
};

export default Chat;
