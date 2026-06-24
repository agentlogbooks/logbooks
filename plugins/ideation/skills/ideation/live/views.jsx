/* Views: lineage tree (hero), live timeline, and the improved board.
   Reads window.IDEATION. Exports view components to window. */

const { useMemo, useState, useRef, useEffect, useLayoutEffect, Fragment } = React;

/* ── shared helpers ────────────────────────────────────────────────── */

const zoneColor = (z) => z ? `var(--${z.toLowerCase()})` : "var(--ink-3)";
const statusColor = (s) => `var(--st-${s})`;
const tagColor = (t) => t ? `var(--${t.toLowerCase()})` : "var(--ink-3)";

const opGlyph = {
  succeeded: "✓",
  running: "↻",
  pending: "○",
  failed: "×",
  skipped: "—",
};

function StatusDot({ status, size = 8 }) {
  const style = {
    width: size, height: size, borderRadius: "50%",
    background: status === "running" ? "var(--olive)" : status === "succeeded" ? "var(--olive)" :
                status === "pending" ? "var(--ink-5)" : "var(--st-rejected)",
    color: status === "running" ? "var(--olive)" : "var(--olive)",
    display: "inline-block", flex: "none",
  };
  if (status === "running") return <span style={{ ...style, animation: "pulse-dot 1.4s ease-in-out infinite" }} />;
  return <span style={style} />;
}

function ZoneGlyph({ zone }) {
  if (!zone) return null;
  return (
    <span style={{
      fontFamily: "var(--mono)", fontSize: 9, letterSpacing: 0.5,
      color: zoneColor(zone), textTransform: "uppercase", fontWeight: 600,
    }}>{zone}</span>
  );
}

function TagPill({ tag }) {
  if (!tag) return null;
  const c = tagColor(tag);
  return (
    <span style={{
      fontFamily: "var(--mono)", fontSize: 9, letterSpacing: 0.8, fontWeight: 600,
      color: c, padding: "2px 6px",
      border: `1px solid color-mix(in oklch, ${c} 40%, transparent)`,
      borderRadius: 4, lineHeight: 1, textTransform: "uppercase",
      background: `color-mix(in oklch, ${c} 12%, transparent)`,
    }}>{tag}</span>
  );
}

function KindBadge({ kind }) {
  const map = { seed: "seed", variant: "variant", hybrid: "hybrid", refinement: "refine", counter: "counter" };
  return (
    <span style={{
      fontFamily: "var(--mono)", fontSize: 9, letterSpacing: 0.6, color: "var(--ink-3)",
      textTransform: "uppercase",
    }}>{map[kind] || kind}</span>
  );
}

/* ── IdeaCard (used by Board view + detail) ─────────────────────────── */

function IdeaCard({ idea, isFresh, isHighlighted, isDim, onClick }) {
  const zc = zoneColor(idea.zone);
  return (
    <div
      onClick={onClick}
      style={{
        position: "relative",
        background: "var(--bg-2)",
        border: `1px solid ${isHighlighted ? `color-mix(in oklch, ${zc} 55%, var(--line-2))` : "var(--line-1)"}`,
        borderRadius: "var(--r-lg)",
        padding: "18px 18px 18px",
        cursor: "pointer",
        transition: "border-color 160ms, opacity 160ms",
        opacity: isDim ? 0.32 : (idea.status === "rejected" ? 0.5 : 1),
        animation: isFresh ? "fade-up 600ms cubic-bezier(.2,.7,.2,1) both" : undefined,
        overflow: "hidden",
        boxShadow: "none",
        display: "flex", flexDirection: "column", gap: 10,
        minHeight: 172,
      }}
    >
      {/* zone accent bar */}
      <div style={{
        position: "absolute", left: 0, top: 0, bottom: 0, width: 3,
        background: zc,
        opacity: isHighlighted ? 1 : 0.55,
      }} />

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <StatusDot status={idea.status === "rejected" ? "failed" : "running"} />
          <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-4)" }}>
            #{String(idea.id).padStart(2, "0")}
          </span>
          <KindBadge kind={idea.kind} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <ZoneGlyph zone={idea.zone} />
          <TagPill tag={idea.tag} />
        </div>
      </div>

      <div>
        <div style={{
          fontFamily: "var(--serif)",
          fontSize: 26, lineHeight: 1.05, fontWeight: 400,
          color: "var(--ink-1)", letterSpacing: -0.01,
          fontStyle: idea.status === "shortlisted" || idea.status === "selected" ? "italic" : "normal",
        }}>{idea.title}</div>
        <div style={{
          marginTop: 8, fontSize: 13, color: "var(--ink-2)", lineHeight: 1.45,
          display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden",
        }}>{idea.desc}</div>
      </div>

      <div style={{ flex: 1 }} />

      {idea.status !== "active" && (
        <div style={{
          fontFamily: "var(--mono)", fontSize: 9, letterSpacing: 0.6,
          color: statusColor(idea.status), textTransform: "uppercase",
          alignSelf: "flex-start",
        }}>{idea.status === "selected" ? "● selected" :
              idea.status === "shortlisted" ? "◆ shortlisted" :
              idea.status === "rejected" ? "× cut" : idea.status}</div>
      )}
    </div>
  );
}

