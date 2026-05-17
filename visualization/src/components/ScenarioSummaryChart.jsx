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
import { Gen1Logo, GEN1_COLOR } from "./Gen1Logo";
import { AdaptiveLogo, ADAPTIVE_COLOR } from "./AdaptiveLogo";
import { formatTime, convertTime, getUnitSuffix, getTimeUnit } from "../utils/formatTime";

// `gen1` key = Gen1 results, `adaptive` key = Adaptive results.
const GEN1 = "gen1";
const ADAPTIVE = "adaptive";
const platformColor = (p) => (p === GEN1 ? GEN1_COLOR : ADAPTIVE_COLOR);
const platformName = (p) => (p === GEN1 ? "Gen1" : "Adaptive");

// Size abbreviations for labels
const sizeAbbrev = {
  XSMALL: "XS",
  SMALL: "S",
  MEDIUM: "M",
  LARGE: "L",
  XLARGE: "XL",
};

// Custom shape with logo and size label
function CustomScatterShape({ cx, cy, payload, hoveredTier }) {
  const isHovered = hoveredTier === payload.tier;
  const isDimmed = hoveredTier !== null && !isHovered;

  const baseR = 13;
  const r = isHovered ? 18 : baseR;
  const opacity = isDimmed ? 0.3 : 1;

  const color = platformColor(payload.platform);
  const sizeLabel = sizeAbbrev[payload.size] || payload.size;

  return (
    <g opacity={opacity} style={{ transition: 'opacity 0.2s ease' }}>
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill={color}
        stroke="#0f172a"
        strokeWidth={2}
        style={{ transition: 'all 0.2s ease' }}
      />
      <text
        x={cx}
        y={cy}
        textAnchor="middle"
        dominantBaseline="central"
        fill="#0f172a"
        fontSize={isHovered ? 13 : 11}
        fontWeight="800"
        style={{ transition: 'font-size 0.2s ease' }}
      >
        {sizeLabel}
      </text>
      <text
        x={cx}
        y={cy - r - 6}
        textAnchor="middle"
        fill={color}
        fontSize={isHovered ? 12 : 10}
        fontWeight="700"
        style={{ transition: 'font-size 0.2s ease' }}
      >
        {platformName(payload.platform)}
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
      return { text: `${percentFaster}% faster`, winner: "gen1" };
    } else if (snowValue > dbxValue) {
      const percentFaster = (((snowValue - dbxValue) / snowValue) * 100).toFixed(0);
      return { text: `${percentFaster}% faster`, winner: "adaptive" };
    }
    return { text: "Same speed", winner: null };
  } else {
    if (dbxValue > snowValue) {
      const percentCheaper = (((dbxValue - snowValue) / dbxValue) * 100).toFixed(0);
      return { text: `${percentCheaper}% cheaper`, winner: "gen1" };
    } else if (snowValue > dbxValue) {
      const percentCheaper = (((snowValue - dbxValue) / snowValue) * 100).toFixed(0);
      return { text: `${percentCheaper}% cheaper`, winner: "adaptive" };
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

    const hasGen1 = comparison.gen1 != null;
    const hasAdaptive = comparison.adaptive != null;
    const hasBoth = hasGen1 && hasAdaptive;

    const speedDiff = formatDiff(comparison.gen1?.time, comparison.adaptive?.time, true);
    const costDiff = formatDiff(comparison.gen1?.cost, comparison.adaptive?.cost, false);

    // Build header text
    let headerText;
    if (hasBoth) {
      headerText = `${comparison.gen1.size} vs ${comparison.adaptive.size}`;
    } else if (hasGen1) {
      headerText = `Gen1 ${comparison.gen1.size}`;
    } else {
      headerText = `Adaptive ${comparison.adaptive.size}`;
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

        {/* Gen1 Row */}
        {hasGen1 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: hasAdaptive ? '8px' : '0' }}>
            <Gen1Logo size={20} />
            <div style={{ flex: 1 }}>
              <div style={{ color: GEN1_COLOR, fontWeight: '600', fontSize: '13px' }}>Gen1 {comparison.gen1.size}</div>
              <div style={{ color: '#94a3b8', fontSize: '12px' }}>
                {formatTime(comparison.gen1.time, timeUnit)} / ${(comparison.gen1.cost ?? 0).toFixed(2)}
              </div>
            </div>
          </div>
        )}

        {/* Adaptive Row */}
        {hasAdaptive && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: hasBoth ? '10px' : '0' }}>
            <AdaptiveLogo size={20} />
            <div style={{ flex: 1 }}>
              <div style={{ color: ADAPTIVE_COLOR, fontWeight: '600', fontSize: '13px' }}>Adaptive {comparison.adaptive.size}</div>
              <div style={{ color: '#94a3b8', fontSize: '12px' }}>
                {formatTime(comparison.adaptive.time, timeUnit)} / ${(comparison.adaptive.cost ?? 0).toFixed(2)}
              </div>
            </div>
          </div>
        )}

        {/* Winner Conclusion - only show if both platforms exist */}
        {hasBoth && !speedDiff.noComparison && (
          <div style={{ borderTop: '1px solid #334155', paddingTop: '10px', fontSize: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ color: '#9ca3af' }}>Speed:</span>
              <span style={{ color: speedDiff.winner === 'gen1' ? GEN1_COLOR : speedDiff.winner === 'adaptive' ? ADAPTIVE_COLOR : '#9ca3af', fontWeight: '600' }}>
                {speedDiff.winner ? `${speedDiff.winner === 'gen1' ? 'Gen1' : 'Adaptive'} ${speedDiff.text}` : speedDiff.text}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#9ca3af' }}>Cost:</span>
              <span style={{ color: costDiff.winner === 'gen1' ? GEN1_COLOR : costDiff.winner === 'adaptive' ? ADAPTIVE_COLOR : '#9ca3af', fontWeight: '600' }}>
                {costDiff.winner ? `${costDiff.winner === 'gen1' ? 'Gen1' : 'Adaptive'} ${costDiff.text}` : costDiff.text}
              </span>
            </div>
          </div>
        )}
      </div>
    );
  }
  return null;
}

