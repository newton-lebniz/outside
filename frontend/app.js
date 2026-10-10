(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const DEMO_LOC = { mode: "demo", lat: 16.2076, lon: 77.3463, place: "Raichur, Karnataka, India" };
  const INTERESTS = [
    ["astronomy", "Astronomy"], ["fitness", "Fitness"], ["nature", "Nature"],
    ["birdwatching", "Birdwatching"], ["community", "Community"], ["exploring", "Exploring"],
  ];
  const TYPE_NAMES = { movement: "Movement", nature: "Nature", social: "Social", sky: "Sky", exploration: "Exploration" };
  const LOADING_MSGS = [
    "Checking the sky.", "Reading the weather.", "Looking for events nearby.",
    "Asking the model on this machine.", "Almost there.",
  ];
  const XP_PER_LEVEL = 500;

  // ---------- storage (best effort) ----------
  const store = {
    get() { try { return JSON.parse(localStorage.getItem("outside.v1")) || {}; } catch { return {}; } },
    set(v) { try { localStorage.setItem("outside.v1", JSON.stringify(v)); } catch { /* ignore */ } },
  };

  const state = { interests: [], loc: null, quest: null, meta: null, ctx: null, stats: null, timer: null, loadTimer: null };

  // ---------- tiny DOM helper (model text always goes through textContent) ----------
  function h(tag, attrs = {}, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === false || v == null) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid != null) el.append(kid.nodeType ? kid : document.createTextNode(kid));
    return el;
  }

  async function api(path, body) {
    let r;
    try {
      r = await fetch(path, {
        method: body ? "POST" : "GET",
        headers: body ? { "Content-Type": "application/json" } : {},
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch {
      throw new Error("Can't reach the Outside server. Start it with: uvicorn backend.main:app");
    }
    if (!r.ok) {
      let detail = "";
      try { detail = (await r.json()).detail; } catch { /* ignore */ }
      throw new Error(typeof detail === "string" && detail ? detail : `Server error (${r.status}).`);
    }
    return r.json();
  }

  // ---------- screens ----------
  const SCREENS = ["onboard", "home", "active", "done"];
  function show(name) {
    for (const s of SCREENS) $(`#screen-${s}`).hidden = s !== name;
    $("#scene").hidden = name === "active";
    document.body.classList.toggle("in-mission", name === "active");
    if (name === "active") setSky("night");
    else if (state.ctx) setSky(skyState(state.ctx));
    window.scrollTo(0, 0);
  }

  // ---------- sky ----------
  const THEME = { day: "#7EC3F0", golden: "#F9D08A", overcast: "#A7B3BC", rain: "#5C6C7B", night: "#0F1733" };
  function setSky(name) {
    document.body.dataset.sky = name;
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", THEME[name]);
  }

  function skyState(ctx) {
    const w = ctx.weather, s = ctx.sky;
    if (!w.is_day) return "night";
    if (["rain", "drizzle", "thunderstorm", "snow"].includes(w.condition) || w.precipitation_mm > 0.1) return "rain";
    if (w.cloud_cover >= 70) return "overcast";
    if (s.minutes_to_sunset >= 0 && s.minutes_to_sunset <= 45) return "golden";
    return "day";
  }

  function toMin(hhmm) { const [a, b] = hhmm.split(":").map(Number); return a * 60 + b; }

  function drawScene(ctx) {
    const w = ctx.weather, s = ctx.sky;
    const now = toMin(ctx.time), set = toMin(s.sunset), rise = toMin(s.sunrise || "06:00");
    let t;
    if (w.is_day) t = (now - rise) / Math.max(set - rise, 1);
    else {
      const night = (1440 - set) + rise;
      t = (now >= set ? now - set : now + 1440 - set) / Math.max(night, 1);
    }
    t = Math.min(Math.max(t, 0.03), 0.97);
    const x = 30 + 330 * t, y = 180 - 560 * t * (1 - t);
    const cc = w.cloud_cover;
    const nClouds = cc >= 85 ? 4 : cc >= 60 ? 3 : cc >= 30 ? 2 : cc >= 10 ? 1 : 0;
    const wet = ["rain", "drizzle", "thunderstorm", "snow"].includes(w.condition) || w.precipitation_mm > 0.1;
    const orbOpacity = cc >= 70 ? 0.45 : 1;
    const cloudSpots = [[96, 78, 1], [262, 96, 1.25], [176, 44, 0.8], [326, 52, 0.9]];
    const NS = "http://www.w3.org/2000/svg";

    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 390 210");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", `${w.is_day ? "Sun" : "Moon"} in the sky. ${w.condition}, ${cc}% cloud cover.`);

    const add = (tag, attrs, parent = svg) => {
      const el = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
      parent.append(el);
      return el;
    };

    add("path", { d: "M30 180 Q195 -100 360 180", fill: "none", stroke: "rgba(255,255,255,.5)", "stroke-width": 2, "stroke-dasharray": "3 8" });

    if (!w.is_day && cc < 60) {
      [[60, 40], [120, 22], [200, 60], [250, 24], [310, 48], [350, 20], [150, 90], [28, 96]].forEach(([sx, sy]) =>
        add("circle", { cx: sx, cy: sy, r: 1.6, fill: "#fff", opacity: 0.85 }));
    }

    const orb = add("g", { class: "orb", opacity: orbOpacity });
    add("circle", { cx: x, cy: y, r: 38, fill: "var(--glow)", opacity: 0.4 }, orb);
    add("circle", { cx: x, cy: y, r: 22, fill: "var(--orb)" }, orb);
    if (!w.is_day) add("circle", { cx: x + 8, cy: y - 5, r: 19, fill: "var(--sky-bottom)", opacity: 0.0 }, orb);

    cloudSpots.slice(0, nClouds).forEach(([cx, cy, sc]) => {
      const g = add("g", { transform: `translate(${cx} ${cy}) scale(${sc})`, fill: "var(--cloud)", opacity: 0.93 });
      add("ellipse", { cx: 0, cy: 0, rx: 38, ry: 14 }, g);
      add("ellipse", { cx: -18, cy: -8, rx: 20, ry: 14 }, g);
      add("ellipse", { cx: 14, cy: -12, rx: 24, ry: 16 }, g);
    });

    if (wet) {
      for (let i = 0; i < 22; i++) {
        const rx = 14 + i * 17.5, ry = 100 + ((i * 37) % 60);
        add("line", { x1: rx, y1: ry, x2: rx - 6, y2: ry + 16, stroke: "rgba(255,255,255,.6)", "stroke-width": 2, "stroke-linecap": "round" });
      }
    }

    add("path", { d: "M0 188 Q70 150 150 178 T300 168 T390 172 V210 H0Z", fill: "var(--hill-back)" });
    add("path", { d: "M0 202 Q100 172 200 196 T390 188 V210 H0Z", fill: "var(--hill-front)" });

    const host = $("#scene");
    host.replaceChildren(svg);
  }

  // ---------- header / level ----------
  function renderLevel() {
    const total = state.stats ? state.stats.total_xp : 0;
    const level = Math.floor(total / XP_PER_LEVEL) + 1;
    $("#level").hidden = false;
    $("#level-text").textContent = `Level ${level}, ${total} XP`;
    $("#level-fill").style.width = `${((total % XP_PER_LEVEL) / XP_PER_LEVEL) * 100}%`;
  }

  // ---------- onboarding ----------
  function renderOnboarding() {
    const wrap = $("#interest-chips");
    wrap.replaceChildren(...INTERESTS.map(([key, label]) =>
      h("button", {
        class: "chip", type: "button", "aria-pressed": String(state.interests.includes(key)), text: label,
        onclick(e) {
          const on = !state.interests.includes(key);
          state.interests = on ? [...state.interests, key] : state.interests.filter((k) => k !== key);
          e.currentTarget.setAttribute("aria-pressed", String(on));
          persist();
        },
      })));
    updateLocStatus();
    show("onboard");
  }

  function updateLocStatus(msg, isError) {
    const el = $("#loc-status");
    el.classList.toggle("error", !!isError);
    if (msg) el.textContent = msg;
    else if (state.loc) el.textContent = state.loc.mode === "geo" ? "Using your location." : `Using the demo location, ${DEMO_LOC.place}.`;
    else el.textContent = "";
    $("#onboard-go").disabled = !state.loc;
  }

  function persist() { store.set({ interests: state.interests, loc: state.loc }); }

  function useGeo() {
    if (!navigator.geolocation) { updateLocStatus("This browser can't share a location. Use the demo location instead.", true); return; }
    updateLocStatus("Waiting for your browser to share a location.");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        state.loc = { mode: "geo", lat: +pos.coords.latitude.toFixed(4), lon: +pos.coords.longitude.toFixed(4), place: "your area" };
        persist(); updateLocStatus();
      },
      () => updateLocStatus("Location was blocked. Allow it in your browser, or use the demo location.", true),
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 },
    );
  }

  // ---------- home ----------
  function startLoading() {
    const area = $("#quest-area");
    const msg = h("p", { class: "msg", text: LOADING_MSGS[0] });
    area.replaceChildren(h("div", { class: "paper loading" }, msg, h("div", { class: "pulse" }),
      h("p", { class: "hint", text: "The first quest can take a few seconds while the model loads." })));
    let i = 0;
    clearInterval(state.loadTimer);
    state.loadTimer = setInterval(() => { i = Math.min(i + 1, LOADING_MSGS.length - 1); msg.textContent = LOADING_MSGS[i]; }, 3200);
  }
  function stopLoading() { clearInterval(state.loadTimer); }

  function contextSentences(ctx) {
    const w = ctx.weather, s = ctx.sky;
    const out = [];
    out.push(`${Math.round(w.temp_c)}°C and ${w.condition} in ${ctx.location.name}, with ${w.cloud_cover}% cloud cover.`);
    if (w.is_day && s.minutes_to_sunset >= 0) out.push(`Sunset is in ${fmtMin(s.minutes_to_sunset)}.`);
    else out.push(`The sun set at ${s.sunset}.`);
    const ev = ctx.nearby_event;
    if (ev) out.push(`${ev.title}${ev.placeholder ? " (demo event)" : ""} is ${ev.distance_km} km away and starts in ${fmtMin(ev.starts_in_minutes)}.`);
    return out;
  }

  function fmtMin(m) {
    m = Math.max(Math.round(m), 0);
    if (m < 60) return `${m} min`;
    const hh = Math.floor(m / 60), mm = m % 60;
    return mm ? `${hh} h ${mm} min` : `${hh} h`;
  }

  function renderQuest(banner) {
    stopLoading();
    const q = state.quest, m = state.meta, ctx = state.ctx;
    drawScene(ctx);
    setSky(skyState(ctx));

    const b = $("#banner");
    b.hidden = !banner;
    if (banner) b.replaceChildren(...banner);

    const heads = [h("span", { class: "type", "data-type": q.quest_type, text: `${TYPE_NAMES[q.quest_type] || q.quest_type} quest` })];
    if (q.is_special) heads.unshift(h("span", { class: "type special", text: "Special quest" }));
    heads.push(h("span", { class: "fact", text: `${q.duration_minutes} min` }), h("span", { class: "fact", text: `+${q.xp} XP` }));
    if (q.is_special && q.walk_minutes) heads.push(h("span", { class: "fact", text: `${q.walk_minutes} min on foot` }));

    const src = m.source === "llm"
      ? `Chosen by ${m.model}, running on this machine, in ${m.latency_s} s.`
      : (m.attempts ? `The model didn't give a usable answer (${m.last_error || "no answer"}), so rules chose this quest.` : "Chosen by the rule-based baseline, no model involved.");

    $("#quest-area").replaceChildren(
      h("div", { class: "paper" + (q.is_special ? " special" : "") },
        ...contextSentences(ctx).map((t) => h("p", { class: "sentence", text: t })),
        h("div", { class: "quest-head" }, ...heads),
        h("h1", { class: "quest-title", text: q.title }),
        h("p", { class: "quest-action", text: q.action }),
        h("p", { class: "quest-why", text: q.reason }),
        h("button", { class: "btn primary wide", type: "button", text: "Start quest", onclick: startMission }),
        h("p", { class: "source" + (m.source === "llm" ? "" : " fallback"), text: src }),
      ),
    );
  }

  function showError(err) {
    stopLoading();
    $("#banner").hidden = true;
    $("#quest-area").replaceChildren(h("div", { class: "paper" },
      h("h1", { text: "No quest yet" }),
      h("p", { class: "status error", text: err.message }),
      h("button", { class: "btn primary wide", type: "button", text: "Try again", onclick: () => loadQuest() }),
    ));
  }

  async function loadQuest(recheck = false) {
    const prev = state.quest;
    show("home");
    startLoading();
    const body = {
      interests: state.interests, lat: state.loc.lat, lon: state.loc.lon, place: state.loc.place,
      use_llm: !$("#rules-only").checked, events_mode: $("#events-mode").value,
    };
    if ($("#sim-weather").value) body.sim_weather = $("#sim-weather").value;
    if ($("#sim-time").value) body.sim_time = $("#sim-time").value;
    try {
      const data = await api("/quest", body);
      state.quest = data.quest; state.meta = data.meta; state.ctx = data.context;
      let banner = null;
      if (recheck && prev && prev.title !== data.quest.title) {
        const lead = prev.quest_type === "sky" && data.quest.quest_type !== "sky"
          ? "The sky isn't cooperating. Sky quest replaced: "
          : "Conditions changed. Quest replaced: ";
        banner = [lead, h("s", { text: prev.title })];
      }
      renderQuest(banner);
    } catch (e) {
      showError(e);
    }
  }

  // ---------- mission ----------
  function startMission() {
    const q = state.quest;
    $("#active-title").textContent = q.title;
    $("#active-action").textContent = q.action;
    $("#active-error").textContent = "";
    const end = Date.now() + q.duration_minutes * 60000;
    const tick = () => {
      const left = Math.max(Math.round((end - Date.now()) / 1000), 0);
      $("#timer").textContent = left === 0 ? "Time's up" : `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;
    };
    clearInterval(state.timer);
    tick();
    state.timer = setInterval(tick, 500);
    show("active");
  }

  async function finishMission() {
    const q = state.quest;
    clearInterval(state.timer);
    $("#finish").disabled = true;
    try {
      const r = await api("/quest/complete", { quest_type: q.quest_type, xp: q.xp, title: q.title });
      state.stats = r;
      renderLevel();
      $("#done-title").textContent = q.is_special ? "Special quest complete" : "Quest complete";
      $("#done-xp").textContent = `+${q.xp} XP`;
      const level = Math.floor(r.total_xp / XP_PER_LEVEL) + 1;
      $("#done-summary").textContent = `${r.today_xp} XP today. You're on level ${level} with ${r.total_xp} XP.`;
      show("done");
    } catch (e) {
      $("#active-error").textContent = e.message;
    } finally {
      $("#finish").disabled = false;
    }
  }

  function cancelMission() { clearInterval(state.timer); show("home"); }

  // ---------- boot ----------
  async function boot() {
    const saved = store.get();
    state.interests = Array.isArray(saved.interests) ? saved.interests : [];
    state.loc = saved.loc || null;

    $("#loc-geo").addEventListener("click", useGeo);
    $("#loc-demo").addEventListener("click", () => { state.loc = DEMO_LOC; persist(); updateLocStatus(); });
    $("#onboard-go").addEventListener("click", () => loadQuest());
    $("#recheck").addEventListener("click", () => { $("#demo").open = false; loadQuest(true); });
    $("#time-live").addEventListener("click", () => { $("#sim-time").value = ""; });
    $("#change-setup").addEventListener("click", renderOnboarding);
    $("#finish").addEventListener("click", finishMission);
    $("#cancel").addEventListener("click", cancelMission);
    $("#next").addEventListener("click", () => loadQuest());

    try { state.stats = await api("/stats"); renderLevel(); } catch { /* shown when a quest is requested */ }

    if (state.loc) loadQuest(); else renderOnboarding();
  }

  boot();
})();
