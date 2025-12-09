import { useState, useEffect, useCallback, useRef } from "react";
import { SnowflakeLogo } from "./components/SnowflakeLogo";
import { DatabricksLogo } from "./components/DatabricksLogo";
import { BenchmarkChart } from "./components/BenchmarkChart";
import { Controls } from "./components/Controls";
import { ComparisonCard } from "./components/ComparisonCard";
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
      <div style={{ maxWidth: '1024px', margin: '0 auto', padding: '32px 16px' }}>
        {/* Header */}
        <header style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold', marginBottom: '8px', background: 'linear-gradient(to right, #29B5E8, #FF3621)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Snowflake vs Databricks
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '1.125rem' }}>
            TPC-H Benchmark Performance Comparison
          </p>
        </header>

        {/* Legend */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '32px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <SnowflakeLogo size={28} />
            <span style={{ color: '#29B5E8', fontWeight: '500' }}>Snowflake</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <DatabricksLogo size={28} />
            <span style={{ color: '#FF3621', fontWeight: '500' }}>Databricks</span>
          </div>
        </div>

        {/* Comparison details */}
        <div style={{ marginBottom: '24px' }}>
          <ComparisonCard comparison={currentComparison} />
        </div>

        {/* Big Chart Title */}
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <h2 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: 'white' }}>
            {currentComparison.scenarioLabel}
          </h2>
          <p style={{ fontSize: '1.25rem', color: '#9ca3af', marginTop: '4px' }}>
            {currentComparison.snowflake.label} vs {currentComparison.databricks.label}
          </p>
        </div>

        {/* Chart */}
        <div
          style={{ backgroundColor: '#1e293b', borderRadius: '16px', padding: '16px', marginBottom: '24px', border: '1px solid #334155' }}
          onMouseEnter={handleChartHover}
          onMouseLeave={() => isPlaying && startAutoPlay()}
        >
          <BenchmarkChart
            comparison={currentComparison}
            onHover={handleChartHover}
          />
        </div>

        {/* Controls */}
        <Controls
          currentIndex={currentIndex}
          totalCount={comparisons.length}
          isPlaying={isPlaying}
          onPlayPause={handlePlayPause}
          onNext={handleNext}
          onPrev={handlePrev}
          onSelect={handleSelect}
        />

        {/* Footer */}
        <footer style={{ textAlign: 'center', marginTop: '32px', color: '#6b7280', fontSize: '0.875rem' }}>
          <p>
            Data exported:{" "}
            {new Date(benchmarkData.exportedAt).toLocaleDateString()}
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
