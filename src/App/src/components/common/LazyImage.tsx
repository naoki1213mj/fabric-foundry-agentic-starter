import React, { memo, useEffect, useRef, useState } from 'react';

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  style?: React.CSSProperties;
  placeholderSrc?: string;
  threshold?: number;
  rootMargin?: string;
}

/**
 * Lazy loading image component using IntersectionObserver
 * Images are only loaded when they enter the viewport
 */
export const LazyImage: React.FC<LazyImageProps> = memo(({
  src,
  alt,
  className = '',
  style = {},
  placeholderSrc,
  threshold = 0.1,
  rootMargin = '100px'
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const [error, setError] = useState(false);
  const imgRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            observer.disconnect();
          }
        });
      },
      {
        threshold,
        rootMargin,
      }
    );

    const currentRef = imgRef.current;
    if (currentRef) {
      observer.observe(currentRef);
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef);
      }
    };
  }, [threshold, rootMargin]);

  const handleLoad = () => {
    setIsLoaded(true);
  };

  const handleError = () => {
    setError(true);
    setIsLoaded(true);
  };

  const placeholderStyle: React.CSSProperties = {
    backgroundColor: 'var(--bg-secondary, #f1f5f9)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100px',
    borderRadius: '8px',
    ...style,
  };

  const imageStyle: React.CSSProperties = {
    opacity: isLoaded ? 1 : 0,
    transition: 'opacity 0.3s ease-in-out',
    ...style,
  };

  const shimmerStyle: React.CSSProperties = {
    background: 'linear-gradient(90deg, var(--bg-tertiary, #e2e8f0) 25%, var(--bg-secondary, #f1f5f9) 50%, var(--bg-tertiary, #e2e8f0) 75%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.5s infinite',
  };

  if (error) {
    return (
      <div
        ref={imgRef}
        className={`lazy-image-error ${className}`}
        style={placeholderStyle}
        role="img"
        aria-label={`画像の読み込みに失敗: ${alt}`}
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{ color: 'var(--text-secondary, #94a3b8)' }}
        >
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <path d="M21 15l-5-5L5 21" />
        </svg>
      </div>
    );
  }

  return (
    <div
      ref={imgRef}
      className={`lazy-image-container ${className}`}
      style={{ position: 'relative', ...style }}
    >
      {/* Loading skeleton */}
      {!isLoaded && (
        <div
          className="lazy-image-placeholder"
          style={{
            ...placeholderStyle,
            ...shimmerStyle,
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
          }}
        />
      )}

      {/* Placeholder image (optional low-res preview) */}
      {placeholderSrc && !isLoaded && isInView && (
        <img
          src={placeholderSrc}
          alt=""
          style={{
            ...style,
            filter: 'blur(10px)',
            position: 'absolute',
            top: 0,
            left: 0,
          }}
          aria-hidden="true"
        />
      )}

      {/* Main image - only load when in view */}
      {isInView && (
        <img
          src={src}
          alt={alt}
          className={className}
          style={imageStyle}
          onLoad={handleLoad}
          onError={handleError}
          loading="lazy"
        />
      )}

      <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
});

LazyImage.displayName = 'LazyImage';

export default LazyImage;
