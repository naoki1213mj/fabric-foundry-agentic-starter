import { DefaultButton } from "@fluentui/react";
import {
    Button,
    Dropdown,
    Option,
    Slider,
    Textarea,
} from "@fluentui/react-components";
import { ChatAdd24Regular } from "@fluentui/react-icons";
import React from "react";
import { useTranslation } from "react-i18next";
import type { AgentMode, ModelType, ReasoningEffort } from "../../types/AppTypes";

interface ChatInputProps {
  userMessage: string;
  onUserMessageChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onNewConversation: () => void;
  isInputDisabled: boolean;
  isSendDisabled: boolean;
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
}

// Agent mode options
const agentModeOptions: { value: AgentMode; label: string; description: string }[] = [
  { value: "sql_only", label: "SQL Only", description: "高速・SQLクエリのみ" },
  { value: "multi_tool", label: "Multi Tool (推奨)", description: "全ツール使用・バランス型" },
  { value: "handoff", label: "Handoff", description: "専門家エージェント委譲" },
  { value: "magentic", label: "Magentic", description: "複雑な計画・マネージャー型" },
];

// Reasoning effort options for Agentic Retrieval (Foundry IQ)
const reasoningEffortOptions: { value: ReasoningEffort; label: string; description: string }[] = [
  { value: "minimal", label: "Minimal", description: "高速・直接検索（LLMなし）" },
  { value: "low", label: "Low (推奨)", description: "シングルパス・バランス型" },
  { value: "medium", label: "Medium", description: "反復検索・最高品質" },
];

// Model options
const modelOptions: { value: ModelType; label: string; description: string }[] = [
  { value: "gpt-5", label: "GPT-5", description: "高精度・推論重視" },
  { value: "gpt-4o-mini", label: "GPT-4o-mini", description: "高速・コスト効率" },
];

/**
 * Chat input component with message input and agent settings
 */
export const ChatInput: React.FC<ChatInputProps> = ({
  userMessage,
  onUserMessageChange,
  onSend,
  onKeyDown,
  onNewConversation,
  isInputDisabled,
  isSendDisabled,
  questionInputRef,
  agentMode,
  onAgentModeChange,
  reasoningEffort,
  onReasoningEffortChange,
  modelType,
  onModelTypeChange,
  temperature,
  onTemperatureChange,
}) => {
  const { t } = useTranslation();

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
        <div className="text-area-container">
          <Textarea
            className="textarea-field"
            value={userMessage}
            onChange={(e, data) => onUserMessageChange(data.value || "")}
            placeholder={t("chat.placeholder")}
            onKeyDown={onKeyDown}
            ref={questionInputRef}
            rows={2}
            style={{ resize: "none" }}
            appearance="outline"
          />
          <DefaultButton
            iconProps={{ iconName: "Send" }}
            role="button"
            onClick={onSend}
            disabled={isSendDisabled}
            className="send-button"
            aria-disabled={isSendDisabled}
            title={t("chat.sendQuestion")}
          />
        </div>
      </div>
      <div className="footer-settings-row">
        <div className="setting-item">
          <span className="setting-label" title="エージェントの動作モード">🤖 Agent Mode:</span>
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
                  <span style={{ fontSize: "11px", color: "#666" }}>{option.description}</span>
                </div>
              </Option>
            ))}
          </Dropdown>
        </div>
        <div className="setting-item">
          <span className="setting-label" title="使用するAIモデル">🧠 {t("model.title")}:</span>
          <Dropdown
            placeholder="Model"
            value={modelOptions.find(opt => opt.value === modelType)?.label || "GPT-5"}
            selectedOptions={[modelType]}
            onOptionSelect={(_, data) => onModelTypeChange(data.optionValue as ModelType)}
            disabled={isInputDisabled}
            style={{ minWidth: "140px" }}
            title="使用するAIモデル"
          >
            {modelOptions.map((option) => (
              <Option key={option.value} value={option.value} text={option.label}>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontWeight: 500 }}>{option.label}</span>
                  <span style={{ fontSize: "11px", color: "#666" }}>{option.description}</span>
                </div>
              </Option>
            ))}
          </Dropdown>
        </div>
        {modelType === "gpt-4o-mini" && (
          <div className="setting-item">
            <span className="setting-label" title="回答の創造性 (0=正確, 2=創造的)">🎨 {t("model.temperature")}:</span>
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
        <div className="setting-item">
          <span className="setting-label" title="ドキュメント検索の推論レベル (Foundry IQ)">🔍 Doc Search:</span>
          <Dropdown
            placeholder="Reasoning Effort"
            value={reasoningEffortOptions.find(opt => opt.value === reasoningEffort)?.label || "Low"}
            selectedOptions={[reasoningEffort]}
            onOptionSelect={(_, data) => onReasoningEffortChange(data.optionValue as ReasoningEffort)}
            disabled={isInputDisabled}
            style={{ minWidth: "140px" }}
            title="ドキュメント検索の推論レベル (Foundry IQ)"
          >
            {reasoningEffortOptions.map((option) => (
              <Option key={option.value} value={option.value} text={option.label}>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontWeight: 500 }}>{option.label}</span>
                  <span style={{ fontSize: "11px", color: "#666" }}>{option.description}</span>
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
