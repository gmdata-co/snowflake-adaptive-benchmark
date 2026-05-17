import { createContext, useContext, useMemo, useState } from "react";
import { ScenarioSummaryChart } from "./components/ScenarioSummaryChart";
import { SnowflakeLogo, GEN1_COLOR } from "./components/SnowflakeLogo";
import { DatabricksLogo, ADAPTIVE_COLOR } from "./components/DatabricksLogo";
import benchmarkData from "./data/benchmarkData.json";

const DEFAULT_CREDIT_PRICE = 2.0;

// Shared idle-policy selection. One state for the whole page so every chart's
// toggle stays in sync; the control just renders at the chart level instead of
// in a global banner.
const PolicyContext = createContext(null);

// Group raw comparison rows by their synthetic scenario id.
function groupByScenario(comparisons) {
  const out = {};
  for (const c of comparisons || []) {
    (out[c.scenario] ||= []).push(c);
  }
  for (const id of Object.keys(out)) {
    out[id].sort((a, b) => a.warehouseTier - b.warehouseTier);
  }
  return out;
}

// Recompute $ from credits so the single $/credit lever drives both
// warehouse types (gen1 stores `credits`, adaptive stores `dbus`; both are
// Snowflake credits; the JSON's precomputed `cost` assumed $2/credit).
function priced(rows, price) {
  return rows.map((c) => ({
    ...c,
    snowflake: c.snowflake
      ? {
          ...c.snowflake,
          cost:
            c.snowflake.credits != null
              ? +(c.snowflake.credits * price).toFixed(2)
              : c.snowflake.cost,
        }
      : null,
    databricks: c.databricks
      ? {
          ...c.databricks,
          cost:
            c.databricks.dbus != null
              ? +(c.databricks.dbus * price).toFixed(2)
              : c.databricks.cost,
        }
      : null,
  }));
}

// Aggregate verdict across all tiers in a panel: mean time & cost per type.
function computeVerdict(rows) {
  let gT = 0, gC = 0, aT = 0, aC = 0, n = 0;
  for (const c of rows) {
    if (!c.snowflake || !c.databricks) continue;
    gT += c.snowflake.time; gC += c.snowflake.cost;
    aT += c.databricks.time; aC += c.databricks.cost;
    n += 1;
  }
  if (!n) return null;
  const mk = (g, a) => {
    if (Math.abs(g - a) / Math.max(g, a) < 0.02)
      return { winner: null, pct: 0, label: "≈ even" };
    const adaptiveWins = a < g;
    const hi = Math.max(g, a), lo = Math.min(g, a);
    return {
      winner: adaptiveWins ? "adaptive" : "gen1",
      pct: Math.round(((hi - lo) / hi) * 100),
    };
  };
  return { speed: mk(gT, aT), cost: mk(gC, aC) };
}

function VerdictTile({ kind, v }) {
  const color =
    v.winner === "adaptive"
      ? ADAPTIVE_COLOR
      : v.winner === "gen1"
      ? GEN1_COLOR
      : "#64748b";
  return (
    <div style={{ flex: 1, textAlign: "center" }}>
      <div
        style={{
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          fontSize: "0.66rem",
          fontWeight: 700,
          color: "#64748b",
          marginBottom: 3,
        }}
      >
        {kind === "speed" ? "Faster overall" : "Cheaper overall"}
      </div>
      <div style={{ color, fontWeight: 800, fontSize: "1.15rem", lineHeight: 1.1 }}>
        {v.winner
          ? `${v.winner === "adaptive" ? "Adaptive" : "Gen1"} · ${v.pct}% ${
              kind === "speed" ? "faster" : "cheaper"
            }`
          : v.label}
      </div>
    </div>
  );
}

