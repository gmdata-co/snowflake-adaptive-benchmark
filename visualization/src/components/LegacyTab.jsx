import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { BenchmarkChart } from "./BenchmarkChart";
import { Controls } from "./Controls";
import { SpeedTile, CostTile, ScenarioTile } from "./ComparisonCard";
import benchmarkData from "../data/benchmarkData.json";
import { getTimeUnit, convertTime } from "../utils/formatTime";

const CYCLE_INTERVAL = 4000;

export function LegacyTab() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const intervalRef = useRef(null);

  const comparisons = benchmarkData.comparisons;
  const currentComparison = comparisons[currentIndex];

  const { timeUnit, xDomain, yDomain } = useMemo(() => {
    if (!currentComparison) {
      return { timeUnit: 'seconds', xDomain: [0, 1000], yDomain: [0, 5] };
    }

    const scenarioComparisons = comparisons.filter(
      (c) => c.scenario === currentComparison.scenario
    );

    let maxTime = 0;
    let maxCost = 0;
    for (const c of scenarioComparisons) {
      maxTime = Math.max(maxTime, c.snowflake.time || 0, c.databricks.time || 0);
      maxCost = Math.max(maxCost, c.snowflake.cost || 0, c.databricks.cost || 0);
    }

    const unit = getTimeUnit(maxTime);
    const maxTimeInUnit = convertTime(maxTime, unit);
    const xMax = Math.ceil(maxTimeInUnit * 1.1);
    const yMax = Math.ceil(maxCost * 1.2 * 10) / 10;

    return {
      timeUnit: unit,
      xDomain: [0, xMax],
      yDomain: [0, yMax],
    };
  }, [currentComparison, comparisons]);

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
    <div>
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
          <SpeedTile comparison={currentComparison} timeUnit={timeUnit} />
        </div>
        <div className="cost-tile">
          <CostTile comparison={currentComparison} />
        </div>
      </div>

      <div
        style={{ backgroundColor: '#1e293b', borderRadius: '12px', padding: '12px', border: '1px solid #334155' }}
        onMouseEnter={handleChartHover}
        onMouseLeave={() => isPlaying && startAutoPlay()}
      >
        <BenchmarkChart
          comparison={currentComparison}
          onHover={handleChartHover}
          timeUnit={timeUnit}
          xDomain={xDomain}
          yDomain={yDomain}
        />
      </div>
    </div>
  );
}
