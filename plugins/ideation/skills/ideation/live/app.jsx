/* Ideation dashboard — live app.
   Shell, phase strip, live sidebar, status footer. Renders whatever the
   LiveStore currently holds (hydrated from /state); no replay engine.

   Wrapped in an IIFE so its top-level React-hook bindings stay function-scoped
   and don't collide with views.jsx's bindings in the shared global scope. */

(function () {
const { useState, useEffect, useMemo, useRef } = React;

/* ── live wiring ───────────────────────────────────────────────────── */

function useLiveState() {
  const [s, setS] = useState(window.LiveStore.get());
  useEffect(() => window.LiveStore.subscribe(setS), []);
  return s;
}

// ticking elapsed-seconds clock from a fixed epoch start
function useClock(startedAt) {
  const [, force] = useState(0);
  useEffect(() => {
    const id = setInterval(() => force((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);
  if (!startedAt) return null;
  return Math.max(0, Math.floor(Date.now() / 1000 - startedAt));
}

function fmtTime(s) {
  if (s == null) return "--:--";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function zoneColorJs(z) { return z ? `var(--${z.toLowerCase()})` : "var(--ink-3)"; }

/* ── App ──────────────────────────────────────────────────────────── */

function App() {
  const data = useLiveState();
  const [view, setView] = useState("tree");
  const [theme, setTheme] = useState("light");
  const [selectedIdeaId, setSelectedIdeaId] = useState(null);
  const [hoveredOpId, setHoveredOpId] = useState(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // op states — server already overlays 'running' onto the DB status
  const opStates = useMemo(() => data.OPERATOR_RUNS.map((op) => ({
    ...op,
    _state: op.status,
    _progress: op.status === "running" ? null : 1,
    _revealCount: op.produces.length,
  })), [data.OPERATOR_RUNS]);

  const activeOpId = opStates.find((o) => o._state === "running")?.id;

  const visibleIdeas = data.IDEAS;
  const visibleAssessments = data.ASSESSMENTS;

  // fresh ideas (just appeared) → the ignite animation. Recomputes only when
  // the IDEAS array changes (store replaces it wholesale on each fetch).
  const prevIdsRef = useRef(new Set());
  const freshIds = useMemo(() => {
    const cur = new Set(visibleIdeas.map((i) => i.id));
    const fresh = new Set();
    cur.forEach((id) => { if (!prevIdsRef.current.has(id)) fresh.add(id); });
    prevIdsRef.current = cur;
    // first load is not "fresh" (everything would ignite at once)
    return prevIdsRef.current.size === fresh.size && fresh.size > 6 ? new Set() : fresh;
  }, [visibleIdeas]);

  // highlight & dim from hover/selection
  const { highlightedIds, dimIds } = useMemo(() => {
    const hi = new Set();
    const dim = new Set();
    const visibleSet = new Set(visibleIdeas.map((i) => i.id));
    if (hoveredOpId) {
      const op = opStates.find((o) => o.id === hoveredOpId);
      if (op) {
        op.produces.forEach((id) => hi.add(id));
        op.cohort.forEach((id) => hi.add(id));
        visibleSet.forEach((id) => { if (!hi.has(id)) dim.add(id); });
      }
    }
    if (selectedIdeaId) {
      const idea = data.IDEAS.find((i) => i.id === selectedIdeaId);
      if (idea) {
        hi.add(selectedIdeaId);
        (idea.parents || []).forEach((p) => hi.add(p));
        data.IDEAS.filter((i) => (i.parents || []).includes(idea.id)).forEach((c) => hi.add(c.id));
      }
    }
    return { highlightedIds: hi, dimIds: dim };
  }, [hoveredOpId, opStates, visibleIdeas, selectedIdeaId, data.IDEAS]);

  const counts = useMemo(() => {
    const c = { ideas: visibleIdeas.length, active: 0, shortlisted: 0, selected: 0, rejected: 0, parked: 0 };
    visibleIdeas.forEach((i) => { c[i.status] = (c[i.status] || 0) + 1; });
    return c;
  }, [visibleIdeas]);

  const opCounts = useMemo(() => {
    const c = { succeeded: 0, running: 0, pending: 0, failed: 0, skipped: 0 };
    opStates.forEach((op) => { c[op._state] = (c[op._state] || 0) + 1; });
    return c;
  }, [opStates]);

  const selectedIdea = selectedIdeaId ? data.IDEAS.find((i) => i.id === selectedIdeaId) : null;

  useEffect(() => {
    const h = (e) => { if (e.key === "Escape") setSelectedIdeaId(null); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  return (
    <div style={{
      width: "100vw", height: "100vh", display: "grid",
      gridTemplateRows: "auto auto 1fr auto",
      background: "var(--bg-0)",
      position: "relative", zIndex: 1,
    }}>
      <Header data={data} view={view} setView={setView} complete={data.complete} />
      <PhaseStrip phases={data.PHASES} opStates={opStates} complete={data.complete} />

      <div style={{
        display: "grid", gridTemplateColumns: "1fr 340px",
        minHeight: 0, overflow: "hidden",
      }}>
        <main style={{ minWidth: 0, minHeight: 0, overflow: "hidden", position: "relative", borderTop: "1px solid var(--line-1)" }}>
          {view === "tree" && (
            <TreeView
              ideas={visibleIdeas}
              freshIds={freshIds}
              highlightedIds={highlightedIds}
              dimIds={dimIds}
              onSelectIdea={setSelectedIdeaId}
              frame={data.FRAME}
              opRuns={data.OPERATOR_RUNS}
              activeOpId={activeOpId}
              assessments={visibleAssessments}
            />
          )}
          {view === "timeline" && (
            <TimelineView
              opRuns={opStates}
              ideas={visibleIdeas}
              plan={data.PLAN}
              onSelectIdea={setSelectedIdeaId}
              onHoverOp={setHoveredOpId}
              activeOpId={activeOpId}
              hoveredOpId={hoveredOpId}
            />
          )}
          {view === "board" && (
            <BoardView
              ideas={visibleIdeas}
              freshIds={freshIds}
              highlightedIds={highlightedIds}
              dimIds={dimIds}
              onSelectIdea={setSelectedIdeaId}
            />
          )}
        </main>

        <Sidebar
          opStates={opStates}
          ideas={visibleIdeas}
          activeOpId={activeOpId}
          onHoverOp={setHoveredOpId}
          onSelectIdea={setSelectedIdeaId}
          counts={counts}
          opCounts={opCounts}
          complete={data.complete}
        />
      </div>

      <LiveFooter
        data={data}
        counts={counts}
        opCounts={opCounts}
        theme={theme}
        setTheme={setTheme}
      />

      {selectedIdea && (
        <IdeaDetail
          idea={selectedIdea}
          opRuns={data.OPERATOR_RUNS}
          ideas={data.IDEAS}
          assessments={data.ASSESSMENTS}
          onClose={() => setSelectedIdeaId(null)}
          onSelectIdea={setSelectedIdeaId}
        />
      )}
    </div>
  );
}

/* ── Masthead ──────────────────────────────────────────────────────── */

function Header({ data, view, setView, complete }) {
  const frame = data.FRAME;
  const title = (frame && frame.problem_statement)
    || data.TOPIC.description
    || `Ideation session · ${data.TOPIC.slug || ""}`;
  return (
    <header style={{
      padding: "22px 34px 20px",
      borderBottom: "1px solid var(--line-1)",
      background: "linear-gradient(180deg, color-mix(in oklch, var(--bg-1) 70%, transparent), transparent)",
      position: "relative",
    }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 14,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Sigil />
          <span style={{
            fontFamily: "var(--mono)", fontSize: 10.5, letterSpacing: 3, color: "var(--ink-3)",
            textTransform: "uppercase",
          }}>Ideation Engine</span>
          <span style={{ width: 14, height: 1, background: "var(--line-2)" }} />
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 7,
            fontFamily: "var(--mono)", fontSize: 10.5, letterSpacing: 1.5, color: "var(--ink-4)",
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: "50%",
              background: complete ? "var(--ink-4)" : "var(--olive)",
              animation: complete ? "none" : "pulse-dot 1.8s ease-in-out infinite",
              color: "var(--olive)",
            }} />
            {complete ? "COMPLETE" : "LIVE"}
          </span>
        </div>
        <ViewSwitcher view={view} setView={setView} />
      </div>

      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 24 }}>
        <h1 style={{
          margin: 0, fontFamily: "var(--serif)", fontStyle: "italic", fontWeight: 400,
          fontSize: "clamp(26px, 3.4vw, 46px)", lineHeight: 0.98, letterSpacing: "-0.015em",
          color: "var(--ink-1)", minWidth: 0,
        }}>{String(title).replace(/\.$/, "")}</h1>
        {data.TOPIC.slug && (
          <span style={{
            fontFamily: "var(--mono)", fontSize: 11, letterSpacing: 1, color: "var(--gold)",
            border: "1px solid color-mix(in oklch, var(--gold) 35%, var(--line-2))",
            background: "color-mix(in oklch, var(--gold) 8%, transparent)",
            padding: "5px 11px", borderRadius: 999, whiteSpace: "nowrap", flex: "none",
            marginBottom: 6,
          }}># {data.TOPIC.slug}</span>
        )}
      </div>
    </header>
  );
}

function Sigil() {
  return (
    <div style={{
      width: 30, height: 30, borderRadius: "50%", flex: "none",
      display: "grid", placeItems: "center", position: "relative",
      border: "1px solid color-mix(in oklch, var(--gold) 40%, var(--line-2))",
      background: "radial-gradient(circle at 50% 40%, color-mix(in oklch, var(--gold) 22%, transparent), transparent 70%)",
      boxShadow: "0 0 16px -4px color-mix(in oklch, var(--gold) 55%, transparent)",
    }}>
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="1.6" strokeLinecap="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M12 3 L12 7 M12 17 L12 21 M3 12 L7 12 M17 12 L21 12 M6 6 L9 9 M15 15 L18 18 M18 6 L15 9 M9 15 L6 18" opacity="0.7" />
      </svg>
    </div>
  );
}

function ViewSwitcher({ view, setView }) {
  const opts = [
    { id: "tree",     label: "Tree",     icon: TreeIcon },
    { id: "timeline", label: "Timeline", icon: TimelineIcon },
    { id: "board",    label: "Board",    icon: BoardIcon },
  ];
  return (
    <div style={{
      display: "flex", padding: 3, gap: 2,
      background: "var(--bg-2)", border: "1px solid var(--line-2)",
      borderRadius: 999,
    }}>
      {opts.map((o) => {
        const active = view === o.id;
        return (
          <button key={o.id} onClick={() => setView(o.id)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "6px 14px", border: "none",
              background: active ? "color-mix(in oklch, var(--gold) 14%, var(--bg-3))" : "transparent",
              color: active ? "var(--ink-1)" : "var(--ink-3)",
              borderRadius: 999, cursor: "pointer",
              fontFamily: "var(--display)", fontSize: 12, fontWeight: 600,
              boxShadow: "none", transition: "background 160ms, color 160ms",
            }}>
            <o.icon size={13} />
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

function TreeIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
      <circle cx="3" cy="3" r="1.4" />
      <circle cx="3" cy="13" r="1.4" />
      <circle cx="13" cy="8" r="1.4" />
      <path d="M4.4 3 Q9 3 11.7 7.3 M4.4 13 Q9 13 11.7 8.7" />
    </svg>
  );
}
function TimelineIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
      <line x1="4" y1="2" x2="4" y2="14" />
      <circle cx="4" cy="4" r="1.3" fill="currentColor" />
      <circle cx="4" cy="8" r="1.3" />
      <circle cx="4" cy="12" r="1.3" />
      <line x1="6" y1="4" x2="13" y2="4" />
      <line x1="6" y1="8" x2="11" y2="8" />
      <line x1="6" y1="12" x2="12" y2="12" />
    </svg>
  );
}
function BoardIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
      <rect x="2" y="2" width="5" height="5" rx="1" />
      <rect x="9" y="2" width="5" height="5" rx="1" />
      <rect x="2" y="9" width="5" height="5" rx="1" />
      <rect x="9" y="9" width="5" height="5" rx="1" />
    </svg>
  );
}

/* ── Phase meter ───────────────────────────────────────────────────── */

function PhaseStrip({ phases, opStates, complete }) {
  const phaseProgress = useMemo(() => {
    const map = {};
    phases.forEach((p) => {
      const ops = opStates.filter((o) => o.phase === p.id);
      const done = ops.filter((o) => o._state === "succeeded").length;
      const running = ops.some((o) => o._state === "running");
      const total = ops.length;
      // running ops have no client-side timing → count them as half-done
      const partial = running ? 0.5 : 0;
      map[p.id] = {
        progress: total ? Math.min(1, (done + partial) / total) : (complete ? 1 : 0),
        running, done, total,
        state: total && done === total ? "succeeded" : (running || done > 0 ? "running" : "pending"),
      };
    });
    return map;
  }, [phases, opStates, complete]);

  return (
    <div style={{
      padding: "16px 34px 18px",
      background: "transparent",
      display: "grid",
      gridTemplateColumns: `repeat(${phases.length}, 1fr)`,
      columnGap: 10,
      position: "relative",
    }}>
      {phases.map((p) => {
        const pp = phaseProgress[p.id];
        const active = pp.state === "running";
        const done = pp.state === "succeeded";
        return (
          <div key={p.id} style={{ position: "relative" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 9 }}>
              <span style={{
                fontFamily: "var(--mono)", fontSize: 10,
                color: done ? "var(--olive)" : active ? "var(--gold)" : "var(--ink-4)",
                width: 14, textAlign: "center",
              }}>{done ? "●" : active ? (
                <span style={{ display: "inline-block", animation: "breathe 1.4s ease-in-out infinite" }}>◆</span>
              ) : "○"}</span>
              <span style={{
                fontFamily: "var(--display)", fontSize: 13, fontWeight: 600, letterSpacing: "0.01em",
                color: done ? "var(--ink-1)" : active ? "var(--gold)" : "var(--ink-3)",
              }}>{p.label}</span>
              <span style={{ flex: 1 }} />
              <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-4)" }}>{pp.done}/{pp.total}</span>
            </div>
            <div style={{
              height: 3, background: "var(--line-1)", borderRadius: 2, overflow: "hidden", position: "relative",
            }}>
              <div style={{
                position: "absolute", inset: 0, width: `${pp.progress * 100}%`,
                background: done
                  ? "linear-gradient(90deg, var(--olive-soft), var(--olive))"
                  : "linear-gradient(90deg, var(--gold-2), var(--gold))",
                borderRadius: 2,
                boxShadow: active ? "0 0 10px -1px var(--gold)" : (done ? "0 0 8px -2px var(--olive)" : "none"),
                transition: "width 350ms cubic-bezier(.2,.7,.2,1)",
              }} />
              {active && (
                <div style={{
                  position: "absolute", inset: 0, borderRadius: 2,
                  background: "linear-gradient(90deg, transparent, color-mix(in oklch, var(--gold) 60%, transparent), transparent)",
                  backgroundSize: "180% 100%",
                  animation: "sheen 1.8s linear infinite",
                }} />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Sidebar ───────────────────────────────────────────────────────── */

function Sidebar({ opStates, ideas, activeOpId, onHoverOp, onSelectIdea, counts, opCounts, complete }) {
  const active = opStates.find((o) => o.id === activeOpId);
  const recent = useMemo(() => {
    return [...ideas].sort((a, b) => b.id - a.id).slice(0, 6);
  }, [ideas]);

  return (
    <aside style={{
      borderLeft: "1px solid var(--line-1)",
      background: "linear-gradient(180deg, var(--bg-1), color-mix(in oklch, var(--bg-1) 80%, var(--bg-0)))",
      display: "flex", flexDirection: "column",
      overflow: "hidden",
    }}>
      {/* counts */}
      <div style={{ padding: "24px 24px 20px", borderBottom: "1px solid var(--line-1)" }}>
        <RailLabel>Logbook · {complete ? "final" : "live"}</RailLabel>
        <div style={{
          display: "flex", alignItems: "baseline", gap: 12, marginTop: 6, marginBottom: 16,
        }}>
          <span style={{
            fontFamily: "var(--display)", fontSize: 64, fontWeight: 700, lineHeight: 0.85,
            letterSpacing: "-0.03em", color: "var(--ink-1)",
            fontVariantNumeric: "tabular-nums",
          }}>{counts.ideas}</span>
          <span style={{
            fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 17, color: "var(--ink-3)",
          }}>ideas<br/>saved</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <CountTile label="active"    value={counts.active || 0} accent="var(--olive)" />
          <CountTile label="shortlist" value={(counts.shortlisted || 0) + (counts.selected || 0)} accent="var(--gold)" />
          <CountTile label="cut"       value={counts.rejected || 0} accent="var(--st-rejected)" />
        </div>
      </div>

      {/* now running */}
      <div style={{ padding: "22px 24px 20px", borderBottom: "1px solid var(--line-1)" }}>
        <RailLabel>{active ? "Now forging" : "Orchestrator"}</RailLabel>
        <div style={{ marginTop: 12 }}>
          {active ? <RunningCard op={active} /> : <IdleCard opStates={opStates} opCounts={opCounts} complete={complete} />}
        </div>
      </div>

      {/* recent saves */}
      <div style={{ padding: "22px 24px", flex: 1, minHeight: 0, overflow: "auto" }}>
        <RailLabel>Recent saves</RailLabel>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 12 }}>
          {recent.length === 0 && (
            <div style={{ fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 14, color: "var(--ink-4)" }}>
              Nothing yet.
            </div>
          )}
          {recent.map((i, idx) => (
            <button key={i.id} onClick={() => onSelectIdea(i.id)}
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "9px 12px",
                background: "var(--bg-2)", border: "1px solid var(--line-1)",
                borderRadius: 8, cursor: "pointer",
                color: "var(--ink-1)", fontFamily: "var(--sans)", fontSize: 12.5,
                textAlign: "left", position: "relative", overflow: "hidden",
                animation: idx === 0 ? "fade-up 400ms cubic-bezier(.2,.7,.2,1)" : undefined,
              }}>
              <span style={{
                width: 7, height: 7, borderRadius: "50%", flex: "none",
                background: zoneColorJs(i.zone),
                boxShadow: `0 0 8px -1px ${zoneColorJs(i.zone)}`,
              }} />
              <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--ink-4)" }}>
                #{String(i.id).padStart(2, "0")}
              </span>
              <span style={{
                flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                fontFamily: (i.status === "shortlisted" || i.status === "selected") ? "var(--serif)" : "var(--sans)",
                fontStyle: (i.status === "shortlisted" || i.status === "selected") ? "italic" : "normal",
                fontSize: (i.status === "shortlisted" || i.status === "selected") ? 14 : 12.5,
              }}>
                {i.title}
              </span>
              <KindBadge kind={i.kind} />
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}

function RailLabel({ children }) {
  return (
    <div style={{
      fontFamily: "var(--mono)", fontSize: 9.5, letterSpacing: 2.4,
      color: "var(--ink-4)", textTransform: "uppercase",
      display: "flex", alignItems: "center", gap: 8,
    }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--gold)", boxShadow: "0 0 6px var(--gold)" }} />
      {children}
    </div>
  );
}

function CountTile({ label, value, accent }) {
  return (
    <div style={{
      background: "var(--bg-2)", border: "1px solid var(--line-1)",
      borderRadius: 9, padding: "11px 12px",
    }}>
      <div style={{
        fontFamily: "var(--display)", fontSize: 26, fontWeight: 700, lineHeight: 1, color: accent,
        fontVariantNumeric: "tabular-nums",
      }}>{value}</div>
      <div style={{
        fontFamily: "var(--mono)", fontSize: 8.5, letterSpacing: 1, color: "var(--ink-4)",
        textTransform: "uppercase", marginTop: 6,
      }}>{label}</div>
    </div>
  );
}

function RunningCard({ op }) {
  return (
    <div style={{
      background: "var(--bg-2)",
      border: "1px solid color-mix(in oklch, var(--gold) 38%, var(--line-2))",
      borderRadius: 12, padding: "16px 16px 18px",
      position: "relative", overflow: "hidden",
      boxShadow: "0 0 30px -14px color-mix(in oklch, var(--gold) 60%, transparent)",
    }}>
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 1,
        background: "linear-gradient(90deg, transparent, var(--gold), transparent)",
        backgroundSize: "200% 100%", animation: "sheen 2.4s linear infinite",
      }} />
      <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
        <span style={{
          width: 20, height: 20, borderRadius: "50%",
          background: "color-mix(in oklch, var(--gold) 18%, var(--bg-1))",
          border: "1px solid color-mix(in oklch, var(--gold) 50%, var(--line-2))",
          color: "var(--gold)", display: "grid", placeItems: "center", fontSize: 11, flex: "none",
        }}>
          <span style={{ display: "inline-block", animation: "spin 2s linear infinite" }}>✷</span>
        </span>
        <span style={{ fontFamily: "var(--mono)", fontSize: 12.5, color: "var(--ink-1)", letterSpacing: 0.3 }}>{op.name}</span>
        {op.persona && (
          <span style={{
            fontFamily: "var(--mono)", fontSize: 9.5, color: "var(--ink-3)",
            border: "1px solid var(--line-2)", padding: "1px 6px", borderRadius: 999,
          }}>{op.persona}</span>
        )}
      </div>
      <div style={{
        marginTop: 10, fontFamily: "var(--serif)", fontSize: 17, lineHeight: 1.25,
        color: "var(--ink-1)",
      }}>{op.label}</div>
      {op.cohort.length > 0 && (
        <div style={{ marginTop: 10, fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-4)" }}>
          cohort [{op.cohort.map((c) => "#" + String(c).padStart(2, "0")).join(" ")}]
        </div>
      )}
      {/* indeterminate progress — no client-side timing for a live run */}
      <div style={{
        marginTop: 14, height: 4, background: "var(--bg-3)", borderRadius: 3, overflow: "hidden", position: "relative",
      }}>
        <div style={{
          position: "absolute", inset: 0, borderRadius: 3,
          background: "linear-gradient(90deg, transparent, var(--gold), transparent)",
          backgroundSize: "180% 100%",
          animation: "sheen 1.5s linear infinite",
        }} />
      </div>
      <div style={{ marginTop: 8, fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-3)", display: "flex", justifyContent: "space-between" }}>
        <span>{op.produces.length > 0 ? `${op.produces.length} produced` : "working…"}</span>
        <span style={{ color: "var(--gold)" }}>live</span>
      </div>
    </div>
  );
}

function IdleCard({ opStates, complete }) {
  const next = opStates.find((o) => o._state === "pending");
  const allDone = complete || (!next && opStates.length > 0 && !opStates.some((o) => o._state === "running"));
  return (
    <div style={{
      padding: "16px 16px 18px", background: "var(--bg-2)",
      border: "1px solid var(--line-1)", borderRadius: 12,
    }}>
      <div style={{ fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 17, color: "var(--ink-2)" }}>
        {allDone ? "Session complete." : opStates.length === 0 ? "Warming up…" : "Standing by…"}
      </div>
      {next && !complete && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: 9.5, letterSpacing: 1.4, color: "var(--ink-4)", marginBottom: 6, textTransform: "uppercase" }}>
            Up next
          </div>
          <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--ink-1)" }}>{next.name}</div>
          <div style={{ color: "var(--ink-3)", marginTop: 3, fontSize: 12.5, lineHeight: 1.4 }}>{next.label}</div>
        </div>
      )}
    </div>
  );
}

/* ── Live status footer (replaces the replay transport) ────────────── */

function LiveFooter({ data, counts, opCounts, theme, setTheme }) {
  const elapsed = useClock(data.startedAt);
  const checkpoint = data.checkpoint;
  const complete = data.complete;

  return (
    <div style={{
      padding: "12px 24px",
      borderTop: "1px solid var(--line-1)",
      background: "var(--bg-1)",
      display: "flex", alignItems: "center", gap: 18,
    }}>
      {/* live indicator */}
      <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
        <span style={{
          width: 9, height: 9, borderRadius: "50%",
          background: complete ? "var(--olive)" : "var(--gold)",
          color: complete ? "var(--olive)" : "var(--gold)",
          animation: complete ? "none" : "pulse-dot 1.6s ease-in-out infinite",
          boxShadow: complete ? "0 0 8px -1px var(--olive)" : "0 0 8px -1px var(--gold)",
        }} />
        <span style={{
          fontFamily: "var(--display)", fontSize: 13, fontWeight: 600,
          color: complete ? "var(--olive)" : "var(--ink-1)",
        }}>{complete ? "Session complete" : "Live session"}</span>
        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--ink-4)" }}>
          {fmtTime(elapsed)}
        </span>
      </div>

      {/* checkpoint banner */}
      {checkpoint && !complete && (
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "4px 12px", borderRadius: 999,
          background: "color-mix(in oklch, var(--gold) 12%, transparent)",
          border: "1px solid color-mix(in oklch, var(--gold) 35%, var(--line-2))",
          color: "var(--gold)", fontFamily: "var(--mono)", fontSize: 11,
        }}>
          <span>⏸</span>
          awaiting you · {String(checkpoint.name || "checkpoint").replace(/_/g, " ")}
        </div>
      )}

      <span style={{ flex: 1 }} />

      {/* op + idea tallies */}
      <div style={{
        display: "flex", alignItems: "center", gap: 16,
        fontFamily: "var(--mono)", fontSize: 11, color: "var(--ink-3)",
      }}>
        <span><span style={{ color: "var(--ink-1)" }}>{opCounts.succeeded || 0}</span> ops done</span>
        {opCounts.running > 0 && <span style={{ color: "var(--gold)" }}>{opCounts.running} running</span>}
        {opCounts.failed > 0 && <span style={{ color: "var(--st-rejected)" }}>{opCounts.failed} failed</span>}
        <span><span style={{ color: "var(--ink-1)" }}>{counts.ideas}</span> ideas</span>
      </div>

      {/* theme toggle */}
      <button onClick={() => setTheme(theme === "light" ? "dark" : "light")}
        title="Toggle theme"
        style={{
          width: 28, height: 28, borderRadius: "50%",
          background: "var(--bg-2)", color: "var(--ink-2)",
          border: "1px solid var(--line-2)",
          display: "grid", placeItems: "center", cursor: "pointer",
        }}>
        {theme === "light" ? (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
            <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z" />
          </svg>
        ) : (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19" />
          </svg>
        )}
      </button>
    </div>
  );
}

/* ── mount ─────────────────────────────────────────────────────────── */

try {
  const __boot = document.getElementById("__boot");
  if (__boot) __boot.remove();
  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(<App />);
} catch (err) {
  const r = document.getElementById("root");
  if (r) r.innerHTML =
    '<div style="position:fixed;inset:0;display:grid;place-items:center;font-family:monospace;color:#b6bccb;padding:40px;text-align:center;">Failed to start: ' +
    (err && err.message ? err.message : err) + '</div>';
  console.error(err);
}

})();
