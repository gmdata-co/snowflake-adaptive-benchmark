// Gen1 warehouse badge. (Component name kept as `SnowflakeLogo` so existing
// imports keep working; the JSON `snowflake` key maps to gen1 results.)
export const GEN1_COLOR = "#29B5E8";

export function SnowflakeLogo({ size = 40, className = "" }) {
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
        background: GEN1_COLOR,
        color: "#03263a",
        fontWeight: 800,
        fontSize: Math.max(8, size * 0.42),
        fontFamily: "system-ui, sans-serif",
        letterSpacing: "-0.03em",
        lineHeight: 1,
        userSelect: "none",
      }}
    >
      G1
    </span>
  );
}
