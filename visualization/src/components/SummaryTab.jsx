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

function ScenarioHeader({ scenarioLabel, comparisons, hoveredTier, onHoverTier, showOutlierToggle, excludeOutlier, onToggleOutlier }) {
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
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: '700',
          color: 'white',
          margin: 0,
        }}>
          {scenarioLabel}
        </h2>

        {/* Outlier Toggle - only shown for CTAS */}
        {showOutlierToggle && (
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            fontSize: '12px',
            color: excludeOutlier ? '#e2e8f0' : '#64748b',
            transition: 'color 0.2s',
          }}>
            <div
              onClick={() => onToggleOutlier(!excludeOutlier)}
              style={{
                width: '36px',
                height: '20px',
                backgroundColor: excludeOutlier ? '#29B5E8' : '#475569',
                borderRadius: '10px',
                position: 'relative',
                transition: 'background-color 0.2s',
                cursor: 'pointer',
              }}
            >
              <div style={{
                width: '16px',
                height: '16px',
                backgroundColor: 'white',
                borderRadius: '50%',
                position: 'absolute',
                top: '2px',
                left: excludeOutlier ? '18px' : '2px',
                transition: 'left 0.2s',
              }} />
            </div>
            Exclude Outlier (Very Wide)
          </label>
        )}
      </div>

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

function ScenarioSection({ scenario, scenarioLabel, comparisons, onNavigateToDetails, showOutlierToggle, queryDetails, snowCreditPrice, dbxDbuPrice }) {
  const [hoveredTier, setHoveredTier] = useState(null);
  const [excludeOutlier, setExcludeOutlier] = useState(false);

  // When excludeOutlier is true, recalculate comparisons from queryDetails
  const effectiveComparisons = useMemo(() => {
    if (!excludeOutlier || !queryDetails || queryDetails.length === 0) {
      return comparisons;
    }

    // Filter out VERY_WIDE queries
    const filteredDetails = queryDetails.filter(
      q => q.scenario === scenario && q.queryIdDisplay !== 'VERY_WIDE'
    );

    // Group by warehouseTier and aggregate
    const tierGroups = {};
    filteredDetails.forEach(q => {
      const tier = q.warehouseTier;
      if (!tierGroups[tier]) {
        tierGroups[tier] = {
          snowflake: { time: 0, credits: 0, size: null },
          databricks: { time: 0, dbus: 0, size: null },
        };
      }
      if (q.snowflake?.executionSec != null) {
        tierGroups[tier].snowflake.time += q.snowflake.executionSec;
        tierGroups[tier].snowflake.credits += q.snowflake.credits || 0;
        tierGroups[tier].snowflake.size = q.snowflake.warehouseSize;
      }
      if (q.databricks?.executionSec != null) {
        tierGroups[tier].databricks.time += q.databricks.executionSec;
        tierGroups[tier].databricks.dbus += q.databricks.dbus || 0;
        tierGroups[tier].databricks.size = q.databricks.warehouseSize;
      }
    });

    // Convert to comparisons format
    return Object.entries(tierGroups).map(([tier, data]) => ({
      id: `${scenario}-${tier}-filtered`,
      scenario,
      warehouseTier: parseInt(tier),
      snowflake: data.snowflake.size ? {
        size: data.snowflake.size,
        label: `Snowflake ${data.snowflake.size}`,
        time: data.snowflake.time,
        credits: data.snowflake.credits,
        cost: data.snowflake.credits * snowCreditPrice,
      } : null,
      databricks: data.databricks.size ? {
        size: data.databricks.size,
        label: `Databricks ${data.databricks.size}`,
        time: data.databricks.time,
        dbus: data.databricks.dbus,
        cost: data.databricks.dbus * dbxDbuPrice,
      } : null,
    })).sort((a, b) => a.warehouseTier - b.warehouseTier);
  }, [excludeOutlier, queryDetails, comparisons, scenario, snowCreditPrice, dbxDbuPrice]);

  const totals = useMemo(() => {
    // Filter to only "primary comparisons" - tiers where both platforms have data
    // This excludes standalone tiers (e.g., Snowflake SMALL only, Databricks XLARGE only)
    const primaryComparisons = effectiveComparisons.filter(
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
  }, [effectiveComparisons]);

  const hoveredComparison = hoveredTier !== null
    ? effectiveComparisons.find(c => c.warehouseTier === hoveredTier)
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
        comparisons={effectiveComparisons}
        hoveredTier={hoveredTier}
        onHoverTier={setHoveredTier}
        showOutlierToggle={showOutlierToggle}
        excludeOutlier={excludeOutlier}
        onToggleOutlier={setExcludeOutlier}
      />

      {/* KPI Tiles Row - Above Chart, aligned with chart plot area */}
      <div className="kpi-tiles-row">
        <SummarySpeedTile totals={totals} timeUnit={timeUnit} hoveredComparison={hoveredComparison} />
        <SummaryCostTile totals={totals} hoveredComparison={hoveredComparison} />
      </div>

      {/* Chart - Full Width */}
      <ScenarioSummaryChart
        scenarioData={effectiveComparisons}
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
  const queryDetails = benchmarkData.queryDetails || [];

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

  // Group comparisons by scenario, deriving the panel list from the data so
  // adaptive QTM variants (e.g. concurrent_qtm2, concurrent_qtm8) each render
  // as their own panel. Ordering: sequential first, then concurrent variants,
  // then dml, with anything else after.
  const groupedByScenario = useMemo(() => {
    const labelsById = {};
    for (const c of comparisons) {
      if (c.scenario && c.scenarioLabel) labelsById[c.scenario] = c.scenarioLabel;
    }
    const scenarioOrder = (id) => {
      if (id === 'sequential') return 0;
      if (id.startsWith('concurrent')) return 1;
      if (id === 'dml') return 2;
      return 3;
    };
    const scenarios = Object.keys(labelsById).sort((a, b) => {
      const o = scenarioOrder(a) - scenarioOrder(b);
      return o !== 0 ? o : a.localeCompare(b);
    });

    return scenarios.map(scenario => ({
      scenario,
      scenarioLabel: labelsById[scenario],
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
            showOutlierToggle={scenario === 'ctas'}
            queryDetails={queryDetails}
            snowCreditPrice={snowCreditPrice}
            dbxDbuPrice={dbxDbuPrice}
          />
        </div>
      ))}
    </div>
  );
}
