import { ChevronDown12Regular, ChevronRight12Regular } from "@fluentui/react-icons";
import React, { useState } from "react";
import "./ReasoningIndicator.css";

interface ReasoningIndicatorProps {
    reasoningContent: string;  // Concatenated reasoning text (streaming delta)
    className?: string;
    isGenerating?: boolean;
    isExpanded?: boolean;
    onToggle?: (expanded: boolean) => void;
}

/**
 * GPT-5の推論プロセスを表示するコンポーネント
 * 思考内容を折りたたみ可能な形式で表示
 */
export const ReasoningIndicator: React.FC<ReasoningIndicatorProps> = ({
    reasoningContent,
    className = "",
    isGenerating = false,
    isExpanded,
    onToggle,
}) => {
    const [internalExpanded, setInternalExpanded] = useState(false); // デフォルトは折りたたみ
    const expanded = isExpanded ?? internalExpanded;
    const toggleExpanded = () => {
        const next = !expanded;
        if (onToggle) {
            onToggle(next);
        } else {
            setInternalExpanded(next);
        }
    };

    // 推論内容がない場合は何も表示しない
    if (!reasoningContent) {
        return null;
    }

    // 表示用に最初の部分を取得
    const previewLength = 100;
    const preview = reasoningContent.length > previewLength
        ? reasoningContent.substring(0, previewLength) + "..."
        : reasoningContent;

    return (
        <div className={`reasoning-status-container ${className}`}>
            {/* ヘッダー（折りたたみトグル） */}
            <button
                className="reasoning-status-header"
                onClick={toggleExpanded}
                aria-expanded={expanded}
                aria-label={expanded ? "推論内容を折りたたむ" : "推論内容を展開"}
            >
                <span className="reasoning-status-toggle-icon">
                    {expanded ? <ChevronDown12Regular /> : <ChevronRight12Regular />}
                </span>
                <span className="reasoning-status-summary-text">
                    🧠 GPT-5 推論プロセス
                    {isGenerating && <span className="reasoning-spinner">⏳ 思考中...</span>}
                    {!isGenerating && !expanded && (
                        <span className="reasoning-preview"> - {preview}</span>
                    )}
                </span>
            </button>

            {/* 推論内容（展開時のみ） */}
            {expanded && (
                <div className="reasoning-content">
                    <pre className="reasoning-text">{reasoningContent}</pre>
                </div>
            )}
        </div>
    );
};

export default ReasoningIndicator;