/* ── BoardView ─────────────────────────────────────────────────────── */

function BoardView({ ideas, freshIds, highlightedIds, dimIds, onSelectIdea }) {
  const sorted = useMemo(() => {
    // group order: hybrids → variants → seeds (newest at top of each)
    const order = { hybrid: 0, refinement: 1, variant: 2, counter: 3, seed: 4 };
    return [...ideas].sort((a, b) => {
      if (order[a.kind] !== order[b.kind]) return order[a.kind] - order[b.kind];
      return b.id - a.id;
    });
  }, [ideas]);

  if (!ideas.length) return <EmptyStage />;

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
      gap: 14, padding: 24,
      alignContent: "start",
      overflow: "auto", height: "100%",
    }}>
      {sorted.map((idea) => (
        <IdeaCard
          key={idea.id}
          idea={idea}
          isFresh={freshIds.has(idea.id)}
          isHighlighted={highlightedIds.has(idea.id)}
          isDim={dimIds && dimIds.size > 0 && !dimIds.has(idea.id) && !highlightedIds.has(idea.id)}
          onClick={() => onSelectIdea(idea.id)}
        />
      ))}
    </div>
  );
}

/* shown when no ideas have been saved yet */
function EmptyStage() {
  return (
    <div style={{
      height: "100%", display: "grid", placeItems: "center", textAlign: "center",
    }}>
      <div>
        <div style={{
          width: 34, height: 34, margin: "0 auto 16px", borderRadius: "50%",
          border: "1px solid color-mix(in oklch, var(--gold) 40%, var(--line-2))",
          display: "grid", placeItems: "center",
          boxShadow: "0 0 22px -6px color-mix(in oklch, var(--gold) 60%, transparent)",
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="1.6" strokeLinecap="round" style={{ animation: "spin 3s linear infinite" }}>
            <circle cx="12" cy="12" r="3" />
            <path d="M12 3 L12 7 M12 17 L12 21 M3 12 L7 12 M17 12 L21 12 M6 6 L9 9 M15 15 L18 18 M18 6 L15 9 M9 15 L6 18" opacity="0.7" />
          </svg>
        </div>
        <div style={{ fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 19, color: "var(--ink-3)" }}>
          Waiting for the first ideas to ignite…
        </div>
      </div>
    </div>
  );
}

/* ── TreeView (the hero) ──────────────────────────────────────────────
   Layout: horizontal phase columns
     col 0  Frame
     col 1  Generate (sub-columns innovator | wild_card)
     col 2  Transform (variants & hybrids)
     col 3  Evaluate / Decide markers
   Each idea is a chip; SVG edges draw parents→children. */

function TreeView({ ideas, freshIds, highlightedIds, dimIds, onSelectIdea, frame, opRuns, activeOpId, assessments }) {
  const containerRef = useRef(null);
  const [hoveredIdeaId, setHoveredIdeaId] = useState(null);

  // expand highlights with hovered idea's lineage
  const allIdeasById = useMemo(() => {
    const m = {}; ideas.forEach(i => { m[i.id] = i; }); return m;
  }, [ideas]);

  const lineageHighlight = useMemo(() => {
    if (!hoveredIdeaId) return null;
    const hi = new Set([hoveredIdeaId]);
    // ancestors
    const visitUp = (id) => {
      const i = allIdeasById[id]; if (!i) return;
      (i.parents || []).forEach(p => { if (!hi.has(p)) { hi.add(p); visitUp(p); } });
    };
    visitUp(hoveredIdeaId);
    // descendants
    const visitDown = (id) => {
      ideas.forEach(c => {
        if ((c.parents || []).includes(id) && !hi.has(c.id)) { hi.add(c.id); visitDown(c.id); }
      });
    };
    visitDown(hoveredIdeaId);
    return hi;
  }, [hoveredIdeaId, allIdeasById, ideas]);

  const effectiveHighlights = lineageHighlight || highlightedIds;
  const effectiveDim = lineageHighlight
    ? new Set(ideas.filter(i => !lineageHighlight.has(i.id)).map(i => i.id))
    : dimIds;

  const layout = useMemo(() => {
    // partition
    const byPersona = (p) => ideas.filter(i => i.kind === "seed" && opOf(i, opRuns)?.persona === p);
    const seedsInno = byPersona("innovator");
    const seedsWild = byPersona("wild_card");
    // seeds from any other (or no) persona fall back to the innovator column so
    // a live session that doesn't use those two personas still draws a tree.
    const placed = new Set([...seedsInno, ...seedsWild].map(i => i.id));
    const seedsOther = ideas.filter(i => i.kind === "seed" && !placed.has(i.id));
    const variants  = ideas.filter(i => i.kind === "variant" || i.kind === "refinement");
    const hybrids   = ideas.filter(i => i.kind === "hybrid" || i.kind === "counter");

    const innoCol = [...seedsInno, ...seedsOther];

    // geometry
    const ROW_H = 34;
    const CHIP_W = 132;
    const CHIP_H = 30;
    const PAD = 26;

    // column x positions
    const COL_X = {
      frame:     PAD,
      innovator: PAD + 206,
      wild:      PAD + 206 + CHIP_W + 14,
      variant:   PAD + 206 + (CHIP_W + 14) * 2 + 34,
      hybrid:    PAD + 206 + (CHIP_W + 14) * 3 + 34,
      mark:      PAD + 206 + (CHIP_W + 14) * 4 + 44,
    };

    const pos = {};   // ideaId → {x,y, cx, cy}
    const place = (list, x, startY) => {
      list.forEach((idea, i) => {
        pos[idea.id] = {
          x, y: startY + i * ROW_H,
          cx: x + CHIP_W / 2, cy: startY + i * ROW_H + CHIP_H / 2,
          left: x, right: x + CHIP_W,
        };
      });
    };

    const topY = 84;
    place(innoCol, COL_X.innovator, topY);
    place(seedsWild, COL_X.wild, topY);

    // place variants near their parents y
    variants.forEach((v, i) => {
      const parentY = v.parents.length && pos[v.parents[0]]?.cy;
      const y = parentY ? parentY - CHIP_H / 2 : topY + i * ROW_H;
      pos[v.id] = {
        x: COL_X.variant, y,
        cx: COL_X.variant + CHIP_W / 2, cy: y + CHIP_H / 2,
        left: COL_X.variant, right: COL_X.variant + CHIP_W,
      };
    });

    // hybrids near average parent y
    hybrids.forEach((h, i) => {
      const ys = h.parents.map(p => pos[p]?.cy).filter(Boolean);
      const avg = ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : topY + i * ROW_H;
      const y = avg - CHIP_H / 2;
      pos[h.id] = {
        x: COL_X.hybrid, y,
        cx: COL_X.hybrid + CHIP_W / 2, cy: avg,
        left: COL_X.hybrid, right: COL_X.hybrid + CHIP_W,
      };
    });

    // width / height
    const maxY = Math.max(
      topY + innoCol.length * ROW_H,
      topY + seedsWild.length * ROW_H,
      topY + variants.length * ROW_H,
      topY + hybrids.length * ROW_H,
    );
    const width = COL_X.mark + 200;
    // floor so the FrameCard / shortlist cards aren't clipped when ideas are few
    const height = Math.max(maxY + 80, 320);

    return {
      pos, COL_X, ROW_H, CHIP_W, CHIP_H, PAD, topY,
      seedsInno: innoCol, seedsWild, variants, hybrids,
      width, height,
    };
  }, [ideas, opRuns]);

  // edges (parent→child)
  const edges = useMemo(() => {
    const out = [];
    ideas.forEach(child => {
      (child.parents || []).forEach(pid => {
        if (layout.pos[pid] && layout.pos[child.id]) {
          out.push({
            from: layout.pos[pid],
            to: layout.pos[child.id],
            childId: child.id, parentId: pid,
            zone: child.zone,
            kind: child.kind,
            fresh: freshIds.has(child.id),
            highlight: effectiveHighlights.has(child.id) || effectiveHighlights.has(pid),
            dim: effectiveDim && effectiveDim.size > 0 && !effectiveDim.has(child.id) && !effectiveDim.has(pid),
          });
        }
      });
    });
    return out;
  }, [ideas, layout, freshIds, effectiveHighlights, effectiveDim]);

  // Only fully empty (no frame AND no ideas) shows the waiting stage. A captured
  // frame with zero ideas still renders its scaffold — this is the opening
  // minute of every session, when the frame lands before the first idea.
  if (!ideas.length && !frame) return <EmptyStage />;

  return (
    <div ref={containerRef} style={{
      width: "100%", height: "100%", overflow: "auto",
      background: "radial-gradient(ellipse 60% 50% at 50% 50%, var(--bg-1), var(--bg-0))",
    }}>
      <svg width={layout.width} height={layout.height} style={{ display: "block", minWidth: "100%", margin: "auto" }}>
        <defs>
          <filter id="edge-glow" x="-20%" y="-40%" width="140%" height="180%">
            <feGaussianBlur stdDeviation="2.4" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        {/* column header rails */}
        {[
          { x: layout.COL_X.frame - 10,     w: 204,                            label: "Frame" },
          { x: layout.COL_X.innovator - 10, w: (layout.CHIP_W + 14) * 2 + 6,   label: "Generate", sub: ["innovator", "wild card"] },
          { x: layout.COL_X.variant - 10,   w: (layout.CHIP_W + 14) * 2 + 6,   label: "Transform", sub: ["variants", "hybrids"] },
          { x: layout.COL_X.mark - 10,      w: 204,                            label: "Decide" },
        ].map((c, i) => (
          <g key={i}>
            <line x1={c.x + 2} y1={50} x2={c.x + c.w - 6} y2={50} stroke="var(--line-1)" strokeWidth={1} />
            <circle cx={c.x + 4} cy={50} r={2.5} fill="var(--gold)" opacity={0.85} />
            <text x={c.x + 14} y={42}
                  fontFamily="var(--display)" fontSize={13} fontWeight={700}
                  letterSpacing={0.5} fill="var(--ink-2)">
              {c.label}
            </text>
            {c.sub && c.sub.map((s, j) => (
              <text key={j} x={c.x + 12 + j * (layout.CHIP_W + 14)} y={70}
                    fontFamily="var(--mono)" fontSize={9}
                    fill="var(--ink-4)" letterSpacing={1}>
                {s.toUpperCase()}
              </text>
            ))}
          </g>
        ))}

        {/* edges — glowing filaments */}
        <g>
          {edges.map((e, i) => {
            const x1 = e.from.right, y1 = e.from.cy;
            const x2 = e.to.left,    y2 = e.to.cy;
            const dx = (x2 - x1) * 0.5;
            const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
            const c = zoneColor(e.zone);
            const op = e.dim ? 0.12 : (e.highlight ? 1 : 0.42);
            return (
              <path key={i} d={d}
                    stroke={c} strokeWidth={e.highlight ? 2 : 1.2}
                    fill="none" opacity={op}
                    filter={e.highlight ? "url(#edge-glow)" : undefined}
                    style={{
                      transition: "opacity 200ms, stroke-width 200ms",
                      strokeDasharray: e.fresh ? "260" : undefined,
                      strokeDashoffset: e.fresh ? "260" : undefined,
                      animation: e.fresh ? "draw 800ms 100ms cubic-bezier(.4,.7,.2,1) forwards" : undefined,
                    }} />
            );
          })}
        </g>

        {/* frame card */}
        <foreignObject x={layout.COL_X.frame} y={layout.topY} width={194} height={layout.height - layout.topY - 20}>
          <FrameCard frame={frame} />
        </foreignObject>

        {/* decide column preview — shortlist forming */}
        <foreignObject x={layout.COL_X.mark} y={layout.topY} width={200} height={layout.height - layout.topY - 20}>
          <ShortlistPreview
            ideas={ideas}
            assessments={assessments}
            onSelectIdea={onSelectIdea}
          />
        </foreignObject>

        {/* idea chips */}
        {ideas.map(idea => {
          const p = layout.pos[idea.id];
          if (!p) return null;
          return (
            <foreignObject key={idea.id} x={p.x} y={p.y} width={layout.CHIP_W} height={layout.CHIP_H}>
              <IdeaChip
                idea={idea}
                isFresh={freshIds.has(idea.id)}
                isHighlighted={effectiveHighlights.has(idea.id)}
                isDim={effectiveDim && effectiveDim.size > 0 && !effectiveDim.has(idea.id) && !effectiveHighlights.has(idea.id)}
                onClick={() => onSelectIdea(idea.id)}
                onHover={(h) => setHoveredIdeaId(h ? idea.id : null)}
                hasScore={assessments.some(a => a.idea === idea.id)}
              />
            </foreignObject>
          );
        })}

        {/* hover popover — reveals the full description for description-rich ideas */}
        {hoveredIdeaId != null && layout.pos[hoveredIdeaId] && allIdeasById[hoveredIdeaId] && (() => {
          const idea = allIdeasById[hoveredIdeaId];
          const p = layout.pos[hoveredIdeaId];
          const POP_W = 250, POP_H = 150;
          const below = p.y < layout.height * 0.52;
          const py = below ? p.y + layout.CHIP_H + 8 : p.y - POP_H - 8;
          const px = Math.max(8, Math.min(p.x - 4, layout.width - POP_W - 8));
          return (
            <foreignObject x={px} y={py} width={POP_W} height={POP_H} style={{ overflow: "visible", pointerEvents: "none" }}>
              <ChipPopover idea={idea} assessments={assessments} />
            </foreignObject>
          );
        })()}
      </svg>
    </div>
  );
}

function ChipPopover({ idea, assessments }) {
  const zc = zoneColor(idea.zone);
  const scores = assessments.filter(a => a.idea === idea.id);
  return (
    <div style={{
      background: "var(--bg-2)",
      border: `1px solid color-mix(in oklch, ${zc} 45%, var(--line-2))`,
      borderLeft: `3px solid ${zc}`,
      borderRadius: 12, padding: "14px 16px",
      boxShadow: "0 12px 32px -20px rgba(0,0,0,0.4)",
      animation: "fade-up 160ms ease-out",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7 }}>
        <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--ink-4)" }}>
          #{String(idea.id).padStart(2, "0")}
        </span>
        <KindBadge kind={idea.kind} />
        <ZoneGlyph zone={idea.zone} />
        <TagPill tag={idea.tag} />
      </div>
      <div style={{
        fontFamily: "var(--serif)",
        fontStyle: idea.status === "shortlisted" || idea.status === "selected" ? "italic" : "normal",
        fontSize: 19, lineHeight: 1.05, color: "var(--ink-1)", marginBottom: 5,
      }}>{idea.title}</div>
      <div style={{
        fontSize: 11.5, lineHeight: 1.45, color: "var(--ink-2)",
        display: "-webkit-box", WebkitLineClamp: 4, WebkitBoxOrient: "vertical", overflow: "hidden",
      }}>{idea.desc}</div>
      {scores.length > 0 && (
        <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
          {scores.map((s, i) => (
            <span key={i} style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--ink-3)" }}>
              {s.metric} <span style={{ color: "var(--amber)" }}>{Number(s.value).toFixed(1)}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function opOf(idea, opRuns) { return opRuns.find(o => o.id === idea.origin); }

function ShortlistPreview({ ideas, assessments, onSelectIdea }) {
  const shortlisted = ideas.filter(i => i.status === "shortlisted" || i.status === "selected");
  // top scored (descending by taste) that aren't shortlisted yet
  const tasteMap = {};
  assessments.filter(a => a.metric === "taste").forEach(a => { tasteMap[a.idea] = a.value; });
  const scoredCandidates = ideas
    .filter(i => tasteMap[i.id] != null && i.status !== "shortlisted" && i.status !== "rejected")
    .sort((a, b) => tasteMap[b.id] - tasteMap[a.id])
    .slice(0, 3);
  const noActivity = shortlisted.length === 0 && scoredCandidates.length === 0;

  return (
    <div style={{
      background: "var(--bg-2)",
      border: "1px solid var(--line-1)", borderRadius: "var(--r-lg)",
      padding: "18px 18px", minHeight: 200,
      boxShadow: "none",
      opacity: noActivity ? 0.6 : 1,
    }}>
      <div style={{
        fontFamily: "var(--mono)", fontSize: 9, letterSpacing: 1, color: noActivity ? "var(--ink-4)" : "var(--amber)",
        textTransform: "uppercase",
      }}>▲ Shortlist forming</div>

      {noActivity ? (
        <div style={{
          marginTop: 12, fontSize: 11, color: "var(--ink-4)", lineHeight: 1.5,
          fontStyle: "italic",
        }}>
          Names will rise here once <span style={{ fontFamily: "var(--mono)", fontStyle: "normal" }}>evaluate.score</span> ranks them by taste &amp; novelty.
        </div>
      ) : (
        <>
          {shortlisted.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--ink-4)", marginBottom: 6, letterSpacing: 0.6 }}>SHORTLISTED</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {shortlisted.map(i => (
                  <button key={i.id} onClick={() => onSelectIdea(i.id)} style={{
                    display: "flex", alignItems: "center", gap: 6,
                    padding: "4px 8px", textAlign: "left",
                    background: `color-mix(in oklch, ${zoneColor(i.zone)} 8%, var(--bg-2))`,
                    border: `1px solid color-mix(in oklch, var(--amber) 25%, var(--line-2))`,
                    borderLeft: `2px solid ${zoneColor(i.zone)}`,
                    borderRadius: 4, cursor: "pointer",
                  }}>
                    <span style={{ color: "var(--amber)", fontSize: 10 }}>◆</span>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--ink-4)" }}>
                      #{String(i.id).padStart(2, "0")}
                    </span>
                    <span style={{
                      fontFamily: "var(--serif)", fontStyle: "italic",
                      fontSize: 13, color: "var(--ink-1)",
                      whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1,
                    }}>{i.title}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {scoredCandidates.length > 0 && (
            <div style={{ marginTop: 14 }}>
              <div style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--ink-4)", marginBottom: 6, letterSpacing: 0.6 }}>TOP CANDIDATES</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {scoredCandidates.map(i => (
                  <button key={i.id} onClick={() => onSelectIdea(i.id)} style={{
                    display: "flex", alignItems: "center", gap: 6,
                    padding: "4px 8px", textAlign: "left",
                    background: "var(--bg-2)", border: "1px solid var(--line-2)",
                    borderLeft: `2px solid ${zoneColor(i.zone)}`,
                    borderRadius: 4, cursor: "pointer",
                  }}>
                    <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--ink-4)" }}>
                      #{String(i.id).padStart(2, "0")}
                    </span>
                    <span style={{
                      fontSize: 12, color: "var(--ink-1)", flex: 1,
                      whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                    }}>{i.title}</span>
                    <span style={{
                      fontFamily: "var(--mono)", fontSize: 9, color: "var(--amber)",
                    }}>{Number(tasteMap[i.id]).toFixed(1)}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FrameCard({ frame }) {
  if (!frame) {
    return (
      <div style={{
        background: "var(--bg-2)",
        border: "1px solid var(--line-1)", borderRadius: "var(--r-lg)",
        padding: "18px 18px", minHeight: 200, boxShadow: "none", opacity: 0.7,
      }}>
        <div style={{
          fontFamily: "var(--mono)", fontSize: 9.5, letterSpacing: 1.4, color: "var(--ink-4)",
          textTransform: "uppercase",
        }}>Frame</div>
        <div style={{
          marginTop: 12, fontFamily: "var(--serif)", fontStyle: "italic",
          fontSize: 15, lineHeight: 1.3, color: "var(--ink-3)",
        }}>No frame captured yet.</div>
      </div>
    );
  }
  return (
    <div style={{
      background: "var(--bg-2)",
      border: "1px solid var(--line-1)", borderRadius: "var(--r-lg)",
      padding: "18px 18px", minHeight: 200,
      boxShadow: "none",
    }}>
      <div style={{
        fontFamily: "var(--mono)", fontSize: 9.5, letterSpacing: 1.4, color: "var(--gold)",
        textTransform: "uppercase", display: "flex", alignItems: "center", gap: 7,
      }}>
        <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--gold)", boxShadow: "0 0 6px var(--gold)" }} />
        Frame · v{frame.version || 1}
      </div>
      <div style={{
        marginTop: 12, fontFamily: "var(--serif)", fontStyle: "italic",
        fontSize: 19, lineHeight: 1.18, color: "var(--ink-1)", letterSpacing: "-0.01em",
      }}>{frame.problem_statement}</div>
      {frame.hmw_questions && frame.hmw_questions.length > 0 && (
        <div style={{
          marginTop: 12, fontSize: 11, color: "var(--ink-3)", lineHeight: 1.4,
        }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: 9, letterSpacing: 0.8, color: "var(--ink-4)", marginBottom: 4 }}>HOW MIGHT WE</div>
          {frame.hmw_questions.slice(0, 2).map((q, i) => (
            <div key={i} style={{ marginBottom: 4 }}>— {q}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function IdeaChip({ idea, isFresh, isHighlighted, isDim, onClick, onHover, hasScore }) {
  const zc = zoneColor(idea.zone);
  const isShortlist = idea.status === "shortlisted" || idea.status === "selected";
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => onHover && onHover(true)}
      onMouseLeave={() => onHover && onHover(false)}
      style={{
        height: "100%", width: "100%",
        display: "flex", alignItems: "center", gap: 7,
        background: isHighlighted
          ? `color-mix(in oklch, ${zc} 18%, var(--bg-2))`
          : "var(--bg-2)",
        border: `1px solid ${isHighlighted ? `color-mix(in oklch, ${zc} 60%, var(--line-2))` : "var(--line-1)"}`,
        borderLeft: `3px solid ${zc}`,
        borderRadius: 7,
        padding: "0 10px",
        cursor: "pointer",
        opacity: isDim ? 0.18 : (idea.status === "rejected" ? 0.38 : 1),
        transition: "opacity 160ms, border-color 160ms, background 160ms",
        boxShadow: isHighlighted ? `0 0 18px -6px ${zc}` : "none",
        animation: isFresh ? "ignite 760ms cubic-bezier(.2,.8,.2,1) both" : undefined,
        ...(isFresh ? { "--glow": `color-mix(in oklch, ${zc} 75%, transparent)` } : {}),
        overflow: "hidden",
      }}
    >
      <span style={{
        fontFamily: "var(--mono)", fontSize: 8.5, color: "var(--ink-4)", flex: "none",
      }}>{String(idea.id).padStart(2, "0")}</span>
      <span style={{
        fontFamily: isShortlist ? "var(--serif)" : "var(--sans)",
        fontStyle: isShortlist ? "italic" : "normal",
        fontWeight: isShortlist ? 400 : 500, fontSize: isShortlist ? 15 : 13, color: "var(--ink-1)",
        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
        flex: 1, letterSpacing: "-0.01em",
      }}>{idea.title}</span>
      {hasScore && (
        <span style={{
          width: 5, height: 5, borderRadius: "50%",
          background: "var(--gold)", flex: "none",
          boxShadow: "0 0 6px var(--gold)",
        }} />
      )}
      {isShortlist && (
        <span style={{ color: "var(--gold)", fontSize: 10, flex: "none" }}>◆</span>
      )}
    </div>
  );
}

/* ── TimelineView ──────────────────────────────────────────────────── */

function TimelineView({ opRuns, ideas, plan, onSelectIdea, onHoverOp, activeOpId, hoveredOpId }) {
  return (
    <div style={{
      padding: "28px 32px", overflow: "auto", height: "100%",
      maxWidth: 900, margin: "0 auto",
    }}>
      {/* Plan strip */}
      {plan && plan.length > 0 && (
        <div style={{
          fontFamily: "var(--mono)", fontSize: 10, letterSpacing: 2.4, color: "var(--ink-4)",
          textTransform: "uppercase", marginBottom: 18,
        }}>Session plan · {plan.length} steps</div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 14, position: "relative" }}>
        {opRuns.map((op, idx) => (
          <OperatorRow
            key={op.id}
            op={op}
            isLast={idx === opRuns.length - 1}
            ideas={ideas}
            isHovered={hoveredOpId === op.id}
            isActive={activeOpId === op.id}
            onHover={(h) => onHoverOp(h ? op.id : null)}
            onSelectIdea={onSelectIdea}
          />
        ))}
      </div>
    </div>
  );
}

function OperatorRow({ op, ideas, isHovered, isActive, isLast, onHover, onSelectIdea }) {
  const produced = ideas.filter(i => op.produces.includes(i.id));
  const isRunning = op.status === "running";
  const isPending = op.status === "pending";
  const isSucceeded = op.status === "succeeded";
  const isFailed = op.status === "failed";

  return (
    <div
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      style={{
        display: "grid",
        gridTemplateColumns: "44px 1fr",
        gap: 14,
        opacity: isPending ? 0.55 : 1,
        position: "relative",
        transition: "opacity 200ms",
      }}>
      {/* left rail */}
      <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{
          width: 28, height: 28, borderRadius: "50%",
          background: isSucceeded ? "color-mix(in oklch, var(--olive) 18%, var(--bg-1))" :
                      isRunning ? "color-mix(in oklch, var(--amber) 18%, var(--bg-1))" :
                      isFailed ? "color-mix(in oklch, var(--st-rejected) 18%, var(--bg-1))" :
                      "var(--bg-1)",
          border: `1px solid ${isSucceeded ? "var(--olive-soft)" : isRunning ? "var(--amber-deep)" : isFailed ? "var(--st-rejected)" : "var(--line-2)"}`,
          display: "grid", placeItems: "center",
          color: isSucceeded ? "var(--olive)" : isRunning ? "var(--amber)" : isFailed ? "var(--st-rejected)" : "var(--ink-4)",
          fontSize: 13,
          flex: "none",
        }}>
          {isRunning ? (
            <span style={{ display: "inline-block", animation: "spin 1.4s linear infinite" }}>↻</span>
          ) : opGlyph[op.status]}
        </div>
        {!isLast && (
          <div style={{
            flex: 1, width: 1, marginTop: 4,
            background: isSucceeded ? "var(--olive-soft)" : "var(--line-1)",
          }} />
        )}
      </div>

      {/* card */}
      <div style={{
        background: isHovered || isActive ? "var(--bg-2)" : "transparent",
        border: `1px solid ${isHovered || isActive ? "var(--line-2)" : "transparent"}`,
        borderRadius: "var(--r-lg)", padding: "12px 16px 14px",
        transition: "background 200ms, border-color 200ms",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontFamily: "var(--mono)", fontSize: 12.5, color: "var(--ink-1)", letterSpacing: 0.2 }}>{op.name}</span>
          {op.persona && (
            <span style={{
              fontFamily: "var(--mono)", fontSize: 9.5, color: "var(--ink-3)",
              border: "1px solid var(--line-2)",
              padding: "1px 7px", borderRadius: 999,
            }}>{op.persona}</span>
          )}
          <span style={{ flex: 1 }} />
          {op.duration != null && isSucceeded && (
            <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-4)" }}>{op.duration.toFixed(1)}s</span>
          )}
          {isRunning && (
            <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--gold)" }}>running…</span>
          )}
        </div>
        <div style={{
          marginTop: 5, fontFamily: "var(--serif)", fontSize: 16, lineHeight: 1.3,
          color: isSucceeded || isRunning ? "var(--ink-2)" : "var(--ink-3)",
        }}>{op.label}</div>

        {/* running progress bar — indeterminate (no client-side timing) */}
        {isRunning && (
          <div style={{
            marginTop: 8, height: 3, background: "var(--bg-3)", borderRadius: 2, overflow: "hidden", position: "relative",
          }}>
            <div style={{
              position: "absolute", inset: 0, borderRadius: 2,
              background: "linear-gradient(90deg, transparent, var(--amber), transparent)",
              backgroundSize: "180% 100%",
              animation: "sheen 1.6s linear infinite",
            }} />
          </div>
        )}

        {/* produced ideas */}
        {produced.length > 0 && (
          <div style={{
            marginTop: 12, display: "flex", flexWrap: "wrap", gap: 7,
          }}>
            {produced.map(i => (
              <button
                key={i.id}
                onClick={() => onSelectIdea(i.id)}
                style={{
                  background: "var(--bg-2)",
                  border: `1px solid var(--line-1)`,
                  borderLeft: `3px solid ${zoneColor(i.zone)}`,
                  borderRadius: 6, padding: "4px 10px",
                  fontFamily: "var(--sans)", fontSize: 12.5,
                  color: "var(--ink-1)", cursor: "pointer",
                  display: "inline-flex", alignItems: "center", gap: 7,
                }}>
                <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--ink-4)" }}>
                  #{String(i.id).padStart(2, "0")}
                </span>
                {i.title}
              </button>
            ))}
          </div>
        )}

        {/* cohort hint */}
        {op.cohort && op.cohort.length > 0 && (
          <div style={{ marginTop: 8, fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-4)" }}>
            on cohort [{op.cohort.map(c => "#" + String(c).padStart(2, "0")).join(", ")}]
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Idea detail panel (slide-over) ────────────────────────────────── */

function IdeaDetail({ idea, opRuns, ideas, assessments, onClose, onSelectIdea }) {
  if (!idea) return null;
  const zc = zoneColor(idea.zone);
  const origin = opRuns.find(o => o.id === idea.origin);
  const parentIdeas = (idea.parents || []).map(p => ideas.find(i => i.id === p)).filter(Boolean);
  const childIdeas = ideas.filter(i => (i.parents || []).includes(idea.id));
  const scores = assessments.filter(a => a.idea === idea.id);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 60,
        background: "color-mix(in oklch, var(--bg-0) 60%, transparent)",
        backdropFilter: "blur(4px)",
        display: "flex", justifyContent: "flex-end",
        animation: "fade-up 240ms ease-out",
      }}>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 460, height: "100%", background: "var(--bg-1)",
          borderLeft: "1px solid var(--line-2)",
          padding: "32px 32px",
          overflow: "auto",
          boxShadow: "-24px 0 60px -32px rgba(0,0,0,.45)",
        }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-4)" }}>
              #{String(idea.id).padStart(2, "0")}
            </span>
            <KindBadge kind={idea.kind} />
            <ZoneGlyph zone={idea.zone} />
            <TagPill tag={idea.tag} />
          </div>
          <button onClick={onClose} style={{
            background: "transparent", border: "1px solid var(--line-2)",
            color: "var(--ink-3)", borderRadius: 6, padding: "4px 8px",
            cursor: "pointer", fontFamily: "var(--mono)", fontSize: 11,
          }}>esc</button>
        </div>

        <div style={{
          marginTop: 18, fontFamily: "var(--serif)", fontSize: 46, lineHeight: 1.05,
          color: "var(--ink-1)", fontStyle: idea.status === "shortlisted" || idea.status === "selected" ? "italic" : "normal",
        }}>{idea.title}</div>

        <div style={{ marginTop: 14, color: "var(--ink-2)", fontSize: 15, lineHeight: 1.55 }}>
          {idea.desc}
        </div>

        {/* origin */}
        {origin && (
          <Section label="Origin">
            <div style={{ fontSize: 13, color: "var(--ink-2)" }}>
              <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--ink-3)" }}>{origin.name}</span>
              {origin.persona && <span style={{ color: "var(--ink-3)" }}> · {origin.persona}</span>}
              <div style={{ marginTop: 4, color: "var(--ink-3)" }}>{origin.label}</div>
            </div>
          </Section>
        )}

        {parentIdeas.length > 0 && (
          <Section label="Parents">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {parentIdeas.map(p => (
                <ChipLink key={p.id} idea={p} onClick={() => onSelectIdea(p.id)} />
              ))}
            </div>
          </Section>
        )}
        {childIdeas.length > 0 && (
          <Section label="Children">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {childIdeas.map(c => (
                <ChipLink key={c.id} idea={c} onClick={() => onSelectIdea(c.id)} />
              ))}
            </div>
          </Section>
        )}

        {scores.length > 0 && (
          <Section label="Assessments">
            <div style={{ display: "grid", gap: 6 }}>
              {scores.map((s, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  fontFamily: "var(--mono)", fontSize: 12,
                }}>
                  <span style={{ color: "var(--ink-3)" }}>{s.metric}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{
                      width: 100, height: 4, background: "var(--bg-3)", borderRadius: 2, overflow: "hidden",
                    }}>
                      <div style={{
                        height: "100%", width: `${Number(s.value) * 10}%`,
                        background: s.value > 7 ? "var(--olive)" : s.value > 5 ? "var(--amber)" : "var(--ink-4)",
                      }} />
                    </div>
                    <span style={{ color: "var(--ink-1)", minWidth: 32, textAlign: "right" }}>
                      {Number(s.value).toFixed(1)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        <Section label="Status">
          <div style={{
            display: "inline-block",
            fontFamily: "var(--mono)", fontSize: 11, letterSpacing: 0.8,
            color: statusColor(idea.status), textTransform: "uppercase",
            padding: "4px 8px",
            background: `color-mix(in oklch, ${statusColor(idea.status)} 12%, transparent)`,
            border: `1px solid color-mix(in oklch, ${statusColor(idea.status)} 30%, transparent)`,
            borderRadius: 4,
          }}>{idea.status}</div>
        </Section>
      </div>
    </div>
  );
}

function Section({ label, children }) {
  return (
    <div style={{ marginTop: 22 }}>
      <div style={{
        fontFamily: "var(--mono)", fontSize: 9, letterSpacing: 1.4, color: "var(--ink-4)",
        textTransform: "uppercase", marginBottom: 8,
      }}>{label}</div>
      {children}
    </div>
  );
}

function ChipLink({ idea, onClick }) {
  return (
    <button onClick={onClick} style={{
      background: "var(--bg-2)", border: "1px solid var(--line-2)",
      borderLeft: `2px solid ${zoneColor(idea.zone)}`,
      borderRadius: 4, padding: "3px 8px",
      fontSize: 12, color: "var(--ink-1)", cursor: "pointer",
      display: "inline-flex", alignItems: "center", gap: 6,
    }}>
      <span style={{ fontFamily: "var(--mono)", fontSize: 9, color: "var(--ink-4)" }}>
        #{String(idea.id).padStart(2, "0")}
      </span>
      {idea.title}
    </button>
  );
}

Object.assign(window, {
  TreeView, TimelineView, BoardView, IdeaCard, IdeaChip, IdeaDetail, EmptyStage,
  StatusDot, ZoneGlyph, TagPill, KindBadge, zoneColor, statusColor,
});
