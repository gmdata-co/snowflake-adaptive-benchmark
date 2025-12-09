import { useState, useEffect, useCallback, useRef } from "react";
import { BenchmarkChart } from "./components/BenchmarkChart";
import { Controls } from "./components/Controls";
import { SpeedTile, CostTile, ScenarioTile } from "./components/ComparisonCard";
import benchmarkData from "./data/benchmarkData.json";

const CYCLE_INTERVAL = 4000;

function App() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const intervalRef = useRef(null);

  const comparisons = benchmarkData.comparisons;
  const currentComparison = comparisons[currentIndex];

  const startAutoPlay = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    intervalRef.current = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % comparisons.length);
    }, CYCLE_INTERVAL);
  }, [comparisons.length]);

  const stopAutoPlay = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (isPlaying) {
      startAutoPlay();
    } else {
      stopAutoPlay();
    }
    return () => stopAutoPlay();
  }, [isPlaying, startAutoPlay, stopAutoPlay]);

  const handlePlayPause = useCallback(() => {
    setIsPlaying((prev) => !prev);
  }, []);

  const handleNext = useCallback(() => {
    setCurrentIndex((prev) => (prev + 1) % comparisons.length);
    if (isPlaying) {
      startAutoPlay();
    }
  }, [comparisons.length, isPlaying, startAutoPlay]);

  const handlePrev = useCallback(() => {
    setCurrentIndex((prev) =>
      prev === 0 ? comparisons.length - 1 : prev - 1
    );
    if (isPlaying) {
      startAutoPlay();
    }
  }, [comparisons.length, isPlaying, startAutoPlay]);

  const handleSelect = useCallback(
    (index) => {
      setCurrentIndex(index);
      if (isPlaying) {
        startAutoPlay();
      }
    },
    [isPlaying, startAutoPlay]
  );

  const handleChartHover = useCallback(() => {
    if (isPlaying) {
      stopAutoPlay();
    }
  }, [isPlaying, stopAutoPlay]);

  if (!currentComparison) {
    return <div style={{ color: 'white', padding: '20px' }}>Loading...</div>;
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#0f172a', color: 'white' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '12px 16px 8px' }}>
        {/* Header */}
        <header style={{ textAlign: 'center', marginBottom: '10px' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '2px', backgroundImage: 'linear-gradient(to right, #00D4FF 0%, #00D4FF 35%, #FF3621 65%, #FF3621 100%)', WebkitBackgroundClip: 'text', backgroundClip: 'text', WebkitTextFillColor: 'transparent', color: 'transparent' }}>
            Snowflake vs Databricks
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '0.75rem' }}>
            TPC-H Benchmark Performance Comparison
          </p>
        </header>

        {/* 3-tile row: Controls (mobile: top), Scenario, Speed, Cost */}
        <div className="tiles-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '12px' }}>
          <div className="controls-tile">
            <Controls
              currentIndex={currentIndex}
              totalCount={comparisons.length}
              isPlaying={isPlaying}
              onPlayPause={handlePlayPause}
              onNext={handleNext}
              onPrev={handlePrev}
              onSelect={handleSelect}
            />
          </div>
          <div className="scenario-tile">
            <ScenarioTile comparison={currentComparison} />
          </div>
          <div className="speed-tile">
            <SpeedTile comparison={currentComparison} />
          </div>
          <div className="cost-tile">
            <CostTile comparison={currentComparison} />
          </div>
        </div>

        {/* Chart - full width below */}
        <div
          style={{ backgroundColor: '#1e293b', borderRadius: '12px', padding: '12px', border: '1px solid #334155' }}
          onMouseEnter={handleChartHover}
          onMouseLeave={() => isPlaying && startAutoPlay()}
        >
          <BenchmarkChart
            comparison={currentComparison}
            onHover={handleChartHover}
          />
        </div>

        {/* Footer */}
        <footer style={{ textAlign: 'center', marginTop: '8px', color: '#6b7280', fontSize: '0.7rem' }}>
          <p style={{ margin: 0 }}>
            Data exported:{" "}
            {new Date(benchmarkData.exportedAt).toLocaleDateString()}
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
