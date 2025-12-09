import snowflakeLogo from "../assets/snowflake-logo.png";

export function SnowflakeLogo({ size = 40, className = "" }) {
  return (
    <img
      src={snowflakeLogo}
      alt="Snowflake"
      width={size}
      height={size}
      className={className}
      style={{ objectFit: "contain" }}
    />
  );
}
