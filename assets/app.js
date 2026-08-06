/* MERIDIAN — MUN crisis newsroom
   Static, no build, no dependencies. Data lives in data/*.json. */

const AG = {
  outlets: null,
  articles: null,
  ticker: null,
  incidents: null,

  async load() {
    if (AG.outlets && AG.articles) return;

    // Preferred path: fetch the JSON, so a deployed site always serves fresh data.
    try {
      const bust = "?v=" + Date.now();
      const [o, a, t, i] = await Promise.all([
        fetch("data/outlets.json" + bust).then((r) => r.json()),
        fetch("data/articles.json" + bust).then((r) => r.json()),
        fetch("data/ticker.json" + bust)
          .then((r) => r.json())
          .catch(() => ({ standing: [] })),
        fetch("data/incidents.json" + bust)
          .then((r) => r.json())
          .catch(() => ({})),
      ]);
      AG.outlets = o;
      AG.articles = a;
      AG.ticker = t;
      AG.incidents = i;
    } catch (err) {
      // Fallback: opened straight off the disk (file://), where browsers block fetch.
      // data/bundle.js is loaded by a plain <script> tag, which is not blocked.
      const b = window.__MERIDIAN__;
      if (!b) throw err;
      AG.outlets = b.outlets;
      AG.articles = b.articles;
      AG.ticker = b.ticker || { standing: [] };
      AG.incidents = b.incidents || {};
    }

    AG.articles = AG.articles.sort((x, y) => new Date(y.published) - new Date(x.published));
  },

  outlet(id) {
    return (
      AG.outlets[id] || {
        name: id,
        short: id,
        kind: "Unknown source",
        color: "#666",
        accent: "#999",
        tell: "This outlet is not in the aggregator's source register.",
      }
    );
  },

  fmt(iso) {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  },

  esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  },

  flags(tags) {
    return (tags || [])
      .map((t) => `<span class="flag flag-${AG.esc(t)}">${AG.esc(t)}</span>`)
      .join("");
  },
};

/* ------------------------------ feed ------------------------------ */

async function renderFeed() {
  await AG.load();
  renderTicker();
  startClock();
  renderChips();
  paintFeed();
  startAutoRefresh();
}

/* Polls for new filings so delegates never have to be told to refresh.
   Silently does nothing when opened from file://, where fetch is blocked. */
function startAutoRefresh(intervalMs = 20000) {
  setInterval(async () => {
    let fresh, freshTicker;
    try {
      const bust = "?v=" + Date.now();
      fresh = await fetch("data/articles.json" + bust).then((r) => r.json());
      freshTicker = await fetch("data/ticker.json" + bust)
        .then((r) => r.json())
        .catch(() => AG.ticker);
    } catch {
      return;
    }

    const known = new Set(AG.articles.map((a) => a.id));
    const added = fresh.filter((a) => !known.has(a.id));
    const changed = added.length > 0 || fresh.length !== AG.articles.length;
    if (!changed) return;

    AG.articles = fresh.sort((x, y) => new Date(y.published) - new Date(x.published));
    AG.ticker = freshTicker;
    AG.fresh = new Set(added.map((a) => a.id));

    renderTicker();
    renderChips();
    paintFeed(AG.filter);
    if (added.length) announce(added.length);
  }, intervalMs);
}

function announce(n) {
  let bar = document.getElementById("newsflash");
  if (!bar) {
    bar = document.createElement("button");
    bar.id = "newsflash";
    bar.className = "newsflash";
    bar.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
      bar.remove();
    });
    document.body.appendChild(bar);
  }
  bar.textContent = `${n} new filing${n === 1 ? "" : "s"} — jump to top`;
  bar.classList.add("show");
  clearTimeout(announce._t);
  announce._t = setTimeout(() => bar.classList.remove("show"), 9000);
}

