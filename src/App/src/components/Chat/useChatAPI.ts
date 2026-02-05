import { useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
import { generateUUIDv4 } from "../../configs/Utils";
import {
    setSelectedConversationId,
} from "../../store/appSlice";
import {
    addNewConversation,
    updateConversation,
} from "../../store/chatHistorySlice";
import {
    addMessages,
    sendMessage,
    setGeneratingResponse,
    setStreamingFlag,
    setUserMessage as setUserMessageAction,
    updateMessageById,
} from "../../store/chatSlice";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
    type AgentMode,
    type ChartDataResponse,
    type ChatMessage,
    type Conversation,
    type ConversationRequest,
    type ModelReasoningEffort,
    type ModelType,
    type ParsedChunk,
    type ReasoningEffort,
    type ReasoningSummary,
    type ToolEvent,
} from "../../types/AppTypes";
import {
    isMalformedChartJSON,
    parseChartContent,
} from "../../utils/jsonUtils";
import { isChartQuery, parseReasoningContent, parseToolEvents } from "./chatUtils";

const [ASSISTANT, ERROR, USER] = ["assistant", "error", "user"];

export interface UseChatAPIOptions {
  agentMode: AgentMode;
  reasoningEffort: ReasoningEffort;
  modelType: ModelType;
  temperature: number;
  modelReasoningEffort: ModelReasoningEffort;
  reasoningSummary: ReasoningSummary;
  onToolEvents: (events: ToolEvent[]) => void;
  onReasoningContent: (content: string) => void;
  onChartLoadingChange: (loading: boolean) => void;
  scrollChatToBottom: () => void;
  throttledScrollChatToBottom: () => void;
}

export interface UseChatAPIReturn {
  sendChatMessage: (question: string, conversationId: string) => Promise<void>;
  abortCurrentRequest: () => void;
}

/**
 * Custom hook for handling chat API requests
 * Extracts API logic from Chat.tsx for better separation of concerns
 */
