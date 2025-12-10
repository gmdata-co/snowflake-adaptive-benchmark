import { useState, useMemo } from "react";
import { ScenarioSummaryChart } from "./ScenarioSummaryChart";
import { SnowflakeLogo } from "./SnowflakeLogo";
import { DatabricksLogo } from "./DatabricksLogo";
import benchmarkData from "../data/benchmarkData.json";
import { formatTime, getTimeUnit } from "../utils/formatTime";

// Pricing defaults moved to App.jsx

const tileStyle = {
  backgroundColor: '#0f172a',
  borderRadius: '8px',
  padding: '14px 20px',
  border: '1px solid #334155',
  boxSizing: 'border-box',
};

// PricingInputs moved to App.jsx

function formatDiff(snowValue, dbxValue, isTime = false) {
  if (isTime) {
    if (dbxValue > snowValue) {
      const percentFaster = (((dbxValue - snowValue) / dbxValue) * 100).toFixed(0);
      return { text: `${percentFaster}% faster`, color: "#29B5E8", winner: "snowflake" };
    } else if (snowValue > dbxValue) {
      const percentFaster = (((snowValue - dbxValue) / snowValue) * 100).toFixed(0);
      return { text: `${percentFaster}% faster`, color: "#FF3621", winner: "databricks" };
    }
    return { text: "Same", color: "#9ca3af", winner: null };
  } else {
    if (dbxValue > snowValue) {
      const percentCheaper = (((dbxValue - snowValue) / dbxValue) * 100).toFixed(0);
      return { text: `${percentCheaper}% cheaper`, color: "#29B5E8", winner: "snowflake" };
    } else if (snowValue > dbxValue) {
      const percentCheaper = (((snowValue - dbxValue) / snowValue) * 100).toFixed(0);
      return { text: `${percentCheaper}% cheaper`, color: "#FF3621", winner: "databricks" };
    }
    return { text: "Same", color: "#9ca3af", winner: null };
  }
}

function SummarySpeedTile({ totals, timeUnit, hoveredComparison }) {
  const displayData = hoveredComparison ? {
    snowflake: { time: hoveredComparison.snowflake.time },
    databricks: { time: hoveredComparison.databricks.time },
  } : totals;

  const timeDiff = formatDiff(displayData.snowflake.time, displayData.databricks.time, true);
  const label = hoveredComparison
    ? `${hoveredComparison.snowflake.size} vs ${hoveredComparison.databricks.size}`
    : "Total Time";

  return (
    <div style={{ ...tileStyle, display: 'flex', flexDirection: 'column', justifyContent: 'center', transition: 'all 0.2s ease' }}>
      <div style={{ textAlign: 'center', marginBottom: '8px' }}>
        <span style={{ color: '#9ca3af', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>{label}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '28px', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <SnowflakeLogo size={18} />
          <span style={{ color: '#29B5E8', fontFamily: 'monospace', fontSize: '20px', fontWeight: '700' }}>{formatTime(displayData.snowflake.time, timeUnit)}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: '#FF3621', fontFamily: 'monospace', fontSize: '20px', fontWeight: '700' }}>{formatTime(displayData.databricks.time, timeUnit)}</span>
          <DatabricksLogo size={18} />
        </div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <span className="winner-badge" style={{ fontSize: '13px', fontWeight: '600', color: timeDiff.color }}>
          {timeDiff.winner === "snowflake" ? "Snowflake" : "Databricks"} {timeDiff.text}
        </span>
      </div>
    </div>
  );
}

function SummaryCostTile({ totals, hoveredComparison }) {
  const displayData = hoveredComparison ? {
    snowflake: { cost: hoveredComparison.snowflake.cost },
    databricks: { cost: hoveredComparison.databricks.cost },
  } : totals;

  const costDiff = formatDiff(displayData.snowflake.cost, displayData.databricks.cost, false);
  const label = hoveredComparison
    ? `${hoveredComparison.snowflake.size} vs ${hoveredComparison.databricks.size}`
    : "Total Cost";

  return (
    <div style={{ ...tileStyle, display: 'flex', flexDirection: 'column', justifyContent: 'center', transition: 'all 0.2s ease' }}>
      <div style={{ textAlign: 'center', marginBottom: '8px' }}>
        <span style={{ color: '#9ca3af', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>{label}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '28px', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <SnowflakeLogo size={18} />
          <span style={{ color: '#29B5E8', fontFamily: 'monospace', fontSize: '20px', fontWeight: '700' }}>${displayData.snowflake.cost.toFixed(2)}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: '#FF3621', fontFamily: 'monospace', fontSize: '20px', fontWeight: '700' }}>${displayData.databricks.cost.toFixed(2)}</span>
          <DatabricksLogo size={18} />
        </div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <span className="winner-badge" style={{ fontSize: '13px', fontWeight: '600', color: costDiff.color }}>
          {costDiff.winner === "snowflake" ? "Snowflake" : "Databricks"} {costDiff.text}
        </span>
      </div>
    </div>
  );
}

