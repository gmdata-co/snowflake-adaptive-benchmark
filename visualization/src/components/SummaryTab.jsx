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
  // Handle missing platform data
  if (snowValue == null || dbxValue == null) {
    return { text: "", color: "#9ca3af", winner: null, noComparison: true };
  }
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
    snowflake: hoveredComparison.snowflake ? { time: hoveredComparison.snowflake.time } : null,
    databricks: hoveredComparison.databricks ? { time: hoveredComparison.databricks.time } : null,
  } : totals;

  const snowTime = displayData.snowflake?.time;
  const dbxTime = displayData.databricks?.time;
  const timeDiff = formatDiff(snowTime, dbxTime, true);

  // Build label based on available platforms
  let label = "Total Time";
  if (hoveredComparison) {
    const snowSize = hoveredComparison.snowflake?.size;
    const dbxSize = hoveredComparison.databricks?.size;
    if (snowSize && dbxSize) {
      label = `${snowSize} vs ${dbxSize}`;
    } else if (snowSize) {
      label = snowSize;
    } else if (dbxSize) {
      label = dbxSize;
    }
  }

  return (
    <div style={{ ...tileStyle, display: 'flex', flexDirection: 'column', justifyContent: 'center', transition: 'all 0.2s ease' }}>
      <div style={{ textAlign: 'center', marginBottom: '8px' }}>
        <span style={{ color: '#9ca3af', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>{label}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '28px', marginBottom: '8px' }}>
        {displayData.snowflake && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <SnowflakeLogo size={18} />
            <span style={{ color: '#29B5E8', fontFamily: 'monospace', fontSize: '20px', fontWeight: '700' }}>{formatTime(snowTime, timeUnit)}</span>
          </div>
        )}
        {displayData.databricks && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#FF3621', fontFamily: 'monospace', fontSize: '20px', fontWeight: '700' }}>{formatTime(dbxTime, timeUnit)}</span>
            <DatabricksLogo size={18} />
          </div>
        )}
      </div>
      {!timeDiff.noComparison && (
        <div style={{ textAlign: 'center' }}>
          <span className="winner-badge" style={{ fontSize: '13px', fontWeight: '600', color: timeDiff.color }}>
            {timeDiff.winner === "snowflake" ? "Snowflake" : "Databricks"} {timeDiff.text}
          </span>
        </div>
      )}
    </div>
  );
}

function SummaryCostTile({ totals, hoveredComparison }) {
  const displayData = hoveredComparison ? {
    snowflake: hoveredComparison.snowflake ? { cost: hoveredComparison.snowflake.cost } : null,
    databricks: hoveredComparison.databricks ? { cost: hoveredComparison.databricks.cost } : null,
  } : totals;

  const snowCost = displayData.snowflake?.cost;
  const dbxCost = displayData.databricks?.cost;
  const costDiff = formatDiff(snowCost, dbxCost, false);

  // Build label based on available platforms
  let label = "Total Cost";
  if (hoveredComparison) {
    const snowSize = hoveredComparison.snowflake?.size;
    const dbxSize = hoveredComparison.databricks?.size;
    if (snowSize && dbxSize) {
      label = `${snowSize} vs ${dbxSize}`;
    } else if (snowSize) {
      label = snowSize;
    } else if (dbxSize) {
      label = dbxSize;
    }
  }

  return (
    <div style={{ ...tileStyle, display: 'flex', flexDirection: 'column', justifyContent: 'center', transition: 'all 0.2s ease' }}>
      <div style={{ textAlign: 'center', marginBottom: '8px' }}>
        <span style={{ color: '#9ca3af', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>{label}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '28px', marginBottom: '8px' }}>
        {displayData.snowflake && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <SnowflakeLogo size={18} />
            <span style={{ color: '#29B5E8', fontFamily: 'monospace', fontSize: '20px', fontWeight: '700' }}>${snowCost.toFixed(2)}</span>
          </div>
        )}
        {displayData.databricks && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#FF3621', fontFamily: 'monospace', fontSize: '20px', fontWeight: '700' }}>${dbxCost.toFixed(2)}</span>
            <DatabricksLogo size={18} />
          </div>
        )}
      </div>
      {!costDiff.noComparison && (
        <div style={{ textAlign: 'center' }}>
          <span className="winner-badge" style={{ fontSize: '13px', fontWeight: '600', color: costDiff.color }}>
            {costDiff.winner === "snowflake" ? "Snowflake" : "Databricks"} {costDiff.text}
          </span>
        </div>
      )}
    </div>
  );
}

