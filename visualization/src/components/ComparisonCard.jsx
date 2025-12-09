import { SnowflakeLogo } from "./SnowflakeLogo";
import { DatabricksLogo } from "./DatabricksLogo";

function formatDiff(snowValue, dbxValue, isTime = false) {
  // Calculate savings as percentage of the higher (worse) value
  // e.g., if snow=$4.02 and dbx=$2.03, savings = ($4.02-$2.03)/$4.02 = 49%

  if (isTime) {
    // For time: lower is better
    if (dbxValue > snowValue) {
      // Snowflake wins - calculate how much faster as % of slower time
      const percentFaster = (((dbxValue - snowValue) / dbxValue) * 100).toFixed(0);
      return { text: `${percentFaster}% faster`, color: "#29B5E8", winner: "snowflake" };
    } else if (snowValue > dbxValue) {
      // Databricks wins
      const percentFaster = (((snowValue - dbxValue) / snowValue) * 100).toFixed(0);
      return { text: `${percentFaster}% faster`, color: "#FF3621", winner: "databricks" };
    }
    return { text: "Same", color: "#9ca3af", winner: null };
  } else {
    // For cost: lower is better
    if (dbxValue > snowValue) {
      // Snowflake wins - calculate savings as % of higher cost
      const percentCheaper = (((dbxValue - snowValue) / dbxValue) * 100).toFixed(0);
      return { text: `${percentCheaper}% cheaper`, color: "#29B5E8", winner: "snowflake" };
    } else if (snowValue > dbxValue) {
      // Databricks wins - calculate savings as % of higher cost
      const percentCheaper = (((snowValue - dbxValue) / snowValue) * 100).toFixed(0);
      return { text: `${percentCheaper}% cheaper`, color: "#FF3621", winner: "databricks" };
    }
    return { text: "Same", color: "#9ca3af", winner: null };
  }
}

export function ComparisonCard({ comparison }) {
  if (!comparison) return null;

  const timeDiff = formatDiff(comparison.snowflake.time, comparison.databricks.time, true);
  const costDiff = formatDiff(comparison.snowflake.cost, comparison.databricks.cost, false);

  const cardStyle = {
    backgroundColor: '#1e293b',
    borderRadius: '16px',
    padding: '24px',
    border: '1px solid #334155',
    boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
    maxWidth: '512px',
    margin: '0 auto',
  };

  const rowStyle = {
    backgroundColor: '#0f172a',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '16px',
  };

  return (
    <div style={cardStyle}>
      {/* Scenario title */}
      <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'white', textAlign: 'center', marginBottom: '16px' }}>
        {comparison.scenarioLabel}
      </h2>

      {/* Warehouse comparison */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <SnowflakeLogo size={24} />
          <span style={{ color: '#29B5E8', fontWeight: '500' }}>{comparison.snowflake.label}</span>
        </div>
        <span style={{ color: '#6b7280' }}>vs</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <DatabricksLogo size={24} />
          <span style={{ color: '#FF3621', fontWeight: '500' }}>{comparison.databricks.label}</span>
        </div>
      </div>

      {/* Duration row */}
      <div style={rowStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ color: '#9ca3af', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Duration</span>
          <span style={{ fontSize: '14px', fontWeight: '600', color: timeDiff.color }}>
            {timeDiff.winner === "snowflake" ? "Snowflake" : "Databricks"} {timeDiff.text}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <SnowflakeLogo size={16} />
            <span style={{ color: 'white', fontFamily: 'monospace', fontSize: '18px' }}>{Math.round(comparison.snowflake.time)}s</span>
          </div>
          <span style={{ color: '#6b7280' }}>vs</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'white', fontFamily: 'monospace', fontSize: '18px' }}>{Math.round(comparison.databricks.time)}s</span>
            <DatabricksLogo size={16} />
          </div>
        </div>
      </div>

      {/* Cost row */}
      <div style={{ ...rowStyle, marginBottom: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ color: '#9ca3af', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Cost</span>
          <span style={{ fontSize: '14px', fontWeight: '600', color: costDiff.color }}>
            {costDiff.winner === "snowflake" ? "Snowflake" : "Databricks"} {costDiff.text}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <SnowflakeLogo size={16} />
            <span style={{ color: 'white', fontFamily: 'monospace', fontSize: '18px' }}>${comparison.snowflake.cost.toFixed(2)}</span>
          </div>
          <span style={{ color: '#6b7280' }}>vs</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'white', fontFamily: 'monospace', fontSize: '18px' }}>${comparison.databricks.cost.toFixed(2)}</span>
            <DatabricksLogo size={16} />
          </div>
        </div>
      </div>
    </div>
  );
}
