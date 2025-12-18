import { useState } from "react";
import { SnowflakeLogo } from "./SnowflakeLogo";
import { DatabricksLogo } from "./DatabricksLogo";
import { QueryCategoryBadge } from "./QueryCategoryBadge";

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
  if (!direction) return <span style={{ opacity: 0.3, marginLeft: "4px" }}>&#8597;</span>;
  return (
    <span style={{ marginLeft: "4px" }}>
      {direction === "asc" ? "&#9650;" : "&#9660;"}
    </span>
  );
}

function QueryDetailsRow({ row }) {
  const snowSec = row.snowflake?.executionSec;
  const dbxSec = row.databricks?.executionSec;
  const snowCost = row.snowflake?.cost;
  const dbxCost = row.databricks?.cost;
  const snowSize = row.snowflake?.warehouseSize;
  const dbxSize = row.databricks?.warehouseSize;

  // Calculate winner and difference
  let diffText = "-";
  let diffColor = "#9ca3af";
  if (snowSec != null && dbxSec != null) {
    const diff = snowSec - dbxSec;
    if (Math.abs(diff) < 0.01) {
      diffText = "Tie";
    } else if (diff < 0) {
      diffText = `Snow ${Math.abs(diff).toFixed(1)}s faster`;
      diffColor = "#29B5E8";
    } else {
      diffText = `DBX ${diff.toFixed(1)}s faster`;
      diffColor = "#FF3621";
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
        <span style={{ color: diffColor, fontSize: "12px" }}>{diffText}</span>
      </td>
      <td style={{ ...cellStyle, color: "#94a3b8", fontSize: "12px", maxWidth: "200px" }}>
        <span title={row.queryDescription}>{truncate(row.queryDescription, 40)}</span>
      </td>
      <td style={{ ...cellStyle, color: "#64748b", fontSize: "11px", maxWidth: "200px", fontFamily: "monospace" }}>
        <span title={row.sqlSnippet}>{truncate(row.sqlSnippet, 50)}</span>
      </td>
    </tr>
  );
}

export function QueryDetailsTable({ data }) {
  const [sortColumn, setSortColumn] = useState("queryIdDisplay");
  const [sortDirection, setSortDirection] = useState("asc");

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
      case "diff":
        aVal = (a.snowflake?.executionSec ?? 0) - (a.databricks?.executionSec ?? 0);
        bVal = (b.snowflake?.executionSec ?? 0) - (b.databricks?.executionSec ?? 0);
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
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
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
            <th {...getHeaderProps("diff")}>
              Difference
              <SortIcon direction={sortColumn === "diff" ? sortDirection : null} />
            </th>
            <th style={{ ...headerStyle, cursor: "default" }}>Description</th>
            <th style={{ ...headerStyle, cursor: "default" }}>SQL</th>
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row) => (
            <QueryDetailsRow key={row.id} row={row} />
          ))}
        </tbody>
      </table>
      {sortedData.length === 0 && (
        <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
          No queries match the current filters
        </div>
      )}
    </div>
  );
}
