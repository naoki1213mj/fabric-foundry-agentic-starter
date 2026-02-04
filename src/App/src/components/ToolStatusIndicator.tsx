import { Spinner, mergeStyles, useTheme } from "@fluentui/react";
import React from "react";
import { TOOL_DISPLAY_CONFIG, ToolEvent } from "../types/AppTypes";
import "./ToolStatusIndicator.css";

interface ToolStatusIndicatorProps {
    toolEvents: ToolEvent[];
    className?: string;
}

/**
 * ツール使用状況を表示するコンポーネント
 * エージェントが使用中のツールをリアルタイムで表示
 */
export const ToolStatusIndicator: React.FC<ToolStatusIndicatorProps> = ({
    toolEvents,
    className = "",
}) => {
    const theme = useTheme();

    // 最新の状態を取得（同じツールは最新のイベントのみ表示）
    const latestEvents = React.useMemo(() => {
        const eventMap = new Map<string, ToolEvent>();
        toolEvents.forEach((event) => {
            eventMap.set(event.tool, event);
        });
        return Array.from(eventMap.values());
    }, [toolEvents]);

    // アクティブなツール（started状態）のみ表示
    const activeTools = latestEvents.filter((e) => e.status === "started");
    // 完了したツール
    const completedTools = latestEvents.filter((e) => e.status === "completed");

    if (activeTools.length === 0 && completedTools.length === 0) {
        return null;
    }

    const containerClass = mergeStyles({
        backgroundColor: theme.palette.neutralLighter,
        borderRadius: "8px",
        padding: "8px 12px",
        marginBottom: "8px",
    });

    return (
        <div className={`tool-status-container ${className} ${containerClass}`}>
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
                        <span className="tool-label">{config.label}...</span>
                        <Spinner
                            size={0}
                            className="tool-spinner"
                            aria-label={`${config.label} 実行中`}
                        />
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
                        <span className="tool-icon">✅</span>
                        <span className="tool-label tool-label-completed">
                            {config.label} 完了
                        </span>
                        {event.message && (
                            <span className="tool-message">({event.message})</span>
                        )}
                    </div>
                );
            })}
        </div>
    );
};

export default ToolStatusIndicator;
