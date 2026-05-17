"""Atlas — AI-powered Travel Intelligence. Streamlit entry point."""
import html
import logging
import uuid

import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from agent.graph import get_graph, run_agent  # noqa: E402

st.set_page_config(page_title="Atlas — Travel Intelligence", page_icon="🧭", layout="wide")

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu,footer,header,.stDeployButton,[data-testid="stToolbar"]{display:none!important}
section[data-testid="stSidebar"]{display:none!important}
[data-testid="stAppViewContainer"]{background:#0d1117}
html,body{background:#0d1117;color:#e6edf3}
.block-container{padding:0!important;max-width:100%!important}
.stChatInput>div{background:#21262d!important;border-radius:24px!important;border:0.5px solid #30363d!important}
div[data-testid="stHorizontalBlock"]{gap:0!important}
[data-testid="column"]:first-child{background:#0d1117;border-right:1px solid #21262d;padding:16px 10px!important;min-height:100vh}
[data-testid="column"]:last-child{padding:0!important}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "history" not in st.session_state:
    st.session_state.history = []
if "pending_input" not in st.session_state:
    st.session_state.pending_input = ""
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

@st.cache_resource
def _get_graph():
    return get_graph()

_get_graph()

# ── Helpers ────────────────────────────────────────────────────────────────────
_FLAGS = {
    "tokyo": "🇯🇵", "kyoto": "🇯🇵", "osaka": "🇯🇵",
    "paris": "🇫🇷", "nice": "🇫🇷", "lyon": "🇫🇷",
    "new york": "🇺🇸", "nyc": "🇺🇸", "chicago": "🇺🇸", "los angeles": "🇺🇸",
    "london": "🇬🇧", "edinburgh": "🇬🇧",
    "rome": "🇮🇹", "milan": "🇮🇹", "florence": "🇮🇹",
    "barcelona": "🇪🇸", "madrid": "🇪🇸",
    "bangkok": "🇹🇭", "dubai": "🇦🇪", "singapore": "🇸🇬",
    "sydney": "🇦🇺", "melbourne": "🇦🇺",
    "amsterdam": "🇳🇱", "berlin": "🇩🇪", "munich": "🇩🇪",
    "toronto": "🇨🇦", "vancouver": "🇨🇦",
    "istanbul": "🇹🇷", "prague": "🇨🇿", "vienna": "🇦🇹",
}

def get_flag(city: str) -> str:
    return _FLAGS.get(city.lower().strip(), "🌐")

_COND_ICONS = {
    "clear sky": "☀️", "few clouds": "🌤️", "scattered clouds": "⛅",
    "broken clouds": "☁️", "overcast": "☁️", "shower rain": "🌦️",
    "light rain": "🌦️", "rain": "🌧️", "thunderstorm": "⛈️",
    "snow": "❄️", "mist": "🌫️", "fog": "🌫️", "haze": "🌫️", "drizzle": "🌦️",
}

def _icon(condition: str) -> str:
    c = condition.lower()
    for k, v in _COND_ICONS.items():
        if k in c:
            return v
    if "sun" in c or "clear" in c:
        return "☀️"
    if "cloud" in c:
        return "⛅"
    if "rain" in c:
        return "🌧️"
    return "🌤️"

def _day_cards_html(forecast: list) -> str:
    cards = ""
    for day in forecast[:6]:
        wet = day.get("precipitation_mm", 0) > 10
        bg = "#0d1f2d" if wet else "#161b22"
        border = "#1f6feb" if wet else "#21262d"
        mm = day.get("precipitation_mm", 0)
        rain_str = f"{mm}mm"
        rain_w = "font-weight:500;" if wet else ""
        cards += (
            f'<div style="background:{bg};border-radius:7px;padding:7px 4px;text-align:center;'
            f'border:0.5px solid {border};min-width:0;">'
            f'<div style="font-size:9px;color:#484f58;margin-bottom:3px">{day.get("date","")[-5:]}</div>'
            f'<div style="font-size:14px;margin:2px 0">{_icon(day.get("condition",""))}</div>'
            f'<div style="font-size:10px;font-weight:500;color:#e6edf3">'
            f'{day.get("temp_min_c","?")}–{day.get("temp_max_c","?")}°</div>'
            f'<div style="font-size:9px;color:#58a6ff;margin-top:1px;{rain_w}">{rain_str}</div>'
            f'</div>'
        )
    return (
        f'<div style="display:grid;grid-template-columns:repeat({min(len(forecast),6)},1fr);gap:5px">'
        f'{cards}</div>'
    )

def _render_chart(forecast: list, key: str) -> None:
    dates = [d["date"] for d in forecast]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=[d["temp_max_c"] for d in forecast], name="High °C",
        line=dict(color="#3fb950", width=1.8),
        hovertemplate="%{x}<br>High: %{y}°C<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=[d["temp_min_c"] for d in forecast], name="Low °C",
        line=dict(color="#58a6ff", width=1.8),
        hovertemplate="%{x}<br>Low: %{y}°C<extra></extra>",
        fill="tonexty", fillcolor="rgba(88,166,255,0.06)",
    ))
    fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
        font_color="#8b949e",
        margin=dict(l=0, r=0, t=6, b=0), height=220,
        legend=dict(orientation="h", y=-0.35, font=dict(color="#8b949e", size=11)),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0)",
            showgrid=False,
            tickfont=dict(color="#484f58", size=10),
            linecolor="#21262d",
        ),
        yaxis=dict(
            gridcolor="#21262d",
            tickfont=dict(color="#484f58", size=10),
            title=None,
            zeroline=False,
        ),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)