function ChartBlock({ rows, domainRows, caption }) {
  const [hoveredTier, setHoveredTier] = useState(null);
  const verdict = useMemo(() => computeVerdict(rows), [rows]);
  const fallback = useMemo(
    () => (rows || []).some((r) => r.policyFallback),
    [rows]
  );
  return (
    <figure style={{ margin: "0 0 8px" }}>
      <ChartPolicyToggle fallback={fallback} />
      {verdict && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            background: "#0b1424",
            border: "1px solid #1e293b",
            borderBottom: "none",
            borderRadius: "12px 12px 0 0",
            padding: "12px 16px",
          }}
        >
          <VerdictTile kind="speed" v={verdict.speed} />
          <div style={{ width: 1, alignSelf: "stretch", background: "#1e293b" }} />
          <VerdictTile kind="cost" v={verdict.cost} />
        </div>
      )}
      <div
        style={{
          background: "#0b1424",
          border: "1px solid #1e293b",
          borderRadius: verdict ? "0 0 12px 12px" : 12,
          padding: "8px 8px 0",
        }}
      >
        <ScenarioSummaryChart
          scenarioData={rows}
          domainData={domainRows}
          hoveredTier={hoveredTier}
          onHoverTier={setHoveredTier}
        />
      </div>
      {caption && (
        <figcaption
          style={{
            color: "#64748b",
            fontSize: "0.78rem",
            textAlign: "center",
            marginTop: 6,
          }}
        >
          {caption}
        </figcaption>
      )}
    </figure>
  );
}

function Takeaway({ children }) {
  return (
    <div
      style={{
        borderLeft: `3px solid ${ADAPTIVE_COLOR}`,
        background: "rgba(245,158,11,0.07)",
        borderRadius: "0 8px 8px 0",
        padding: "12px 16px",
        margin: "18px 0 4px",
      }}
    >
      <div
        style={{
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          fontSize: "0.7rem",
          fontWeight: 700,
          color: ADAPTIVE_COLOR,
          marginBottom: 4,
        }}
      >
        Takeaway
      </div>
      <p style={{ margin: 0, color: "#e2e8f0", fontSize: "0.95rem", lineHeight: 1.6 }}>
        {children}
      </p>
    </div>
  );
}

function P({ children }) {
  return (
    <p
      style={{
        color: "#cbd5e1",
        fontSize: "1rem",
        lineHeight: 1.7,
        margin: "0 0 14px",
      }}
    >
      {children}
    </p>
  );
}

function SectionHeading({ kicker, title, goal }) {
  return (
    <header style={{ margin: "0 0 16px" }}>
      <div
        style={{
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          fontSize: "0.72rem",
          fontWeight: 700,
          color: "#64748b",
          marginBottom: 6,
        }}
      >
        {kicker}
      </div>
      <h2
        style={{
          fontSize: "1.7rem",
          fontWeight: 800,
          color: "#f1f5f9",
          margin: "0 0 10px",
          lineHeight: 1.2,
        }}
      >
        {title}
      </h2>
      <div
        style={{
          display: "flex",
          gap: 10,
          alignItems: "baseline",
          color: "#94a3b8",
          fontSize: "0.95rem",
        }}
      >
        <span
          style={{
            color: ADAPTIVE_COLOR,
            fontWeight: 700,
            fontSize: "0.72rem",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            whiteSpace: "nowrap",
          }}
        >
          The goal
        </span>
        <span>{goal}</span>
      </div>
    </header>
  );
}

function Section({ id, children }) {
  return (
    <section
      id={id}
      style={{
        padding: "44px 0",
        borderTop: "1px solid #1e293b",
      }}
    >
      {children}
    </section>
  );
}

function Legend() {
  return (
    <div style={{ display: "flex", gap: 24, alignItems: "center", flexWrap: "wrap" }}>
      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <SnowflakeLogo size={18} />
        <span style={{ color: GEN1_COLOR, fontWeight: 600, fontSize: "0.85rem" }}>
          Gen1 warehouse
        </span>
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <DatabricksLogo size={18} />
        <span style={{ color: ADAPTIVE_COLOR, fontWeight: 600, fontSize: "0.85rem" }}>
          Adaptive warehouse
        </span>
      </span>
    </div>
  );
}

