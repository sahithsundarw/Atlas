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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600&family=Instrument+Serif:ital@0;1&display=swap');

#MainMenu,footer,header,.stDeployButton,[data-testid="stToolbar"]{display:none!important}
section[data-testid="stSidebar"]{display:none!important}
html,body,[data-testid="stAppViewContainer"]{background:#F6F2EA!important}
.block-container{padding:0!important;max-width:100%!important}
*{font-family:"Geist",ui-sans-serif,system-ui,sans-serif!important}
button{font-family:"Geist",ui-sans-serif,system-ui,sans-serif!important}

[data-testid="stChatInput"]>div{
  background:#FBF8F1!important;
  border-radius:4px!important;
  border:1px solid rgba(26,22,18,0.12)!important;
  color:#1A1612!important;
}
[data-testid="stChatInput"] textarea{color:#1A1612!important}
div[data-testid="stHorizontalBlock"]{gap:0!important}
[data-testid="column"]:first-child{
  background:#EFE9DD;
  border-right:1px solid rgba(26,22,18,0.09);
  padding:20px 14px!important;
  min-height:100vh;
}
[data-testid="column"]:last-child{padding:0!important;background:#F6F2EA}

.stButton>button{
  background:#FBF8F1;
  border:1px solid rgba(26,22,18,0.12);
  border-radius:4px;
  color:#1A1612;
  font-size:13px;
  transition:border-color 0.15s;
}
.stButton>button:hover{border-color:rgba(26,22,18,0.3);background:#F6F2EA}
</style>
""", unsafe_allow_html=True)

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
    "bali": "🇮🇩",
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
        bg = "#EAE0D0" if wet else "#FBF8F1"
        border = "#C8632F" if wet else "rgba(26,22,18,0.10)"
        mm = day.get("precipitation_mm", 0)
        rain_color = "#C8632F" if wet else "rgba(26,22,18,0.38)"
        cards += (
            f'<div style="background:{bg};border-radius:4px;padding:8px 4px;text-align:center;'
            f'border:1px solid {border};min-width:0;">'
            f'<div style="font-size:9px;color:rgba(26,22,18,0.38);margin-bottom:3px">{day.get("date","")[-5:]}</div>'
            f'<div style="font-size:14px;margin:2px 0">{_icon(day.get("condition",""))}</div>'
            f'<div style="font-size:10px;font-weight:500;color:#1A1612">'
            f'{day.get("temp_min_c","?")}–{day.get("temp_max_c","?")}°</div>'
            f'<div style="font-size:9px;color:{rain_color};margin-top:1px">{mm}mm</div>'
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
        line=dict(color="#C8632F", width=2),
        hovertemplate="%{x}<br>High: %{y}°C<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=[d["temp_min_c"] for d in forecast], name="Low °C",
        line=dict(color="#C8632F", width=1.5, dash="dot"),
        hovertemplate="%{x}<br>Low: %{y}°C<extra></extra>",
        fill="tonexty", fillcolor="rgba(200,99,47,0.08)",
    ))
    fig.update_layout(
        paper_bgcolor="#FBF8F1", plot_bgcolor="#FBF8F1",
        font_color="rgba(26,22,18,0.5)",
        margin=dict(l=0, r=0, t=6, b=0), height=200,
        legend=dict(orientation="h", y=-0.35, font=dict(color="rgba(26,22,18,0.5)", size=11)),
        xaxis=dict(
            gridcolor="rgba(26,22,18,0.06)",
            tickfont=dict(color="rgba(26,22,18,0.38)", size=10),
            linecolor="rgba(26,22,18,0.09)",
        ),
        yaxis=dict(
            gridcolor="rgba(26,22,18,0.06)",
            tickfont=dict(color="rgba(26,22,18,0.38)", size=10),
            title=None,
            zeroline=False,
        ),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)

def _render_turn(question: str, response: dict, idx: int) -> None:
    st.markdown(
        f'<div style="display:flex;justify-content:flex-end;margin:12px 0 6px 0">'
        f'<div style="background:#C8632F;color:#fff;padding:9px 15px;'
        f'border-radius:4px;font-size:13px;max-width:68%;line-height:1.55">'
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
    sim      = response.get("similarity_score", 0.0)
    badge    = "Live search" if source == "web" else "Knowledge base"
    conf_html = (
        f'<span style="font-size:10px;padding:2px 7px;border-radius:4px;'
        f'background:rgba(200,99,47,0.12);color:#C8632F">{round(sim*100)}% match</span>'
        if source not in ("web", "seasonal") and sim > 0 else ""
    )

    st.markdown(
        '<div style="display:flex;gap:10px;margin:4px 0 18px 0;align-items:flex-start">'
        '<div style="width:26px;height:26px;min-width:26px;border-radius:50%;'
        'background:rgba(200,99,47,0.12);border:1px solid rgba(200,99,47,0.25);'
        'display:flex;align-items:center;justify-content:center;font-size:13px;margin-top:2px">🧭</div>'
        '<div style="flex:1;min-width:0">',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
        f'<span style="font-size:16px">{flag}</span>'
        f'<span style="font-size:16px;font-weight:500;color:#1A1612">{city}</span>'
        f'<span style="font-size:10px;padding:2px 8px;border-radius:4px;'
        f'background:rgba(26,22,18,0.07);color:rgba(26,22,18,0.55)">{badge}</span>'
        f'{conf_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    for e in response.get("errors", []):
        st.warning(e)

    if summary:
        st.markdown(
            f'<div style="font-size:13px;color:rgba(26,22,18,0.65);line-height:1.65;'
            f'border-left:2px solid #C8632F;padding-left:10px;margin-bottom:14px">'
            f'{html.escape(summary)}</div>',
            unsafe_allow_html=True,
        )

    if source == "seasonal":
        st.markdown(
            '<div style="font-size:12px;color:rgba(26,22,18,0.45);font-style:italic;margin-bottom:10px">'
            '☀ Seasonal climate info — live 5-day forecast not available for this period.</div>',
            unsafe_allow_html=True,
        )
    elif forecast:
        st.markdown(
            '<div style="font-size:9px;font-weight:500;letter-spacing:.06em;'
            'color:rgba(26,22,18,0.38);text-transform:uppercase;margin-bottom:6px">6-Day Forecast</div>',
            unsafe_allow_html=True,
        )
        st.markdown(_day_cards_html(forecast), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        _render_chart(forecast, key=f"chart_{idx}")

    if images:
        st.markdown(
            '<div style="font-size:9px;font-weight:500;letter-spacing:.06em;'
            'color:rgba(26,22,18,0.38);text-transform:uppercase;margin:14px 0 6px 0">Photos</div>',
            unsafe_allow_html=True,
        )
        pcols = st.columns(3)
        for i, url in enumerate(images[:6]):
            c = credits[i] if i < len(credits) else {}
            with pcols[i % 3]:
                st.image(url, use_container_width=True)
                if c.get("name"):
                    st.markdown(
                        f'<div style="font-size:9px;color:rgba(26,22,18,0.38);margin-top:2px;'
                        f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
                        f'<a href="{c.get("link","#")}" target="_blank" '
                        f'style="color:rgba(26,22,18,0.38);text-decoration:none">📷 {c["name"]}</a></div>',
                        unsafe_allow_html=True,
                    )

    st.markdown("</div></div>", unsafe_allow_html=True)


sidebar_col, main_col = st.columns([1, 4], gap="small")

with sidebar_col:
    st.markdown(
        '<div style="padding:4px 6px 16px 6px">'
        '<div style="display:flex;align-items:center;gap:8px;padding:2px 0 16px 0">'
        '<div style="width:7px;height:7px;border-radius:50%;background:#C8632F;'
        'box-shadow:0 0 0 3px rgba(200,99,47,0.18)"></div>'
        '<span style="font-family:\'Instrument Serif\',Georgia,serif;font-size:22px;'
        'color:#1A1612;line-height:1">Atlas</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    if st.button("＋  New conversation", use_container_width=True):
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
            '<div style="font-size:11px;font-weight:500;letter-spacing:.04em;'
            'color:rgba(26,22,18,0.38);text-transform:uppercase;padding:10px 4px 4px 4px">Recent</div>',
            unsafe_allow_html=True,
        )
        for thread in reversed(st.session_state.history[-8:]):
            if st.button(thread["title"], key=f"hist_{thread['id']}", use_container_width=True):
                st.session_state.conversation = thread["turns"]
                st.session_state.thread_id = str(uuid.uuid4())
                st.rerun()


with main_col:
    CHIPS = [
        ("🏙️", "Tell me about Tokyo"),
        ("🌸", "Outdoor Kyoto in May"),
        ("🍜", "Best food in Paris"),
        ("🗽", "Things to do in NYC"),
    ]

    if not st.session_state.conversation:
        st.markdown(
            '<div style="padding:56px 48px 36px 48px;max-width:580px">'
            '<div style="font-size:13px;color:rgba(26,22,18,0.45);margin-bottom:16px">Good to see you</div>'
            '<div style="font-family:\'Instrument Serif\',Georgia,serif;font-size:42px;'
            'color:#1A1612;line-height:1.2;margin-bottom:14px">'
            'Where to <em>next?</em></div>'
            '<p style="font-size:15px;color:rgba(26,22,18,0.45);line-height:1.6;margin:0">'
            'Ask about any city — weather, food, things to do, or just vibe.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div style="padding:0 48px 24px 48px">', unsafe_allow_html=True)
        chip_cols = st.columns(4)
        for col, (emoji, prompt) in zip(chip_cols, CHIPS):
            with col:
                if st.button(f"{emoji}  {prompt}", use_container_width=True, key=f"chip_{prompt}"):
                    st.session_state.pending_input = prompt
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown(
            '<div style="max-width:720px;margin:0 auto;padding:20px 20px 80px 20px">',
            unsafe_allow_html=True,
        )
        for i, turn in enumerate(st.session_state.conversation):
            _render_turn(turn["question"], turn["response"], idx=i)
            if i < len(st.session_state.conversation) - 1:
                st.markdown(
                    '<hr style="border:none;border-top:1px solid rgba(26,22,18,0.07);margin:4px 0 20px 0">',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    user_input = st.chat_input("Ask Atlas about anywhere…")

    if not user_input and st.session_state.pending_input:
        user_input = st.session_state.pending_input
        st.session_state.pending_input = ""

    if user_input:
        with st.spinner(""):
            response = run_agent(user_input, st.session_state.thread_id)
        st.session_state.conversation.append({"question": user_input, "response": response})
        st.rerun()
