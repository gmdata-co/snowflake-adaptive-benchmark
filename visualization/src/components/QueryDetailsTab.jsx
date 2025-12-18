import { useState, useMemo, useEffect } from "react";
import { QueryDetailsTable } from "./QueryDetailsTable";
import { QueryDetailsKpiTiles } from "./QueryDetailsKpiTiles";
import { MultiSelectFilter } from "./MultiSelectFilter";
import benchmarkData from "../data/benchmarkData.json";

const SCENARIO_LABELS = {
  normal: "Sequential",
  concurrent: "Concurrent",
  coldstart: "Cold Start",
  ctas: "CTAS",
  dml: "DML",
};

export function QueryDetailsTab({ initialScenario, initialTier, snowCreditPrice, dbxDbuPrice }) {
  const [selectedScenarios, setSelectedScenarios] = useState([]);
  const [selectedTiers, setSelectedTiers] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedWarehouseSizes, setSelectedWarehouseSizes] = useState([]);
  const [selectedQueryIds, setSelectedQueryIds] = useState([]);

  // Update filters when initial values change (navigation from Summary)
  useEffect(() => {
    if (initialScenario) {
      setSelectedScenarios([initialScenario]);
    }
    if (initialTier !== undefined && initialTier !== null) {
      setSelectedTiers([initialTier]);
    }
  }, [initialScenario, initialTier]);

  const queryDetails = benchmarkData.queryDetails || [];

  // Get unique values for each filter
  const availableScenarios = useMemo(() => {
    const scenarios = [...new Set(queryDetails.map((d) => d.scenario))];
    return scenarios.sort((a, b) => {
      const order = ["normal", "concurrent", "coldstart", "ctas", "dml"];
      return order.indexOf(a) - order.indexOf(b);
    });
  }, [queryDetails]);

  const availableTiers = useMemo(() => {
    const tiers = [...new Set(queryDetails.map((d) => d.warehouseTier))];
    return tiers.sort((a, b) => a - b);
  }, [queryDetails]);

  const availableCategories = useMemo(() => {
    const categories = [...new Set(queryDetails.map((d) => d.queryCategory))];
    return categories.sort();
  }, [queryDetails]);

  const availableWarehouseSizes = useMemo(() => {
    const sizes = new Set();
    queryDetails.forEach((d) => {
      if (d.snowflake?.warehouseSize) sizes.add(d.snowflake.warehouseSize);
      if (d.databricks?.warehouseSize) sizes.add(d.databricks.warehouseSize);
    });
    const sizeOrder = ["SMALL", "MEDIUM", "LARGE", "XLARGE"];
    return [...sizes].sort((a, b) => sizeOrder.indexOf(a) - sizeOrder.indexOf(b));
  }, [queryDetails]);

  const availableQueryIds = useMemo(() => {
    const ids = [...new Set(queryDetails.map((d) => d.queryIdDisplay))];
    // Sort: Q01-Q22 first (numerically), then CTAS variants alphabetically
    return ids.sort((a, b) => {
      const aIsQ = a.startsWith("Q");
      const bIsQ = b.startsWith("Q");
      if (aIsQ && bIsQ) {
        return parseInt(a.slice(1)) - parseInt(b.slice(1));
      }
      if (aIsQ) return -1;
      if (bIsQ) return 1;
      return a.localeCompare(b);
    });
  }, [queryDetails]);

  // Filter data based on all selections
  const filteredData = useMemo(() => {
    return queryDetails.filter((d) => {
      // Scenario filter (empty means all)
      if (selectedScenarios.length > 0 && !selectedScenarios.includes(d.scenario)) {
        return false;
      }

      // Tier filter (empty means all)
      if (selectedTiers.length > 0 && !selectedTiers.includes(d.warehouseTier)) {
        return false;
      }

      // Category filter (empty means all)
      if (selectedCategories.length > 0 && !selectedCategories.includes(d.queryCategory)) {
        return false;
      }

      // Warehouse size filter (empty means all)
      if (selectedWarehouseSizes.length > 0) {
        const snowSize = d.snowflake?.warehouseSize;
        const dbxSize = d.databricks?.warehouseSize;
        if (!selectedWarehouseSizes.includes(snowSize) && !selectedWarehouseSizes.includes(dbxSize)) {
          return false;
        }
      }

      // Query ID filter (empty means all)
      if (selectedQueryIds.length > 0 && !selectedQueryIds.includes(d.queryIdDisplay)) {
        return false;
      }

      return true;
    });
  }, [queryDetails, selectedScenarios, selectedTiers, selectedCategories, selectedWarehouseSizes, selectedQueryIds]);

  // Compute costs from raw credits/dbus using current pricing
  const dataWithCosts = useMemo(() => {
    return filteredData.map((row) => ({
      ...row,
      snowflake: row.snowflake
        ? {
            ...row.snowflake,
            cost:
              row.snowflake.credits != null
                ? row.snowflake.credits * snowCreditPrice
                : null,
          }
        : null,
      databricks: row.databricks
        ? {
            ...row.databricks,
            cost:
              row.databricks.dbus != null
                ? row.databricks.dbus * dbxDbuPrice
                : null,
          }
        : null,
    }));
  }, [filteredData, snowCreditPrice, dbxDbuPrice]);

  const clearFilters = () => {
    setSelectedScenarios([]);
    setSelectedTiers([]);
    setSelectedCategories([]);
    setSelectedWarehouseSizes([]);
    setSelectedQueryIds([]);
  };

  const hasFilters =
    selectedScenarios.length > 0 ||
    selectedTiers.length > 0 ||
    selectedCategories.length > 0 ||
    selectedWarehouseSizes.length > 0 ||
    selectedQueryIds.length > 0;

  return (
    <div
      style={{
        backgroundColor: "#1e293b",
        borderRadius: "12px",
        padding: "20px",
      }}
    >
      {/* Filters Section */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: "24px",
          flexWrap: "wrap",
          marginBottom: "20px",
          paddingBottom: "16px",
          borderBottom: "1px solid #334155",
        }}
      >
        <MultiSelectFilter
          label="Scenario"
          options={availableScenarios}
          selected={selectedScenarios}
          onChange={setSelectedScenarios}
          getOptionLabel={(s) => SCENARIO_LABELS[s] || s}
        />
        <MultiSelectFilter
          label="Warehouse Tier"
          options={availableTiers}
          selected={selectedTiers}
          onChange={setSelectedTiers}
          getOptionLabel={(t) => `Tier ${t}`}
        />
        <MultiSelectFilter
          label="Warehouse Size"
          options={availableWarehouseSizes}
          selected={selectedWarehouseSizes}
          onChange={setSelectedWarehouseSizes}
        />
        <MultiSelectFilter
          label="Query Category"
          options={availableCategories}
          selected={selectedCategories}
          onChange={setSelectedCategories}
        />
        <MultiSelectFilter
          label="Query Name"
          options={availableQueryIds}
          selected={selectedQueryIds}
          onChange={setSelectedQueryIds}
        />
        {hasFilters && (
          <div>
            <button
              onClick={clearFilters}
              style={{
                backgroundColor: "transparent",
                border: "1px solid #475569",
                borderRadius: "6px",
                padding: "6px 12px",
                color: "#94a3b8",
                fontSize: "12px",
                cursor: "pointer",
                transition: "all 0.2s",
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
              Clear All Filters
            </button>
          </div>
        )}
      </div>

      {/* KPI Tiles */}
      <QueryDetailsKpiTiles data={dataWithCosts} />

      {/* Results Count */}
      <div
        style={{
          color: "#9ca3af",
          fontSize: "12px",
          marginBottom: "12px",
        }}
      >
        Showing {dataWithCosts.length} quer{dataWithCosts.length === 1 ? "y" : "ies"}
      </div>

      {/* Data Table */}
      <QueryDetailsTable data={dataWithCosts} />
    </div>
  );
}
