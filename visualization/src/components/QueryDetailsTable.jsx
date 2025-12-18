import { useState } from "react";
import { SnowflakeLogo } from "./SnowflakeLogo";
import { DatabricksLogo } from "./DatabricksLogo";
import { QueryCategoryBadge } from "./QueryCategoryBadge";
import { SqlModal } from "./SqlModal";

const headerStyle = {
  padding: "12px 8px",
  textAlign: "left",
  color: "#9ca3af",
  fontSize: "11px",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  fontWeight: "600",
  cursor: "pointer",
  userSelect: "none",
  whiteSpace: "nowrap",
};

const cellStyle = {
  padding: "10px 8px",
  borderBottom: "1px solid #1e293b",
};

function SortIcon({ direction }) {
  if (!direction) return <span style={{ opacity: 0.3, marginLeft: "4px" }}>↕</span>;
  return (
    <span style={{ marginLeft: "4px" }}>
      {direction === "asc" ? "▲" : "▼"}
    </span>
  );
}

function QueryDetailsRow({ row, onSqlClick }) {
  const snowSec = row.snowflake?.executionSec;
  const dbxSec = row.databricks?.executionSec;
  const snowCost = row.snowflake?.cost;
  const dbxCost = row.databricks?.cost;
  const snowSize = row.snowflake?.warehouseSize;
  const dbxSize = row.databricks?.warehouseSize;

  // Calculate time difference
  let timeDiffText = "-";
  let timeDiffColor = "#9ca3af";
  if (snowSec != null && dbxSec != null) {
    const diff = snowSec - dbxSec;
    if (Math.abs(diff) < 0.01) {
      timeDiffText = "Tie";
    } else if (diff < 0) {
      timeDiffText = `Snow ${Math.abs(diff).toFixed(1)}s faster`;
      timeDiffColor = "#29B5E8";
    } else {
      timeDiffText = `DBX ${diff.toFixed(1)}s faster`;
      timeDiffColor = "#FF3621";
    }
  }

  // Calculate cost difference
  let costDiffText = "-";
  let costDiffColor = "#9ca3af";
  if (snowCost != null && dbxCost != null) {
    const diff = snowCost - dbxCost;
    if (Math.abs(diff) < 0.001) {
      costDiffText = "Tie";
    } else if (diff < 0) {
      costDiffText = `Snow $${Math.abs(diff).toFixed(3)} cheaper`;
      costDiffColor = "#29B5E8";
    } else {
      costDiffText = `DBX $${diff.toFixed(3)} cheaper`;
      costDiffColor = "#FF3621";
    }
  }

  // Truncate text helper
  const truncate = (text, maxLen) => {
    if (!text) return "";
    return text.length > maxLen ? text.slice(0, maxLen) + "..." : text;
  };

  // Build warehouse size display
  let warehouseDisplay = "";
  if (snowSize && dbxSize) {
    warehouseDisplay = `${snowSize} vs ${dbxSize}`;
  } else if (snowSize) {
    warehouseDisplay = snowSize;
  } else if (dbxSize) {
    warehouseDisplay = dbxSize;
  }

  return (
    <tr>
      <td style={cellStyle}>
        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
          <span style={{ fontWeight: "600", color: "white", fontFamily: "monospace" }}>
            {row.queryIdDisplay}
            <span style={{ color: "#64748b", fontWeight: "400", marginLeft: "6px" }}>
              (run {row.runId})
            </span>
          </span>
          {warehouseDisplay && (
            <span style={{ color: "#64748b", fontSize: "10px" }}>
              {warehouseDisplay}
            </span>
          )}
        </div>
      </td>
      <td style={cellStyle}>
        <QueryCategoryBadge category={row.queryCategory} />
      </td>
      <td style={{ ...cellStyle, textAlign: "right" }}>
        <span style={{ color: "#29B5E8", fontFamily: "monospace" }}>
          {snowSec != null ? `${snowSec.toFixed(2)}s` : "-"}
        </span>
      </td>
      <td style={{ ...cellStyle, textAlign: "right" }}>
        <span style={{ color: "#FF3621", fontFamily: "monospace" }}>
          {dbxSec != null ? `${dbxSec.toFixed(2)}s` : "-"}
        </span>
      </td>
      <td style={{ ...cellStyle, textAlign: "right" }}>
        <span style={{ color: "#29B5E8", fontFamily: "monospace", fontSize: "12px" }}>
          {snowCost != null ? `$${snowCost.toFixed(4)}` : "-"}
        </span>
      </td>
      <td style={{ ...cellStyle, textAlign: "right" }}>
        <span style={{ color: "#FF3621", fontFamily: "monospace", fontSize: "12px" }}>
          {dbxCost != null ? `$${dbxCost.toFixed(4)}` : "-"}
        </span>
      </td>
      <td style={cellStyle}>
        <span style={{ color: timeDiffColor, fontSize: "12px" }}>{timeDiffText}</span>
      </td>
      <td style={cellStyle}>
        <span style={{ color: costDiffColor, fontSize: "12px" }}>{costDiffText}</span>
      </td>
      <td style={{ ...cellStyle, color: "#94a3b8", fontSize: "12px", maxWidth: "180px" }}>
        <span title={row.queryDescription}>{truncate(row.queryDescription, 35)}</span>
      </td>
      <td style={{ ...cellStyle, maxWidth: "150px" }}>
        <button
          onClick={() => onSqlClick(row)}
          style={{
            background: "transparent",
            border: "none",
            color: "#64748b",
            fontSize: "11px",
            fontFamily: "monospace",
            cursor: "pointer",
            padding: "2px 4px",
            borderRadius: "4px",
            textAlign: "left",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = "#334155";
            e.target.style.color = "#94a3b8";
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = "transparent";
            e.target.style.color = "#64748b";
          }}
          title="Click to view full SQL"
        >
          {truncate(row.sqlSnippet, 40)}
        </button>
      </td>
    </tr>
  );
}