function renderTicker() {
  const run = document.getElementById("ticker");
  if (!run) return;

  const heads = AG.articles
    .slice(0, 8)
    .map(
      (a) =>
        `<span class="tag">${AG.esc(AG.outlet(a.outlet).short)}</span><span class="txt">${AG.esc(a.headline)}</span>`
    );

  const standing = (AG.ticker.standing || []).map((s) => `<span class="txt standing">${AG.esc(s)}</span>`);

  // interleave so the belt never runs a long stretch of one kind
  const mixed = [];
  const n = Math.max(heads.length, standing.length);
  for (let i = 0; i < n; i++) {
    if (heads[i]) mixed.push(heads[i]);
    if (standing[i]) mixed.push(standing[i]);
  }

  const seq = mixed.join('<span class="sep">&#9670;</span>') + '<span class="sep">&#9670;</span>';
  run.innerHTML = `<span class="seq">${seq}</span><span class="seq">${seq}</span>`;

  // duration scales with content so speed stays constant no matter how many articles exist
  requestAnimationFrame(() => {
    const half = run.scrollWidth / 2;
    const pxPerSec = 62;
    run.style.animationDuration = Math.max(18, Math.round(half / pxPerSec)) + "s";
  });
}

function startClock() {
  const el = document.getElementById("clock");
  if (!el) return;
  const tick = () => {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    el.textContent = `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())} UTC`;
  };
  tick();
  setInterval(tick, 1000);
}

function renderChips() {
  const box = document.getElementById("filters");
  if (!box) return;
  const ids = [...new Set(AG.articles.map((a) => a.outlet))];
  box.innerHTML =
    `<span class="flabel">Source</span>` +
    `<button class="chip" data-outlet="all" aria-pressed="true">All</button>` +
    ids
      .map(
        (id) =>
          `<button class="chip" data-outlet="${AG.esc(id)}" aria-pressed="false">${AG.esc(AG.outlet(id).name)}</button>`
      )
      .join("");

  box.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    box.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === btn)));
    paintFeed(btn.dataset.outlet);
  });
}

function paintFeed(filter = "all") {
  const feed = document.getElementById("feed");
  if (!feed) return;
  AG.filter = filter;
  const list = filter === "all" ? AG.articles : AG.articles.filter((a) => a.outlet === filter);

  if (!list.length) {
    feed.innerHTML = `<div class="empty">No filings from this source yet.</div>`;
    return;
  }

  feed.innerHTML = list
    .map((a) => {
      const o = AG.outlet(a.outlet);
      const lotus = a.outlet === "lotus" ? " lotus" : "";
      const isNew = AG.fresh && AG.fresh.has(a.id) ? " justin" : "";
      return `
      <a class="entry${lotus}${isNew}" href="article.html?id=${encodeURIComponent(a.id)}">
        <div class="entry-meta">
          <span class="outlet-tag" style="background:${AG.esc(o.color)}">${AG.esc(o.short)}</span>
          <span class="stamp">${AG.fmt(a.published)}</span>
          ${a.dateline ? `<span class="stamp">${AG.esc(a.dateline)}</span>` : ""}
        </div>
        <div>
          <h2>${AG.flags(a.tags)}${AG.esc(a.headline)}</h2>
          ${a.standfirst ? `<p>${AG.esc(a.standfirst)}</p>` : ""}
          ${othersNote(a)}
        </div>
      </a>`;
    })
    .join("");
}

/* Intentionally empty. An earlier build flagged on the feed which stories had
   competing versions. That did the delegates' work for them — noticing that two
   outlets disagree is the exercise, not a service the site provides. Kept as a
   named hook so it can be switched back on for a debrief if the chair wants. */
function othersNote() {
  return "";
}

/* ---------------------------- article ---------------------------- */

