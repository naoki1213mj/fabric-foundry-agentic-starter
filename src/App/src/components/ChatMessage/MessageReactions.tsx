import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import "./MessageReactions.css";

export type ReactionType = "thumbsUp" | "thumbsDown" | null;

interface MessageReactionsProps {
  messageId?: string;
  onReaction?: (reaction: ReactionType) => void;
  className?: string;
}

/**
 * Message reactions component with thumbs up/down buttons
 * Allows users to provide feedback on AI responses
 */
export const MessageReactions: React.FC<MessageReactionsProps> = ({
  messageId,
  onReaction,
  className = "",
}) => {
  const { t } = useTranslation();
  const [selectedReaction, setSelectedReaction] = useState<ReactionType>(null);
  const [isAnimating, setIsAnimating] = useState<ReactionType>(null);

  const handleReaction = (reaction: ReactionType) => {
    // Toggle off if clicking the same reaction
    const newReaction = selectedReaction === reaction ? null : reaction;
    setSelectedReaction(newReaction);
    setIsAnimating(reaction);

    // Trigger animation reset
    setTimeout(() => setIsAnimating(null), 300);

    // Callback for parent component
    if (onReaction) {
      onReaction(newReaction);
    }

    // TODO: Send reaction to API for analytics
    // Reaction tracking will be handled via Application Insights
  };

  return (
    <div className={`message-reactions ${className}`}>
      <button
        className={`reaction-btn ${selectedReaction === "thumbsUp" ? "active" : ""} ${isAnimating === "thumbsUp" ? "animating" : ""}`}
        onClick={() => handleReaction("thumbsUp")}
        title={t("reaction.helpful") || "役に立った"}
        aria-label={t("reaction.helpful") || "Mark as helpful"}
        aria-pressed={selectedReaction === "thumbsUp"}
      >
        <span className="reaction-icon">👍</span>
      </button>
      <button
        className={`reaction-btn ${selectedReaction === "thumbsDown" ? "active" : ""} ${isAnimating === "thumbsDown" ? "animating" : ""}`}
        onClick={() => handleReaction("thumbsDown")}
        title={t("reaction.notHelpful") || "役に立たなかった"}
        aria-label={t("reaction.notHelpful") || "Mark as not helpful"}
        aria-pressed={selectedReaction === "thumbsDown"}
      >
        <span className="reaction-icon">👎</span>
      </button>
    </div>
  );
};

export default MessageReactions;
