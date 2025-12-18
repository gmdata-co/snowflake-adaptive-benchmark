import { useState } from "react";
import { TabNavigation } from "./components/TabNavigation";
import { SummaryTab } from "./components/SummaryTab";
import { QueryDetailsTab } from "./components/QueryDetailsTab";
import { SnowflakeLogo } from "./components/SnowflakeLogo";
import { DatabricksLogo } from "./components/DatabricksLogo";
import benchmarkData from "./data/benchmarkData.json";

const DEFAULT_SNOW_CREDIT_PRICE = 2.0;
const DEFAULT_DBX_DBU_PRICE = 0.7;

const SCENARIOS = [
  { id: 'normal', label: '22 Sequential Queries' },
  { id: 'concurrent', label: '22 Concurrent Queries' },
  { id: 'coldstart', label: '5 Cold Start Queries' },
  { id: 'ctas', label: 'CTAS Query' },
  { id: 'dml', label: 'DML Refresh' },
];

function HamburgerMenu({ isOpen, onToggle, scenarios, onSelectScenario }) {
  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={onToggle}
        style={{
          backgroundColor: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: '#94a3b8',
          padding: '4px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        onMouseEnter={(e) => e.target.style.color = '#fff'}
        onMouseLeave={(e) => e.target.style.color = '#94a3b8'}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </svg>
      </button>
      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          marginTop: '8px',
          backgroundColor: '#1e293b',
          borderRadius: '8px',
          border: '1px solid #334155',
          padding: '8px',
          minWidth: '180px',
          zIndex: 300,
        }}>
          <div style={{ color: '#9ca3af', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600', padding: '4px 8px', marginBottom: '4px' }}>
            Jump to
          </div>
          {scenarios.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => {
                const element = document.getElementById(`scenario-${id}`);
                if (element) {
                  const y = element.getBoundingClientRect().top + window.pageYOffset - 80;
                  window.scrollTo({ top: y, behavior: 'smooth' });
                }
                onToggle();
              }}
              style={{
                display: 'block',
                width: '100%',
                background: 'transparent',
                border: 'none',
                borderRadius: '4px',
                padding: '8px',
                textAlign: 'left',
                cursor: 'pointer',
                color: '#cbd5e1',
                fontSize: '12px',
              }}
              onMouseEnter={(e) => e.target.style.backgroundColor = '#334155'}
              onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function HeaderPricingInputs({ snowCreditPrice, dbxDbuPrice, onSnowPriceChange, onDbxPriceChange }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: '48px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '2px', whiteSpace: 'nowrap' }}>
        <SnowflakeLogo size={14} />
        <span style={{ color: '#9ca3af', fontSize: '11px', lineHeight: '1' }}>$</span>
        <input
          type="text"
          inputMode="decimal"
          value={snowCreditPrice}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            if (!isNaN(val) || e.target.value === '' || e.target.value === '.') {
              onSnowPriceChange(isNaN(val) ? 0 : val);
            }
          }}
          style={{
            width: '40px',
            backgroundColor: 'transparent',
            border: 'none',
            borderBottom: '1px solid #334155',
            padding: '0 4px 2px',
            color: '#29B5E8',
            fontSize: '11px',
            fontFamily: 'monospace',
            textAlign: 'right',
            outline: 'none',
            lineHeight: '1',
          }}
        />
        <span style={{ color: '#64748b', fontSize: '11px', lineHeight: '1', whiteSpace: 'nowrap' }}>/credit</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '2px', whiteSpace: 'nowrap' }}>
        <DatabricksLogo size={14} />
        <span style={{ color: '#9ca3af', fontSize: '11px', lineHeight: '1' }}>$</span>
        <input
          type="text"
          inputMode="decimal"
          value={dbxDbuPrice}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            if (!isNaN(val) || e.target.value === '' || e.target.value === '.') {
              onDbxPriceChange(isNaN(val) ? 0 : val);
            }
          }}
          style={{
            width: '40px',
            backgroundColor: 'transparent',
            border: 'none',
            borderBottom: '1px solid #334155',
            padding: '0 4px 2px',
            color: '#FF3621',
            fontSize: '11px',
            fontFamily: 'monospace',
            textAlign: 'right',
            outline: 'none',
            lineHeight: '1',
          }}
        />
        <span style={{ color: '#64748b', fontSize: '11px', lineHeight: '1', whiteSpace: 'nowrap' }}>/DBU</span>
      </div>
    </div>
  );
}

function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [snowCreditPrice, setSnowCreditPrice] = useState(DEFAULT_SNOW_CREDIT_PRICE);
  const [dbxDbuPrice, setDbxDbuPrice] = useState(DEFAULT_DBX_DBU_PRICE);
  const [activeTab, setActiveTab] = useState("summary");
  const [detailsInitialState, setDetailsInitialState] = useState({ scenario: null, tier: null });

  // Navigate from summary to details with filters pre-applied
  const navigateToDetails = (scenario, tier) => {
    setDetailsInitialState({ scenario, tier });
    setActiveTab("details");
    // Scroll to top when navigating
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#0f172a', color: 'white' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '12px 16px 8px' }}>
        {/* Header */}
        <header style={{ position: 'sticky', top: 0, zIndex: 200, backgroundColor: '#0f172a', paddingTop: '12px', paddingBottom: '10px', marginBottom: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
            {/* Left: pricing inputs */}
            <div style={{ width: '200px' }}>
              <HeaderPricingInputs
                snowCreditPrice={snowCreditPrice}
                dbxDbuPrice={dbxDbuPrice}
                onSnowPriceChange={setSnowCreditPrice}
                onDbxPriceChange={setDbxDbuPrice}
              />
            </div>
            {/* Center: title */}
            <div style={{ textAlign: 'center', flex: 1 }}>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '2px', backgroundImage: 'linear-gradient(to right, #00D4FF 0%, #00D4FF 35%, #FF3621 65%, #FF3621 100%)', WebkitBackgroundClip: 'text', backgroundClip: 'text', WebkitTextFillColor: 'transparent', color: 'transparent' }}>
                Snowflake vs Databricks
              </h1>
              <p style={{ color: '#9ca3af', fontSize: '0.75rem', margin: 0 }}>
                TPC-H Benchmark Performance Comparison
              </p>
            </div>
            {/* Right: hamburger menu */}
            <div style={{ width: '200px', display: 'flex', justifyContent: 'flex-end' }}>
              <HamburgerMenu
                isOpen={menuOpen}
                onToggle={() => setMenuOpen(!menuOpen)}
                scenarios={SCENARIOS}
              />
            </div>
          </div>
        </header>

        {/* Tab Navigation */}
        <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Tab Content */}
        <div style={{ minHeight: '60vh' }}>
          {activeTab === "summary" && (
            <SummaryTab
              snowCreditPrice={snowCreditPrice}
              dbxDbuPrice={dbxDbuPrice}
              onNavigateToDetails={navigateToDetails}
            />
          )}
          {activeTab === "details" && (
            <QueryDetailsTab
              initialScenario={detailsInitialState.scenario}
              initialTier={detailsInitialState.tier}
              snowCreditPrice={snowCreditPrice}
              dbxDbuPrice={dbxDbuPrice}
            />
          )}
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

export default App;
