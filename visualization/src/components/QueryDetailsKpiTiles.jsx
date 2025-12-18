import { useMemo } from "react";
import { SnowflakeLogo } from "./SnowflakeLogo";
import { DatabricksLogo } from "./DatabricksLogo";
import { formatTime, getTimeUnit } from "../utils/formatTime";

const tileStyle = {
  backgroundColor: "#0f172a",
  borderRadius: "8px",
  padding: "14px 20px",
  border: "1px solid #334155",
  boxSizing: "border-box",
  flex: 1,
};

function formatDiff(snowValue, dbxValue) {
  if (snowValue == null || dbxValue == null) {
    return { text: "", color: "#9ca3af", winner: null, noComparison: true };
  }
  if (dbxValue > snowValue) {
    const percentFaster = (((dbxValue - snowValue) / dbxValue) * 100).toFixed(0);
    return { text: `${percentFaster}% faster`, color: "#29B5E8", winner: "snowflake" };
  } else if (snowValue > dbxValue) {
    const percentFaster = (((snowValue - dbxValue) / snowValue) * 100).toFixed(0);
    return { text: `${percentFaster}% faster`, color: "#FF3621", winner: "databricks" };
  }
  return { text: "Same", color: "#9ca3af", winner: null };
}

export function QueryDetailsKpiTiles({ data }) {
  const totals = useMemo(() => {
    let snowTime = 0;
    let dbxTime = 0;
    let snowCost = 0;
    let dbxCost = 0;
    let snowCount = 0;
    let dbxCount = 0;

    data.forEach((row) => {
      if (row.snowflake?.executionSec != null) {
        snowTime += row.snowflake.executionSec;
        snowCount++;
      }
      if (row.databricks?.executionSec != null) {
        dbxTime += row.databricks.executionSec;
        dbxCount++;
      }
      if (row.snowflake?.cost != null) {
        snowCost += row.snowflake.cost;
      }
      if (row.databricks?.cost != null) {
        dbxCost += row.databricks.cost;
      }
    });

    return {
      snowTime: snowCount > 0 ? snowTime : null,
      dbxTime: dbxCount > 0 ? dbxTime : null,
      snowCost: snowCost > 0 ? snowCost : null,
      dbxCost: dbxCost > 0 ? dbxCost : null,
      snowCount,
      dbxCount,
    };
  }, [data]);

  const timeDiff = formatDiff(totals.snowTime, totals.dbxTime);
  const costDiff = formatDiff(totals.snowCost, totals.dbxCost);
  const maxTime = Math.max(totals.snowTime || 0, totals.dbxTime || 0);
  const timeUnit = getTimeUnit(maxTime);

  // Don't render if no data
  if (data.length === 0) {
    return null;
  }

  return (
    <div style={{ display: "flex", gap: "16px", marginBottom: "16px" }}>
      {/* Speed/Time Tile */}
      <div
        style={{
          ...tileStyle,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          transition: "all 0.2s ease",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "8px" }}>
          <span
            style={{
              color: "#9ca3af",
              fontSize: "11px",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              fontWeight: "600",
            }}
          >
            Total Execution Time
          </span>
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "28px",
            marginBottom: "8px",
          }}
        >
          {totals.snowTime != null && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <SnowflakeLogo size={18} />
              <span
                style={{
                  color: "#29B5E8",
                  fontFamily: "monospace",
                  fontSize: "20px",
                  fontWeight: "700",
                }}
              >
                {formatTime(totals.snowTime, timeUnit)}
              </span>
            </div>
          )}
          {totals.dbxTime != null && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  color: "#FF3621",
                  fontFamily: "monospace",
                  fontSize: "20px",
                  fontWeight: "700",
                }}
              >
                {formatTime(totals.dbxTime, timeUnit)}
              </span>
              <DatabricksLogo size={18} />
            </div>
          )}
        </div>
        {!timeDiff.noComparison && (
          <div style={{ textAlign: "center" }}>
            <span
              className="winner-badge"
              style={{ fontSize: "13px", fontWeight: "600", color: timeDiff.color }}
            >
              {timeDiff.winner === "snowflake" ? "Snowflake" : "Databricks"} {timeDiff.text}
            </span>
          </div>
        )}
      </div>

      {/* Estimated Cost Tile */}
      {(totals.snowCost != null || totals.dbxCost != null) && (
        <div
          style={{
            ...tileStyle,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            transition: "all 0.2s ease",
          }}
        >
          <div style={{ textAlign: "center", marginBottom: "8px" }}>
            <span
              style={{
                color: "#9ca3af",
                fontSize: "11px",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                fontWeight: "600",
              }}
            >
              Estimated Cost
            </span>
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: "28px",
              marginBottom: "8px",
            }}
          >
            {totals.snowCost != null && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <SnowflakeLogo size={18} />
                <span
                  style={{
                    color: "#29B5E8",
                    fontFamily: "monospace",
                    fontSize: "20px",
                    fontWeight: "700",
                  }}
                >
                  ${totals.snowCost.toFixed(2)}
                </span>
              </div>
            )}
            {totals.dbxCost != null && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span
                  style={{
                    color: "#FF3621",
                    fontFamily: "monospace",
                    fontSize: "20px",
                    fontWeight: "700",
                  }}
                >
                  ${totals.dbxCost.toFixed(2)}
                </span>
                <DatabricksLogo size={18} />
              </div>
            )}
          </div>
          {!costDiff.noComparison && (
            <div style={{ textAlign: "center" }}>
              <span
                className="winner-badge"
                style={{ fontSize: "13px", fontWeight: "600", color: costDiff.color }}
              >
                {costDiff.winner === "snowflake" ? "Snowflake" : "Databricks"} {costDiff.text}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Query Count Tile */}
      <div
        style={{
          ...tileStyle,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          transition: "all 0.2s ease",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "8px" }}>
          <span
            style={{
              color: "#9ca3af",
              fontSize: "11px",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              fontWeight: "600",
            }}
          >
            Queries Shown
          </span>
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "28px",
            marginBottom: "8px",
          }}
        >
          <span
            style={{
              color: "#e2e8f0",
              fontFamily: "monospace",
              fontSize: "20px",
              fontWeight: "700",
            }}
          >
            {data.length}
          </span>
        </div>
        <div style={{ textAlign: "center" }}>
          <span style={{ fontSize: "12px", color: "#64748b" }}>
            {totals.snowCount} Snowflake, {totals.dbxCount} Databricks
          </span>
        </div>
      </div>
    </div>
  );
}
