import { useState, useEffect } from "react";

// SQL keywords to highlight
const SQL_KEYWORDS = [
  "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "EXISTS", "BETWEEN",
  "LIKE", "IS", "NULL", "AS", "ON", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
  "FULL", "CROSS", "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "OFFSET",
  "UNION", "ALL", "DISTINCT", "CASE", "WHEN", "THEN", "ELSE", "END",
  "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE", "CREATE", "TABLE",
  "DROP", "ALTER", "INDEX", "WITH", "CTE", "OVER", "PARTITION", "INTERVAL",
  "SUM", "COUNT", "AVG", "MIN", "MAX", "ROUND", "COALESCE", "CAST",
  "DATE", "EXTRACT", "YEAR", "MONTH", "DAY", "ASC", "DESC", "NULLS", "FIRST", "LAST"
];

function highlightSql(sql) {
  if (!sql) return "";

  // Escape HTML
  let highlighted = sql
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Highlight SQL keywords (case insensitive, whole words only)
  SQL_KEYWORDS.forEach(keyword => {
    const regex = new RegExp(`\\b(${keyword})\\b`, "gi");
    highlighted = highlighted.replace(regex, '<span style="color: #93c5fd; font-weight: bold;">$1</span>');
  });

  // Highlight strings (single quotes)
  highlighted = highlighted.replace(/'([^']*)'/g, '<span style="color: #86efac;">\'$1\'</span>');

  // Highlight numbers
  highlighted = highlighted.replace(/\b(\d+\.?\d*)\b/g, '<span style="color: #fcd34d;">$1</span>');

  // Highlight comments
  highlighted = highlighted.replace(/(--.*$)/gm, '<span style="color: #6b7280; font-style: italic;">$1</span>');

  return highlighted;
}

export function SqlModal({ query, onClose }) {
  const [copied, setCopied] = useState(false);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  // Handle copy
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(query.fullSql || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  if (!query) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: "#1e293b",
          borderRadius: "12px",
          border: "1px solid #334155",
          maxWidth: "900px",
          width: "100%",
          maxHeight: "80vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            padding: "16px 20px",
            borderBottom: "1px solid #334155",
          }}
        >
          <div>
            <h3
              style={{
                margin: 0,
                color: "white",
                fontSize: "16px",
                fontWeight: "600",
                fontFamily: "monospace",
              }}
            >
              {query.queryIdDisplay}
              <span
                style={{
                  color: "#64748b",
                  fontWeight: "400",
                  marginLeft: "8px",
                  fontSize: "14px",
                }}
              >
                {query.queryCategory}
              </span>
            </h3>
            <p
              style={{
                margin: "4px 0 0",
                color: "#94a3b8",
                fontSize: "13px",
              }}
            >
              {query.queryDescription}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              backgroundColor: "transparent",
              border: "none",
              color: "#64748b",
              fontSize: "24px",
              cursor: "pointer",
              padding: "0",
              lineHeight: "1",
            }}
            onMouseEnter={(e) => (e.target.style.color = "#fff")}
            onMouseLeave={(e) => (e.target.style.color = "#64748b")}
          >
            &times;
          </button>
        </div>

        {/* SQL Content */}
        <div
          style={{
            flex: 1,
            overflow: "auto",
            padding: "16px 20px",
          }}
        >
          <pre
            style={{
              margin: 0,
              padding: "16px",
              backgroundColor: "#0f172a",
              borderRadius: "8px",
              border: "1px solid #334155",
              overflow: "auto",
              fontFamily: "'Fira Code', 'Consolas', 'Monaco', monospace",
              fontSize: "13px",
              lineHeight: "1.6",
              color: "#e2e8f0",
            }}
            dangerouslySetInnerHTML={{
              __html: highlightSql(query.fullSql),
            }}
          />
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: "12px",
            padding: "12px 20px",
            borderTop: "1px solid #334155",
          }}
        >
          <button
            onClick={handleCopy}
            style={{
              backgroundColor: copied ? "#22c55e" : "#334155",
              border: "none",
              borderRadius: "6px",
              padding: "8px 16px",
              color: "white",
              fontSize: "13px",
              cursor: "pointer",
              transition: "background-color 0.2s",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
            onMouseEnter={(e) => {
              if (!copied) e.target.style.backgroundColor = "#475569";
            }}
            onMouseLeave={(e) => {
              if (!copied) e.target.style.backgroundColor = "#334155";
            }}
          >
            {copied ? (
              <>
                <span>&#10003;</span> Copied!
              </>
            ) : (
              <>
                <span>&#128203;</span> Copy SQL
              </>
            )}
          </button>
          <button
            onClick={onClose}
            style={{
              backgroundColor: "transparent",
              border: "1px solid #475569",
              borderRadius: "6px",
              padding: "8px 16px",
              color: "#94a3b8",
              fontSize: "13px",
              cursor: "pointer",
            }}
            onMouseEnter={(e) => {
              e.target.style.borderColor = "#64748b";
              e.target.style.color = "#e2e8f0";
            }}
            onMouseLeave={(e) => {
              e.target.style.borderColor = "#475569";
              e.target.style.color = "#94a3b8";
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
