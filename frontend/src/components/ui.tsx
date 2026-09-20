import React from "react";

interface SkeletonProps {
  className?: string;
  lines?: number;
  height?: string;
}

/**
 * Animated skeleton loader for use while content is loading.
 * Renders one or more pulsing placeholder lines.
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  className = "",
  lines = 1,
  height = "1rem",
}) => {
  return (
    <div className={`skeleton-container ${className}`} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton-line"
          style={{
            height,
            width: i === lines - 1 && lines > 1 ? "70%" : "100%",
          }}
        />
      ))}
    </div>
  );
};

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
}

/**
 * Centered loading spinner with optional label.
 */
export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  label = "Analyzing your data…",
}) => {
  const sizeMap = { sm: 20, md: 36, lg: 56 };
  const px = sizeMap[size];

  return (
    <div className="loading-spinner-wrapper" role="status" aria-live="polite">
      <svg
        width={px}
        height={px}
        viewBox="0 0 50 50"
        className="spinner-svg"
        aria-hidden="true"
      >
        <circle
          cx="25"
          cy="25"
          r="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray="90 150"
          strokeDashoffset="0"
          className="spinner-circle"
        />
      </svg>
      {label && <span className="spinner-label">{label}</span>}
    </div>
  );
};

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

/**
 * Empty state placeholder for when no data is present.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon = "📊",
  title,
  description,
  action,
}) => {
  return (
    <div className="empty-state">
      <div className="empty-state-icon" aria-hidden="true">
        {icon}
      </div>
      <h3 className="empty-state-title">{title}</h3>
      {description && (
        <p className="empty-state-description">{description}</p>
      )}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info";
}

/**
 * Small inline badge / chip for status labels.
 */
export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "default",
}) => {
  return (
    <span className={`badge badge--${variant}`} role="status">
      {children}
    </span>
  );
};

interface TooltipProps {
  children: React.ReactNode;
  content: string;
  position?: "top" | "bottom" | "left" | "right";
}

/**
 * Simple CSS-only tooltip wrapper.
 */
export const Tooltip: React.FC<TooltipProps> = ({
  children,
  content,
  position = "top",
}) => {
  return (
    <span
      className={`tooltip-wrapper tooltip--${position}`}
      data-tooltip={content}
    >
      {children}
    </span>
  );
};