// Idle-policy colors: wait-for-suspend = the realistic default (blue),
// immediate-drop = the "no idle" alternate (amber) so the active dataset is
// unmistakable at a glance.
const POLICY_COLOR = {
  wait_for_suspend: ADAPTIVE_COLOR,
  immediate_drop: "#f59e0b",
};

// Compact, chart-level policy toggle: a small segmented switch plus a single
// muted line of context. All instances share PolicyContext, so flipping one
// flips every chart in sync.
function ChartPolicyToggle({ fallback = false }) {
  const { policy, setPolicy, policyMeta } = useContext(PolicyContext);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        flexWrap: "wrap",
        margin: "0 0 6px",
      }}
    >
      <div
        style={{
          display: "flex",
          border: "1px solid #334155",
          borderRadius: 6,
          overflow: "hidden",
          flexShrink: 0,
        }}
        title="Which warehouse-shutdown policy's data to show"
      >
        {POLICY_ORDER.map((p) => {
          const active = p === policy;
          const c = POLICY_COLOR[p] || ADAPTIVE_COLOR;
          return (
            <button
              key={p}
              onClick={() => setPolicy(p)}
              style={{
                background: active ? c : "transparent",
                color: active ? "#0f172a" : "#94a3b8",
                border: "none",
                padding: "3px 10px",
                fontSize: "0.7rem",
                fontWeight: 700,
                cursor: "pointer",
                letterSpacing: "0.03em",
              }}
            >
              {policyMeta[p]?.short || p}
            </button>
          );
        })}
      </div>
      <span style={{ color: "#64748b", fontSize: "0.74rem", lineHeight: 1.4 }}>
        {policyMeta[policy]?.label || ""}
        {fallback && (
          <span style={{ color: "#475569" }}>
            {" "}
            · reuses the full prior run (no separate idle-tail measurement)
          </span>
        )}
      </span>
    </div>
  );
}

function PriceControl({ price, onChange }) {
  const [text, setText] = useState(String(price));
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        gap: 4,
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}>$</span>
      <input
        type="text"
        inputMode="decimal"
        value={text}
        onChange={(e) => {
          const t = e.target.value;
          if (/^[0-9]*\.?[0-9]*$/.test(t)) {
            setText(t);
            const v = parseFloat(t);
            if (!isNaN(v)) onChange(v);
          }
        }}
        style={{
          width: 44,
          background: "transparent",
          border: "none",
          borderBottom: "1px solid #334155",
          padding: "0 4px 2px",
          color: "#e2e8f0",
          fontSize: "0.85rem",
          fontFamily: "monospace",
          textAlign: "right",
          outline: "none",
        }}
      />
      <span style={{ color: "#64748b", fontSize: "0.85rem" }}>/ credit</span>
    </div>
  );
}

const POLICY_ORDER = ["wait_for_suspend", "immediate_drop"];