def _render_turn(question: str, response: dict, idx: int) -> None:
    """Render one turn: user bubble + assistant response."""
    # User bubble
    st.markdown(
        f'<div style="display:flex;justify-content:flex-end;margin:12px 0 6px 0">'
        f'<div style="background:#1f6feb;color:#fff;padding:9px 15px;'
        f'border-radius:16px 16px 3px 16px;font-size:13px;max-width:68%;line-height:1.55">'
        f'{html.escape(question)}</div></div>',
        unsafe_allow_html=True,
    )

    if "errors" in response and not response.get("city"):
        for e in response["errors"]:
            st.error(e)
        return

    city     = response.get("city", "Unknown")
    source   = response.get("source", "web")
    forecast = response.get("weather_forecast", [])
    images   = response.get("image_urls", [])
    credits  = response.get("image_credits", [])
    summary  = response.get("city_summary", "")
    flag     = get_flag(city)
    badge    = "Live search" if source == "web" else "Knowledge base"

    # Open assistant row
    st.markdown(
        '<div style="display:flex;gap:10px;margin:4px 0 18px 0;align-items:flex-start">'
        '<div style="width:26px;height:26px;min-width:26px;border-radius:50%;background:#4a9eff;'
        'display:flex;align-items:center;justify-content:center;font-size:13px;margin-top:2px">🧭</div>'
        '<div style="flex:1;min-width:0">',
        unsafe_allow_html=True,
    )

    # City row + source badge
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
        f'<span style="font-size:16px">{flag}</span>'
        f'<span style="font-size:16px;font-weight:500;color:#e6edf3">{city}</span>'
        f'<span style="font-size:10px;padding:2px 8px;border-radius:10px;'
        f'background:#0d2438;color:#58a6ff">{badge}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for e in response.get("errors", []):
        st.warning(e)

    # Summary
    if summary:
        st.markdown(
            f'<div style="font-size:13px;color:#8b949e;line-height:1.65;'
            f'border-left:2px solid #1f6feb;padding-left:10px;margin-bottom:14px">'
            f'{html.escape(summary)}</div>',
            unsafe_allow_html=True,
        )

    # Forecast
    if forecast:
        st.markdown(
            '<div style="font-size:9px;font-weight:500;letter-spacing:.06em;'
            'color:#484f58;text-transform:uppercase;margin-bottom:6px">6-Day Forecast</div>',
            unsafe_allow_html=True,
        )
        st.markdown(_day_cards_html(forecast), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        _render_chart(forecast, key=f"chart_{idx}")
    else:
        st.warning("Weather unavailable.")

    # Photos
    if images:
        st.markdown(
            '<div style="font-size:9px;font-weight:500;letter-spacing:.06em;'
            'color:#484f58;text-transform:uppercase;margin:14px 0 6px 0">Photos</div>',
            unsafe_allow_html=True,
        )
        pcols = st.columns(3)
        for i, url in enumerate(images[:6]):
            c = credits[i] if i < len(credits) else {}
            with pcols[i % 3]:
                st.image(url, use_container_width=True)
                if c.get("name"):
                    st.markdown(
                        f'<div style="font-size:9px;color:#484f58;margin-top:2px;'
                        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
                        f'<a href="{c.get("link","#")}" target="_blank" '
                        f'style="color:#484f58;text-decoration:none">📷 {c["name"]}</a></div>',
                        unsafe_allow_html=True,
                    )
    else:
        st.warning("Photos unavailable.")

    # Close assistant-row divs
    st.markdown("</div></div>", unsafe_allow_html=True)


# ── Two-panel layout ───────────────────────────────────────────────────────────
sidebar_col, main_col = st.columns([1, 4], gap="small")

# ══════════════════════════════════════════════════════════════════════════════
# LEFT SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with sidebar_col:
    st.markdown(
        '<div style="background:#0d1117;border-right:1px solid #21262d;'
        'min-height:100vh;padding:16px 12px;display:flex;flex-direction:column;gap:4px">'
        '<div style="display:flex;align-items:center;gap:8px;padding:6px 4px 14px 4px">'
        '<div style="width:8px;height:8px;border-radius:50%;background:#4a9eff"></div>'
        '<span style="font-size:15px;font-weight:500;color:#e6edf3">Atlas</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button("✏️  New chat", use_container_width=True):
        if st.session_state.conversation:
            st.session_state.history.append({
                "id": str(uuid.uuid4()),
                "title": st.session_state.conversation[0]["question"][:32],
                "turns": st.session_state.conversation.copy(),
            })
        st.session_state.conversation = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

    if st.session_state.history:
        st.markdown(
            '<div style="font-size:10px;font-weight:500;letter-spacing:.06em;color:#484f58;'
            'text-transform:uppercase;padding:10px 4px 4px 4px">Recent</div>',
            unsafe_allow_html=True,
        )
        for thread in reversed(st.session_state.history[-8:]):
            if st.button(
                f"💬  {thread['title']}",
                key=f"hist_{thread['id']}",
                use_container_width=True,
            ):
                st.session_state.conversation = thread["turns"]
                st.session_state.thread_id = str(uuid.uuid4())
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT MAIN
# ══════════════════════════════════════════════════════════════════════════════
with main_col:

    # ── EMPTY STATE — HERO ────────────────────────────────────────────────────
    CHIPS = [
        ("🏙️", "Tell me about Tokyo"),
        ("🌸", "Outdoor Kyoto in May"),
        ("🍜", "Best food in Paris"),
        ("🗽", "Things to do in NYC"),
    ]

    if not st.session_state.conversation:
        # Hero: top content (tag + headline + subtitle)
        st.markdown(
            '<div style="background:#0a1628;padding:56px 48px 36px 48px">'
            '<div style="max-width:520px">'
            '<div style="display:inline-flex;align-items:center;gap:6px;'
            'background:rgba(255,255,255,0.07);border:0.5px solid rgba(255,255,255,0.15);'
            'border-radius:20px;padding:5px 14px;font-size:12px;color:rgba(255,255,255,0.6);'
            'margin-bottom:20px">✦ AI-powered travel intelligence</div>'
            '<div style="font-size:42px;font-weight:600;color:#fff;line-height:1.2;margin-bottom:14px">'
            'Your personal<br><span style="color:#4a9eff">travel expert,</span><br>always on.</div>'
            '<p style="font-size:15px;color:rgba(255,255,255,0.45);line-height:1.6;margin:0">'
            'Ask about any city. Get weather, highlights,<br>and photos — instantly.</p>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        # Hero: decorative input bar (visual only)
        st.markdown(
            '<div style="background:#0a1628;padding:0 48px 16px 48px">'
            '<div style="background:rgba(255,255,255,0.07);border:0.5px solid rgba(255,255,255,0.18);'
            'border-radius:32px;padding:14px 20px;display:flex;align-items:center;gap:12px">'
            '<span style="font-size:20px;color:rgba(255,255,255,0.2)">+</span>'
            '<span style="flex:1;font-size:14px;color:rgba(255,255,255,0.3)">'
            'Try "Is Kyoto good in May?" or "Best food in Tokyo"</span>'
            '<div style="width:34px;height:34px;border-radius:50%;background:#4a9eff;'
            'display:flex;align-items:center;justify-content:center;font-size:16px;color:white">↑</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        # Hero: chip buttons (functional Streamlit buttons styled over navy bg)
        st.markdown('<div style="background:#0a1628;padding:0 44px 48px 44px">', unsafe_allow_html=True)
        chip_cols = st.columns(4)
        for col, (emoji, prompt) in zip(chip_cols, CHIPS):
            with col:
                if st.button(f"{emoji} {prompt}", use_container_width=True, key=f"chip_{prompt}"):
                    st.session_state.pending_input = prompt
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── CONVERSATION THREAD ───────────────────────────────────────────────────
    else:
        st.markdown(
            '<div style="max-width:720px;margin:0 auto;padding:20px 20px 80px 20px">',
            unsafe_allow_html=True,
        )
        for i, turn in enumerate(st.session_state.conversation):
            _render_turn(turn["question"], turn["response"], idx=i)
            if i < len(st.session_state.conversation) - 1:
                st.markdown(
                    '<hr style="border:none;border-top:1px solid #1f1f1f;margin:4px 0 20px 0">',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── INPUT BAR ─────────────────────────────────────────────────────────────
    user_input = st.chat_input("Ask about a city or follow up…")

    if not user_input and st.session_state.pending_input:
        user_input = st.session_state.pending_input
        st.session_state.pending_input = ""

    if user_input:
        with st.spinner(""):
            response = run_agent(user_input, st.session_state.thread_id)
        st.session_state.conversation.append({"question": user_input, "response": response})
        st.rerun()
