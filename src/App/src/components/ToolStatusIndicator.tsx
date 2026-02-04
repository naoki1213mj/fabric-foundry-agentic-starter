import { ChevronDown12Regular, ChevronRight12Regular } from "@fluentui/react-icons";
import React, { useState } from "react";
import { TOOL_DISPLAY_CONFIG, ToolEvent } from "../types/AppTypes";
import "./ToolStatusIndicator.css";

interface ToolStatusIndicatorProps {
    toolEvents: ToolEvent[];
    className?: string;
}

/**
 * ツール使用結果を表示するコンポーネント
 * 応答完了後に使用したツールを折りたたみ可能な形式で表示
 */
export const ToolStatusIndicator: React.FC<ToolStatusIndicatorProps> = ({
    toolEvents,
    className = "",
}) => {
    const [isExpanded, setIsExpanded] = useState(false); // デフォルトは折りたたみ

    // 最新の状態を取得（同じツールは最新のイベントのみ表示）
    const latestEvents = React.useMemo(() => {
        const eventMap = new Map<string, ToolEvent>();
        toolEvents.forEach((event) => {
            eventMap.set(event.tool, event);
        });
        return Array.from(eventMap.values());
    }, [toolEvents]);

    // 完了したツールのみ表示（startedは完了後は表示しない）
    const allTools = React.useMemo(() => {
        const completedTools = latestEvents.filter((e) => e.status === "completed");
        const errorTools = latestEvents.filter((e) => e.status === "error");
        return [...completedTools, ...errorTools];
    }, [latestEvents]);

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
                onClick={() => setIsExpanded(!isExpanded)}
                aria-expanded={isExpanded}
                aria-label={isExpanded ? "ツール使用状況を折りたたむ" : "ツール使用状況を展開"}
            >
                <span className="tool-status-toggle-icon">
                    {isExpanded ? <ChevronDown12Regular /> : <ChevronRight12Regular />}
                </span>
                <span className="tool-status-summary-text">
                    🛠️ {allTools.length}個のツールを使用
                </span>
            </button>

            {/* ツールリスト（展開時のみ） */}
            {isExpanded && (
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
                                return (
                                    <div
                                        key={event.tool}
                                        className={`tool-status-item ${isError ? "tool-status-error" : "tool-status-completed"}`}
                                    >
                                        <span className="tool-icon">{config.icon}</span>
                                        <span className="tool-label">{config.label}</span>
                                        {event.message && (
                                            <span className="tool-message">{event.message}</span>
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
