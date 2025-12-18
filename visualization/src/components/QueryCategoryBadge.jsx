const CATEGORY_COLORS = {
  "Simple Aggregation & Filtering": { bg: "#065f46", text: "#6ee7b7" },
  "Basic Joins (2-4 tables)": { bg: "#1e40af", text: "#93c5fd" },
  "Complex Joins (5+ tables)": { bg: "#7c2d12", text: "#fdba74" },
  "Subqueries & Semi-Joins": { bg: "#581c87", text: "#d8b4fe" },
  "Correlated & Nested Subqueries": { bg: "#831843", text: "#f9a8d4" },
  "Advanced Patterns": { bg: "#374151", text: "#d1d5db" },
  "CTAS Variant": { bg: "#064e3b", text: "#a7f3d0" },
};

export function QueryCategoryBadge({ category }) {
  const colors = CATEGORY_COLORS[category] || { bg: "#374151", text: "#9ca3af" };

  return (
    <span
      style={{
        backgroundColor: colors.bg,
        color: colors.text,
        padding: "2px 8px",
        borderRadius: "4px",
        fontSize: "11px",
        fontWeight: "500",
        whiteSpace: "nowrap",
      }}
    >
      {category}
    </span>
  );
}
