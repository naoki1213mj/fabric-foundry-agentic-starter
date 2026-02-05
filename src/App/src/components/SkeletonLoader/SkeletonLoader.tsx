import React from "react";
import "./SkeletonLoader.css";

interface SkeletonLoaderProps {
  variant?: "text" | "circle" | "rectangle";
  width?: string | number;
  height?: string | number;
  lines?: number;
  className?: string;
}

/**
 * Skeleton loader component for loading states
 * Displays animated placeholder content while data is loading
 */
export const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  variant = "text",
  width,
  height,
  lines = 1,
  className = "",
}) => {
  const getStyle = (): React.CSSProperties => {
    const style: React.CSSProperties = {};
    if (width) style.width = typeof width === "number" ? `${width}px` : width;
    if (height) style.height = typeof height === "number" ? `${height}px` : height;
    return style;
  };

  if (variant === "text" && lines > 1) {
    return (
      <div className={`skeleton-container ${className}`}>
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={`skeleton skeleton-text ${index === lines - 1 ? "skeleton-text-short" : ""}`}
            style={getStyle()}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`skeleton skeleton-${variant} ${className}`}
      style={getStyle()}
    />
  );
};

/**
 * Skeleton for chat message loading state
 */
export const MessageSkeleton: React.FC<{ isUser?: boolean }> = ({ isUser = false }) => {
  return (
    <div className={`message-skeleton ${isUser ? "message-skeleton-user" : "message-skeleton-assistant"}`}>
      {!isUser && (
        <div className="message-skeleton-avatar">
          <SkeletonLoader variant="circle" width={32} height={32} />
        </div>
      )}
      <div className="message-skeleton-content">
        <SkeletonLoader variant="text" lines={isUser ? 1 : 3} />
      </div>
    </div>
  );
};

/**
 * Skeleton for thinking/processing state
 */
export const ThinkingSkeleton: React.FC = () => {
  return (
    <div className="thinking-skeleton">
      <div className="thinking-skeleton-header">
        <SkeletonLoader variant="circle" width={32} height={32} />
        <SkeletonLoader variant="text" width="120px" />
      </div>
      <div className="thinking-skeleton-body">
        <div className="thinking-dots">
          <span className="thinking-dot" />
          <span className="thinking-dot" />
          <span className="thinking-dot" />
        </div>
        <SkeletonLoader variant="text" lines={2} />
      </div>
    </div>
  );
};

export default SkeletonLoader;
