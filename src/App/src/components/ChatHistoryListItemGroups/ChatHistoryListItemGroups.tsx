import {
    List,
    Separator,
    Spinner,
    SpinnerSize,
    Stack,
    StackItem,
    Text,
} from "@fluentui/react";
import * as React from "react";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { segregateItems } from "../../configs/Utils";
import { useAppSelector } from "../../store/hooks";
import { Conversation } from "../../types/AppTypes";
import { ChatHistoryListItemCell } from "../ChatHistoryListItemCell/ChatHistoryListItemCell";
import styles from "./ChatHistoryListItemGroups.module.css";

export interface GroupedChatHistory {
  title: string;
  entries: Conversation[];
}
interface ChatHistoryListItemGroupsProps {
  handleFetchHistory: () => Promise<void>;
  onSelectConversation: (id: string) => void;
}

export const ChatHistoryListItemGroups: React.FC<
  ChatHistoryListItemGroupsProps
> = ({
  handleFetchHistory,
  onSelectConversation,
}) => {
  const { t } = useTranslation();
  const observerTarget = useRef(null);
  const initialCall = useRef(true);
  const chatHistory = useAppSelector((state) => state.chatHistory);

  const groupedChatHistory = segregateItems(chatHistory.list);

  const handleSelectHistory = (item?: Conversation) => {
    if (typeof item === "object") {
      onSelectConversation(item?.id);
    }
  };

  const onRenderCell = (item?: Conversation) => {
    return (
      <ChatHistoryListItemCell
        item={item}
        onSelect={() => handleSelectHistory(item)}
        key={item?.id}
      />
    );
  };
  useEffect(() => {
    if (initialCall.current) {
      initialCall.current = false;
    }
  }, []);

  useEffect(() => {
    if (initialCall.current) {
      return;
    }
    // Copy ref to local variable for cleanup
    const observerTargetCurrent = observerTarget.current;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          if (!chatHistory?.fetchingConversations) {
            handleFetchHistory();
          }
        }
      },
      { threshold: 1 }
    );

    if (observerTargetCurrent) observer.observe(observerTargetCurrent);

    return () => {
      if (observerTargetCurrent) observer.unobserve(observerTargetCurrent);
    };
  }, [chatHistory?.fetchingConversations, handleFetchHistory]);

  const allConversationsLength = groupedChatHistory.reduce(
    (previousValue, currentValue) =>
      previousValue + currentValue.entries.length,
    0
  );

  // Show centered spinner during initial load
  if (chatHistory.fetchingConversations && allConversationsLength === 0) {
    return (
      <Stack
        horizontal
        horizontalAlign="center"
        verticalAlign="center"
        style={{ width: "100%", height: "100%", minHeight: "200px" }}
      >
        <StackItem>
          <Spinner
            size={SpinnerSize.medium}
            aria-label={t("history.loading")}
          />
        </StackItem>
      </Stack>
    );
  }

  if (!chatHistory.fetchingConversations && allConversationsLength === 0) {
    return (
      <Stack
        horizontal
        horizontalAlign="center"
        verticalAlign="center"
        style={{ width: "100%", marginTop: 10 }}
      >
        <StackItem>
          <Text
            style={{ alignSelf: "center", fontWeight: "400", fontSize: 14 }}
          >
            <span>{t("history.noHistory")}</span>
          </Text>
        </StackItem>
      </Stack>
    );
  }

  return (
    <div
      id="historyListContainer"
      className={styles.listContainer}
      data-is-scrollable
    >
      {groupedChatHistory.map(
        (group, index) =>
          group.entries.length > 0 && (
            <Stack
              horizontalAlign="start"
              verticalAlign="center"
              key={`GROUP-${group.title}-${index}`}
              className={styles.chatGroup}
              aria-label={`chat history group: ${group.title}`}
            >
              <Stack aria-label={group.title} className={styles.chatMonth}>
                {group.title}
              </Stack>
              <List
                aria-label={`chat history list`}
                items={group.entries}
                onRenderCell={onRenderCell}
                className={styles.chatList}
              />
            </Stack>
          )
      )}
      <div id="chatHistoryListItemObserver" ref={observerTarget} />
      <Separator
        styles={{
          root: {
            width: "100%",
            padding: "0px",
            height: "2px",
            position: "relative",
            "::before": {
              backgroundColor: "#d6d6d6",
            },
          },
        }}
      />
      {Boolean(chatHistory?.fetchingConversations) && (
        <div className={styles.spinnerContainer}>
          <Spinner
            size={SpinnerSize.small}
            aria-label={t("history.loadingMore")}
            className={styles.spinner}
          />
        </div>
      )}
    </div>
  );
};