export function ScenarioSummaryChart({
  scenarioData,
  domainData,
  hoveredTier,
  onHoverTier,
}) {
  // Axes/time-unit are derived from domainData (the union of BOTH idle
  // policies for this panel) so flipping the toggle never rebuilds the
  // axes — only the plotted dots move. Falls back to scenarioData when no
  // domain source is supplied. Points themselves come from scenarioData
  // (the active policy).
  const { timeUnit, xDomain, yDomain, chartData } = useMemo(() => {
    const domainSrc =
      domainData && domainData.length ? domainData : scenarioData;

    let maxTime = 0;
    let maxCost = 0;
    for (const comparison of domainSrc) {
      if (comparison.gen1) {
        maxTime = Math.max(maxTime, comparison.gen1.time || 0);
        maxCost = Math.max(maxCost, comparison.gen1.cost || 0);
      }
      if (comparison.adaptive) {
        maxTime = Math.max(maxTime, comparison.adaptive.time || 0);
        maxCost = Math.max(maxCost, comparison.adaptive.cost || 0);
      }
    }

    const unit = getTimeUnit(maxTime);
    const xMax = Math.ceil(convertTime(maxTime, unit) * 1.1);
    const yMax = Math.ceil(maxCost * 1.2 * 10) / 10;

    const data = [];
    for (const comparison of scenarioData) {
      // Only include platforms that have data
      if (comparison.gen1) {
        data.push({
          platform: "gen1",
          tier: comparison.warehouseTier,
          size: comparison.gen1.size,
          label: comparison.gen1.label,
          time: comparison.gen1.time,
          cost: comparison.gen1.cost,
        });
      }
      if (comparison.adaptive) {
        data.push({
          platform: "adaptive",
          tier: comparison.warehouseTier,
          size: comparison.adaptive.size,
          label: comparison.adaptive.label,
          time: comparison.adaptive.time,
          cost: comparison.adaptive.cost,
        });
      }
    }

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
  }, [scenarioData, domainData]);

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
