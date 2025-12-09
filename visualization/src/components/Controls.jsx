import { useCallback, useEffect } from "react";

function PlayIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
    </svg>
  );
}

function ChevronLeft() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

export function Controls({
  currentIndex,
  totalCount,
  isPlaying,
  onPlayPause,
  onNext,
  onPrev,
  onSelect,
}) {
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === " " || e.key === "Spacebar") {
        e.preventDefault();
        onPlayPause();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        onNext();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        onPrev();
      }
    },
    [onPlayPause, onNext, onPrev]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
      {/* Progress dots */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {Array.from({ length: totalCount }).map((_, index) => (
          <button
            key={index}
            onClick={() => onSelect(index)}
            style={{
              width: index === currentIndex ? '14px' : '12px',
              height: index === currentIndex ? '14px' : '12px',
              borderRadius: '50%',
              backgroundColor: index === currentIndex ? 'white' : '#4b5563',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.3s',
            }}
            aria-label={`Go to comparison ${index + 1}`}
          />
        ))}
      </div>

      {/* Navigation controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          onClick={onPrev}
          style={{
            padding: '8px',
            borderRadius: '50%',
            backgroundColor: '#334155',
            border: 'none',
            color: '#9ca3af',
            cursor: 'pointer',
          }}
          aria-label="Previous comparison"
        >
          <ChevronLeft />
        </button>

        <button
          onClick={onPlayPause}
          style={{
            padding: '16px',
            borderRadius: '50%',
            background: isPlaying ? 'white' : 'linear-gradient(to right, #29B5E8, #FF3621)',
            border: 'none',
            color: isPlaying ? '#0f172a' : 'white',
            cursor: 'pointer',
          }}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? <PauseIcon /> : <PlayIcon />}
        </button>

        <button
          onClick={onNext}
          style={{
            padding: '8px',
            borderRadius: '50%',
            backgroundColor: '#334155',
            border: 'none',
            color: '#9ca3af',
            cursor: 'pointer',
          }}
          aria-label="Next comparison"
        >
          <ChevronRight />
        </button>
      </div>

      {/* Keyboard hint */}
      <p style={{ fontSize: '12px', color: '#6b7280' }}>
        Press <kbd style={{ padding: '2px 6px', backgroundColor: '#334155', borderRadius: '4px', color: '#9ca3af' }}>Space</kbd> to play/pause,{" "}
        <kbd style={{ padding: '2px 6px', backgroundColor: '#334155', borderRadius: '4px', color: '#9ca3af' }}>←</kbd>{" "}
        <kbd style={{ padding: '2px 6px', backgroundColor: '#334155', borderRadius: '4px', color: '#9ca3af' }}>→</kbd> to navigate
      </p>
    </div>
  );
}
