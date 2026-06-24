/* Live data layer — replaces the prototype's static data.jsx.

   Holds a single snapshot of the session in a tiny observable store, hydrated
   from the server's /state endpoint (which projects the SQLite logbook +
   event overlay into the IDEATION model the views expect). The /events SSE
   stream is used only as a "something changed, re-fetch" trigger, so a tab
   opened mid-session always sees the full, authoritative state. */

const PHASES = [
  { id: "frame",     label: "Frame",     glyph: "◇" },
  { id: "generate",  label: "Generate",  glyph: "✶" },
  { id: "transform", label: "Transform", glyph: "✧" },
  { id: "evaluate",  label: "Evaluate",  glyph: "◐" },
  { id: "decide",    label: "Decide",    glyph: "▲" },
];

const PERSONA_LABEL = {
  innovator: "innovator",
  wild_card: "wild card",
  connector: "connector",
  provocateur: "provocateur",
  historian: "historian",
  namer: "namer",
};

const EMPTY_STATE = {
  TOPIC: { slug: "", description: "", owner: "" },
  FRAME: null,
  IDEAS: [],
  ASSESSMENTS: [],
  OPERATOR_RUNS: [],
  PLAN: [],
  PHASES,
  PERSONA_LABEL,
  checkpoint: null,
  complete: false,
  startedAt: null,
};

function createLiveStore() {
  let state = EMPTY_STATE;
  const listeners = new Set();
  return {
    get: () => state,
    set: (next) => {
      // always re-attach the static constants the server doesn't send
      state = { ...next, PHASES, PERSONA_LABEL };
      window.IDEATION = state;
      listeners.forEach((l) => { try { l(state); } catch (e) { /* keep others alive */ } });
    },
    subscribe: (l) => { listeners.add(l); return () => listeners.delete(l); },
  };
}

const LiveStore = createLiveStore();
window.LiveStore = LiveStore;
window.IDEATION = LiveStore.get();

(function wireLiveData() {
  let inflight = false;
  let pending = false;

  async function refetch() {
    if (inflight) { pending = true; return; }
    inflight = true;
    try {
      const r = await fetch("/state", { cache: "no-store" });
      if (r.ok) LiveStore.set(await r.json());
    } catch (e) {
      /* server momentarily unreachable — keep last good snapshot */
    } finally {
      inflight = false;
      if (pending) { pending = false; refetch(); }
    }
  }

  // first paint
  refetch();

  // event-driven refresh — debounce bursts (a generate op emits ~10 events)
  let debounce = null;
  try {
    const es = new EventSource("/events");
    es.onmessage = () => {
      clearTimeout(debounce);
      debounce = setTimeout(refetch, 140);
    };
    es.onerror = () => { /* EventSource auto-reconnects */ };
  } catch (e) { /* no SSE — the poll below still keeps us fresh */ }

  // safety poll — covers any missed event and the no-SSE fallback
  setInterval(refetch, 4000);

  window.__ideationRefetch = refetch;
})();
