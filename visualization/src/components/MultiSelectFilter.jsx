import { useState, useRef, useEffect } from "react";

const labelStyle = {
  color: "#9ca3af",
  fontSize: "11px",
  display: "block",
  marginBottom: "4px",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const dropdownButtonStyle = {
  backgroundColor: "#1e293b",
  border: "1px solid #334155",
  borderRadius: "6px",
  padding: "6px 10px",
  color: "#e2e8f0",
  fontSize: "13px",
  minWidth: "150px",
  cursor: "pointer",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "8px",
};

const dropdownMenuStyle = {
  position: "absolute",
  top: "100%",
  left: 0,
  marginTop: "4px",
  backgroundColor: "#1e293b",
  border: "1px solid #334155",
  borderRadius: "6px",
  padding: "4px 0",
  minWidth: "100%",
  maxHeight: "250px",
  overflowY: "auto",
  zIndex: 100,
  boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
};

const optionStyle = {
  padding: "6px 10px",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  gap: "8px",
  fontSize: "13px",
  color: "#e2e8f0",
  transition: "background-color 0.1s",
};

const checkboxStyle = {
  width: "14px",
  height: "14px",
  accentColor: "#29B5E8",
};

export function MultiSelectFilter({ label, options, selected, onChange, getOptionLabel }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const allSelected = selected.length === 0;

  const toggleOption = (option) => {
    if (selected.includes(option)) {
      onChange(selected.filter((s) => s !== option));
    } else {
      onChange([...selected, option]);
    }
  };

  const selectAll = () => {
    onChange([]);
  };

  const isSelected = (option) => {
    if (selected.length === 0) return true;
    return selected.includes(option);
  };

  // Build display text
  let displayText = "All";
  if (selected.length > 0) {
    if (selected.length === 1) {
      displayText = getOptionLabel ? getOptionLabel(selected[0]) : selected[0];
    } else {
      displayText = `${selected.length} selected`;
    }
  }

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <label style={labelStyle}>{label}</label>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={dropdownButtonStyle}
        type="button"
      >
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {displayText}
        </span>
        <span style={{ color: "#64748b", fontSize: "10px" }}>
          {isOpen ? "▲" : "▼"}
        </span>
      </button>

      {isOpen && (
        <div style={dropdownMenuStyle}>
          {/* All option */}
          <div
            style={{
              ...optionStyle,
              borderBottom: "1px solid #334155",
              marginBottom: "4px",
            }}
            onClick={selectAll}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#334155")}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
          >
            <input
              type="checkbox"
              checked={allSelected}
              readOnly
              style={checkboxStyle}
            />
            <span>All</span>
          </div>

          {/* Individual options */}
          {options.map((option) => {
            const optionLabel = getOptionLabel ? getOptionLabel(option) : option;
            const checked = isSelected(option);

            return (
              <div
                key={option}
                style={optionStyle}
                onClick={() => toggleOption(option)}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#334155")}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  readOnly
                  style={checkboxStyle}
                />
                <span>{optionLabel}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