function App() {
  const [price, setPrice] = useState(DEFAULT_CREDIT_PRICE);
  const [policy, setPolicy] = useState(
    benchmarkData.defaultPolicy || "wait_for_suspend"
  );

  const policies = benchmarkData.policies || {};
  const policyMeta = benchmarkData.policyMeta || {};
  const activeComparisons =
    policies[policy]?.comparisons || benchmarkData.comparisons;

  const grouped = useMemo(
    () => groupByScenario(activeComparisons),
    [activeComparisons]
  );
  const get = (id) => priced(grouped[id] || [], price);

  // Axis domains are computed from BOTH policies' points (union), so toggling
  // wait <-> immediate never rebuilds the axes — only the plotted dots move.
  // Still reprices with the $/credit lever (intended).
  const groupedAll = useMemo(
    () =>
      groupByScenario([
        ...(policies.wait_for_suspend?.comparisons || []),
        ...(policies.immediate_drop?.comparisons || []),
        ...(benchmarkData.comparisons || []),
      ]),
    [policies]
  );
  const getDomain = (id) => priced(groupedAll[id] || [], price);

  return (
    <PolicyContext.Provider value={{ policy, setPolicy, policyMeta }}>
    <div style={{ minHeight: "100vh", background: "#0f172a", color: "white" }}>
      {/* Sticky minimal control bar */}
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 100,
          background: "rgba(15,23,42,0.92)",
          backdropFilter: "blur(6px)",
          borderBottom: "1px solid #1e293b",
        }}
      >
        <div
          style={{
            maxWidth: 900,
            margin: "0 auto",
            padding: "10px 24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 16,
          }}
        >
          <Legend />
          <PriceControl price={price} onChange={setPrice} />
        </div>
      </div>

      <article style={{ maxWidth: 900, margin: "0 auto", padding: "0 24px 80px" }}>
        {/* Lede */}
        <div style={{ padding: "56px 0 8px" }}>
          <div
            style={{
              textTransform: "uppercase",
              letterSpacing: "0.14em",
              fontSize: "0.74rem",
              fontWeight: 700,
              color: ADAPTIVE_COLOR,
              marginBottom: 12,
            }}
          >
            Snowflake warehouse benchmark
          </div>
          <h1
            style={{
              fontSize: "2.6rem",
              fontWeight: 800,
              lineHeight: 1.15,
              margin: "0 0 18px",
              color: "#f8fafc",
            }}
          >
            Adaptive vs Gen1: where does Snowflake's new
            warehouse actually save you money?
          </h1>
          <P>
            Snowflake's new <strong>Adaptive</strong> Warehouse promises to
            take sizing off your hands: instead of picking a fixed size and
            paying for capacity your smallest queries will never fully use,
            Snowflake auto-pools and scales compute behind the scenes and
            charges you only for what each query actually consumes. The
            obvious question is
            whether that actually saves money, and where. To find out we put it
            head-to-head against the classic <strong>Gen1</strong> warehouse on
            TPC-H <strong>SF100</strong> (~600M-row <code>lineitem</code>),
            across four sizes (Small → XLarge) and four workload shapes.
          </P>
          <P>
            Adaptive has two dials: <strong>MAX_QUERY_PERFORMANCE_LEVEL</strong>{" "}
            (its size cap) and <strong>QTM</strong>, the query-throughput
            multiplier, a concurrency/burst dial. Because Snowflake now
            defaults new warehouses to Gen2, the baseline was explicitly pinned
            to true <strong>Gen1</strong> so this is an Adaptive-vs-Gen1
            comparison, not Gen2 in disguise. Every variant ran on its own
            freshly-created warehouse so Snowflake's billing never smeared
            credits between configs. One lever is yours: the{" "}
            <strong>$/credit</strong> price up top (default $2) recomputes every
            chart live.
          </P>
          <P>
            Every chart below is the same shape: <strong>duration on the
            x-axis, dollars on the y-axis</strong>. Bottom-left is the dream:
            fast and cheap. Hover any point for the head-to-head.
          </P>
        </div>

        {/* 1. Single query */}
        <Section id="single_query_qtm2">
          <SectionHeading
            kicker="Chapter 1 · One question"
            title="The cheapest way to answer a single query"
            goal="Run one query that finishes in under a minute, for the least possible spend."
          />
          <P>
            Every size answers query 1 in well under a minute; the slowest
            here is Gen1 Small at 8 seconds, the fastest is ~2.5s. Latency
            isn't the constraint; <em>spend</em> is. So the question becomes:
            how little can you pay for an answer you'll get either way?
          </P>
          <P>
            On Gen1, scaling up barely helps (8.2s shrinks to 2.6s), but cost
            climbs almost linearly, $0.07 → $0.53, because Gen1 bills the whole
            warehouse against a 60-second minimum even when the query took
            three. Adaptive bills the <em>query</em>, so reaching for a bigger
            size to shave a couple of seconds barely moves the bill ($0.09 →
            $0.38).
          </P>
          <ChartBlock
            rows={get("single_query_qtm2")}
            domainRows={getDomain("single_query_qtm2")}
            caption="TPC-H query 1, run once per warehouse. Adaptive at QTM=2."
          />
          <Takeaway>
            For a one-off query, Gen1 Small is the cost floor at ~$0.07; don't
            size up, it only buys seconds you don't need at a price you do pay.
            If you want the speed of a big warehouse without the size tax,
            Adaptive delivers XLarge latency for a fraction of Gen1 XLarge's
            cost.
          </Takeaway>
        </Section>

        {/* 2. Sequential */}
        <Section id="sequential_qtm2">
          <SectionHeading
            kicker="Chapter 2 · A continuous workload"
            title="A warehouse kept continuously busy"
            goal="Simulate a steady, back-to-back workload that keeps a warehouse fully saturated, so you pay only for useful work, never idle."
          />
          <P>
            Twenty-two queries run in sequence with no gaps, so the warehouse
            never goes idle. Whether that load is a scheduled job chain, a
            steady stream of requests, or an analyst working all day, the shape
            is the same: continuous work. This is the cleanest test of raw
            compute value, because with no idle time to reclaim, elasticity has
            nothing to optimize away.
          </P>
          <P>
            Adaptive is the faster engine at every size, clearing the
            22-query sequence roughly 13 to 15 percent quicker (533s vs 617s
            at Small, 200s vs 220s at XLarge). On cost the two trade places by
            scale: at Small, Gen1 is cheaper ($0.82 vs $1.09); by Medium they
            are effectively even ($1.02 vs $1.00); and from Large up Adaptive
            pulls clearly ahead ($1.36 vs $1.73 at Large, $1.72 vs $2.51 at
            XLarge). The bigger the warehouse, the more Adaptive's per-query
            billing beats paying for a full fixed size.
          </P>
          <ChartBlock
            rows={get("sequential_qtm2")}
            domainRows={getDomain("sequential_qtm2")}
            caption="22 TPC-H queries, sequential. Adaptive at QTM=2."
          />
          <Takeaway>
            On a continuously busy warehouse, Adaptive is consistently the
            faster engine, and it is the cheaper one at every size from Medium
            up. Gen1 holds a cost edge only at the smallest tier; the larger
            the warehouse, the more decisively Adaptive wins on both speed and
            price.
          </Takeaway>
        </Section>

        {/* 3. Concurrent */}
        <Section id="concurrent_qtm2">
          <SectionHeading
            kicker="Chapter 3 · Everyone at once"
            title="Concurrency: Adaptive's home turf"
            goal="Fire 22 queries simultaneously: a BI tool, a dashboard refresh, a whole team hitting it together."
          />
          <P>
            Gen1 absorbs a concurrency spike with multi-cluster scale-out,
            here capped at four clusters, billed per active cluster. In
            practice it never hit that cap: Medium, Large and XLarge each
            cleared the 22-query burst on just <strong>two</strong> clusters,
            and Small needed <strong>three</strong>. The pattern is telling:
            the smaller the warehouse, the more clusters it must fan out to,
            because each Small cluster has the least capacity to absorb
            concurrency. Adaptive instead pools the queries into shared compute
            and bursts via the <strong>QTM</strong> dial: higher QTM means more
            parallel compute (faster) at more credits.
          </P>
          <P>
            At <strong>QTM=2</strong>, Adaptive is cheaper at every single size
            at matched speed; Small costs $0.25 against Gen1's $0.53, a clean
            halving. Push to <strong>QTM=8</strong> and it gets faster still;
            Small and Medium become the sweet spot (Medium: 80s and $0.21,
            faster <em>and</em> roughly a third of Gen1's cost). But at Large
            and XLarge, QTM=8 overshoots: the burst buys little extra speed and
            cost sails past Gen1 ($1.53 vs $1.08 at XLarge).
          </P>
          <ChartBlock
            rows={get("concurrent_qtm2")}
            domainRows={getDomain("concurrent_qtm2")}
            caption="22 concurrent queries · Adaptive QTM=2 vs Gen1 multi-cluster (max 4)."
          />
          <ChartBlock
            rows={get("concurrent_qtm8")}
            domainRows={getDomain("concurrent_qtm8")}
            caption="Same workload · Adaptive QTM=8: more burst, faster, but cost climbs at the big sizes."
          />
          <Takeaway>
            Under real concurrency Adaptive wins decisively on cost. Keep the
            size small and let QTM do the scaling; small/medium at a high QTM
            beats Gen1 multi-cluster on both speed and dollars. Reserve large
            sizes + high QTM for when latency truly outranks the bill.
          </Takeaway>
        </Section>

        {/* 4. DML */}
        <Section id="dml_qtm2">
          <SectionHeading
            kicker="Chapter 4 · The pipeline"
            title="A DML refresh: the ETL write job"
            goal="A delete + insert refresh: bursty work, then done, the shape of every ELT pipeline step."
          />
          <P>
            A pipeline step does a chunk of work and stops. Gen1 makes you
            commit to a size up front and pays for it whether the burst needed
            it or not, and at Large/XLarge that idle tax is brutal: $0.27 and
            $0.53 for work that took seconds. Adaptive sizes itself to the
            burst: Large lands at $0.10, XLarge at $0.14, up to ~4× cheaper at
            equal-or-better speed.
          </P>
          <P>
            The lone exception is Small, where Adaptive ($0.14) trails Gen1
            ($0.07): there's no oversized idle warehouse to reclaim, so
            Adaptive's per-query premium has nothing to pay it back with;
            exactly the pattern from Chapter 2.
          </P>
          <ChartBlock
            rows={get("dml_qtm2")}
            domainRows={getDomain("dml_qtm2")}
            caption="Delete + insert refresh on lineitem. Adaptive at QTM=2."
          />
          <Takeaway>
            For bursty pipeline writes, Adaptive removes the "guess the size"
            tax; sizing up is nearly free, so you stop paying for an oversized
            warehouse that idles the moment the batch finishes.
          </Takeaway>
        </Section>

        {/* Bottom line */}
        <Section id="bottom-line">
          <SectionHeading
            kicker="The bottom line"
            title="When to reach for which warehouse"
            goal="One pattern explains every chapter above."
          />
          <P>
            Adaptive wins wherever a Gen1 warehouse would otherwise sit partly
            idle: concurrency spikes, bursty pipelines, big sizes you only
            need for seconds. Even on a continuously saturated warehouse it
            stays the faster engine, and the cost gap turns in its favor as
            soon as you move past the smallest size. Gen1's remaining edge is
            narrow: the very smallest, steadily busy warehouse, where its flat
            rate undercuts Adaptive's per-query premium.
          </P>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
              marginTop: 8,
            }}
          >
            {[
              ["One-off query", "Gen1 Small, the $0.07 floor. Or Adaptive if you want big-warehouse speed without the size tax."],
              ["Continuous single user", "Close call. Adaptive is faster at every size; Gen1 wins on cost only at Small. From Medium up, Adaptive is both faster and cheaper."],
              ["Concurrency / BI", "Adaptive, small size, QTM as the dial. Cheaper and faster than Gen1 multi-cluster."],
              ["Pipeline writes", "Adaptive at Large/XLarge: sizing up is nearly free; no idle tax after the batch."],
            ].map(([h, b]) => (
              <div
                key={h}
                style={{
                  background: "#0b1424",
                  border: "1px solid #1e293b",
                  borderRadius: 10,
                  padding: "14px 16px",
                }}
              >
                <div
                  style={{
                    color: ADAPTIVE_COLOR,
                    fontWeight: 700,
                    fontSize: "0.9rem",
                    marginBottom: 6,
                  }}
                >
                  {h}
                </div>
                <div
                  style={{ color: "#cbd5e1", fontSize: "0.9rem", lineHeight: 1.55 }}
                >
                  {b}
                </div>
              </div>
            ))}
          </div>
        </Section>

        <footer
          style={{
            textAlign: "center",
            marginTop: 32,
            color: "#475569",
            fontSize: "0.75rem",
          }}
        >
          Data exported{" "}
          {new Date(benchmarkData.exportedAt).toLocaleDateString()} · TPC-H
          SF100 · costs recomputed at ${price}/credit
        </footer>
      </article>
    </div>
    </PolicyContext.Provider>
  );
}

export default App;
