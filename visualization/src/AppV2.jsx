import { useState } from "react";
import { TabNavigation } from "./components/TabNavigation";
import { LegacyTab } from "./components/LegacyTab";
import { SummaryTab } from "./components/SummaryTab";
import benchmarkData from "./data/benchmarkData.json";

function AppV2() {
  const [activeTab, setActiveTab] = useState(1);

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#0f172a', color: 'white' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '12px 16px 8px' }}>
        {/* Header */}
        <header style={{ textAlign: 'center', marginBottom: '10px' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '2px', backgroundImage: 'linear-gradient(to right, #00D4FF 0%, #00D4FF 35%, #FF3621 65%, #FF3621 100%)', WebkitBackgroundClip: 'text', backgroundClip: 'text', WebkitTextFillColor: 'transparent', color: 'transparent' }}>
            Snowflake vs Databricks
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '0.75rem' }}>
            TPC-H Benchmark Performance Comparison
          </p>
        </header>

        {/* Tab Navigation */}
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Tab Content */}
        <div style={{ minHeight: '60vh' }}>
          {activeTab === 1 && <SummaryTab />}
          {activeTab === 2 && <LegacyTab />}
        </div>

        {/* Footer */}
        <footer style={{ textAlign: 'center', marginTop: '8px', color: '#6b7280', fontSize: '0.7rem' }}>
          <p style={{ margin: 0 }}>
            Data exported:{" "}
            {new Date(benchmarkData.exportedAt).toLocaleDateString()}
          </p>
        </footer>
      </div>
    </div>
  );
}

export default AppV2;
