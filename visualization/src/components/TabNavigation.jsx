export function TabNavigation({ activeTab, onTabChange }) {
  const tabs = [
    { id: "summary", label: "Summary" },
    { id: "details", label: "Query Details" },
  ];

  return (
    <div style={{ display: "flex", justifyContent: "center", gap: "8px", marginBottom: "16px" }}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          style={{
            padding: "8px 20px",
            borderRadius: "8px",
            border: "none",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: "600",
            transition: "all 0.2s ease",
            backgroundColor: activeTab === tab.id ? "#29B5E8" : "#334155",
            color: activeTab === tab.id ? "#0f172a" : "#9ca3af",
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