function ScenarioHeader({ scenarioLabel, comparisons, hoveredTier, onHoverTier }) {
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
        {comparisons.map((comparison) => {
          const tier = comparison.warehouseTier;
          const snowSize = comparison.snowflake?.size;
          const dbxSize = comparison.databricks?.size;
          const isHighlighted = hoveredTier === tier;
          const isDimmed = hoveredTier !== null && !isHighlighted;
          const hasBoth = snowSize && dbxSize;

          return (
            <div
              key={tier}
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
              {snowSize && (
                <span style={{ color: '#29B5E8', fontWeight: '600', fontSize: '0.82rem' }}>{snowSize}</span>
              )}
              {hasBoth && (
                <span style={{ color: '#64748b', fontSize: '0.72rem' }}>vs</span>
              )}
              {dbxSize && (
                <span style={{ color: '#FF3621', fontWeight: '600', fontSize: '0.82rem' }}>{dbxSize}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ScenarioSection({ scenario, scenarioLabel, comparisons, onNavigateToDetails }) {
  const [hoveredTier, setHoveredTier] = useState(null);

  const totals = useMemo(() => {
    // Filter to only "primary comparisons" - tiers where both platforms have data
    // This excludes standalone tiers (e.g., Snowflake SMALL only, Databricks XLARGE only)
    const primaryComparisons = comparisons.filter(
      c => c.snowflake != null && c.databricks != null
    );

    // Sum only primary comparison values
    const snowTime = primaryComparisons
      .filter(c => c.snowflake?.time != null)
      .reduce((sum, c) => sum + c.snowflake.time, 0);
    const snowCost = primaryComparisons
      .filter(c => c.snowflake?.cost != null)
      .reduce((sum, c) => sum + c.snowflake.cost, 0);
    const dbxTime = primaryComparisons
      .filter(c => c.databricks?.time != null)
      .reduce((sum, c) => sum + c.databricks.time, 0);
    const dbxCost = primaryComparisons
      .filter(c => c.databricks?.cost != null)
      .reduce((sum, c) => sum + c.databricks.cost, 0);

    return {
      snowflake: { time: snowTime, cost: snowCost },
      databricks: { time: dbxTime, cost: dbxCost },
    };
  }, [comparisons]);

  const hoveredComparison = hoveredTier !== null
    ? comparisons.find(c => c.warehouseTier === hoveredTier)
    : null;

  // Calculate maxTime handling null values
  const getMaxTime = () => {
    if (hoveredComparison) {
      const times = [
        hoveredComparison.snowflake?.time,
        hoveredComparison.databricks?.time,
      ].filter(t => t != null);
      return times.length > 0 ? Math.max(...times) : 0;
    }
    const times = [totals.snowflake?.time, totals.databricks?.time].filter(t => t != null);
    return times.length > 0 ? Math.max(...times) : 0;
  };
  const maxTime = getMaxTime();
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
        comparisons={comparisons}
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

      {/* View Details Button */}
      {onNavigateToDetails && (
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "12px" }}>
          <button
            onClick={() => onNavigateToDetails(scenario, hoveredTier)}
            style={{
              backgroundColor: "transparent",
              border: "1px solid #475569",
              borderRadius: "6px",
              padding: "6px 14px",
              color: "#94a3b8",
              fontSize: "12px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.target.style.borderColor = "#64748b";
              e.target.style.color = "#e2e8f0";
              e.target.style.backgroundColor = "#334155";
            }}
            onMouseLeave={(e) => {
              e.target.style.borderColor = "#475569";
              e.target.style.color = "#94a3b8";
              e.target.style.backgroundColor = "transparent";
            }}
          >
            View Query Details
            <span style={{ fontSize: "14px" }}>&rarr;</span>
          </button>
        </div>
      )}
    </div>
  );
}

// TableOfContents moved to App.jsx as HamburgerMenu

export function SummaryTab({ snowCreditPrice, dbxDbuPrice, onNavigateToDetails }) {
  const rawComparisons = benchmarkData.comparisons;

  // Recalculate costs based on user-specified prices
  const comparisons = useMemo(() => {
    return rawComparisons.map(c => ({
      ...c,
      snowflake: c.snowflake ? {
        ...c.snowflake,
        cost: c.snowflake.credits ? c.snowflake.credits * snowCreditPrice : c.snowflake.cost,
      } : null,
      databricks: c.databricks ? {
        ...c.databricks,
        cost: c.databricks.dbus ? c.databricks.dbus * dbxDbuPrice : c.databricks.cost,
      } : null,
    }));
  }, [rawComparisons, snowCreditPrice, dbxDbuPrice]);

  // Group comparisons by scenario - order: sequential, concurrent, cold, ctas, dml
  const groupedByScenario = useMemo(() => {
    const scenarios = ['normal', 'concurrent', 'coldstart', 'ctas', 'dml'];
    const scenarioLabels = {
      normal: '22 Sequential Queries',
      concurrent: '22 Concurrent Queries',
      coldstart: '5 Cold Start Queries',
      ctas: '5 CTAS Queries',
      dml: 'DML Refresh',
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
            scenario={scenario}
            scenarioLabel={scenarioLabel}
            comparisons={comparisons}
            onNavigateToDetails={onNavigateToDetails}
          />
        </div>
      ))}
    </div>
  );
}
