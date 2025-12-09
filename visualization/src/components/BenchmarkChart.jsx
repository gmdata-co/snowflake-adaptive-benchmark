import { useMemo } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from "recharts";
import { SnowflakeLogo } from "./SnowflakeLogo";
import { DatabricksLogo } from "./DatabricksLogo";
import snowflakeLogo from "../assets/snowflake-logo.png";
import databricksLogo from "../assets/databricks-logo.png";

// Custom shape for scatter points with logos (using SVG image for PNG support)
function CustomScatterShape({ cx, cy, payload }) {
  const size = 36;
  const logoSrc = payload.platform === "snowflake" ? snowflakeLogo : databricksLogo;

  return (
    <image
      x={cx - size / 2}
      y={cy - size / 2}
      width={size}
      height={size}
      href={logoSrc}
    />
  );
}

// Custom label for data points
function CustomLabel({ x, y, payload }) {
  if (!payload) return null;
  const isSnowflake = payload.platform === "snowflake";
  const color = isSnowflake ? "#29B5E8" : "#FF3621";

  return (
    <text
      x={x}
      y={y - 26}
      textAnchor="middle"
      fill={color}
      fontSize={11}
      fontWeight="600"
    >
      {`${Math.round(payload.time)}s / $${payload.cost.toFixed(2)}`}
    </text>
  );
}

// Custom tooltip
function CustomTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const isSnowflake = data.platform === "snowflake";

    return (
      <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
          {isSnowflake ? (
            <SnowflakeLogo size={20} />
          ) : (
            <DatabricksLogo size={20} />
          )}
          <span style={{ fontWeight: '600', color: isSnowflake ? "#29B5E8" : "#FF3621" }}>
            {data.label}
          </span>
        </div>
        <div style={{ fontSize: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px' }}>
            <span style={{ color: '#9ca3af' }}>Duration:</span>
            <span style={{ color: 'white', fontWeight: '500' }}>
              {Math.round(data.time)}s
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', marginTop: '4px' }}>
            <span style={{ color: '#9ca3af' }}>Cost:</span>
            <span style={{ color: 'white', fontWeight: '500' }}>
              ${data.cost.toFixed(2)}
            </span>
          </div>
        </div>
      </div>
    );
  }
  return null;
}

export function BenchmarkChart({ comparison, onHover }) {
  // Transform comparison data for the chart
  const chartData = useMemo(() => {
    if (!comparison) return [];

    return [
      {
        platform: "snowflake",
        label: comparison.snowflake.label,
        time: comparison.snowflake.time,
        cost: comparison.snowflake.cost,
      },
      {
        platform: "databricks",
        label: comparison.databricks.label,
        time: comparison.databricks.time,
        cost: comparison.databricks.cost,
      },
    ];
  }, [comparison]);

  // Fixed axis domains across all comparisons for consistent visual comparison
  // Max time across all data: 862.52s, max cost: 3.65
  // Using fixed scales so animations show true movement
  const xDomain = [0, 1000];  // Duration in seconds
  const yDomain = [0, 4.5];   // Cost in USD

  if (!comparison) {
    return <div className="chart-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>Loading chart...</div>;
  }

  return (
    <div className="chart-container" style={{ width: '100%' }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart
          margin={{ top: 30, right: 30, bottom: 35, left: 50 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#334155"
            opacity={0.5}
          />
          <XAxis
            type="number"
            dataKey="time"
            domain={xDomain}
            name="Duration"
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            axisLine={{ stroke: "#475569" }}
            tickLine={{ stroke: "#475569" }}
            tickFormatter={(value) => `${Math.round(value)}s`}
            label={{
              value: "Duration (seconds)",
              position: "bottom",
              offset: 10,
              fill: "#94a3b8",
              fontSize: 14,
            }}
          />
          <YAxis
            type="number"
            dataKey="cost"
            domain={yDomain}
            name="Cost"
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            axisLine={{ stroke: "#475569" }}
            tickLine={{ stroke: "#475569" }}
            tickFormatter={(value) => `$${value.toFixed(2)}`}
            width={55}
            label={{
              value: "Cost (USD)",
              angle: -90,
              position: "insideLeft",
              offset: -5,
              fill: "#94a3b8",
              fontSize: 14,
              style: { textAnchor: "middle" },
            }}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ strokeDasharray: "3 3", stroke: "#64748b" }}
          />
          <Scatter
            data={chartData}
            shape={<CustomScatterShape />}
            onMouseEnter={onHover}
          >
            <LabelList content={<CustomLabel />} />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
