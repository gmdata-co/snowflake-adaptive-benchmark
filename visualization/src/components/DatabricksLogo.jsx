// Adaptive warehouse badge. (Component name kept as `DatabricksLogo` so
// existing imports keep working; the JSON `databricks` key maps to adaptive.)
export const ADAPTIVE_COLOR = "#F59E0B";

export function DatabricksLogo({ size = 40, className = "" }) {
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: size,
        height: size,
        borderRadius: Math.max(4, size * 0.22),
        background: ADAPTIVE_COLOR,
        color: "#3a2400",
        fontWeight: 800,
        fontSize: Math.max(8, size * 0.42),
        fontFamily: "system-ui, sans-serif",
        letterSpacing: "-0.03em",
        lineHeight: 1,
        userSelect: "none",
      }}
    >
      AD
    </span>
  );
}
