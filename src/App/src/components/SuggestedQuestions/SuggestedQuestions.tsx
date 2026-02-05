import React from "react";
import { useTranslation } from "react-i18next";
import "./SuggestedQuestions.css";

interface SuggestedQuestionsProps {
  onSelectQuestion: (question: string) => void;
  disabled?: boolean;
}

// Sample questions for different scenarios
const suggestedQuestions = [
  {
    icon: "📊",
    labelKey: "suggestions.salesAnalysis",
    question: "売上トップ10製品を教えてください",
  },
  {
    icon: "👥",
    labelKey: "suggestions.customerInsights",
    question: "最も価値のある顧客セグメントは？",
  },
  {
    icon: "📈",
    labelKey: "suggestions.trendAnalysis",
    question: "過去3年間の売上トレンドを分析して",
  },
  {
    icon: "🔍",
    labelKey: "suggestions.productSpecs",
    question: "Mountain Bike製品の仕様を教えて",
  },
];

/**
 * Suggested questions component for empty chat state
 * Displays clickable sample questions to help users get started
 */
export const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  onSelectQuestion,
  disabled = false,
}) => {
  const { t } = useTranslation();

  return (
    <div className="suggested-questions">
      <div className="suggestions-header">
        <span className="suggestions-icon">💡</span>
        <span className="suggestions-title">{t("suggestions.title") || "試してみてください"}</span>
      </div>
      <div className="suggestions-grid">
        {suggestedQuestions.map((item, index) => (
          <button
            key={index}
            className="suggestion-btn"
            onClick={() => onSelectQuestion(item.question)}
            disabled={disabled}
            title={item.question}
          >
            <span className="suggestion-icon">{item.icon}</span>
            <span className="suggestion-text">
              {t(item.labelKey) || item.question}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedQuestions;
