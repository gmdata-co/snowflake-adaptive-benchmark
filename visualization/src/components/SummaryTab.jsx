import { useState, useMemo, useEffect } from "react";
import { ScenarioSummaryChart } from "./ScenarioSummaryChart";
import { SnowflakeLogo } from "./SnowflakeLogo";
import { DatabricksLogo } from "./DatabricksLogo";
import benchmarkData from "../data/benchmarkData.json";
import { formatTime, getTimeUnit } from "../utils/formatTime";

const tileStyle = {
  backgroundColor: '#0f172a',
  borderRadius: '8px',
  padding: '14px 20px',
  border: '1px solid #334155',
  boxSizing: 'border-box',
};

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

function ScenarioHeader({ scenarioLabel, warehouseSizes, hoveredTier }) {
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
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        {warehouseSizes.snowflake.map((snowSize, i) => {
          const tier = i + 1;
          const dbxSize = warehouseSizes.databricks[i];
          const isHighlighted = hoveredTier === tier;
          const isDimmed = hoveredTier !== null && !isHighlighted;

          return (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '6px',
                backgroundColor: isHighlighted ? '#334155' : '#0f172a',
                border: isHighlighted ? '1px solid #475569' : '1px solid #334155',
                opacity: isDimmed ? 0.4 : 1,
                transition: 'all 0.2s ease',
              }}
            >
              <span style={{ color: '#29B5E8', fontWeight: '600', fontSize: '0.85rem' }}>{snowSize}</span>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>vs</span>
              <span style={{ color: '#FF3621', fontWeight: '600', fontSize: '0.85rem' }}>{dbxSize}</span>
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
      />

      {/* KPI Tiles Row - Above Chart, aligned with chart plot area */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '12px',
        marginBottom: '16px',
        marginLeft: '100px',
        marginRight: '80px',
      }}>
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

function TableOfContents({ scenarios, activeScenario, isOpen, onToggle }) {
  const scrollToScenario = (scenarioId) => {
    const element = document.getElementById(`scenario-${scenarioId}`);
    if (element) {
      const yOffset = -100; // Extra space at top
      const y = element.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
    }
  };

  return (
    <div style={{
      position: 'fixed',
      right: '20px',
      top: '140px',
      zIndex: 100,
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0',
    }}>
      {/* Toggle button */}
      <button
        onClick={onToggle}
        style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRight: isOpen ? 'none' : '1px solid #334155',
          borderRadius: isOpen ? '8px 0 0 8px' : '8px',
          padding: '12px 8px',
          cursor: 'pointer',
          color: '#94a3b8',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.target.style.backgroundColor = '#334155';
          e.target.style.color = '#fff';
        }}
        onMouseLeave={(e) => {
          e.target.style.backgroundColor = '#1e293b';
          e.target.style.color = '#94a3b8';
        }}
        title={isOpen ? 'Hide scenarios' : 'Show scenarios'}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
          }}
        >
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>

      {/* Collapsible panel */}
      <div style={{
        backgroundColor: '#1e293b',
        borderRadius: '8px 0 0 8px',
        padding: isOpen ? '16px' : '0',
        border: '1px solid #334155',
        borderRight: 'none',
        overflow: 'hidden',
        width: isOpen ? '200px' : '0',
        opacity: isOpen ? 1 : 0,
        transition: 'all 0.2s ease',
      }}>
        <h3 style={{
          color: '#9ca3af',
          fontSize: '11px',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          fontWeight: '600',
          marginBottom: '12px',
          marginTop: 0,
          whiteSpace: 'nowrap',
        }}>
          Scenarios
        </h3>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {scenarios.map(({ scenario, scenarioLabel }) => (
            <button
              key={scenario}
              onClick={() => scrollToScenario(scenario)}
              style={{
                background: activeScenario === scenario ? '#334155' : 'transparent',
                border: 'none',
                borderRadius: '6px',
                padding: '8px 10px',
                textAlign: 'left',
                cursor: 'pointer',
                color: activeScenario === scenario ? '#fff' : '#94a3b8',
                fontSize: '12px',
                fontWeight: activeScenario === scenario ? '600' : '400',
                transition: 'all 0.15s ease',
                borderLeft: activeScenario === scenario ? '3px solid #3b82f6' : '3px solid transparent',
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => {
                if (activeScenario !== scenario) {
                  e.target.style.backgroundColor = '#0f172a';
                  e.target.style.color = '#cbd5e1';
                }
              }}
              onMouseLeave={(e) => {
                if (activeScenario !== scenario) {
                  e.target.style.backgroundColor = 'transparent';
                  e.target.style.color = '#94a3b8';
                }
              }}
            >
              {scenarioLabel}
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
}

export function SummaryTab() {
  const comparisons = benchmarkData.comparisons;
  const [activeScenario, setActiveScenario] = useState('normal');
  const [tocOpen, setTocOpen] = useState(true);

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

  // Set up intersection observer to track active section
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const scenarioId = entry.target.id.replace('scenario-', '');
            setActiveScenario(scenarioId);
          }
        });
      },
      { threshold: 0.3, rootMargin: '-100px 0px -50% 0px' }
    );

    // Delay to ensure elements are mounted
    const timeoutId = setTimeout(() => {
      groupedByScenario.forEach(({ scenario }) => {
        const element = document.getElementById(`scenario-${scenario}`);
        if (element) observer.observe(element);
      });
    }, 100);

    return () => {
      clearTimeout(timeoutId);
      observer.disconnect();
    };
  }, [groupedByScenario]);

  return (
    <>
      {/* Main content - centered as before */}
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

      {/* Floating Table of Contents */}
      <TableOfContents
        scenarios={groupedByScenario}
        activeScenario={activeScenario}
        isOpen={tocOpen}
        onToggle={() => setTocOpen(!tocOpen)}
      />
    </>
  );
}