function ScenarioHeader({ scenarioLabel, warehouseSizes, hoveredTier, onHoverTier }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '16px',
      paddingBottom: '16px',
      borderBottom: '1px solid #334155',
      flexWrap: 'wrap',
      gap: '12px',
    }}>
      {/* Scenario Title */}
      <h2 style={{
        fontSize: '1.5rem',
        fontWeight: '700',
        color: 'white',
        margin: 0,
      }}>
        {scenarioLabel}
      </h2>

      {/* Warehouse Tier Pills */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '9px', flexWrap: 'wrap', marginRight: '85px' }}>
        {warehouseSizes.snowflake.map((snowSize, i) => {
          const tier = i + 1;
          const dbxSize = warehouseSizes.databricks[i];
          const isHighlighted = hoveredTier === tier;
          const isDimmed = hoveredTier !== null && !isHighlighted;

          return (
            <div
              key={i}
              onMouseEnter={() => onHoverTier(tier)}
              onMouseLeave={() => onHoverTier(null)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '5px 11px',
                borderRadius: '6px',
                backgroundColor: isHighlighted ? '#334155' : '#0f172a',
                border: isHighlighted ? '1px solid #475569' : '1px solid #334155',
                opacity: isDimmed ? 0.4 : 1,
                transition: 'all 0.2s ease',
                cursor: 'pointer',
              }}
            >
              <span style={{ color: '#29B5E8', fontWeight: '600', fontSize: '0.82rem' }}>{snowSize}</span>
              <span style={{ color: '#64748b', fontSize: '0.72rem' }}>vs</span>
              <span style={{ color: '#FF3621', fontWeight: '600', fontSize: '0.82rem' }}>{dbxSize}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ScenarioSection({ scenarioLabel, comparisons }) {
  const [hoveredTier, setHoveredTier] = useState(null);

  const totals = useMemo(() => {
    return {
      snowflake: {
        time: comparisons.reduce((sum, c) => sum + c.snowflake.time, 0),
        cost: comparisons.reduce((sum, c) => sum + c.snowflake.cost, 0),
      },
      databricks: {
        time: comparisons.reduce((sum, c) => sum + c.databricks.time, 0),
        cost: comparisons.reduce((sum, c) => sum + c.databricks.cost, 0),
      },
    };
  }, [comparisons]);

  const warehouseSizes = useMemo(() => ({
    snowflake: comparisons.map(c => c.snowflake.size),
    databricks: comparisons.map(c => c.databricks.size),
  }), [comparisons]);

  const hoveredComparison = hoveredTier
    ? comparisons.find(c => c.warehouseTier === hoveredTier)
    : null;

  const maxTime = hoveredComparison
    ? Math.max(hoveredComparison.snowflake.time, hoveredComparison.databricks.time)
    : Math.max(totals.snowflake.time, totals.databricks.time);
  const timeUnit = getTimeUnit(maxTime);

  return (
    <div style={{
      backgroundColor: '#1e293b',
      borderRadius: '12px',
      padding: '20px',
      border: '1px solid #334155',
    }}>
      {/* Header with title and warehouse tiers */}
      <ScenarioHeader
        scenarioLabel={scenarioLabel}
        warehouseSizes={warehouseSizes}
        hoveredTier={hoveredTier}
        onHoverTier={setHoveredTier}
      />

      {/* KPI Tiles Row - Above Chart, aligned with chart plot area */}
      <div className="kpi-tiles-row">
        <SummarySpeedTile totals={totals} timeUnit={timeUnit} hoveredComparison={hoveredComparison} />
        <SummaryCostTile totals={totals} hoveredComparison={hoveredComparison} />
      </div>

      {/* Chart - Full Width */}
      <ScenarioSummaryChart
        scenarioData={comparisons}
        hoveredTier={hoveredTier}
        onHoverTier={setHoveredTier}
      />
    </div>
  );
}

// TableOfContents moved to App.jsx as HamburgerMenu

export function SummaryTab({ snowCreditPrice, dbxDbuPrice }) {
  const rawComparisons = benchmarkData.comparisons;

  // Recalculate costs based on user-specified prices
  const comparisons = useMemo(() => {
    return rawComparisons.map(c => ({
      ...c,
      snowflake: {
        ...c.snowflake,
        cost: c.snowflake.credits ? c.snowflake.credits * snowCreditPrice : c.snowflake.cost,
      },
      databricks: {
        ...c.databricks,
        cost: c.databricks.dbus ? c.databricks.dbus * dbxDbuPrice : c.databricks.cost,
      },
    }));
  }, [rawComparisons, snowCreditPrice, dbxDbuPrice]);

  // Group comparisons by scenario - order: sequential, concurrent, cold, ctas
  const groupedByScenario = useMemo(() => {
    const scenarios = ['normal', 'concurrent', 'coldstart', 'ctas'];
    const scenarioLabels = {
      normal: '22 Sequential Queries',
      concurrent: '22 Concurrent Queries',
      coldstart: '5 Cold Start Queries',
      ctas: 'CTAS Query',
    };

    return scenarios.map(scenario => ({
      scenario,
      scenarioLabel: scenarioLabels[scenario],
      comparisons: comparisons
        .filter(c => c.scenario === scenario)
        .sort((a, b) => a.warehouseTier - b.warehouseTier),
    }));
  }, [comparisons]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {groupedByScenario.map(({ scenario, scenarioLabel, comparisons }) => (
        <div key={scenario} id={`scenario-${scenario}`}>
          <ScenarioSection
            scenarioLabel={scenarioLabel}
            comparisons={comparisons}
          />
        </div>
      ))}
    </div>
  );
}
