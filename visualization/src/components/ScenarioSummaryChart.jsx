import { useMemo } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { SnowflakeLogo } from "./SnowflakeLogo";
import { DatabricksLogo } from "./DatabricksLogo";
import snowflakeLogo from "../assets/snowflake-logo.png";
import databricksLogo from "../assets/databricks-logo.png";
import { formatTime, convertTime, getUnitSuffix, getTimeUnit } from "../utils/formatTime";

// Size abbreviations for labels
const sizeAbbrev = {
  SMALL: "S",
  MEDIUM: "M",
  LARGE: "L",
  XLARGE: "XL",
};

// Custom shape with logo and size label
function CustomScatterShape({ cx, cy, payload, hoveredTier }) {
  const isHovered = hoveredTier === payload.tier;
  const isDimmed = hoveredTier !== null && !isHovered;

  const baseSize = 32;
  const size = isHovered ? 44 : baseSize;
  const opacity = isDimmed ? 0.3 : 1;

  const logoSrc = payload.platform === "snowflake" ? snowflakeLogo : databricksLogo;
  const labelColor = payload.platform === "snowflake" ? "#29B5E8" : "#FF3621";
  const sizeLabel = sizeAbbrev[payload.size] || payload.size;

  return (
    <g opacity={opacity} style={{ transition: 'opacity 0.2s ease' }}>
      <image
        x={cx - size / 2}
        y={cy - size / 2}
        width={size}
        height={size}
        href={logoSrc}
        style={{ transition: 'all 0.2s ease' }}
      />
      <text
        x={cx}
        y={cy - size / 2 - 6}
        textAnchor="middle"
        fill={labelColor}
        fontSize={isHovered ? 13 : 11}
        fontWeight="700"
        style={{ transition: 'font-size 0.2s ease' }}
      >
        {sizeLabel}
      </text>
    </g>
  );
}

function formatDiff(snowValue, dbxValue, isTime = false) {
  // Handle missing platform data
  if (snowValue == null || dbxValue == null) {
    return { text: "", winner: null, noComparison: true };
  }
  if (isTime) {
    if (dbxValue > snowValue) {
      const percentFaster = (((dbxValue - snowValue) / dbxValue) * 100).toFixed(0);
      return { text: `${percentFaster}% faster`, winner: "snowflake" };
    } else if (snowValue > dbxValue) {
      const percentFaster = (((snowValue - dbxValue) / snowValue) * 100).toFixed(0);
      return { text: `${percentFaster}% faster`, winner: "databricks" };
    }
    return { text: "Same speed", winner: null };
  } else {
    if (dbxValue > snowValue) {
      const percentCheaper = (((dbxValue - snowValue) / dbxValue) * 100).toFixed(0);
      return { text: `${percentCheaper}% cheaper`, winner: "snowflake" };
    } else if (snowValue > dbxValue) {
      const percentCheaper = (((snowValue - dbxValue) / snowValue) * 100).toFixed(0);
      return { text: `${percentCheaper}% cheaper`, winner: "databricks" };
    }
    return { text: "Same cost", winner: null };
  }
}

// Enhanced tooltip with fade-in and winner conclusion
function ComparisonTooltip({ active, payload, timeUnit, scenarioData }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const tier = data.tier;

    // Find the comparison for this tier
    const comparison = scenarioData.find(c => c.warehouseTier === tier);
    if (!comparison) return null;

    const hasSnowflake = comparison.snowflake != null;
    const hasDatabricks = comparison.databricks != null;
    const hasBoth = hasSnowflake && hasDatabricks;

    const speedDiff = formatDiff(comparison.snowflake?.time, comparison.databricks?.time, true);
    const costDiff = formatDiff(comparison.snowflake?.cost, comparison.databricks?.cost, false);

    // Build header text
    let headerText;
    if (hasBoth) {
      headerText = `${comparison.snowflake.size} vs ${comparison.databricks.size}`;
    } else if (hasSnowflake) {
      headerText = `Snowflake ${comparison.snowflake.size}`;
    } else {
      headerText = `Databricks ${comparison.databricks.size}`;
    }

    return (
      <div style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: '8px',
        padding: '12px',
        boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
        minWidth: '220px',
        animation: 'fadeIn 0.15s ease-out',
      }}>
        <style>{`
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
        `}</style>

        <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '10px', textAlign: 'center', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
          {headerText}
        </div>

        {/* Snowflake Row */}
        {hasSnowflake && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: hasDatabricks ? '8px' : '0' }}>
            <SnowflakeLogo size={20} />
            <div style={{ flex: 1 }}>
              <div style={{ color: '#29B5E8', fontWeight: '600', fontSize: '13px' }}>{comparison.snowflake.size}</div>
              <div style={{ color: '#94a3b8', fontSize: '12px' }}>
                {formatTime(comparison.snowflake.time, timeUnit)} / ${(comparison.snowflake.cost ?? 0).toFixed(2)}
              </div>
            </div>
          </div>
        )}

        {/* Databricks Row */}
        {hasDatabricks && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: hasBoth ? '10px' : '0' }}>
            <DatabricksLogo size={20} />
            <div style={{ flex: 1 }}>
              <div style={{ color: '#FF3621', fontWeight: '600', fontSize: '13px' }}>{comparison.databricks.size}</div>
              <div style={{ color: '#94a3b8', fontSize: '12px' }}>
                {formatTime(comparison.databricks.time, timeUnit)} / ${(comparison.databricks.cost ?? 0).toFixed(2)}
              </div>
            </div>
          </div>
        )}

        {/* Winner Conclusion - only show if both platforms exist */}
        {hasBoth && !speedDiff.noComparison && (
          <div style={{ borderTop: '1px solid #334155', paddingTop: '10px', fontSize: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ color: '#9ca3af' }}>Speed:</span>
              <span style={{ color: speedDiff.winner === 'snowflake' ? '#29B5E8' : speedDiff.winner === 'databricks' ? '#FF3621' : '#9ca3af', fontWeight: '600' }}>
                {speedDiff.winner ? `${speedDiff.winner === 'snowflake' ? 'Snowflake' : 'Databricks'} ${speedDiff.text}` : speedDiff.text}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#9ca3af' }}>Cost:</span>
              <span style={{ color: costDiff.winner === 'snowflake' ? '#29B5E8' : costDiff.winner === 'databricks' ? '#FF3621' : '#9ca3af', fontWeight: '600' }}>
                {costDiff.winner ? `${costDiff.winner === 'snowflake' ? 'Snowflake' : 'Databricks'} ${costDiff.text}` : costDiff.text}
              </span>
            </div>
          </div>
        )}
      </div>
    );
  }
  return null;
}

