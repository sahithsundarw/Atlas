const { useState, useEffect, useRef } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "light",
  "accent": "#C8632F",
  "showWeatherCard": true,
  "showFeatured": true,
  "greeting": "Good evening"
}/*EDITMODE-END*/;

const FEATURED = [
  { id: "kyoto",   country: "JP", place: "Kyoto",     blurb: "Temple gardens, late spring",     img: "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=600&q=80" },
  { id: "lisbon",  country: "PT", place: "Lisbon",    blurb: "Tiled hills above the Tagus",     img: "https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=600&q=80" },
  { id: "sant",    country: "GR", place: "Santorini", blurb: "Whitewash and caldera light",     img: "https://images.unsplash.com/photo-1613395877344-13d4a8e0d49e?w=600&q=80" },
];

const RECENT_FALLBACK = [
  { id: "1", title: "Outdoor Kyoto in May" },
  { id: "2", title: "Best food in Paris" },
  { id: "3", title: "Tell me about Tokyo" },
  { id: "4", title: "Things to do in NYC" },
  { id: "5", title: "How is India in the winter?" },
  { id: "6", title: "Tell me about Santorini" },
  { id: "7", title: "Quiet alternatives to Bali" },
  { id: "8", title: "3 days in Lisbon" },
];

const PROMPTS = [
  "Tokyo in cherry blossom season",
  "Outdoor Kyoto in May",
  "Best food in Paris",
  "3 days in Lisbon",
];

// ─── API helpers ──────────────────────────────────────────────────────────────
async function queryAtlas(message, threadId) {
  const res = await fetch('http://localhost:8000/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId }),
  });
  if (!res.ok) throw new Error('API error ' + res.status);
  return res.json();
}

function getWeatherIcon(condition) {
  const c = (condition || '').toLowerCase();
  if (c.includes('clear') || c.includes('sunny')) return 'sun';
  if (c.includes('few clouds') || c.includes('partly')) return 'partly';
  if (c.includes('cloud') || c.includes('overcast')) return 'cloud';
  if (c.includes('drizzle') || c.includes('light rain')) return 'shower';
  return 'rain';
}

function generateFollowUps(city, intent) {
  const i = (intent || '').toLowerCase();
  if (i.includes('weather') || i.includes('forecast')) return [
    `Outdoor activities in ${city}`, `Best time to visit ${city}`, `${city} in winter`,
  ];
  if (i.includes('night') || i.includes('bar') || i.includes('club')) return [
    `Best bars in ${city}`, `${city} food scene`, `Hotels in ${city}`,
  ];
  if (i.includes('food') || i.includes('restaurant')) return [
    `Street food in ${city}`, `Rooftop restaurants in ${city}`, `${city} in spring`,
  ];
  return [
    `Best restaurants in ${city}`,
    `${city} in winter`,
    `Things to do in ${city} with family`,
  ];
}