async function renderArticle() {
  await AG.load();
  const id = new URLSearchParams(location.search).get("id");
  const a = AG.articles.find((x) => x.id === id);
  const root = document.getElementById("article");
  if (!root) return;

  if (!a) {
    root.innerHTML = `<div class="empty">Filing not found. It may have been withdrawn.<br><br><a href="index.html">Return to the wire</a></div>`;
    return;
  }

  const o = AG.outlet(a.outlet);
  const isLotus = a.outlet === "lotus";
  document.title = `${a.headline} — ${o.name}`;
  root.className = "article" + (isLotus ? " lotus-page" : "");

  const body = (a.body || [])
    .map((b) => {
      if (typeof b === "string") return `<p>${AG.esc(b)}</p>`;
      if (b.type === "quote")
        return `<blockquote>${AG.esc(b.text)}${b.cite ? `<cite>${AG.esc(b.cite)}</cite>` : ""}</blockquote>`;
      return "";
    })
    .join("");

  root.innerHTML = `
    <a class="backlink" href="index.html">&larr; Meridian</a>
    <div class="kicker">${AG.esc(o.name)} &nbsp;&middot;&nbsp; ${AG.esc(o.kind)}</div>
    <h1>${AG.flags(a.tags)}${AG.esc(a.headline)}</h1>
    ${a.standfirst ? `<p class="standfirst">${AG.esc(a.standfirst)}</p>` : ""}
    <div class="byline">
      ${a.byline ? AG.esc(a.byline) + " &nbsp;&middot;&nbsp; " : ""}
      ${a.dateline ? AG.esc(a.dateline) + " &nbsp;&middot;&nbsp; " : ""}
      ${AG.fmt(a.published)}
    </div>
    <div class="body">${body}</div>
    ${otherCoverage(a)}
    ${isLotus ? "" : sourceNote(o)}
  `;
}

/* Related coverage, listed the way any aggregator lists it: outlet and headline,
   nothing more. No count, no "these disagree", no comparison link. Delegates have
   to open them and notice for themselves. */
function otherCoverage(a) {
  if (!a.incident) return "";
  const others = incidentGroup(a.incident).filter((x) => x.id !== a.id);
  if (!others.length) return "";
  return `
  <div class="othercov">
    <h3>Also filed on this story</h3>
    <ul>
      ${others
        .map((x) => {
          const o = AG.outlet(x.outlet);
          return `<li><span class="outlet-tag" style="background:${AG.esc(o.color)}">${AG.esc(o.short)}</span>
            <a href="article.html?id=${encodeURIComponent(x.id)}">${AG.esc(x.headline)}</a></li>`;
        })
        .join("")}
    </ul>
  </div>`;
}

function sourceNote(o) {
  return `
  <div class="source-note">
    <h3>About this source</h3>
    <dl>
      <dt>Outlet</dt><dd>${AG.esc(o.name)}</dd>
      <dt>Type</dt><dd>${AG.esc(o.kind)}</dd>
      <dt>Owner</dt><dd>${AG.esc(o.owner || "Not disclosed")}</dd>
      <dt>Corrections</dt><dd>${AG.esc(o.corrections || "None on record")}</dd>
    </dl>
    <p style="margin:12px 0 0"><a href="sources.html">Full source register &rarr;</a></p>
  </div>`;
}

/* ---------------------------- compare ---------------------------- */

function incidentGroup(id) {
  return AG.articles.filter((a) => a.incident === id);
}

function incidentLabel(id) {
  return (AG.incidents && AG.incidents[id] && AG.incidents[id].label) || id;
}

/* A row is contested when the outlets covering it do not all say the same thing.
   Missing entries count as their own position — silence is a claim too. */
function claimMatrix(group) {
  const keys = [];
  group.forEach((a) =>
    Object.keys(a.claims || {}).forEach((k) => {
      if (!keys.includes(k)) keys.push(k);
    })
  );
  return keys.map((k) => {
    const cells = group.map((a) => (a.claims && a.claims[k]) || null);
    const stated = cells.filter(Boolean);
    const contested = new Set(stated.map((s) => s.toLowerCase().trim())).size > 1 || stated.length !== cells.length;
    return { key: k, cells, contested };
  });
}