export const useChatAPI = ({
  agentMode,
  reasoningEffort,
  modelType,
  temperature,
  modelReasoningEffort,
  reasoningSummary,
  onToolEvents,
  onReasoningContent,
  onChartLoadingChange,
  scrollChatToBottom,
  throttledScrollChatToBottom,
}: UseChatAPIOptions): UseChatAPIReturn => {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const { userMessage, generatingResponse, messages } = useAppSelector((state) => state.chat);
  const selectedConversationId = useAppSelector((state) => state.app.selectedConversationId);
  const abortFuncs = useRef<AbortController[]>([]);

  // Save to database helper
  const saveToDB = useCallback(async (
    newMessages: ChatMessage[],
    convId: string,
    reqType: string = "Text"
  ) => {
    if (!convId || !newMessages.length) {
      return;
    }
    const isNewConversation = reqType !== "graph" ? !selectedConversationId : false;

    try {
      const result = await dispatch(updateConversation({
        conversationId: convId,
        messages: newMessages
      })).unwrap();

      if (isNewConversation && result?.success) {
        const resolvedConversationId = result?.data?.conversation_id || convId;
        const newConversation: Conversation = {
          id: resolvedConversationId,
          title: result?.data?.title,
          messages: messages,
          date: result?.data?.date,
          updatedAt: result?.data?.date,
        };
        dispatch(addNewConversation(newConversation));
        dispatch(setSelectedConversationId(resolvedConversationId));
      }
    } catch {
      // Error saving data to database
    } finally {
      dispatch(setGeneratingResponse(false));
    }
  }, [selectedConversationId, messages, dispatch]);

  // Helper function to create and dispatch a message
  const createAndDispatchMessage = useCallback((
    role: string,
    content: string | ChartDataResponse,
    shouldScroll: boolean = true
  ): ChatMessage => {
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
  const extractChartData = useCallback((
    chartResponse: ChartDataResponse | string
  ): ChartDataResponse | string => {
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

  // Process streaming response
  const processStreamResponse = useCallback(async (
    reader: ReadableStreamDefaultReader<Uint8Array>,
    streamMessage: ChatMessage,
    hasError: { value: boolean },
    runningText: { value: string }
  ): Promise<boolean> => {
    let isChartResponseReceived = false;
    const KEEPALIVE_MARKER = "__KEEPALIVE__";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      let text = new TextDecoder("utf-8").decode(value);

      // Filter out keepalive markers (used to prevent App Service timeout)
      if (text.includes(KEEPALIVE_MARKER)) {
        text = text.replaceAll(KEEPALIVE_MARKER, "");
        if (!text.trim()) continue; // Skip if only keepalive
      }

      // Parse and extract tool events from the stream
      const { events: newToolEvents, cleanedText } = parseToolEvents(text);
      if (newToolEvents.length > 0) {
        onToolEvents(newToolEvents);
        text = cleanedText;
      }

      // Parse and extract reasoning content from the stream (GPT-5 thinking)
      // SDK sends cumulative text, so we REPLACE the state instead of appending
      const { reasoningReplace, cleanedText: textAfterReasoning } =
        parseReasoningContent(text);
      if (reasoningReplace !== null) {
        onReasoningContent(reasoningReplace);
        text = textAfterReasoning;
      }

      try {
        const textObj = JSON.parse(text);
        if (textObj?.object?.data || textObj?.object?.message) {
          runningText.value = text;
          isChartResponseReceived = true;
        }
        if (textObj?.error) {
          hasError.value = true;
          runningText.value = text;
        }
      } catch {
        // Not JSON, continue processing as stream
      }

      if (!isChartResponseReceived) {
        const objects = text.split("\n").filter((val) => val !== "");

        for (const textValue of objects) {
          if (!textValue || textValue === "{}") continue;

          try {
            const parsed: ParsedChunk = JSON.parse(textValue);

            if (parsed?.error && !hasError.value) {
              hasError.value = true;
              runningText.value = parsed?.error;
            } else if (typeof parsed === "object" && !hasError.value) {
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
                runningText.value = responseContent;
              }
            }
          } catch {
            // Skip malformed chunks
          }
        }

        if (hasError.value) break;
      }
    }

    return isChartResponseReceived;
  }, [dispatch, onReasoningContent, onToolEvents, throttledScrollChatToBottom]);

  // Process chart response
  const processChartResponse = useCallback((
    runningText: string,
    newMessage: ChatMessage
  ): ChatMessage[] => {
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
        return [newMessage, chartMessage];
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
        return [newMessage, errorMessage];
      }
    } catch {
      // Error parsing chart response
    }
    return [];
  }, [createAndDispatchMessage, extractChartData]);

  // Main API request function
  const sendChatMessage = useCallback(async (
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
      onChartLoadingChange(true);
    }
    onToolEvents([]);

    dispatch(addMessages([newMessage]));
    dispatch(setUserMessageAction(""));
    scrollChatToBottom();

    const abortController = new AbortController();
    abortFuncs.current.unshift(abortController);

    const request: ConversationRequest = {
      id: conversationId || generateUUIDv4(),
      query: question,
      agentMode: agentMode,
      reasoningEffort: reasoningEffort,
      model: modelType,
      temperature: modelType === "gpt-4o-mini" ? temperature : undefined,
      modelReasoningEffort: modelType === "gpt-5" ? modelReasoningEffort : undefined,
      reasoningSummary: modelType === "gpt-5" && reasoningSummary !== "off" ? reasoningSummary : undefined,
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
      const result = await dispatch(sendMessage({
        request,
        abortSignal: abortController.signal
      }));

      if (!sendMessage.fulfilled.match(result)) {
        throw new Error("Failed to send message");
      }
      const response = result.payload;

      if (response?.body) {
        const reader = response.body.getReader();
        const hasError = { value: false };
        const runningText = { value: "" };

        const isChartResponseReceived = await processStreamResponse(
          reader,
          streamMessage,
          hasError,
          runningText
        );

        // Process final response
        if (hasError.value) {
          const parsedError = JSON.parse(runningText.value);
          const errorMsg = parsedError.error === "Attempted to access streaming response content, without having called `read()`."
            ? "An error occurred. Please try again later."
            : parsedError.error;

          const errorMessage = createAndDispatchMessage(ERROR, errorMsg);
          updatedMessages = [newMessage, errorMessage];
        } else if (isChartQuery(userMessage)) {
          if (streamMessage.content) {
            updatedMessages = [newMessage, streamMessage];
          } else {
            updatedMessages = processChartResponse(runningText.value, newMessage);
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
      } else {
        // Network error or other failure - display error in chat UI
        const errorText = e instanceof Error
          ? e.message
          : t("error.tryAgainLater") + " " + t("error.contactAdmin");
        const errorMessage = createAndDispatchMessage(ERROR, errorText);
        updatedMessages = [newMessage, errorMessage];
      }
    } finally {
      dispatch(setGeneratingResponse(false));
      dispatch(setStreamingFlag(false));
      onChartLoadingChange(false);
      abortController.abort();
    }
  }, [
    generatingResponse,
    userMessage,
    agentMode,
    reasoningEffort,
    modelType,
    temperature,
    modelReasoningEffort,
    reasoningSummary,
    dispatch,
    scrollChatToBottom,
    onChartLoadingChange,
    onToolEvents,
    createAndDispatchMessage,
    processChartResponse,
    processStreamResponse,
    saveToDB,
    t
  ]);

  // Abort current request
  const abortCurrentRequest = useCallback(() => {
    const controller = abortFuncs.current.shift();
    if (controller) {
      controller.abort("User cancelled request");
    }
  }, []);

  return {
    sendChatMessage,
    abortCurrentRequest,
  };
};

export default useChatAPI;