// ─── Glyphs ────────────────────────────────────────────────────────────────
function WxGlyph({ kind, size = 20 }) {
  const s = size, c = "currentColor";
  return (
    <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`} style={{display:"block"}} fill="none" stroke={c} strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round">
      {kind === "sun" && (<><circle cx={s/2} cy={s/2} r={s*0.22}/><g opacity=".7"><line x1={s/2} y1={2} x2={s/2} y2={s*0.18}/><line x1={s/2} y1={s-2} x2={s/2} y2={s*0.82}/><line x1={2} y1={s/2} x2={s*0.18} y2={s/2}/><line x1={s-2} y1={s/2} x2={s*0.82} y2={s/2}/></g></>)}
      {kind === "partly" && (<><circle cx={s*0.38} cy={s*0.38} r={s*0.16}/><path d={`M ${s*0.32} ${s*0.7} a ${s*0.18} ${s*0.18} 0 0 1 ${s*0.36} 0 h ${s*0.06} a ${s*0.12} ${s*0.12} 0 0 1 0 ${s*0.24} h ${-s*0.5} a ${s*0.12} ${s*0.12} 0 0 1 0 ${-s*0.24} z`}/></>)}
      {kind === "cloud" && (<path d={`M ${s*0.22} ${s*0.6} a ${s*0.2} ${s*0.2} 0 0 1 ${s*0.4} 0 h ${s*0.06} a ${s*0.14} ${s*0.14} 0 0 1 0 ${s*0.28} h ${-s*0.56} a ${s*0.14} ${s*0.14} 0 0 1 0 ${-s*0.28} z`}/>)}
      {kind === "shower" && (<><path d={`M ${s*0.22} ${s*0.5} a ${s*0.2} ${s*0.2} 0 0 1 ${s*0.4} 0 h ${s*0.06} a ${s*0.14} ${s*0.14} 0 0 1 0 ${s*0.28} h ${-s*0.56} a ${s*0.14} ${s*0.14} 0 0 1 0 ${-s*0.28} z`}/><line x1={s*0.38} y1={s*0.86} x2={s*0.34} y2={s*0.96}/><line x1={s*0.6} y1={s*0.86} x2={s*0.56} y2={s*0.96}/></>)}
      {kind === "rain" && (<><path d={`M ${s*0.22} ${s*0.46} a ${s*0.2} ${s*0.2} 0 0 1 ${s*0.4} 0 h ${s*0.06} a ${s*0.14} ${s*0.14} 0 0 1 0 ${s*0.28} h ${-s*0.56} a ${s*0.14} ${s*0.14} 0 0 1 0 ${-s*0.28} z`}/><line x1={s*0.34} y1={s*0.82} x2={s*0.3} y2={s*0.95}/><line x1={s*0.5} y1={s*0.82} x2={s*0.46} y2={s*0.95}/><line x1={s*0.66} y1={s*0.82} x2={s*0.62} y2={s*0.95}/></>)}
    </svg>
  );
}

// ─── Forecast chart (SVG, no external deps) ───────────────────────────────────
function ForecastChart({ forecast }) {
  const [hovIdx, setHovIdx] = useState(null);
  const svgRef = useRef(null);

  if (!forecast || forecast.length < 2) return null;

  const W = 600, H = 130, PAD_L = 32, PAD_R = 12, PAD_T = 14, PAD_B = 28;
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;

  const allTemps = forecast.flatMap(d => [d.lo, d.hi]);
  const tMin = Math.floor(Math.min(...allTemps)) - 2;
  const tMax = Math.ceil(Math.max(...allTemps)) + 2;

  const xOf = i => PAD_L + (i / (forecast.length - 1)) * plotW;
  const yOf = v => PAD_T + plotH - ((v - tMin) / (tMax - tMin)) * plotH;

  const hiPts = forecast.map((d, i) => [xOf(i), yOf(d.hi)]);
  const loPts = forecast.map((d, i) => [xOf(i), yOf(d.lo)]);

  const toPath = pts => pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const bandPath = toPath(hiPts) + ' ' + [...loPts].reverse().map(p => `L${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ') + ' Z';

  const yTicks = [];
  const step = (tMax - tMin) > 20 ? 10 : 5;
  for (let t = Math.ceil(tMin / step) * step; t <= tMax; t += step) {
    yTicks.push(t);
  }

  function handleMouseMove(e) {
    const svg = svgRef.current;
    if (!svg) return;
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const svgPt = pt.matrixTransform(svg.getScreenCTM().inverse());
    let nearest = 0, minDist = Infinity;
    forecast.forEach((_, i) => {
      const dist = Math.abs(svgPt.x - xOf(i));
      if (dist < minDist) { minDist = dist; nearest = i; }
    });
    setHovIdx(nearest);
  }

  const hov = hovIdx !== null ? forecast[hovIdx] : null;
  const hovX = hovIdx !== null ? xOf(hovIdx) : 0;
  const TIP_W = 80, TIP_H = 44, TIP_PAD = 6;
  const tipX = Math.min(Math.max(hovX - TIP_W / 2, PAD_L), W - PAD_R - TIP_W);
  const tipY = PAD_T - 2;

  return (
    <div className="forecast-chart">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        style={{width:'100%', height:'auto', display:'block', cursor:'crosshair'}}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHovIdx(null)}
      >
        <defs>
          <linearGradient id="band-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.22"/>
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.04"/>
          </linearGradient>
        </defs>

        {/* invisible hit area */}
        <rect x={PAD_L} y={PAD_T} width={plotW} height={plotH + PAD_B} fill="transparent"/>

        {yTicks.map(t => (
          <g key={t}>
            <line x1={PAD_L} y1={yOf(t)} x2={W - PAD_R} y2={yOf(t)} stroke="var(--border)" strokeWidth="0.5" strokeDasharray="3,3"/>
            <text x={PAD_L - 4} y={yOf(t)} textAnchor="end" dominantBaseline="middle" fontSize="9" fill="var(--muted)">{t}°</text>
          </g>
        ))}

        <path d={bandPath} fill="url(#band-fill)"/>
        <path d={toPath(loPts)} fill="none" stroke="var(--accent)" strokeWidth="1.5" strokeOpacity="0.45" strokeLinejoin="round"/>
        <path d={toPath(hiPts)} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinejoin="round"/>

        {hiPts.map((p, i) => (
          <circle key={i} cx={p[0]} cy={p[1]} r={hovIdx === i ? 4 : 2.5} fill="var(--accent)" style={{transition:'r 0.1s'}}/>
        ))}
        {loPts.map((p, i) => (
          <circle key={i} cx={p[0]} cy={p[1]} r={hovIdx === i ? 3.5 : 2} fill="var(--accent)" opacity={hovIdx === i ? 0.8 : 0.5} style={{transition:'r 0.1s'}}/>
        ))}

        {forecast.map((d, i) => (
          <text key={i} x={xOf(i)} y={H - 7} textAnchor="middle" fontSize="9" fill={hovIdx === i ? "var(--accent)" : "var(--muted)"}>{d.date}</text>
        ))}

        {hov && (
          <g>
            <line x1={hovX} y1={PAD_T} x2={hovX} y2={H - PAD_B} stroke="var(--accent)" strokeWidth="1" strokeDasharray="3,2" strokeOpacity="0.6"/>
            <rect x={tipX} y={tipY} width={TIP_W} height={TIP_H} rx="4" fill="var(--surface)" stroke="var(--border)" strokeWidth="0.75" filter="drop-shadow(0 1px 4px rgba(0,0,0,0.15))"/>
            <text x={tipX + TIP_W / 2} y={tipY + TIP_PAD + 8} textAnchor="middle" fontSize="9" fill="var(--muted)" fontWeight="500">{hov.date}</text>
            <text x={tipX + TIP_PAD + 4} y={tipY + TIP_PAD + 22} fontSize="9" fill="var(--accent)" fontWeight="600">▲ {Math.round(hov.hi)}°C</text>
            <text x={tipX + TIP_PAD + 4} y={tipY + TIP_PAD + 35} fontSize="9" fill="var(--accent)" fontWeight="400" opacity="0.65">▼ {Math.round(hov.lo)}°C</text>
          </g>
        )}
      </svg>
    </div>
  );
}

// ─── Photo grid ───────────────────────────────────────────────────────────────
function PhotoGrid({ urls }) {
  if (!urls || urls.length === 0) return null;
  return (
    <div className="photo-grid">
      {urls.slice(0, 6).map((url, i) => (
        <div className="photo-item" key={i}>
          <img src={url} alt="" loading="lazy" />
        </div>
      ))}
    </div>
  );
}

// ─── Sidebar ───────────────────────────────────────────────────────────────
function Sidebar({ active, onSelect, onNew, theme, onTheme, chatHistory }) {
  const items = chatHistory.length > 0 ? chatHistory : RECENT_FALLBACK;
  return (
    <aside className="sidebar" data-screen-label="sidebar">
      <div className="brand">
        <span className="brand-dot"></span>
        <span className="brand-mark">Atlas</span>
      </div>

      <button className="new-chat" onClick={onNew}>
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M6.5 2v9M2 6.5h9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
        New conversation
      </button>

      <div className="side-section">Recent</div>

      <nav className="side-list" aria-label="Recent conversations">
        {items.map(it => (
          <button
            key={it.id}
            className={"side-item" + (active === it.id ? " is-active" : "")}
            onClick={() => onSelect(it)}
          >
            {it.title}
          </button>
        ))}
      </nav>

      <div className="side-foot">
        <div className="avatar">SA</div>
        <div className="who-name">Sahith</div>
        <button className="icon-btn" aria-label="Toggle theme" onClick={onTheme} title={theme === "light" ? "Switch to dark" : "Switch to light"}>
          {theme === "light" ? (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M11 8.2A4.5 4.5 0 0 1 5.8 3a4.5 4.5 0 1 0 5.2 5.2z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/></svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="7" cy="7" r="2.4" stroke="currentColor" strokeWidth="1.2"/><path d="M7 1.5v1.6M7 10.9v1.6M1.5 7h1.6M10.9 7h1.6M3.1 3.1l1.1 1.1M9.8 9.8l1.1 1.1M3.1 10.9l1.1-1.1M9.8 4.2l1.1-1.1" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round"/></svg>
          )}
        </button>
      </div>
    </aside>
  );
}

// ─── Landing (composer-as-hero) ────────────────────────────────────────────
function Landing({ onAsk, greeting, showFeatured }) {
  return (
    <div className="landing" data-screen-label="01 Landing">
      <div className="landing-inner">
        <div className="welcome">
          <div className="welcome-eyebrow">{greeting}, Sahith</div>
          <h1 className="welcome-h1">Where to <em>next?</em></h1>
        </div>

        <Composer onSend={onAsk} placeholder="Ask Atlas about anywhere…" big />

        <div className="prompts">
          {PROMPTS.map(p => (
            <button key={p} className="prompt" onClick={() => onAsk(p)}>
              <span className="prompt-arrow">→</span>
              {p}
            </button>
          ))}
        </div>

        {showFeatured && (
          <section className="featured">
            <header className="featured-head">
              <span className="featured-eyebrow">Featured this week</span>
              <a className="featured-link" href="#">See all 142 →</a>
            </header>
            <div className="featured-row">
              {FEATURED.map(f => (
                <button key={f.id} className="feat-card" onClick={() => onAsk(`Tell me about ${f.place}`)}>
                  <div className="feat-img" style={{backgroundImage: `url(${f.img})`}}>
                    <span className="feat-cc">{f.country}</span>
                  </div>
                  <div className="feat-meta">
                    <div className="feat-place">{f.place}</div>
                    <div className="feat-blurb">{f.blurb}</div>
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

// ─── Chat ──────────────────────────────────────────────────────────────────
function Chat({ onAsk, showWeather, messages, loading, error }) {
  const threadRef = useRef(null);

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [messages, loading]);

  return (
    <div className="chat" data-screen-label="02 Chat">
      <div className="chat-thread" ref={threadRef}>

        {messages.map((msg, idx) => {
          if (msg.role === 'user') {
            return (
              <div key={idx} className="msg msg-user">
                <div className="msg-bubble">{msg.content}</div>
              </div>
            );
          }

          const d = msg.data || {};
          const forecast = (d.weather_forecast || []).map(w => ({
            date: (w.date || '').length >= 10 ? w.date.slice(5, 10).replace('-', '/') : (w.date || ''),
            lo: w.temp_min_c,
            hi: w.temp_max_c,
            rain: w.precipitation_mm,
            icon: getWeatherIcon(w.condition),
          }));

          const heroImg = (d.image_urls && d.image_urls[0]) || '';
          const extraImgs = (d.image_urls || []).slice(1);
          const currentTemp = forecast.length > 0 ? Math.round(forecast[0].hi) : null;
          const followUps = generateFollowUps(d.city || '', d.intent || '');

          const paragraphs = (msg.content || '')
            .split(/\n\n+/)
            .map(p => p.trim())
            .filter(Boolean);

          return (
            <div key={idx} className="msg msg-ai">
              {heroImg && (
                <div className="place-hero" style={{backgroundImage: `url(${heroImg})`}}>
                  <div className="place-hero-meta">
                    {d.flag && <span className="place-cc">{d.flag}</span>}
                    <span className="place-name">{d.city || 'Atlas'}</span>
                  </div>
                  <div className="place-hero-now">
                    {currentTemp !== null && (
                      <span className="now-temp">{currentTemp}°</span>
                    )}
                    <span className="now-cond">
                      {d.source === 'web' ? 'Live search' : 'Knowledge base'}
                    </span>
                    {d.source !== 'web' && d.similarity_score > 0 && (
                      <span className="confidence-badge" title="Vector similarity to knowledge base">
                        {Math.round(d.similarity_score * 100)}% match
                      </span>
                    )}
                  </div>
                </div>
              )}

              <div className="ai-body">
                {paragraphs.map((p, i) => <p key={i}>{p}</p>)}
              </div>

              {showWeather && d.source === 'seasonal' && (
                <div className="card weather-card">
                  <header className="card-head">
                    <div className="card-title">Seasonal climate</div>
                    <div className="card-sub">{d.city} · historical averages</div>
                  </header>
                  <div className="seasonal-banner">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"><circle cx="8" cy="8" r="3"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.1 3.1l1.4 1.4M11.5 11.5l1.4 1.4M3.1 12.9l1.4-1.4M11.5 4.5l1.4-1.4"/></svg>
                    <span>Live 5-day forecast not available for this period — see description above for climate details.</span>
                  </div>
                </div>
              )}

              {showWeather && d.source !== 'seasonal' && forecast.length > 0 && (
                <div className="card weather-card">
                  <header className="card-head">
                    <div className="card-title">6-day forecast</div>
                    <div className="card-sub">{d.city} · just now</div>
                  </header>
                  <ForecastChart forecast={forecast} />
                  <div className="wx-row">
                    {forecast.map((fd, i) => (
                      <div key={i} className={"wx-cell" + (fd.rain > 10 ? " is-wet" : "")}>
                        <div className="wx-date">{fd.date}</div>
                        <div className="wx-icon"><WxGlyph kind={fd.icon}/></div>
                        <div className="wx-temp">
                          <span className="wx-hi">{Math.round(fd.hi)}°</span>
                          <span className="wx-lo">{Math.round(fd.lo)}°</span>
                        </div>
                        {fd.rain > 0 && <div className="wx-rain">{fd.rain.toFixed(1)}mm</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {extraImgs.length > 0 && <PhotoGrid urls={extraImgs} />}

              <div className="ai-actions">
                {followUps.map(f => (
                  <button key={f} className="pill" onClick={() => onAsk(f)}>{f}</button>
                ))}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="msg msg-ai">
            <div className="typing-dots">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}

        {error && (
          <div className="msg msg-ai">
            <div className="error-tip">
              <strong>Error</strong>
              Could not reach Atlas. Make sure the API server is running on port 8000. ({error})
            </div>
          </div>
        )}

      </div>

      <div className="composer-dock">
        <Composer onSend={onAsk} placeholder="Ask a follow-up…" />
      </div>
    </div>
  );
}

// ─── Composer ──────────────────────────────────────────────────────────────
function Composer({ onSend, placeholder, big }) {
  const [v, setV] = useState("");
  const submit = () => { if (v.trim()) { onSend(v); setV(""); } };
  return (
    <form className={"composer" + (big ? " composer--big" : "")} onSubmit={e => { e.preventDefault(); submit(); }}>
      <input
        className="comp-input"
        placeholder={placeholder}
        value={v}
        onChange={e => setV(e.target.value)}
        autoFocus={big}
      />
      <button type="submit" className="comp-send" aria-label="Send" disabled={!v.trim()}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 11.5V2.5M3 6.5l4-4 4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
      </button>
    </form>
  );
}

// ─── App ───────────────────────────────────────────────────────────────────
function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [view, setView] = useState("home");
  const [activeChat, setActiveChat] = useState(null);
  const [threadId, setThreadId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);

  async function onAsk(q) {
    setView("chat");
    setLoading(true);
    setError(null);
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    try {
      const data = await queryAtlas(q, threadId);
      setMessages(prev => [...prev, { role: 'assistant', content: data.city_summary, data }]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function onNew() {
    if (messages.length > 0) {
      const firstQ = messages.find(m => m.role === 'user');
      setChatHistory(prev => [{
        id: threadId,
        title: firstQ ? firstQ.content : 'New conversation',
      }, ...prev].slice(0, 20));
    }
    setMessages([]);
    setThreadId(crypto.randomUUID());
    setView("home");
    setActiveChat(null);
  }

  function onSelect(it) {
    setActiveChat(it.id);
    setView("chat");
  }

  const onTheme = () => setTweak("theme", t.theme === "light" ? "dark" : "light");

  const cssVars = { "--accent": t.accent };

  return (
    <div className={"app theme-" + t.theme} style={cssVars}>
      <Sidebar
        active={activeChat}
        onSelect={onSelect}
        onNew={onNew}
        theme={t.theme}
        onTheme={onTheme}
        chatHistory={chatHistory}
      />
      <main className="main">
        {view === "home"
          ? <Landing onAsk={onAsk} greeting={t.greeting} showFeatured={t.showFeatured} />
          : <Chat onAsk={onAsk} showWeather={t.showWeatherCard} messages={messages} loading={loading} error={error} />}
      </main>

      <TweaksPanel>
        <TweakSection label="Theme" />
        <TweakRadio label="Mode" value={t.theme}
          options={["light", "dark"]}
          onChange={v => setTweak("theme", v)} />
        <TweakColor label="Accent" value={t.accent}
          options={["#C8632F", "#B8593F", "#A06A4A", "#5C7A6E", "#3E6B8C"]}
          onChange={v => setTweak("accent", v)} />

        <TweakSection label="Welcome" />
        <TweakSelect label="Greeting" value={t.greeting}
          options={["Good morning", "Good afternoon", "Good evening", "Hello"]}
          onChange={v => setTweak("greeting", v)} />
        <TweakToggle label="Featured row" value={t.showFeatured}
          onChange={v => setTweak("showFeatured", v)} />

        <TweakSection label="Chat" />
        <TweakToggle label="Weather card" value={t.showWeatherCard}
          onChange={v => setTweak("showWeatherCard", v)} />

        <TweakSection label="View" />
        <TweakRadio label="Screen" value={view}
          options={["home", "chat"]}
          onChange={v => setView(v)} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
