import re
import uuid

import streamlit as st

from main import app as travel_app  # your compiled LangGraph app

st.set_page_config(page_title="Wayfarer · AI Travel Planner", page_icon="✈️", layout="wide")

# ---------------------------------------------------------------- styling
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root{
  --sky:#EEF3F8; --ink:#10233D; --muted:#5B6B80; --line:#D5DEE8;
  --teal:#0E8A94; --teal-soft:#DDF1F2; --amber:#F4B63F; --paper:#FFFFFF;
}
html, body, [class*="css"], .stApp { font-family:'IBM Plex Sans',sans-serif; color:var(--ink); }
.stApp { background: var(--sky); }
#MainMenu, footer, header[data-testid="stHeader"] { visibility:hidden; height:0; }
.block-container { max-width: 1080px; padding-top: 2.2rem; }

h1,h2,h3 { font-family:'Bricolage Grotesque',sans-serif !important; color:var(--ink); letter-spacing:-.02em; }

/* hero */
.hero { background: var(--ink); color:#fff; border-radius:26px; padding:38px 40px 34px; position:relative; overflow:hidden; }
.hero h1 { color:#fff !important; font-size:3rem; font-weight:800; margin:0 0 6px; line-height:1.05; }
.hero p { color:#B9C8DA; font-size:1.05rem; margin:0; max-width:520px; }
.hero svg { position:absolute; right:-10px; top:-6px; opacity:.95; }

/* input */
.stTextArea textarea { background:var(--paper); border:1.5px solid var(--line); border-radius:16px; font-size:1.02rem; padding:16px; color:var(--ink); }
.stTextArea textarea:focus { border-color:var(--teal); box-shadow:0 0 0 3px var(--teal-soft); }
.stButton>button { background:var(--teal); color:#fff; border:none; border-radius:14px; padding:.7rem 1.6rem; font-weight:600; font-size:1rem; }
.stButton>button:hover { background:#0B737C; color:#fff; }
.stButton>button:focus-visible { outline:3px solid var(--amber); }

/* route stepper */
.route { display:flex; align-items:center; background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:18px 22px; margin:18px 0; }
.stop { display:flex; flex-direction:column; align-items:center; gap:6px; min-width:96px; font-size:.85rem; color:var(--muted); }
.dot { width:18px; height:18px; border-radius:50%; border:3px solid var(--line); background:var(--paper); }
.leg { flex:1; height:0; border-top:3px dotted var(--line); margin-bottom:22px; }
.stop.done { color:var(--ink); } .stop.done .dot { background:var(--teal); border-color:var(--teal); }
.leg.done { border-top:3px solid var(--teal); }
.stop.active { color:var(--ink); font-weight:600; }
.stop.active .dot { border-color:var(--amber); background:var(--amber); animation:pulse 1.2s infinite; }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(244,182,63,.6)} 100%{box-shadow:0 0 0 12px rgba(244,182,63,0)} }
@media (prefers-reduced-motion: reduce){ .stop.active .dot{animation:none} }

/* boarding-pass cards */
.pass { display:flex; background:var(--paper); border:1px solid var(--line); border-radius:18px; margin-bottom:14px; overflow:hidden; }
.pass .main { flex:1; padding:16px 20px; }
.pass .stub { width:130px; padding:16px; background:var(--teal-soft); border-left:2px dashed var(--teal); display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; }
.pass .airline { font-family:'Bricolage Grotesque'; font-weight:700; font-size:1.1rem; }
.pass .path { display:flex; align-items:center; gap:12px; margin-top:8px; font-size:.92rem; color:var(--ink); }
.pass .path .arrow { color:var(--teal); font-size:1.2rem; }
.pass .status { font-weight:600; text-transform:capitalize; color:var(--teal); }
.pass .lbl { font-size:.75rem; color:var(--muted); }

/* hotel cards */
.hotel { background:var(--paper); border:1px solid var(--line); border-left:5px solid var(--amber); border-radius:14px; padding:14px 18px; margin-bottom:12px; }
.hotel a { color:var(--teal); font-weight:600; text-decoration:none; }
.hotel p { margin:6px 0 0; color:var(--muted); font-size:.92rem; }

/* final answer */
.final { background:var(--paper); border:1px solid var(--line); border-radius:22px; padding:10px 30px 24px; box-shadow:0 10px 30px rgba(16,35,61,.07); }

.stTabs [data-baseweb="tab"] { font-family:'Bricolage Grotesque'; font-weight:700; font-size:1rem; }
.stTabs [aria-selected="true"] { color:var(--teal); }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- helpers
STEPS = [
    ("flight_agent", "Flights"),
    ("hotel_agent", "Hotels"),
    ("itinerary_agent", "Itinerary"),
    ("final_agent", "Final plan"),
]


def route_html(done: set, active: str | None) -> str:
    parts = []
    for i, (key, label) in enumerate(STEPS):
        cls = "done" if key in done else ("active" if key == active else "")
        parts.append(f'<div class="stop {cls}"><div class="dot"></div>{label}</div>')
        if i < len(STEPS) - 1:
            parts.append(f'<div class="leg {"done" if key in done else ""}"></div>')
    return f'<div class="route">{"".join(parts)}</div>'


def parse_flights(text: str) -> list[dict]:
    flights, cur = [], {}
    for line in text.splitlines():
        m = re.match(r"\s*(airline|departure|arival|status):(.*)", line)
        if m:
            cur[m.group(1)] = m.group(2).strip()
            if m.group(1) == "status":
                flights.append(cur)
                cur = {}
    return flights


def render_flights(text: str):
    flights = parse_flights(text)
    if not flights:
        st.info("No flight data returned. Check your aviationstack key and plan limits.")
        return
    for f in flights:
        st.markdown(
            f"""
<div class="pass">
  <div class="main">
    <div class="airline">{f.get('airline','unknown')}</div>
    <div class="path"><span>{f.get('departure','unknown')}</span><span class="arrow">✈</span><span>{f.get('arival','unknown')}</span></div>
  </div>
  <div class="stub"><div class="lbl">Status</div><div class="status">{f.get('status','unknown')}</div></div>
</div>""",
            unsafe_allow_html=True,
        )


def render_hotels(text: str):
    blocks = [b for b in text.split("\n\n") if b.strip()]
    if not blocks:
        st.info("No hotel results returned.")
        return
    for b in blocks:
        lines = [l.strip() for l in b.splitlines() if l.strip()]
        title = re.sub(r"^\d+\.\s*\*\*|\*\*$", "", lines[0]) if lines else "Result"
        url = lines[1] if len(lines) > 1 else ""
        desc = " ".join(lines[2:])
        st.markdown(
            f'<div class="hotel"><a href="{url}" target="_blank">{title}</a><p>{desc}</p></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------- state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"user_{uuid.uuid4().hex[:8]}"
if "result" not in st.session_state:
    st.session_state.result = None

# ---------------------------------------------------------------- hero
st.markdown(
    """
<div class="hero">
  <svg width="260" height="170" viewBox="0 0 260 170" fill="none" aria-hidden="true">
    <path d="M10 150 C 80 150, 110 40, 250 30" stroke="#F4B63F" stroke-width="3" stroke-dasharray="3 9" stroke-linecap="round"/>
    <circle cx="10" cy="150" r="6" fill="#0E8A94"/>
    <path d="M232 22 l26 8 -26 8 -6 -6 10 -2 -10 -2z" fill="#fff"/>
  </svg>
  <h1>Wayfarer</h1>
  <p>Tell us where you want to go. Your agents check flights, find stays and write the plan.</p>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")
query = st.text_area(
    "Travel request",
    placeholder="Example: 5 days in Goa from Delhi in December, mid-range budget, love beaches and food",
    height=110,
    label_visibility="collapsed",
)

c1, c2, _ = st.columns([1.2, 1.2, 5])
go = c1.button("Plan my trip")
if c2.button("New chat"):
    st.session_state.thread_id = f"user_{uuid.uuid4().hex[:8]}"
    st.session_state.result = None
    st.rerun()

# ---------------------------------------------------------------- run agent
if go:
    if not query.strip():
        st.warning("Describe your trip first: where, when and what you enjoy.")
    else:
        from langchain_core.messages import HumanMessage

        route_slot = st.empty()
        done, state = set(), {}
        route_slot.markdown(route_html(done, STEPS[0][0]), unsafe_allow_html=True)

        payload = {
            "messages": [HumanMessage(content=query)],
            "user_query": query,
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "final_response": "",
            "llm_calls": 0,
        }
        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        try:
            for update in travel_app.stream(payload, config=config, stream_mode="updates"):
                for node, out in update.items():
                    done.add(node)
                    state.update({k: v for k, v in out.items() if k != "messages"})
                    nxt = next((k for k, _ in STEPS if k not in done), None)
                    route_slot.markdown(route_html(done, nxt), unsafe_allow_html=True)
            st.session_state.result = state
        except Exception as e:
            route_slot.empty()
            st.error(f"Something went wrong while planning: {e}")

# ---------------------------------------------------------------- results
res = st.session_state.result
if res:
    st.markdown(route_html({k for k, _ in STEPS}, None), unsafe_allow_html=True)
    tab_plan, tab_itin, tab_fl, tab_ho = st.tabs(["Your plan", "Itinerary", "Flights", "Hotels"])

    with tab_plan:
        st.markdown('<div class="final">', unsafe_allow_html=True)
        st.markdown(res.get("final_response", ""))
        st.markdown("</div>", unsafe_allow_html=True)
        st.download_button(
            "Download plan",
            res.get("final_response", ""),
            file_name="travel_plan.md",
            mime="text/markdown",
        )
    with tab_itin:
        st.markdown(res.get("itinerary", ""))
    with tab_fl:
        render_flights(res.get("flight_results", ""))
    with tab_ho:
        render_hotels(res.get("hotel_results", ""))