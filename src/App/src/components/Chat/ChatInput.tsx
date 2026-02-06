import { DefaultButton } from "@fluentui/react";
import {
    Button,
    Dropdown,
    Option,
    Slider,
    Textarea,
} from "@fluentui/react-components";
import { ChatAdd24Regular, Stop24Regular } from "@fluentui/react-icons";
import React, { useCallback, useEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { AgentMode, ModelReasoningEffort, ModelType, ReasoningEffort, ReasoningSummary } from "../../types/AppTypes";

interface ChatInputProps {
  userMessage: string;
  onUserMessageChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onNewConversation: () => void;
  isInputDisabled: boolean;
  isSendDisabled: boolean;
  isGenerating: boolean;
  questionInputRef: React.RefObject<HTMLTextAreaElement>;
  // Agent settings
  agentMode: AgentMode;
  onAgentModeChange: (mode: AgentMode) => void;
  reasoningEffort: ReasoningEffort;
  onReasoningEffortChange: (effort: ReasoningEffort) => void;
  // Model settings
  modelType: ModelType;
  onModelTypeChange: (model: ModelType) => void;
  temperature: number;
  onTemperatureChange: (temp: number) => void;
  modelReasoningEffort: ModelReasoningEffort;
  onModelReasoningEffortChange: (effort: ModelReasoningEffort) => void;
  reasoningSummary: ReasoningSummary;
  onReasoningSummaryChange: (summary: ReasoningSummary) => void;
}

/**
 * Chat input component with message input and agent settings
 */
export const ChatInput: React.FC<ChatInputProps> = ({
  userMessage,
  onUserMessageChange,
  onSend,
  onStop,
  onKeyDown,
  onNewConversation,
  isInputDisabled,
  isSendDisabled,
  isGenerating,
  questionInputRef,
  agentMode,
  onAgentModeChange,
  reasoningEffort,
  onReasoningEffortChange,
  modelType,
  onModelTypeChange,
  temperature,
  onTemperatureChange,
  modelReasoningEffort,
  onModelReasoningEffortChange,
  reasoningSummary,
  onReasoningSummaryChange,
}) => {
  const { t } = useTranslation();
  const textareaContainerRef = useRef<HTMLDivElement>(null);

  // Agent mode options (i18n)
  const agentModeOptions = useMemo(() => [
    { value: "sql_only" as AgentMode, label: "SQL Only", description: t("agentMode.sqlOnly") },
    { value: "multi_tool" as AgentMode, label: `Multi Tool (${t("common.recommended") || "推奨"})`, description: t("agentMode.multiTool") },
    { value: "handoff" as AgentMode, label: "Handoff", description: t("agentMode.handoff") },
    { value: "magentic" as AgentMode, label: "Magentic", description: t("agentMode.magentic") },
  ], [t]);

  // Reasoning effort options for Agentic Retrieval (Foundry IQ)
  const reasoningEffortOptions = useMemo(() => [
    { value: "minimal" as ReasoningEffort, label: "Minimal", description: t("docSearch.minimal") },
    { value: "low" as ReasoningEffort, label: `Low (${t("common.recommended") || "推奨"})`, description: t("docSearch.low") },
    { value: "medium" as ReasoningEffort, label: "Medium", description: t("docSearch.medium") },
  ], [t]);

  // Model options
  const modelOptions = useMemo(() => [
    { value: "gpt-5" as ModelType, label: "GPT-5", description: t("modelSettings.gpt5Desc") },
    { value: "gpt-4o-mini" as ModelType, label: "GPT-4o-mini", description: t("modelSettings.gpt4oMiniDesc") },
  ], [t]);

  // Model reasoning effort options for GPT-5
  const modelReasoningOptions = useMemo(() => [
    { value: "low" as ModelReasoningEffort, label: "Low", description: t("modelSettings.reasoningLow") },
    { value: "medium" as ModelReasoningEffort, label: `Medium (${t("common.recommended") || "推奨"})`, description: t("modelSettings.reasoningMedium") },
    { value: "high" as ModelReasoningEffort, label: "High", description: t("modelSettings.reasoningHigh") },
  ], [t]);

  // Reasoning summary options for GPT-5 (思考プロセス表示)
  const reasoningSummaryOptions = useMemo(() => [
    { value: "off" as ReasoningSummary, label: "Off", description: t("modelSettings.summaryOff") },
    { value: "auto" as ReasoningSummary, label: "Auto", description: t("modelSettings.summaryAuto") },
    { value: "concise" as ReasoningSummary, label: "Concise", description: t("modelSettings.summaryConcise") },
    { value: "detailed" as ReasoningSummary, label: "Detailed", description: t("modelSettings.summaryDetailed") },
  ], [t]);

  // テキストエリアの自動拡張
  const adjustTextareaHeight = useCallback(() => {
    const textarea = questionInputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const newHeight = Math.min(textarea.scrollHeight, 200); // 最大200px
      textarea.style.height = `${newHeight}px`;
    }
  }, [questionInputRef]);

  useEffect(() => {
    adjustTextareaHeight();
  }, [userMessage, adjustTextareaHeight]);

  return (
    <div className="chat-footer">
      <div className="footer-input-row">
        <Button
          className="btn-create-conv"
          shape="circular"
          appearance="subtle"
          icon={<ChatAdd24Regular />}
          onClick={onNewConversation}
          title={t("chat.createNewConversation")}
          disabled={isInputDisabled}
        />
        <div className="text-area-container" ref={textareaContainerRef}>
          <Textarea
            className="textarea-field"
            value={userMessage}
            onChange={(e, data) => onUserMessageChange(data.value || "")}
            placeholder={t("chat.placeholder")}
            onKeyDown={onKeyDown}
            ref={questionInputRef}
            rows={1}
            style={{ resize: "vertical", minHeight: "44px", maxHeight: "200px", overflow: "auto" }}
            appearance="outline"
          />
          {isGenerating ? (
            <Button
              icon={<Stop24Regular />}
              onClick={onStop}
              className="stop-button"
              appearance="primary"
              title={t("chat.stopGenerating")}
              aria-label={t("chat.stopGenerating")}
            />
          ) : (
            <DefaultButton
              iconProps={{ iconName: "Send" }}
              role="button"
              onClick={onSend}
              disabled={isSendDisabled}
              className="send-button"
              aria-disabled={isSendDisabled}
              title={t("chat.sendQuestion")}
            />
          )}
        </div>
      </div>
      <div className="footer-settings-row">
        <div className="setting-item">
          <span className="setting-label" title={t("agentMode.label")}>🤖 Agent Mode:</span>
          <Dropdown
            placeholder="Agent Mode"
            value={agentModeOptions.find(opt => opt.value === agentMode)?.label || "Multi Tool"}
            selectedOptions={[agentMode]}
            onOptionSelect={(_, data) => onAgentModeChange(data.optionValue as AgentMode)}
            disabled={isInputDisabled}
            style={{ minWidth: "160px" }}
          >
            {agentModeOptions.map((option) => (
              <Option key={option.value} value={option.value} text={option.label}>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontWeight: 500 }}>{option.label}</span>
                  <span style={{ fontSize: "11px", color: "var(--color-text-tertiary)" }}>{option.description}</span>
                </div>
              </Option>
            ))}
          </Dropdown>
        </div>
        <div className="setting-item">
          <span className="setting-label" title={t("modelSettings.label")}>🧠 {t("model.title")}:</span>
          <Dropdown
            placeholder="Model"
            value={modelOptions.find(opt => opt.value === modelType)?.label || "GPT-5"}
            selectedOptions={[modelType]}
            onOptionSelect={(_, data) => onModelTypeChange(data.optionValue as ModelType)}
            disabled={isInputDisabled}
            style={{ minWidth: "140px" }}
            title={t("modelSettings.label")}
          >
            {modelOptions.map((option) => (
              <Option key={option.value} value={option.value} text={option.label}>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontWeight: 500 }}>{option.label}</span>
                  <span style={{ fontSize: "11px", color: "var(--color-text-tertiary)" }}>{option.description}</span>
                </div>
              </Option>
            ))}
          </Dropdown>
        </div>
        {modelType === "gpt-4o-mini" && (
          <div className="setting-item">
            <span className="setting-label" title={t("modelSettings.temperatureLabel")}>🎨 {t("model.temperature")}:</span>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: "120px" }}>
              <Slider
                min={0}
                max={2}
                step={0.1}
                value={temperature}
                onChange={(_, data) => onTemperatureChange(data.value)}
                disabled={isInputDisabled}
                style={{ flex: 1 }}
              />
              <span style={{ fontSize: "12px", minWidth: "28px" }}>{temperature.toFixed(1)}</span>
            </div>
          </div>
        )}
        {modelType === "gpt-5" && (
          <div className="setting-item">
            <span className="setting-label" title={t("modelSettings.reasoningLabel")}>🧠 {t("model.reasoningEffort")}:</span>
            <Dropdown
              placeholder="Reasoning"
              value={modelReasoningOptions.find(opt => opt.value === modelReasoningEffort)?.label || "Medium"}
              selectedOptions={[modelReasoningEffort]}
              onOptionSelect={(_, data) => onModelReasoningEffortChange(data.optionValue as ModelReasoningEffort)}
              disabled={isInputDisabled}
              style={{ minWidth: "130px" }}
              title={t("modelSettings.reasoningLabel")}
            >
              {modelReasoningOptions.map((option) => (
                <Option key={option.value} value={option.value} text={option.label}>
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <span style={{ fontWeight: 500 }}>{option.label}</span>
                    <span style={{ fontSize: "11px", color: "var(--color-text-tertiary)" }}>{option.description}</span>
                  </div>
                </Option>
              ))}
            </Dropdown>
          </div>
        )}
        {modelType === "gpt-5" && (
          <div className="setting-item">
            <span className="setting-label" title={t("modelSettings.summaryLabel")}>💭 {t("modelSettings.thinkingDisplay")}:</span>
            <Dropdown
              placeholder={t("modelSettings.thinkingDisplay")}
              value={reasoningSummaryOptions.find(opt => opt.value === reasoningSummary)?.label || "Auto"}
              selectedOptions={[reasoningSummary]}
              onOptionSelect={(_, data) => onReasoningSummaryChange(data.optionValue as ReasoningSummary)}
              disabled={isInputDisabled}
              style={{ minWidth: "130px" }}
              title={t("modelSettings.summaryLabel")}
            >
              {reasoningSummaryOptions.map((option) => (
                <Option key={option.value} value={option.value} text={option.label}>
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <span style={{ fontWeight: 500 }}>{option.label}</span>
                    <span style={{ fontSize: "11px", color: "var(--color-text-tertiary)" }}>{option.description}</span>
                  </div>
                </Option>
              ))}
            </Dropdown>
          </div>
        )}
        <div className="setting-item">
          <span className="setting-label" title={t("docSearch.label")}>🔍 Doc Search:</span>
          <Dropdown
            placeholder="Reasoning Effort"
            value={reasoningEffortOptions.find(opt => opt.value === reasoningEffort)?.label || "Low"}
            selectedOptions={[reasoningEffort]}
            onOptionSelect={(_, data) => onReasoningEffortChange(data.optionValue as ReasoningEffort)}
            disabled={isInputDisabled}
            style={{ minWidth: "140px" }}
            title={t("docSearch.label")}
          >
            {reasoningEffortOptions.map((option) => (
              <Option key={option.value} value={option.value} text={option.label}>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontWeight: 500 }}>{option.label}</span>
                  <span style={{ fontSize: "11px", color: "var(--color-text-tertiary)" }}>{option.description}</span>
                </div>
              </Option>
            ))}
          </Dropdown>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;