async function renderCompare() {
  await AG.load();
  const root = document.getElementById("compare");
  if (!root) return;

  const wanted = new URLSearchParams(location.search).get("incident");
  const ids = [...new Set(AG.articles.map((a) => a.incident).filter(Boolean))];
  const show = wanted && ids.includes(wanted) ? [wanted] : ids;

  if (!show.length) {
    root.innerHTML = `<div class="empty">No incident has multi-source coverage yet.</div>`;
    return;
  }

  root.innerHTML =
    `<div style="max-width:700px;margin-bottom:30px">
       <h2 style="font-size:30px;margin:0 0 10px">Compare coverage</h2>
       <p style="color:var(--ink-soft)">When several outlets cover one incident, they rarely agree. Rows highlighted below are the ones where the reporting conflicts. Meridian does not tell you who is right.</p>
     </div>` +
    show
      .map((id) => {
        const group = incidentGroup(id).sort((a, b) => new Date(a.published) - new Date(b.published));
        if (group.length < 2) return "";
        const rows = claimMatrix(group);
        const disputed = rows.filter((r) => r.contested).length;
        const meta = (AG.incidents && AG.incidents[id]) || {};

        const head = group
          .map((a) => {
            const o = AG.outlet(a.outlet);
            return `<th><span class="outlet-tag" style="background:${AG.esc(o.color)}">${AG.esc(o.short)}</span>
              <a href="article.html?id=${encodeURIComponent(a.id)}" class="cmp-head">${AG.esc(a.headline)}</a>
              <span class="cmp-time">${AG.fmt(a.published)}</span></th>`;
          })
          .join("");

        const body = rows
          .map(
            (r) => `<tr class="${r.contested ? "contested" : ""}">
              <th scope="row">${AG.esc(r.key)}${r.contested ? '<span class="cmp-flag">contested</span>' : ""}</th>
              ${r.cells
                .map((c) => (c ? `<td>${AG.esc(c)}</td>` : `<td class="silent">not mentioned</td>`))
                .join("")}
            </tr>`
          )
          .join("");

        return `
        <section class="incident">
          <h3>${AG.esc(meta.label || id)}</h3>
          ${meta.summary ? `<p class="incident-sum">${AG.esc(meta.summary)}</p>` : ""}
          <p class="incident-stat">${group.length} sources &nbsp;·&nbsp; <strong>${disputed}</strong> of ${rows.length} material facts contested</p>
          <div class="cmp-scroll">
            <table class="cmp">
              <thead><tr><th class="cmp-corner"></th>${head}</tr></thead>
              <tbody>${body}</tbody>
            </table>
          </div>
        </section>`;
      })
      .join("");
}

/* ---------------------------- sources ---------------------------- */

async function renderSources() {
  await AG.load();
  const root = document.getElementById("dossiers");
  if (!root) return;
  root.innerHTML = Object.entries(AG.outlets)
    .map(
      ([id, o]) => `
    <div class="dossier">
      <div class="dossier-head" style="background:${AG.esc(o.color)}">
        <div class="kind">${AG.esc(o.kind)}</div>
        <h2>${AG.esc(o.name)}</h2>
      </div>
      <dl>
        <dt>Established</dt><dd>${AG.esc(o.founded)}</dd>
        <dt>Ownership</dt><dd>${AG.esc(o.owner)}</dd>
        <dt>Funding</dt><dd>${AG.esc(o.funding)}</dd>
        <dt>Corrections</dt><dd>${AG.esc(o.corrections)}</dd>
        <dt>Standards</dt><dd>${AG.esc(o.policy)}</dd>
        <dt>Aggregator note</dt><dd><em>${AG.esc(o.tell)}</em></dd>
      </dl>
    </div>`
    )
    .join("");
}
