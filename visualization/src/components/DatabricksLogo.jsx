import databricksLogo from "../assets/databricks-logo.png";

export function DatabricksLogo({ size = 40, className = "" }) {
  return (
    <img
      src={databricksLogo}
      alt="Databricks"
      width={size}
      height={size}
      className={className}
      style={{ objectFit: "contain" }}
    />
  );
}