export function ScenarioSummaryChart({ scenarioData, hoveredTier, onHoverTier }) {
  // Compute time unit and domains from all data points
  const { timeUnit, xDomain, yDomain, chartData } = useMemo(() => {
    let maxTime = 0;
    let maxCost = 0;

    const data = [];
    for (const comparison of scenarioData) {
      // Only include platforms that have data
      if (comparison.snowflake) {
        maxTime = Math.max(maxTime, comparison.snowflake.time || 0);
        maxCost = Math.max(maxCost, comparison.snowflake.cost || 0);

        data.push({
          platform: "snowflake",
          tier: comparison.warehouseTier,
          size: comparison.snowflake.size,
          label: comparison.snowflake.label,
          time: comparison.snowflake.time,
          cost: comparison.snowflake.cost,
        });
      }

      if (comparison.databricks) {
        maxTime = Math.max(maxTime, comparison.databricks.time || 0);
        maxCost = Math.max(maxCost, comparison.databricks.cost || 0);

        data.push({
          platform: "databricks",
          tier: comparison.warehouseTier,
          size: comparison.databricks.size,
          label: comparison.databricks.label,
          time: comparison.databricks.time,
          cost: comparison.databricks.cost,
        });
      }
    }

    const unit = getTimeUnit(maxTime);
    const maxTimeInUnit = convertTime(maxTime, unit);
    const xMax = Math.ceil(maxTimeInUnit * 1.1);
    const yMax = Math.ceil(maxCost * 1.2 * 10) / 10;

    // Add displayTime for chart positioning
    const chartDataWithDisplay = data.map(d => ({
      ...d,
      displayTime: convertTime(d.time, unit),
    }));

    return {
      timeUnit: unit,
      xDomain: [0, xMax],
      yDomain: [0, yMax],
      chartData: chartDataWithDisplay,
    };
  }, [scenarioData]);

  const unitSuffix = getUnitSuffix(timeUnit);

  return (
    <div style={{ width: '100%', height: '500px' }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 40, right: 30, bottom: 35, left: 50 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="#334155"
          opacity={0.5}
        />
        <XAxis
          type="number"
          dataKey="displayTime"
          domain={xDomain}
          name="Duration"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          axisLine={{ stroke: "#475569" }}
          tickLine={{ stroke: "#475569" }}
          tickFormatter={(value) => `${Math.round(value)}${unitSuffix}`}
          label={{
            value: `Duration (${unitSuffix === 's' ? 'seconds' : unitSuffix === 'min' ? 'minutes' : 'hours'})`,
            position: "bottom",
            offset: 10,
            fill: "#94a3b8",
            fontSize: 14,
          }}
        />
        <YAxis
          type="number"
          dataKey="cost"
          domain={yDomain}
          name="Cost"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          axisLine={{ stroke: "#475569" }}
          tickLine={{ stroke: "#475569" }}
          tickFormatter={(value) => `$${value.toFixed(2)}`}
          width={55}
          label={{
            value: "Cost (USD)",
            angle: -90,
            position: "insideLeft",
            offset: -5,
            fill: "#94a3b8",
            fontSize: 14,
            style: { textAnchor: "middle" },
          }}
        />
        <Tooltip
          content={<ComparisonTooltip timeUnit={timeUnit} scenarioData={scenarioData} />}
          cursor={{ strokeDasharray: "3 3", stroke: "#64748b" }}
          isAnimationActive={false}
        />
        <Scatter
          data={chartData}
          shape={(props) => <CustomScatterShape {...props} hoveredTier={hoveredTier} />}
          onMouseEnter={(data) => onHoverTier(data.tier)}
          onMouseLeave={() => onHoverTier(null)}
        />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
