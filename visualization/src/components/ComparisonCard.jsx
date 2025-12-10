import { SnowflakeLogo } from "./SnowflakeLogo";
import { DatabricksLogo } from "./DatabricksLogo";
import { formatTime } from "../utils/formatTime";

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

const tileStyle = {
  backgroundColor: '#1e293b',
  borderRadius: '12px',
  padding: '12px 16px',
  border: '1px solid #334155',
  height: '100%',
  boxSizing: 'border-box',
};

export function SpeedTile({ comparison, timeUnit = 'seconds' }) {
  if (!comparison) return null;
  const timeDiff = formatDiff(comparison.snowflake.time, comparison.databricks.time, true);

  return (
    <div style={{ ...tileStyle, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center', marginBottom: '6px' }}>
        <span style={{ color: '#9ca3af', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>Speed</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <SnowflakeLogo size={16} />
          <span style={{ color: 'white', fontFamily: 'monospace', fontSize: '18px', fontWeight: '600' }}>{formatTime(comparison.snowflake.time, timeUnit)}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ color: 'white', fontFamily: 'monospace', fontSize: '18px', fontWeight: '600' }}>{formatTime(comparison.databricks.time, timeUnit)}</span>
          <DatabricksLogo size={16} />
        </div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <span key={comparison.id} className="winner-badge" style={{ fontSize: '14px', fontWeight: '700', color: timeDiff.color }}>
          {timeDiff.winner === "snowflake" ? "Snowflake" : "Databricks"} {timeDiff.text}
        </span>
      </div>
    </div>
  );
}

export function CostTile({ comparison }) {
  if (!comparison) return null;
  const costDiff = formatDiff(comparison.snowflake.cost, comparison.databricks.cost, false);

  return (
    <div style={{ ...tileStyle, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center', marginBottom: '6px' }}>
        <span style={{ color: '#9ca3af', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>Cost</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <SnowflakeLogo size={16} />
          <span style={{ color: 'white', fontFamily: 'monospace', fontSize: '18px', fontWeight: '600' }}>${comparison.snowflake.cost.toFixed(2)}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ color: 'white', fontFamily: 'monospace', fontSize: '18px', fontWeight: '600' }}>${comparison.databricks.cost.toFixed(2)}</span>
          <DatabricksLogo size={16} />
        </div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <span key={comparison.id} className="winner-badge" style={{ fontSize: '14px', fontWeight: '700', color: costDiff.color }}>
          {costDiff.winner === "snowflake" ? "Snowflake" : "Databricks"} {costDiff.text}
        </span>
      </div>
    </div>
  );
}

export function ScenarioTile({ comparison }) {
  if (!comparison) return null;

  return (
    <div style={{ ...tileStyle, textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'white', marginBottom: '8px' }}>
        {comparison.scenarioLabel}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <SnowflakeLogo size={22} />
          <span style={{ color: '#29B5E8', fontWeight: '600', fontSize: '1.25rem' }}>{comparison.snowflake.size}</span>
        </div>
        <span style={{ color: '#6b7280', fontSize: '1rem' }}>vs</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <DatabricksLogo size={22} />
          <span style={{ color: '#FF3621', fontWeight: '600', fontSize: '1.25rem' }}>{comparison.databricks.size}</span>
        </div>
      </div>
    </div>
  );
}
