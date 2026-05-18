import { createContext, useContext, useMemo, useState } from "react";
import { ScenarioSummaryChart } from "./components/ScenarioSummaryChart";
import { Gen1Logo, GEN1_COLOR } from "./components/Gen1Logo";
import { AdaptiveLogo, ADAPTIVE_COLOR } from "./components/AdaptiveLogo";
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
    gen1: c.gen1
      ? {
          ...c.gen1,
          cost:
            c.gen1.credits != null
              ? +(c.gen1.credits * price).toFixed(2)
              : c.gen1.cost,
        }
      : null,
    adaptive: c.adaptive
      ? {
          ...c.adaptive,
          cost:
            c.adaptive.dbus != null
              ? +(c.adaptive.dbus * price).toFixed(2)
              : c.adaptive.cost,
        }
      : null,
  }));
}

// Aggregate verdict across all tiers in a panel: mean time & cost per type.
function computeVerdict(rows) {
  let gT = 0, gC = 0, aT = 0, aC = 0, n = 0;
  for (const c of rows) {
    if (!c.gen1 || !c.adaptive) continue;
    gT += c.gen1.time; gC += c.gen1.cost;
    aT += c.adaptive.time; aC += c.adaptive.cost;
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
        <Gen1Logo size={18} />
        <span style={{ color: GEN1_COLOR, fontWeight: 600, fontSize: "0.85rem" }}>
          Gen1 warehouse
        </span>
      </span>
      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <AdaptiveLogo size={18} />
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
  // wait <-> immediate never rebuilds the axes; only the plotted dots move.
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
            On Gen1 the size dial behaves exactly as you would expect. Step up
            a size and the query time drops by roughly half while the price
            roughly doubles: Small in 9.5s for $0.07, Medium in 4.3s for $0.14,
            Large in 3.1s for $0.28. By XLarge it is pure diminishing returns,
            $0.55 for 3.4s, no faster than Large at double the price.
          </P>
          <P>
            On Adaptive the picture is more interesting. Small, Medium and
            Large stay relatively close together, then XLarge breaks away as
            the outlier: it costs roughly 4x Small and Medium ($0.38 vs $0.09)
            while finishing only about a second faster than Medium (2.7s vs
            3.8s). You pay a large premium for a speedup you can barely measure.
          </P>
          <ChartBlock
            rows={get("single_query_qtm2")}
            domainRows={getDomain("single_query_qtm2")}
            caption="TPC-H query 1, run once per warehouse. Adaptive at QTM=2."
          />
          <Takeaway>
            If you let Snowflake reach for the larger resources, it will
            happily do so, even when a smaller warehouse would have
            produced a near-identical answer. The size cap does not appear to
            push your work down onto smaller compute on its own; set it high
            and you pay high. That caveat aside, Adaptive still wins this
            single query overall, faster on average and cheaper on average than
            Gen1.
          </Takeaway>
        </Section>

        {/* 2. Sequential */}
        <Section id="sequential_qtm2">
          <SectionHeading
            kicker="Chapter 2 · A continuous workload"
            title="A warehouse kept continuously busy"
            goal="Simulate a steady, back-to-back workload that keeps a warehouse fully saturated."
          />
          <P>
            Sixty-six queries run in sequence with no gaps, so the warehouse
            never goes idle. Whether that load is a scheduled job chain, a
            steady stream of requests, or an analyst working all day, the shape
            is the same: continuous work. This is the cleanest test of raw
            compute value, because with no idle time to reclaim, elasticity has
            nothing to optimize away.
          </P>
          <P>
            On raw speed the two are closer than you might expect, and Gen1
            holds its own. Adaptive is dramatically faster only at the
            XS size (about 8.5 minutes vs 11.4); at Small, Medium and
            Large Gen1 actually finishes a touch sooner, and at XLarge they
            tie at roughly ~3.2 minutes. On cost Gen1 leads across most of the range
            and in aggregate.
          </P>
          <ChartBlock
            rows={get("sequential_qtm2")}
            domainRows={getDomain("sequential_qtm2")}
            caption="22 TPC-H queries, sequential. Adaptive at QTM=2."
          />
          <Takeaway>
            On a continuously busy warehouse, Gen1 is the workhorse: speed
            comparable to Adaptive across most sizes, and cheaper from XSmall
            through Large. Adaptive earns its keep at the extremes, a large
            speed jump at the smallest size and a real cost saving only at
            XLarge. For steady, saturated workloads in the middle of the size
            range, a fixed Gen1 warehouse wins this scenario.
          </Takeaway>
        </Section>

        {/* 3. Concurrent */}
        <Section id="concurrent_qtm2">
          <SectionHeading
            kicker="Chapter 3 · Everyone at once"
            title="Concurrency: Adaptive is faster, cost depends on size"
            goal="Fire 22 queries simultaneously: a BI tool, a dashboard refresh, a whole team hitting it together."
          />
          <P>
            Gen1 absorbs a concurrency spike with multi-cluster scale-out,
            here capped at four clusters and billed per active cluster.
            Adaptive instead pools the queries into shared compute and bursts
            via the <strong>QTM</strong> dial: a higher QTM buys more parallel
            compute, and more credits. The idle-tail toggle moves only Gen1:
            dropping the warehouse the instant the burst ends ("no idle tail")
            trims its bill by roughly $0.10 to $0.20 per size; Adaptive has no
            idle concept and is unaffected.
          </P>
          <P>
            At <strong>QTM=2</strong> Adaptive clears the burst faster than
            Gen1 at every size. On cost it is mixed: Adaptive is cheaper at
            the small end (XSmall $0.17 vs $0.23, Small $0.23 vs $0.34) and
            again at XLarge ($0.83 vs $1.26), while Gen1's multi-cluster model
            is the cheaper way through the middle (Medium $0.39 vs $0.54,
            Large $0.69 vs $0.84). Pushing to <strong>QTM=8</strong> is faster
            still, but you pay for it: it runs above Gen1 at most sizes
            (Medium $0.81 vs $0.39, XLarge $1.89 vs $1.26) and only draws
            level at Small. QTM=8 earns its keep only when latency clearly
            outranks the bill.
          </P>
          <ChartBlock
            rows={get("concurrent_qtm2")}
            domainRows={getDomain("concurrent_qtm2")}
            caption="22 concurrent queries, Adaptive QTM=2 vs Gen1 multi-cluster (max 4)."
          />
          <ChartBlock
            rows={get("concurrent_qtm8")}
            domainRows={getDomain("concurrent_qtm8")}
            caption="Same workload, Adaptive QTM=8: faster than QTM=2, but above Gen1 on cost at most sizes."
          />
          <Takeaway>
            For concurrency, Adaptive is the faster engine at every size. The
            catch is the QTM dial. Pushing from QTM=2 to QTM=8 buys only a few
            seconds (Medium 84s to 81s, XLarge 73s to 71s) while the bill
            roughly doubles (Medium $0.54 to $0.81, XLarge $0.83 to $1.89). We
            set QTM too high for this workload: Snowflake did not need that
            headroom to clear the burst, but it still charged us for reserving
            it. Set a high QTM only when you need it.
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
            The job here is a realistic incremental refresh: delete one month
            of <code>lineitem</code> and re-insert it from source, about 1% of
            the rows in a ~600M-row table. The base table is large, but the
            change is not. Snowflake's micro-partition pruning targets exactly
            the partitions that month touches and skips the rest, so the engine
            can see up front that this is a small, surgical write, not a
            full-table rewrite. That is the key to everything below.
          </P>
          <P>
            Gen1 makes
            you commit to a size up front and bills it against the minimum
            whether the burst needed that size or not. The delete plus insert
            finishes in seconds at Small and above, yet Gen1's price climbs
            straight up the dial: $0.05 at XSmall, $0.08 at Small, $0.15 at
            Medium, $0.29 at Large, $0.60 at XLarge. You are paying for the
            warehouse, not the work.
          </P>
          <P>
            Adaptive tells the opposite story, and this is the chapter where it
            looks smartest. Notice how tightly Small, Medium, Large and XLarge
            cluster: $0.05, $0.05, $0.07, $0.09. They even arrive in clean
            price order, yet by XLarge the meter has barely moved off Small. A
            delete plus insert prunes to a narrow slice of partitions, and
            Snowflake clearly recognizes it can finish the job without throwing
            expensive compute at it; it declines to over-provision even when
            the size cap would let it. The bill tracks the work, not the dial.
          </P>
          <P>
            The lone exception is XSmall, where Adaptive ($0.10) trails Gen1
            ($0.05). With no oversized idle warehouse to reclaim, Adaptive's
            per-query premium has nothing to pay it back, exactly the pattern
            from Chapter 2.
          </P>
          <ChartBlock
            rows={get("dml_qtm2")}
            domainRows={getDomain("dml_qtm2")}
            caption="Delete + insert refresh on lineitem. Adaptive at QTM=2."
          />
          <Takeaway>
            This is Adaptive at its smartest. It reads the shape of the work,
            a tightly pruned 1% write against a huge table, and deliberately
            stays small instead of cashing in the size cap you handed it. Even
            when you point it at XLarge, it spends like a Small because that is
            all the job needs, so the bill tracks the resources used, not the
            dial you set. For incremental pipelines, this is exactly the behavior
            you want, and it removes the "guess the size" tax entirely.
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
            One behavior runs underneath every chapter and is worth stating
            plainly: Snowflake never trades speed for savings on its own. It
            optimizes for the fastest answer it can return, and it will reach
            for the full ceiling you give it to get there; the size cap in
            Chapter 1, the QTM headroom in Chapter 3. Over-reserving QTM bought no measurable speedup yet still
            showed up on the bill. The one exception is the DML refresh, where
            efficient pruning lets it stay small because the work itself is
            small, not because it chose to economize.
          </P>
          <P>
            The takeaway is not that
            Adaptive is reckless, it is that the dials are still yours and you need to turn them: it will
            spend up to whatever cap you set, so set the cap to the job.
            Adaptive's pitch was that you stop thinking about sizing; in
            practice this benchmark shows you still have to pick a size, the
            difference is that the size is now a ceiling on spend rather than a
            fixed reservation.
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
              ["One-off query", "The XS Adaptive does very well! Adaptive does tend to be a premium."],
              ["Continuous single user", "Gen1 is the value pick: comparable speed and cheaper from XSmall through Large. Go Adaptive only for the speed jump at the smallest size or the cost saving at XLarge."],
              ["Concurrency / BI", "Adaptive is faster at every size; cheaper at the small sizes and at XLarge. Gen1 multi-cluster is the cheaper pick through Medium and Large."],
              ["Incremental writes", "Adaptive at Large/XLarge: sizing up is nearly free due to efficient pruning; no idle tax after the batch."],
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