export function QueryDetailsTable({ data }) {
  const [sortColumn, setSortColumn] = useState("queryIdDisplay");
  const [sortDirection, setSortDirection] = useState("asc");
  const [selectedQuery, setSelectedQuery] = useState(null);

  const sortedData = [...data].sort((a, b) => {
    let aVal, bVal;

    switch (sortColumn) {
      case "queryIdDisplay":
        // Sort by query_num first, then ctas_variant
        aVal = a.queryNum * 100 + (a.ctasVariant ? a.ctasVariant.charCodeAt(0) : 0);
        bVal = b.queryNum * 100 + (b.ctasVariant ? b.ctasVariant.charCodeAt(0) : 0);
        break;
      case "snowExecution":
        aVal = a.snowflake?.executionSec ?? Infinity;
        bVal = b.snowflake?.executionSec ?? Infinity;
        break;
      case "dbxExecution":
        aVal = a.databricks?.executionSec ?? Infinity;
        bVal = b.databricks?.executionSec ?? Infinity;
        break;
      case "snowCost":
        aVal = a.snowflake?.cost ?? Infinity;
        bVal = b.snowflake?.cost ?? Infinity;
        break;
      case "dbxCost":
        aVal = a.databricks?.cost ?? Infinity;
        bVal = b.databricks?.cost ?? Infinity;
        break;
      case "timeDiff":
        aVal = (a.snowflake?.executionSec ?? 0) - (a.databricks?.executionSec ?? 0);
        bVal = (b.snowflake?.executionSec ?? 0) - (b.databricks?.executionSec ?? 0);
        break;
      case "costDiff":
        aVal = (a.snowflake?.cost ?? 0) - (a.databricks?.cost ?? 0);
        bVal = (b.snowflake?.cost ?? 0) - (b.databricks?.cost ?? 0);
        break;
      case "queryCategory":
        aVal = a.queryCategory || "";
        bVal = b.queryCategory || "";
        break;
      default:
        aVal = a[sortColumn] || "";
        bVal = b[sortColumn] || "";
    }

    if (typeof aVal === "string") {
      const comparison = aVal.localeCompare(bVal);
      return sortDirection === "asc" ? comparison : -comparison;
    }

    if (sortDirection === "asc") {
      return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    } else {
      return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
    }
  });

  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const getHeaderProps = (column) => ({
    onClick: () => handleSort(column),
    style: headerStyle,
  });

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", minWidth: "1200px", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid #334155" }}>
            <th {...getHeaderProps("queryIdDisplay")}>
              Query
              <SortIcon direction={sortColumn === "queryIdDisplay" ? sortDirection : null} />
            </th>
            <th {...getHeaderProps("queryCategory")}>
              Category
              <SortIcon direction={sortColumn === "queryCategory" ? sortDirection : null} />
            </th>
            <th {...getHeaderProps("snowExecution")} style={{ ...headerStyle, textAlign: "right" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                <SnowflakeLogo size={12} /> Time
              </span>
              <SortIcon direction={sortColumn === "snowExecution" ? sortDirection : null} />
            </th>
            <th {...getHeaderProps("dbxExecution")} style={{ ...headerStyle, textAlign: "right" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                <DatabricksLogo size={12} /> Time
              </span>
              <SortIcon direction={sortColumn === "dbxExecution" ? sortDirection : null} />
            </th>
            <th {...getHeaderProps("snowCost")} style={{ ...headerStyle, textAlign: "right" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                <SnowflakeLogo size={12} /> Cost
              </span>
              <SortIcon direction={sortColumn === "snowCost" ? sortDirection : null} />
            </th>
            <th {...getHeaderProps("dbxCost")} style={{ ...headerStyle, textAlign: "right" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                <DatabricksLogo size={12} /> Cost
              </span>
              <SortIcon direction={sortColumn === "dbxCost" ? sortDirection : null} />
            </th>
            <th {...getHeaderProps("timeDiff")}>
              Time Diff
              <SortIcon direction={sortColumn === "timeDiff" ? sortDirection : null} />
            </th>
            <th {...getHeaderProps("costDiff")}>
              Cost Diff
              <SortIcon direction={sortColumn === "costDiff" ? sortDirection : null} />
            </th>
            <th style={{ ...headerStyle, cursor: "default" }}>Description</th>
            <th style={{ ...headerStyle, cursor: "default" }}>SQL</th>
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row) => (
            <QueryDetailsRow key={row.id} row={row} onSqlClick={setSelectedQuery} />
          ))}
        </tbody>
      </table>
      {sortedData.length === 0 && (
        <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
          No queries match the current filters
        </div>
      )}
      {selectedQuery && (
        <SqlModal query={selectedQuery} onClose={() => setSelectedQuery(null)} />
      )}
    </div>
  );
}
