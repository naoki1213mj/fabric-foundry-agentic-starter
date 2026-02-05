import {
    DefaultButton,
    Dialog,
    DialogFooter,
    IconButton,
    ITextField,
    PrimaryButton,
    Spinner,
    SpinnerSize,
    Stack,
    Text,
    TextField,
} from "@fluentui/react";
import { useBoolean } from "@fluentui/react-hooks";
import * as React from "react";
import { useEffect, useRef, useState } from "react";

import { setSelectedConversationId } from "../../store/appSlice";
import { deleteConversation, renameConversation } from "../../store/chatHistorySlice";
import { clearChat } from "../../store/chatSlice";
import { setCitation } from "../../store/citationSlice";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { Conversation } from "../../types/AppTypes";
import styles from "./ChatHistoryListItemCell.module.css";
import {
    deleteDialogContentProps,
    deleteDialogModalProps,
    formatTimestamp,
    truncateTitle,
} from "./chatHistoryUtils";

interface ChatHistoryListItemCellProps {
  item?: Conversation;
  onSelect: (item: Conversation | null) => void;
}

export const ChatHistoryListItemCell: React.FC<
  ChatHistoryListItemCellProps
> = ({
  item,
  onSelect,
}) => {
  const dispatch = useAppDispatch();
  const selectedConversationId = useAppSelector((state) => state.app.selectedConversationId);
  const currentCitationConvId = useAppSelector((state) => state.citation.currentConversationIdForCitation);
  const generatingResponse = useAppSelector((state) => state.chat.generatingResponse);
  const [isHovered, setIsHovered] = React.useState(false);
  const [edit, setEdit] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [hideDeleteDialog, { toggle: toggleDeleteDialog }] = useBoolean(true);
  const [errorDelete, setErrorDelete] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [renameLoading, setRenameLoading] = useState(false);
  const [errorRename, setErrorRename] = useState<string | undefined>(undefined);
  const [textFieldFocused, setTextFieldFocused] = useState(false);
  const textFieldRef = useRef<ITextField | null>(null);
  const isSelected = item?.id === selectedConversationId;

  useEffect(() => {
    if (textFieldFocused && textFieldRef.current) {
      textFieldRef.current.focus();
      setTextFieldFocused(false);
    }
  }, [textFieldFocused]);

  if (!item) {
    return null;
  }

  const onDelete = async () => {
    toggleDeleteDialog();
    setDeleteLoading(true);
    if(currentCitationConvId === item.id) {
      dispatch(setCitation({ activeCitation: null, showCitation: false, currentConversationIdForCitation: "" }));
    } else {
      dispatch(setCitation({ showCitation: true }));
    }
    try {
      await dispatch(deleteConversation(item.id)).unwrap();
      if (isSelected) {
        dispatch(setSelectedConversationId(""));
        dispatch(clearChat());
      }
      setDeleteLoading(false);
    } catch (error) {
      setErrorDelete(true);
      setDeleteLoading(false);
      setTimeout(() => {
        setErrorDelete(false);
      }, 5000);
    }
  };

  const onEdit = (e: any) => {
    e.preventDefault();
    e.stopPropagation();
    setEdit(true);
    setTextFieldFocused(true);
    setEditTitle(item?.title);
  };

  const handleSelectItem = (e: any) => {
    if (isSelected) {
      return;
    }
    if (e?.target?.tagName === "INPUT") {
      e.preventDefault();
      e.stopPropagation();
    } else {
      onSelect(item);
    }
  };

  const truncatedTitleText = truncateTitle(item?.title);
  const timestamp = formatTimestamp(item?.updatedAt || item?.date);

  const handleSaveEdit = async (e: any) => {
    e.preventDefault();
    e.stopPropagation();
    if (errorRename || renameLoading || editTitle.trim() === "") {
      return;
    }

    if (editTitle.trim() === item?.title?.trim()) {
      setEdit(false);
      setTextFieldFocused(false);
      return;
    }
    setRenameLoading(true);
    try {
      await dispatch(renameConversation({ conversationId: item.id, newTitle: editTitle })).unwrap();
      setRenameLoading(false);
      setEdit(false);
      setEditTitle("");
    } catch {
      setErrorRename("Error: could not rename item");
      setTimeout(() => {
        setTextFieldFocused(true);
        setErrorRename(undefined);
        if (textFieldRef.current) {
          textFieldRef.current.focus();
        }
      }, 5000);
      setRenameLoading(false);
    }
  };

  const chatHistoryTitleOnChange = (e: any) => {
    setEditTitle(e.target.value);
  };

  const cancelEditTitle = (e: any) => {
    e.preventDefault();
    e.stopPropagation();
    setEdit(false);
    setEditTitle("");
  };

  const handleKeyPressEdit = (e: any) => {
    if (e.key === "Enter") {
      return handleSaveEdit(e);
    }
    if (e.key === "Escape") {
      cancelEditTitle(e);
      return;
    }
  };
  const onClickDelete = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    toggleDeleteDialog();
  };

  const handleOnKeyDownOnItemcell = (e: React.KeyboardEvent) => {
    const target = e.target as HTMLElement;
    if (
      e.key === "Enter" ||
      (e.key === " " && target.className.includes("itemCell"))
    ) {
      handleSelectItem(e);
    }
  };

  const isButtonDisabled = generatingResponse && isSelected;
  return (
    <Stack
      key={item.id}
      tabIndex={0}
      aria-label="chat history item"
      className={`${styles.itemCell} ${isSelected ? `${styles.cursorDefault} ${styles.itemCellSelected}` : ""}`}
      onClick={(e) => handleSelectItem(e)}
      onKeyDown={(e) => handleOnKeyDownOnItemcell(e)}
      verticalAlign="center"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {edit ? (
        <>
          <Stack.Item style={{ width: "100%" }}>
            <form
              aria-label="edit title form"
              onSubmit={(e) => handleSaveEdit(e)}
              style={{ padding: "5px 0px" }}
            >
              <Stack horizontal verticalAlign={"start"}>
                <Stack.Item>
                  <TextField
                    componentRef={textFieldRef}
                    autoFocus={textFieldFocused}
                    value={editTitle}
                    placeholder={item.title}
                    onChange={chatHistoryTitleOnChange}
                    onKeyDown={handleKeyPressEdit}
                    errorMessage={errorRename}
                    disabled={errorRename !== undefined || renameLoading}
                    title={editTitle}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                  />
                </Stack.Item>
                {editTitle && (
                  <Stack.Item>
                    <Stack
                      aria-label="action button group"
                      horizontal
                      verticalAlign={"center"}
                    >
                      {renameLoading ? (
                        <Spinner
                          size={SpinnerSize.small}
                          aria-label="Renaming conversation"
                          styles={{ root: { marginLeft: "5px",position:"relative",top:"8px" } }}
                        />
                      ) : (
                        <>
                          <IconButton
                            role="button"
                            disabled={errorRename !== undefined || editTitle.trim() === ""}
                            onKeyDown={(e) =>
                              e.key === " " || e.key === "Enter"
                                ? handleSaveEdit(e)
                                : null
                            }
                            onClick={(e) => handleSaveEdit(e)}
                            aria-label="confirm new title"
                            iconProps={{ iconName: "CheckMark" }}
                            styles={{ root: { color: "green", marginLeft: "5px" } }}
                          />
                          <IconButton
                            role="button"
                            disabled={errorRename !== undefined}
                            onKeyDown={(e) =>
                              e.key === " " || e.key === "Enter"
                                ? cancelEditTitle(e)
                                : null
                            }
                            onClick={(e) => cancelEditTitle(e)}
                            aria-label="cancel edit title"
                            iconProps={{ iconName: "Cancel" }}
                            styles={{ root: { color: "red", marginLeft: "5px" } }}
                          />
                        </>
                      )}
                    </Stack>
                  </Stack.Item>
                )}
              </Stack>
            </form>
          </Stack.Item>
        </>
      ) : (
        <>
          <Stack
            horizontal
            verticalAlign={"center"}
            className={styles.chatHistoryItem}
            title={item?.title}
          >
            <Stack verticalAlign={"center"} style={{ flex: 1, minWidth: 0 }}>
              <div className={`${styles.chatTitle} ${isSelected ? styles.selectedTitle : ""}`}>
                {truncatedTitleText}
              </div>
              {timestamp && (
                <div className={`${styles.chatTimestamp} ${isSelected ? styles.selectedTimestamp : ""}`}>
                  {timestamp}
                </div>
              )}
            </Stack>
            {deleteLoading && (
              <Spinner
                size={SpinnerSize.small}
                aria-label="Deleting conversation"
                styles={{ root: { marginLeft: "8px" } }}
              />
            )}
            {!deleteLoading && (isHovered || isSelected) && (
              <Stack
                horizontal
                horizontalAlign="end"
                className={styles.chatHistoryItemsButtonsContainer}
              >
                <IconButton
                  className={styles.itemButton}
                  disabled={isButtonDisabled}
                  iconProps={{ iconName: "Delete" }}
                  title="Delete"
                  onClick={onClickDelete}
                  onKeyDown={(e) =>
                    e.key === " " ? toggleDeleteDialog() : null
                  }
                />
                <IconButton
                  className={styles.itemButton}
                  disabled={isButtonDisabled}
                  iconProps={{ iconName: "Edit" }}
                  title="Edit"
                  onClick={(e) => onEdit(e)}
                  onKeyDown={(e) => (e.key === " " ? onEdit(e) : null)}
                />
              </Stack>
            )}
          </Stack>
        </>
      )}
      {errorDelete && (
        <Text
          styles={{
            root: { color: "red", marginTop: 5, fontSize: 14 },
          }}
        >
          Error: could not delete item
        </Text>
      )}
      <Dialog
        hidden={hideDeleteDialog}
        onDismiss={toggleDeleteDialog}
        dialogContentProps={deleteDialogContentProps}
        modalProps={deleteDialogModalProps}
      >
        <DialogFooter>
          <PrimaryButton onClick={onDelete} text="Delete" />
          <DefaultButton onClick={toggleDeleteDialog} text="Cancel" />
        </DialogFooter>
      </Dialog>
    </Stack>
  );
};
