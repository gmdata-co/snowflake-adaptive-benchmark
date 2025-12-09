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
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '6px', padding: '12px 16px', backgroundColor: '#1e293b', borderRadius: '12px', border: '1px solid #334155', height: '100%', boxSizing: 'border-box' }}>
      {/* Progress dots and navigation controls - combined row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', justifyContent: 'center' }}>
        <button
          onClick={onPrev}
          style={{
            padding: '6px',
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

        {/* Progress dots */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          {Array.from({ length: totalCount }).map((_, index) => (
            <button
              key={index}
              onClick={() => onSelect(index)}
              style={{
                width: index === currentIndex ? '10px' : '8px',
                height: index === currentIndex ? '10px' : '8px',
                borderRadius: '50%',
                backgroundColor: index === currentIndex ? 'white' : '#4b5563',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              aria-label={`Go to comparison ${index + 1}`}
            />
          ))}
        </div>

        <button
          onClick={onNext}
          style={{
            padding: '6px',
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

        <button
          onClick={onPlayPause}
          style={{
            padding: '10px',
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
      </div>

      {/* Keyboard hint - hidden on small screens */}
      <p className="keyboard-hint" style={{ fontSize: '9px', color: '#6b7280', margin: 0 }}>
        <kbd style={{ padding: '1px 4px', backgroundColor: '#334155', borderRadius: '3px', color: '#9ca3af', fontSize: '8px' }}>Space</kbd> play/pause{" "}
        <kbd style={{ padding: '1px 4px', backgroundColor: '#334155', borderRadius: '3px', color: '#9ca3af', fontSize: '8px' }}>←</kbd>{" "}
        <kbd style={{ padding: '1px 4px', backgroundColor: '#334155', borderRadius: '3px', color: '#9ca3af', fontSize: '8px' }}>→</kbd> navigate
      </p>
    </div>
  );
}
