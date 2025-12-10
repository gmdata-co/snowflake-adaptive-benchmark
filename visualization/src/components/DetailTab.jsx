import { useMemo } from "react";
import { BenchmarkChart } from "./BenchmarkChart";
import { SpeedTile, CostTile, ScenarioTile } from "./ComparisonCard";
import benchmarkData from "../data/benchmarkData.json";
import { getTimeUnit, convertTime } from "../utils/formatTime";

export function DetailTab() {
  const comparisons = benchmarkData.comparisons;

  // Compute axis domains for each scenario
  const scenarioDomains = useMemo(() => {
    const scenarios = ['normal', 'coldstart', 'concurrent', 'ctas'];
    const domains = {};

    for (const scenario of scenarios) {
      const scenarioComparisons = comparisons.filter(c => c.scenario === scenario);

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

      domains[scenario] = {
        timeUnit: unit,
        xDomain: [0, xMax],
        yDomain: [0, yMax],
      };
    }

    return domains;
  }, [comparisons]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {comparisons.map((comparison) => {
        const { timeUnit, xDomain, yDomain } = scenarioDomains[comparison.scenario];

        return (
          <div
            key={comparison.id}
            style={{
              backgroundColor: '#1e293b',
              borderRadius: '12px',
              padding: '16px',
              border: '1px solid #334155',
            }}
          >
            {/* KPI Tiles Row */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '10px',
              marginBottom: '12px'
            }}>
              <ScenarioTile comparison={comparison} />
              <SpeedTile comparison={comparison} timeUnit={timeUnit} />
              <CostTile comparison={comparison} />
            </div>

            {/* Chart */}
            <BenchmarkChart
              comparison={comparison}
              timeUnit={timeUnit}
              xDomain={xDomain}
              yDomain={yDomain}
            />
          </div>
        );
      })}
    </div>
  );
}
