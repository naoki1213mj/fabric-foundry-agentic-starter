import {
    CommandBarButton,
    ContextualMenu,
    DefaultButton,
    Dialog,
    DialogFooter,
    DialogType,
    ICommandBarStyles,
    IContextualMenuItem,
    PrimaryButton,
    Spinner,
    SpinnerSize,
    Stack
} from "@fluentui/react";
import React, { useState } from "react";
import { useTranslation } from "react-i18next";

import { useAppSelector } from "../../store/hooks";
import { ChatHistoryListItemGroups } from "../ChatHistoryListItemGroups/ChatHistoryListItemGroups";
import styles from "./ChatHistoryPanel.module.css";

const commandBarStyle: ICommandBarStyles = {
  root: {
    padding: "0",
    display: "flex",
    justifyContent: "center",
    backgroundColor: "transparent",
  },
};

export type ChatHistoryPanelProps = {
  clearingError: boolean;
  clearing: boolean;
  onHideClearAllDialog?: () => void;
  onClearAllChatHistory?: () => Promise<void>;
  handleFetchHistory: () => Promise<void>;
  onSelectConversation: (id: string) => Promise<void>;
  showClearAllConfirmationDialog: boolean;
  onClickClearAllOption: () => void;
};

const modalProps = {
  titleAriaId: "labelId",
  subtitleAriaId: "subTextId",
  isBlocking: true,
  styles: { main: { maxWidth: 450 } },
};

export const ChatHistoryPanel: React.FC<ChatHistoryPanelProps> = (props) => {
  const {
    clearingError,
    clearing,
    onHideClearAllDialog,
    onClearAllChatHistory,
    handleFetchHistory,
    onSelectConversation,
    showClearAllConfirmationDialog,
    onClickClearAllOption,
  } = props;
  const { t } = useTranslation();
  const chatHistory = useAppSelector((state) => state.chatHistory);
  const generatingResponse = useAppSelector((state) => state.chat.generatingResponse);
  const [showClearAllContextMenu, setShowClearAllContextMenu] =
    useState<boolean>(false);
  const clearAllDialogContentProps = {
    type: DialogType.close,
    title: !clearingError
      ? t("history.clearAllConfirm")
      : t("history.clearAllError"),
    closeButtonAriaLabel: t("common.close"),
    subText: !clearingError
      ? t("history.clearAllSubtext")
      : t("history.clearAllErrorSubtext"),
  };

  const disableClearAllChatHistory =
    !chatHistory.list.length ||
    generatingResponse ||
    chatHistory.fetchingConversations;
  const menuItems: IContextualMenuItem[] = [
    {
      key: "clearAll",
      text: t("history.title") + "をすべて削除",
      disabled: disableClearAllChatHistory,
      iconProps: { iconName: "Delete" },
      onClick: () => {
        onClickClearAllOption();
      },
    },
  ];

  const handleClearAllContextualMenu = () => {
    setShowClearAllContextMenu((prev) => !prev);
  };

  return (
    <section
      className={styles.historyContainer}
      data-is-scrollable
      aria-label={"chat history panel"}
    >
      <Stack
        horizontal
        horizontalAlign="space-between"
        verticalAlign="center"
        wrap
        aria-label="chat history header"
        className={styles.chatHistoryHeader}
      >
        <div
          role="heading"
          aria-level={2}
          style={{
            fontWeight: "600",
          }}
        >
          {t("history.title")}
        </div>
        <Stack horizontal className={styles.historyPanelTopRightButtons}>
          <Stack horizontal>
            <CommandBarButton
              iconProps={{ iconName: "More" }}
              title={t("history.title") + "をすべて削除"}
              onClick={handleClearAllContextualMenu}
              aria-label={t("history.title") + "をすべて削除"}
              styles={commandBarStyle}
              role="button"
              id="moreButton"
            />
            <ContextualMenu
              items={menuItems}
              hidden={!showClearAllContextMenu}
              target={"#moreButton"}
              onDismiss={handleClearAllContextualMenu}
            />
          </Stack>

        </Stack>
      </Stack>
      <Stack
        aria-label="chat history panel content"
        style={{
          display: "flex",
          flex: 1,
          minHeight: 0,
          position: "relative",
          overflow: "hidden",
        }}
      >
        {clearing && (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              backgroundColor: "var(--color-overlay)",
              zIndex: "var(--z-modal)" as unknown as number,
            }}
          >
          <Spinner
              size={SpinnerSize.large}
              label={t("history.clearing")}
              ariaLive="assertive"
              labelPosition="bottom"
            />
          </div>
        )}
        <Stack className={styles.chatHistoryListContainer}>
          <ChatHistoryListItemGroups
            handleFetchHistory={handleFetchHistory}
            onSelectConversation={onSelectConversation}
          />
        </Stack>
      </Stack>
      <Dialog
        hidden={!showClearAllConfirmationDialog}
        onDismiss={clearing ? () => {} : onHideClearAllDialog}
        dialogContentProps={clearAllDialogContentProps}
        modalProps={modalProps}
      >
        <DialogFooter>
          {!clearingError && (
            <PrimaryButton
              onClick={onClearAllChatHistory}
              disabled={clearing}
              text={t("common.clearAll")}
            />
          )}
          <DefaultButton
            onClick={onHideClearAllDialog}
            disabled={clearing}
            text={!clearingError ? t("common.cancel") : t("common.close")}
          />
        </DialogFooter>
      </Dialog>
    </section>
  );
};
