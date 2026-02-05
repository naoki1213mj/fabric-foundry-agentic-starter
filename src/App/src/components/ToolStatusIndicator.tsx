import { ChevronDown12Regular, ChevronRight12Regular } from "@fluentui/react-icons";
import React, { useState } from "react";
import { TOOL_DISPLAY_CONFIG, ToolEvent } from "../types/AppTypes";
import "./ToolStatusIndicator.css";

interface ToolStatusIndicatorProps {
    toolEvents: ToolEvent[];
    className?: string;
    isGenerating?: boolean;
    isExpanded?: boolean;
    onToggle?: (expanded: boolean) => void;
}

/**
 * ツール使用結果を表示するコンポーネント
 * 応答完了後に使用したツールを折りたたみ可能な形式で表示
 */
export const ToolStatusIndicator: React.FC<ToolStatusIndicatorProps> = ({
    toolEvents,
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

    // 最新の状態を取得（同じツールは最新のイベントのみ表示）
    const latestEvents = React.useMemo(() => {
        const eventMap = new Map<string, ToolEvent>();
        toolEvents.forEach((event) => {
            eventMap.set(event.tool, event);
        });
        return Array.from(eventMap.values());
    }, [toolEvents]);

    // すべてのツールを表示（生成完了後も表示を維持）
    // 生成中: started, completed, error すべて表示
    // 生成完了後: started は「完了」として表示、completed, error はそのまま表示
    const allTools = React.useMemo(() => {
        const completedTools = latestEvents.filter((e) => e.status === "completed");
        const errorTools = latestEvents.filter((e) => e.status === "error");
        const startedTools = latestEvents.filter((e) => e.status === "started");

        if (isGenerating) {
            // 生成中は進行中のツールも表示
            return [...startedTools, ...completedTools, ...errorTools];
        } else {
            // 生成完了後: startedのままのツールは「完了」として扱う（completedイベントが来なかった場合の救済）
            // ただし、すでにcompletedがあるツールは除外
            const completedToolNames = new Set(completedTools.map(t => t.tool));
            const errorToolNames = new Set(errorTools.map(t => t.tool));
            const remainingStarted = startedTools.filter(
                t => !completedToolNames.has(t.tool) && !errorToolNames.has(t.tool)
            );
            return [...remainingStarted, ...completedTools, ...errorTools];
        }
    }, [latestEvents, isGenerating]);

    // カテゴリ別にグループ化（Hookは早期リターンの前に配置）
    const toolsByCategory = React.useMemo(() => {
        const groups = new Map<string, typeof allTools>();
        allTools.forEach((event) => {
            const config = TOOL_DISPLAY_CONFIG[event.tool];
            const category = config?.category || "その他";
            if (!groups.has(category)) {
                groups.set(category, []);
            }
            groups.get(category)!.push(event);
        });
        return groups;
    }, [allTools]);

    // 表示するツールがない場合は何も表示しない
    if (allTools.length === 0) {
        return null;
    }

    return (
        <div className={`tool-status-container tool-status-summary ${className}`}>
            {/* ヘッダー（折りたたみトグル） */}
            <button
                className="tool-status-header"
                onClick={toggleExpanded}
                aria-expanded={expanded}
                aria-label={expanded ? "ツール使用状況を折りたたむ" : "ツール使用状況を展開"}
            >
                <span className="tool-status-toggle-icon">
                    {expanded ? <ChevronDown12Regular /> : <ChevronRight12Regular />}
                </span>
                <span className="tool-status-summary-text">
                    🛠️ {allTools.length}個のツールを{isGenerating ? "実行中" : "使用"}
                    {isGenerating && <span className="tool-spinner">⏳</span>}
                </span>
            </button>

            {/* ツールリスト（展開時のみ） */}
            {expanded && (
                <div className="tool-status-list">
                    {Array.from(toolsByCategory.entries()).map(([category, tools]) => (
                        <div key={category} className="tool-category-group">
                            <span className="tool-category-label">{category}</span>
                            {tools.map((event) => {
                                const config = TOOL_DISPLAY_CONFIG[event.tool] || {
                                    icon: "🔧",
                                    label: event.tool,
                                };
                                const isError = event.status === "error";
                                // 生成中は進行中として表示、生成完了後は進行中も「完了」として表示
                                const isInProgress = isGenerating && event.status === "started";
                                return (
                                    <div
                                        key={event.tool}
                                        className={`tool-status-item ${isError ? "tool-status-error" : isInProgress ? "tool-status-in-progress" : "tool-status-completed"}`}
                                    >
                                        <span className="tool-icon">{config.icon}</span>
                                        <span className="tool-label">{config.label}</span>
                                        {event.message && (
                                            <span className="tool-message">{event.message}</span>
                                        )}
                                        {isInProgress && (
                                            <span className="tool-status-badge tool-badge-progress">実行中...</span>
                                        )}
                                        {isError && (
                                            <span className="tool-status-badge tool-badge-error">エラー</span>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ToolStatusIndicator;
