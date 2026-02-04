import { ChevronDown12Regular, ChevronRight12Regular } from "@fluentui/react-icons";
import React, { useState } from "react";
import { TOOL_DISPLAY_CONFIG, ToolEvent } from "../types/AppTypes";
import "./ToolStatusIndicator.css";

interface ToolStatusIndicatorProps {
    toolEvents: ToolEvent[];
    className?: string;
    /** 応答生成中かどうか */
    isGenerating?: boolean;
}

/**
 * ツール使用状況を表示するコンポーネント
 * エージェントが使用中/使用済みのツールを表示
 * 応答完了後は折りたたみ可能なサマリー表示
 */
export const ToolStatusIndicator: React.FC<ToolStatusIndicatorProps> = ({
    toolEvents,
    className = "",
    isGenerating = false,
}) => {
    const [isExpanded, setIsExpanded] = useState(true);

    // 最新の状態を取得（同じツールは最新のイベントのみ表示）
    const latestEvents = React.useMemo(() => {
        const eventMap = new Map<string, ToolEvent>();
        toolEvents.forEach((event) => {
            eventMap.set(event.tool, event);
        });
        return Array.from(eventMap.values());
    }, [toolEvents]);

    // アクティブなツール（started状態）
    const activeTools = latestEvents.filter((e) => e.status === "started");
    // 完了したツール
    const completedTools = latestEvents.filter((e) => e.status === "completed");
    // エラーのツール
    const errorTools = latestEvents.filter((e) => e.status === "error");

    const totalCompleted = completedTools.length;

    if (latestEvents.length === 0) {
        return null;
    }

    // 生成中は常に展開、完了後は折りたたみ可能
    const showExpanded = isGenerating || isExpanded;

    return (
        <div className={`tool-status-container ${className} ${isGenerating ? "" : "tool-status-summary"}`}>
            {/* ヘッダー（折りたたみトグル） - 生成完了後のみ表示 */}
            {!isGenerating && (
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
                        🔧 {totalCompleted}個のツールを使用
                    </span>
                </button>
            )}

            {/* ツールリスト */}
            {showExpanded && (
                <div className="tool-status-list">
                    {/* アクティブなツール */}
                    {activeTools.map((event) => {
                        const config = TOOL_DISPLAY_CONFIG[event.tool] || {
                            icon: "🔧",
                            label: event.tool,
                        };
                        return (
                            <div
                                key={`active-${event.tool}`}
                                className="tool-status-item tool-status-active"
                            >
                                <span className="tool-icon">{config.icon}</span>
                                <span className="tool-label">{config.label}</span>
                                <span className="tool-status-badge tool-badge-active">
                                    実行中
                                </span>
                            </div>
                        );
                    })}

                    {/* 完了したツール */}
                    {completedTools.map((event) => {
                        const config = TOOL_DISPLAY_CONFIG[event.tool] || {
                            icon: "🔧",
                            label: event.tool,
                        };
                        return (
                            <div
                                key={`completed-${event.tool}`}
                                className="tool-status-item tool-status-completed"
                            >
                                <span className="tool-icon">{config.icon}</span>
                                <span className="tool-label">{config.label}</span>
                                {event.message && (
                                    <span className="tool-message">{event.message}</span>
                                )}
                            </div>
                        );
                    })}

                    {/* エラーのツール */}
                    {errorTools.map((event) => {
                        const config = TOOL_DISPLAY_CONFIG[event.tool] || {
                            icon: "🔧",
                            label: event.tool,
                        };
                        return (
                            <div
                                key={`error-${event.tool}`}
                                className="tool-status-item tool-status-error"
                            >
                                <span className="tool-icon">{config.icon}</span>
                                <span className="tool-label">{config.label}</span>
                                <span className="tool-status-badge tool-badge-error">
                                    エラー
                                </span>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default ToolStatusIndicator;
