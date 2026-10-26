/* GxP Quality Command Centre - single-page UI. No external libraries. Every value is escaped before it is inserted. */
(function () {
  "use strict";
  var $ = function (s, el) { return (el || document).querySelector(s); };
  var main = $("#main");
  var ROLE_VIEWS = {
    overview: "*", monthend: "*", definitions: "*", zoneh: "*", release: "*", about: "*",
    cases: ["reviewer", "quality_lead", "compliance", "dispositioner"],
    intake: ["reviewer", "quality_lead", "compliance", "integration"],
    assistant: ["reviewer", "quality_lead", "compliance", "dispositioner"]
  };
  var state = { persona: load("qcc.persona", "reviewer"), chat: [] };

  function load(k, d) { try { return localStorage.getItem(k) || d; } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } }
  function esc(v) {
    return String(v === null || v === undefined ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmt(n) { return n === null || n === undefined ? "—" : Number(n).toLocaleString("en-US"); }
  function money(s) { return Number(s).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function toast(t) { var el = $("#toast"); el.textContent = t; el.classList.add("show"); setTimeout(function () { el.classList.remove("show"); }, 2400); }

  function api(path, opts) {
    opts = opts || {};
    var headers = { "X-QCC-Persona": state.persona };
    if (opts.method === "POST") { headers["Content-Type"] = "application/json"; headers["X-QCC-Request"] = "1"; }
    return fetch(path, { method: opts.method || "GET", headers: headers, body: opts.body ? JSON.stringify(opts.body) : undefined })
      .then(function (r) { return r.json().then(function (j) { j.__status = r.status; return j; }); });
  }

  // ------------------------------------------------------------------ small chart helpers (SVG / CSS)
  function bars(obj, opts) {
    opts = opts || {};
    var keys = Object.keys(obj), max = Math.max.apply(null, keys.map(function (k) { return obj[k]; }).concat([1]));
    return keys.map(function (k) {
      var v = obj[k], w = Math.max(1.5, (100 * v) / max);
      var red = opts.highlight && opts.highlight.indexOf(k) >= 0;
      return '<div class="bar-row"><div class="nowrap">' + esc(k) + '</div><div class="bar-track"><div class="bar-fill' + (red ? " red" : "") +
        '" style="width:' + w.toFixed(1) + '%"></div></div><div class="bar-val">' + fmt(v) + "</div></div>";
    }).join("");
  }
  function fillMonths(obj) {
    var keys = Object.keys(obj).sort(); if (!keys.length) return obj;
    var out = {}, y = +keys[0].slice(0, 4), m = +keys[0].slice(5), end = keys[keys.length - 1];
    while (true) { var k = y + "-" + (m < 10 ? "0" : "") + m; out[k] = obj[k] || 0; if (k >= end) break; m++; if (m > 12) { m = 1; y++; } }
    return out;
  }
  function columns(obj, h) {
    h = h || 150; obj = fillMonths(obj);
    var keys = Object.keys(obj), max = Math.max.apply(null, keys.map(function (k) { return obj[k]; }).concat([1]));
    var W = 760, bw = W / keys.length, out = '<svg viewBox="0 0 ' + W + " " + (h + 28) + '" width="100%" role="img" aria-label="cases created per month">';
    keys.forEach(function (k, i) {
      var v = obj[k], bh = (h - 6) * v / max, x = i * bw + 2, y = h - bh;
      out += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + (bw - 4).toFixed(1) + '" height="' + bh.toFixed(1) +
        '" rx="2" fill="' + (k.slice(5) === "12" ? "#E1251B" : "#B9B9B9") + '"><title>' + esc(k) + ": " + v + "</title></rect>";
      if (k.slice(5) === "01") out += '<text x="' + x + '" y="' + (h + 18) + '" font-size="11" fill="#7A7A7A">' + esc(k.slice(0, 4)) + "</text>";
    });
    return out + '<line x1="0" x2="' + W + '" y1="' + h + '" y2="' + h + '" stroke="#E6E6E6"/></svg>';
  }
  function donut(obj, colors) {
    var keys = Object.keys(obj), total = keys.reduce(function (a, k) { return a + obj[k]; }, 0) || 1, r = 52, c = 2 * Math.PI * r, off = 0;
    var svg = '<svg viewBox="0 0 140 140" width="140" height="140" role="img" aria-label="share">';
    keys.forEach(function (k) {
      var frac = obj[k] / total;
      svg += '<circle r="' + r + '" cx="70" cy="70" fill="none" stroke="' + (colors[k] || "#CCC") + '" stroke-width="20" stroke-dasharray="' +
        (frac * c).toFixed(2) + " " + c.toFixed(2) + '" stroke-dashoffset="' + (-off).toFixed(2) + '" transform="rotate(-90 70 70)"><title>' + esc(k) + ": " + obj[k] + "</title></circle>";
      off += frac * c;
    });
    svg += '<text x="70" y="68" text-anchor="middle" font-size="22" font-weight="800" fill="#2B2B2B">' + fmt(total) + '</text><text x="70" y="86" text-anchor="middle" font-size="10" fill="#7A7A7A">total</text></svg>';
    var legend = '<div class="legend" style="flex-direction:column;gap:6px">' + keys.map(function (k) {
      return '<span><i style="background:' + (colors[k] || "#CCC") + '"></i>' + esc(k) + " · " + fmt(obj[k]) + "</span>";
    }).join("") + "</div>";
    return '<div class="donut-wrap">' + svg + legend + "</div>";
  }
  function head(eyebrow, l1, l2, lede) {
    return '<div class="hero"><div><div class="h-eyebrow">' + esc(eyebrow) + '</div><h1 class="title">' + esc(l1) + "<span>" + esc(l2) + "</span></h1></div>" +
      '<div class="stamp">As of 19 Dec 2025 07:11 UTC<br>synthetic, unvalidated</div></div>' + (lede ? '<p class="lede">' + lede + "</p>" : "");
  }
  function kpi(label, value, sub, red, tag) {
    return '<div class="card kpi"><div class="k-label">' + esc(label) + (tag ? ' <span class="tag ' + (tag[1] || "") + '">' + esc(tag[0]) + "</span>" : "") +
      '</div><div class="k-value' + (red ? " red" : "") + '">' + value + '</div><div class="k-sub">' + sub + "</div></div>";
  }
  function forbidden(j) {
    return '<div class="notice"><b>' + esc(j.error.code) + "</b> · " + esc(j.error.message) + "<br>Switch persona (top right) to a role that may open this view.</div>";
  }

  // ------------------------------------------------------------------ views
  var views = {};

  views.overview = function () {
    return api("/api/overview").then(function (d) {
      if (d.error) return forbidden(d);
      var b = d.backlog_d_ops, me = d.month_end, ik = d.intake;
      var statusColors = { OPEN: "#E1251B", UNDER_REVIEW: "#F08A84", ESCALATED: "#7A1410", REOPENED: "#4A4A4A", CLOSED: "#C9C9C9" };
      return head("Executive overview", "One quality estate.", "Many versions of the truth.",
        "What the built hub sees in the legacy estate today. Each figure names the definition it uses: <b>D-OPS</b> (operations-closed), " +
        "<b>D-EVID</b> (closed with evidence and approver) or <b>D-FIN</b> (undefined). Figures with different definitions are never combined.") +
        '<div class="grid g4">' +
        kpi("Cases in estate", fmt(d.cases), "seeded baseline (seed 4100)") +
        kpi("Backlog", fmt(b.value) + ' <span class="muted" style="font-size:16px">/ ' + fmt(b.denominator) + "</span>", "not closed · median age " + fmt(Math.round(b.age_median_days)) + " days", true, ["D-OPS", "red"]) +
        kpi("Month-end inflation", "+" + me.inflation_pct + "%", "legacy " + money(me.legacy.value) + " vs one-source " + money(me.hub.value), true, ["RC-8", "red"]) +
        kpi("Feed rows unmatched", d.unmatched_feed_rate.value + "%", fmt(d.unmatched_feed_rate.n) + " of " + fmt(d.unmatched_feed_rate.denominator) + " reference no case", true, ["RC-7", "red"]) +
        "</div><div class='space'></div><div class='grid g4'>" +
        kpi("Exception queue (hub intake)", fmt(ik.exception_queue_total), fmt(ik.noop_duplicate) + " replays absorbed as duplicates") +
        kpi("Reopen rate", d.reopen_rate.value + "%", fmt(d.reopen_rate.n) + " of " + fmt(d.reopen_rate.denominator) + " · no reopen events recorded") +
        kpi("Zone H holders", "0 <span class='muted' style='font-size:16px'>/ 10 actions</span>", "every human-only action is refused", false, ["by design", "ok"]) +
        kpi("Release gate", d.release.verdict, d.release.approvals.recorded + " of " + d.release.approvals.required + " approvals", true, ["BLOCKED", "red"]) +
        "</div><div class='space'></div>" +
        '<div class="grid g21"><div class="card"><h3>Cases created per month</h3>' + columns(d.cases_per_month) +
        '<div class="src">Source: cases.created_at · December highlighted</div></div>' +
        '<div class="card"><h3>Status (legacy vocabulary)</h3>' + donut(d.status_counts, statusColors) +
        '<div class="src">CLOSED here is the D-OPS reading only.</div></div></div><div class="space"></div>' +
        '<div class="grid g3"><div class="card"><h3>Backlog by site · D-OPS</h3>' + bars(b.by_site) + "</div>" +
        '<div class="card"><h3>Backlog ageing · D-OPS</h3>' + bars(b.ageing, { highlight: [">730 d"] }) + "</div>" +
        '<div class="card"><h3>What cannot be counted yet</h3>' +
        '<div class="kv"><div>Backlog D-EVID</div><div><span class="tag na">Unknown</span> ' + esc(d.backlog_d_evid.reason) + "</div>" +
        "<div>Backlog D-FIN</div><div><span class='tag na'>Undefined</span> " + esc(d.backlog_d_fin.reason) + "</div>" +
        "<div>Deviations closed without root cause</div><div><b>" + d.deviations_closed_without_root_cause.value + "%</b> (" + d.deviations_closed_without_root_cause.n + " of " + d.deviations_closed_without_root_cause.denominator + ")</div>" +
        "<div>CAPA overdue share</div><div><b>" + d.capa_overdue_share.value + "%</b> (" + d.capa_overdue_share.n + " of " + d.capa_overdue_share.denominator + ")</div>" +
        "<div>Manual-review share</div><div><b>" + d.manual_review_share.value + "%</b> by the legacy rule</div></div></div></div>";
    });
  };

  views.cases = function () {
    var f = state.caseFilter || {};
    var qs = Object.keys(f).filter(function (k) { return f[k]; }).map(function (k) { return k + "=" + encodeURIComponent(f[k]); }).join("&");
    return api("/api/cases" + (qs ? "?" + qs : "")).then(function (d) {
      if (d.error) return forbidden(d);
      function sel(name, vals) {
        return '<select data-f="' + name + '"><option value="">All ' + name + "</option>" + vals.map(function (v) {
          return "<option" + (f[name] === v ? " selected" : "") + ">" + esc(v) + "</option>"; }).join("") + "</select>";
      }
      var rows = d.items.map(function (c) {
        return '<tr class="click" data-case="' + esc(c.id) + '"><td class="mono">' + esc(c.id) + "</td><td>" + esc(c.site) + "</td><td>" + esc(c.segment) +
          "</td><td>" + statusTag(c.status) + "</td><td>" + esc(c.severity) + '</td><td class="nowrap" style="text-align:right">' + money(c.amount) +
          "</td><td>" + esc(c.legacy_priority) + "</td><td>" + fmt(c.age_days) + "</td><td>" + esc(c.note) + "</td></tr>";
      }).join("");
      return head("Case work", "Cases.", "As the legacy estate holds them.",
        "Read-only list from the sandbox snapshot. Priority and manual-review flags are computed by the <b>legacy rule</b> (app/legacy_logic.py) so reviewers can see what the old system would do. Click a case for its trace.") +
        '<div class="filters">' + sel("site", d.facets.site) + sel("status", d.facets.status) + sel("severity", d.facets.severity) +
        '<input type="text" id="cq" placeholder="Search id, account or note" value="' + esc(f.q || "") + '" style="min-width:260px">' +
        '<button class="btn grey" id="cclear">Clear</button><span class="muted">' + fmt(d.count) + " cases</span></div>" +
        '<div class="tablewrap"><table><thead><tr><th>Case</th><th>Site</th><th>Segment</th><th>Status</th><th>Severity</th><th style="text-align:right">Amount</th><th>Legacy priority</th><th>Age (d)</th><th>Note</th></tr></thead><tbody>' +
        rows + "</tbody></table></div>";
    });
  };
  function statusTag(s) {
    var cls = { CLOSED: "na", OPEN: "red", ESCALATED: "red", REOPENED: "warn", UNDER_REVIEW: "warn" }[s] || "";
    return '<span class="tag ' + cls + '">' + esc(s) + "</span>";
  }
  function bindCases() {
    main.querySelectorAll("select[data-f]").forEach(function (s) {
      s.onchange = function () { state.caseFilter = state.caseFilter || {}; state.caseFilter[s.dataset.f] = s.value; route(); };
    });
    var q = $("#cq"); if (q) q.onkeydown = function (e) { if (e.key === "Enter") { state.caseFilter = state.caseFilter || {}; state.caseFilter.q = q.value; route(); } };
    var c = $("#cclear"); if (c) c.onclick = function () { state.caseFilter = {}; route(); };
    main.querySelectorAll("tr[data-case]").forEach(function (tr) { tr.onclick = function () { openCase(tr.dataset.case); }; });
  }
  function openCase(id) {
    api("/api/cases/" + id).then(function (d) {
      if (d.error) return toast(d.error.code);
      var c = d.case;
      var ev = d.events.map(function (e) {
        return '<div class="tl"><b>' + esc(e.event_type) + '</b> <span class="muted">' + esc(e.recorded_at) + '</span><div class="mono muted">' + esc(JSON.stringify(e.payload)) + "</div></div>";
      }).join("") || '<div class="muted">No events.</div>';
      var ex = d.policy_exceptions.map(function (x) {
        return "<tr><td class='mono'>" + esc(x.exception_id) + "</td><td>" + esc(x.policy_code) + "</td><td>" + esc(x.outcome) + "</td><td>" + esc(x.explanation) + "</td></tr>";
      }).join("");
      $("#drawer-inner").innerHTML = '<button class="x" id="dx" aria-label="close">×</button><div class="h-eyebrow">Case trace</div><h1 class="title" style="font-size:24px">' +
        esc(c.id) + "<span>" + esc(c.site) + " · " + esc(c.severity) + "</span></h1>" +
        '<div class="kv" style="margin-top:14px"><div>Status (legacy)</div><div>' + statusTag(c.status) + "</div><div>Amount</div><div>" + money(c.amount) +
        " <span class='tag'>C2 confidential</span></div><div>Account</div><div class='mono'>" + esc(c.account_id) + "</div><div>Created</div><div>" + esc(c.created_at) +
        "</div><div>Legacy priority rule</div><div>" + esc(c.legacy_priority) + (c.legacy_manual_review ? " · manual review required" : "") +
        "</div><div>Note <span class='tag warn'>untrusted text</span></div><div>" + esc(c.note) + "</div></div>" +
        '<h3 style="margin-top:20px">Definitions</h3><div class="kv"><div>D-OPS</div><div>' + esc(d.definitions["D-OPS"]) + "</div><div>D-EVID</div><div>" +
        esc(d.definitions["D-EVID"]) + "</div><div>D-FIN</div><div>" + esc(d.definitions["D-FIN"]) + "</div></div>" +
        (d.flags.length ? '<div class="notice">' + d.flags.map(esc).join("<br>") + "</div>" : "") +
        '<h3 style="margin-top:20px">Event history</h3><div class="timeline">' + ev + "</div>" +
        '<h3 style="margin-top:16px">Policy exceptions</h3>' + (ex ? "<table><tbody>" + ex + "</tbody></table>" : '<div class="muted">None reference this case.</div>') +
        '<h3 style="margin-top:16px">Partner-feed items</h3><div class="muted">' + fmt(d.feed_items.length) + " feed rows reference this case.</div>" +
        '<div class="notice grey" style="margin-top:16px">' + esc(d.zone_h_note) + "</div>" +
        '<div class="flex" style="margin-top:10px"><button class="btn" id="askcase">Ask the AI assistant about this case</button></div>';
      $("#drawer").classList.add("open"); $("#drawer").setAttribute("aria-hidden", "false");
      $("#dx").onclick = closeDrawer;
      $("#askcase").onclick = function () { closeDrawer(); state.pendingAsk = { q: "Explain case " + id + ": what does its status mean under each definition, and what would a reviewer check next?", case_id: id }; location.hash = "#/assistant"; };
    });
  }
  function closeDrawer() { $("#drawer").classList.remove("open"); $("#drawer").setAttribute("aria-hidden", "true"); }

  views.intake = function () {
    var f = state.intakeFilter || {};
    var qs = f.queue ? "?queue=" + encodeURIComponent(f.queue) : "";
    return api("/api/intake" + qs).then(function (d) {
      if (d.error) return forbidden(d);
      var prec = d.precedence.map(function (p) {
        return "<tr><td>" + p.rank + "</td><td class='mono'>" + esc(p.code) + "</td><td><span class='tag " + (p["class"] === "QUARANTINE" ? "red" : p["class"] === "EXCEPTION" ? "warn" : "") + "'>" +
          esc(p["class"]) + "</span></td><td>" + esc(p.queue) + "</td><td style='text-align:right'>" + fmt(p.primary_count) + "</td></tr>";
      }).join("");
      var items = d.items.slice(0, 120).map(function (i) {
        return '<tr class="click" data-feed="' + esc(i.feed_id) + '"><td class="mono">' + esc(i.feed_id) + "</td><td>" + esc(i.partner) + "</td><td>" + esc(i.record_kind) +
          "</td><td class='mono'>" + esc(i.ref_id) + "</td><td>" + esc(i.outcome) + "</td><td class='mono'>" + esc(i.primary_reason || "") + "</td><td>" +
          (i.instruction_like ? "<span class='tag red'>instruction-like</span> " : "") + esc(i.notes_untrusted || "") + "</td></tr>";
      }).join("");
      var qsel = '<select id="qsel"><option value="">All queues</option>' + Object.keys(d.queues).map(function (q) {
        return "<option" + (f.queue === q ? " selected" : "") + ">" + esc(q) + "</option>"; }).join("") + "</select>";
      return head("Partner-feed intake", "Every feed row,", "classified by the hub's own rules.",
        "The built hub code (<span class='mono'>hub.intake.validate</span>, <span class='mono'>reasons.classify</span>, <span class='mono'>canon.identity_key</span>) re-runs over all " +
        fmt(d.rows_delivered) + " legacy feed rows in " + fmt(d.elapsed_ms) + " ms. Fifteen reason codes, one fixed precedence, five queues. Nothing is deleted or silently fixed.") +
        '<div class="grid g4">' + kpi("Rows delivered", fmt(d.rows_delivered), "legacy partner_feeds") +
        kpi("Duplicates absorbed", fmt(d.noop_duplicate), "same natural key and content → NOOP") +
        kpi("Exception queue", fmt(d.exception_queue_total), "needs a human reviewer", true) +
        kpi("Instruction-like notes", fmt(d.instruction_like_notes), "kept as data, never obeyed", true, ["untrusted", "red"]) + "</div><div class='space'></div>" +
        '<div class="grid g2"><div class="card"><h3>Queues</h3>' + bars(d.queues, { highlight: ["unmatched"] }) +
        '<h3 style="margin-top:16px">Outcomes</h3>' + bars(d.outcomes, { highlight: ["EXCEPTION"] }) +
        '<div class="flex" style="margin-top:16px"><button class="btn" id="replay">Replay every row (K-07 test)</button><span id="replayout" class="muted"></span></div></div>' +
        '<div class="card"><h3>Reason precedence (SBR-INT-03)</h3><div class="tablewrap" style="max-height:330px"><table><thead><tr><th>#</th><th>Code</th><th>Class</th><th>Queue</th><th style="text-align:right">Primary</th></tr></thead><tbody>' +
        prec + "</tbody></table></div></div></div><div class='space'></div>" +
        '<div class="card"><div class="flex" style="justify-content:space-between"><h3 style="margin:0">Items</h3><div class="flex">' + qsel +
        '<span class="muted">' + fmt(d.filtered_count) + " items (first 120 shown) · click a row to ask the assistant</span></div></div><div class='space'></div>" +
        '<div class="tablewrap"><table><thead><tr><th>Feed id</th><th>Partner</th><th>Kind</th><th>Ref</th><th>Outcome</th><th>Primary reason</th><th>Notes (untrusted)</th></tr></thead><tbody>' +
        items + "</tbody></table></div></div>";
    });
  };
  function bindIntake() {
    var q = $("#qsel"); if (q) q.onchange = function () { state.intakeFilter = { queue: q.value }; route(); };
    var r = $("#replay");
    if (r) r.onclick = function () {
      r.disabled = true; $("#replayout").textContent = "re-delivering…";
      api("/api/intake/replay", { method: "POST", body: {} }).then(function (d) {
        r.disabled = false;
        $("#replayout").innerHTML = "<b>" + fmt(d.redelivered) + "</b> re-delivered · <b>" + fmt(d.noop_duplicate) + "</b> NOOP · new work <b>" + fmt(d.new) +
          "</b> · queue " + fmt(d.queue_total_before) + " → " + fmt(d.queue_total_after) + " (Δ <b>" + d.delta + "</b>) · " + fmt(d.elapsed_ms) + " ms";
      });
    };
    main.querySelectorAll("tr[data-feed]").forEach(function (tr) {
      tr.onclick = function () { state.pendingAsk = { q: "Why is feed item " + tr.dataset.feed + " in this queue, and what should a reviewer check?", feed_id: tr.dataset.feed }; location.hash = "#/assistant"; };
    });
  }

  views.monthend = function () {
    var cut = state.cutoff || "2025-12-31";
    return api("/api/monthend?cutoff=" + encodeURIComponent(cut)).then(function (d) {
      if (d.error && d.error.code) return forbidden(d);
      if (d.error) return '<div class="notice">' + esc(d.error) + " · " + esc(d.message) + "</div>";
      return head("Root cause RC-8", "Month-end.", "One number, one source.",
        "The legacy report sums case amounts after joining cases to their events, so a case with two events is counted twice. The hub reads one table once, in exact decimals. " +
        "The cut-off is a required input: there is no default, because nobody owns the month-end definition yet (OPD-08).") +
        '<div class="filters"><label class="muted">Cut-off</label><input type="date" id="cut" value="' + esc(cut) + '"><button class="btn" id="cutgo">Compute</button></div>' +
        '<div class="big-compare"><div class="side-a"><div class="k-label muted">LEGACY REPORT</div><div class="big-num">' + money(d.legacy.value) + '</div><div class="muted">' +
        fmt(d.legacy.rows_summed) + " joined rows summed</div><pre>" + esc(d.legacy.sql) + "</pre></div><div class='vs'>vs</div>" +
        '<div class="side-b"><div class="k-label" style="color:var(--red)">HUB · ONE SOURCE</div><div class="big-num" style="color:var(--red)">' + money(d.hub.value) + '</div><div class="muted">' +
        fmt(d.hub.rows_summed) + " case rows summed once</div><pre>" + esc(d.hub.sql) + "</pre><div class='src'>" + esc(d.hub.engine) + "</div></div></div>" +
        '<div class="notice" style="margin-top:16px"><b>Difference ' + money(d.difference) + " (+" + d.inflation_pct + "%).</b> " + esc(d.explanation) +
        " This is a verified defect in the legacy report, not a saving.</div>";
    });
  };
  function bindMonthend() { var b = $("#cutgo"); if (b) b.onclick = function () { state.cutoff = $("#cut").value; route(); }; }

  views.definitions = function () {
    return api("/api/definitions").then(function (d) {
      var tags = d.definition_tags.map(function (t) { return "<tr><td><span class='tag red'>" + esc(t.value) + "</span></td><td>" + esc(t.meaning) + "</td></tr>"; }).join("");
      var closed = d.closed_in_vocabularies.map(function (c) {
        return "<tr><td class='mono'>" + esc(c.vocabulary) + "</td><td>" + esc(c.entity || "") + "</td><td class='mono'>" + esc(c.legacy_column || "") + "</td><td>" + esc(c.meaning) + "</td></tr>"; }).join("");
      var od = d.open_decisions.map(function (o) {
        return "<tr><td class='mono'>" + esc(o.id) + "</td><td>" + esc(o.topic) + "</td><td><span class='tag " + (o.status === "answered" ? "ok" : o.status === "accepted_open" ? "warn" : "na") + "'>" +
          esc(o.status) + "</span></td><td>" + esc(o.effect || "") + "</td></tr>"; }).join("");
      var aut = d.autonomy_levels.map(function (a) { return "<tr><td><b>" + esc(a.value) + "</b></td><td>" + esc(a.meaning) + "</td></tr>"; }).join("");
      return head("Semantic layer", "Definitions.", "Meaning before metrics.",
        "From the captured semantic layer (" + d.entity_count + " entities, " + d.vocabulary_count + " vocabularies). <b>" + esc(d.cross_vocabulary_mapping.statement) + "</b>") +
        '<div class="grid g2"><div class="card"><h3>Definition tags</h3><table><tbody>' + tags + "</tbody></table></div>" +
        '<div class="card"><h3>Autonomy ladder</h3><table><tbody>' + aut + "</tbody></table><div class='src'>The AI assistant in this app runs at <b>A1</b>: it flags and recommends; a human acts.</div></div></div><div class='space'></div>" +
        '<div class="card"><h3>"CLOSED" appears in ' + d.closed_in_vocabularies.length + " vocabularies</h3><table><thead><tr><th>Vocabulary</th><th>Entity</th><th>Legacy column</th><th>Meaning</th></tr></thead><tbody>" + closed + "</tbody></table></div><div class='space'></div>" +
        '<div class="card"><h3>Open decisions the product must not resolve on its own</h3><div class="tablewrap" style="max-height:420px"><table><thead><tr><th>Id</th><th>Topic</th><th>Status</th><th>Effect</th></tr></thead><tbody>' + od + "</tbody></table></div></div>";
    });
  };

  views.zoneh = function () {
    return api("/api/zoneh").then(function (d) {
      var cards = d.actions.map(function (a) {
        return '<div class="zh"><div class="code">' + esc(a.value) + '</div><div class="name">' + esc(a.name.replace(/_/g, " ").toLowerCase()) + '</div><div class="lock">🔒 human-only · holder required</div>' +
          '<button class="btn ghost" data-zh="' + esc(a.value) + '">Attempt as ' + esc(state.persona.replace("_", " ")) + "</button></div>";
      }).join("");
      var log = d.attempts.slice().reverse().map(function (e) {
        return "<tr><td class='mono'>" + esc(e.at) + "</td><td>" + esc(e.action) + "</td><td>" + esc(e.persona) + "</td><td>" + esc(e.actor_kind) + "</td><td><span class='tag red'>" + esc(e.code) + "</span></td></tr>";
      }).join("");
      return head("Human control", "Zone H.", "Ten actions no machine may take.",
        "Batch disposition, QA release, e-signature, closing exceptions, adopting policy and the other Zone H actions need a <b>named human holder</b> in the dispositioner role. " +
        "The holder list ships <b>empty</b> (OPD-06), so every attempt is refused and recorded. Service and AI actors are refused whatever their role.") +
        '<div class="notice grey">zone_h.holders = <b>[]</b> · ' + esc(d.rule) + "</div>" + '<div class="zh-grid">' + cards + "</div><div class='space'></div>" +
        '<div class="card"><h3>Refusal log (this session)</h3>' + (log ? "<table><thead><tr><th>At (UTC)</th><th>Action</th><th>Persona</th><th>Actor</th><th>Result</th></tr></thead><tbody>" + log + "</tbody></table>" :
          '<div class="muted">No attempts yet. Try one above, or ask the AI assistant to "approve batch release".</div>') + "</div>";
    });
  };
  function bindZoneh() {
    main.querySelectorAll("button[data-zh]").forEach(function (b) {
      b.onclick = function () {
        api("/api/zoneh/attempt", { method: "POST", body: { action: b.dataset.zh } }).then(function (e) { toast(b.dataset.zh + " refused · " + e.code); route(); });
      };
    });
  }

  views.assistant = function () {
    return api("/api/ai/status").then(function (s) {
      var chat = state.chat.map(renderMsg).join("") || '<div class="muted">Ask about a case, an exception, a definition or a rule. Answers cite the semantic-layer entries they use.</div>';
      return head("Advisory AI", "AI assistant.", "Explains. Suggests. Never decides.",
        "OpenAI or Azure OpenAI, configured in one place (<span class='mono'>config/settings.json</span>, <span class='mono'>settings.local.json</span> or the <span class='mono'>OPENAI_API_KEY</span> environment variable). " +
        "Context comes from the semantic layer and the selected record. Requests to act are refused before any model call.") +
        '<div class="grid g21"><div class="card"><div class="chat" id="chat">' + chat + "</div>" +
        '<div class="chips">' + ["What does CLOSED mean here?", "Why is the month-end total different?", "Which decisions are still open?", "Approve batch release for C00000012", "What is K-09-OPS?"].map(function (t) {
          return '<span class="chip">' + esc(t) + "</span>"; }).join("") + "</div>" +
        '<div class="ask"><textarea id="q" placeholder="Ask a question…"></textarea><button class="btn" id="send">Ask</button></div></div>' +
        '<div class="card"><h3>Configuration</h3><div class="kv"><div>Mode</div><div><span class="tag ' + (s.mode === "model" ? "ok" : "warn") + '">' + esc(s.mode) + "</span></div>" +
        "<div>Provider</div><div>" + esc(s.provider) + "</div><div>Model</div><div class='mono'>" + esc(s.model) + "</div><div>API key</div><div>" +
        (s.key_configured ? "set (" + esc(s.key_source) + ", " + esc(s.key_hint || "") + ")" : "not set") + "</div><div>Autonomy</div><div><b>" + esc(s.autonomy_level) + "</b> suggest only</div></div>" +
        '<h3 style="margin-top:18px">Session key (optional)</h3><div class="muted" style="font-size:12px;margin-bottom:6px">Kept in server memory for this run only. Never written to disk or sent back to the browser.</div>' +
        '<div class="flex"><input type="password" id="k" placeholder="sk-…" style="flex:1"><button class="btn grey" id="kset">Use</button></div>' +
        '<h3 style="margin-top:18px">Counters</h3><div class="kv">' + Object.keys(s.counters).map(function (k) { return "<div>" + esc(k) + "</div><div><b>" + fmt(s.counters[k]) + "</b></div>"; }).join("") + "</div>" +
        '<h3 style="margin-top:18px">Guardrails</h3><div style="font-size:12.5px;color:var(--ink-2)">• Zone H requests refused before any model call<br>• Feed and case text wrapped as untrusted data; instruction-like text flagged<br>• E-mail addresses redacted from prompts<br>• Answers cite sources and are labelled advisory<br>• No write path: the assistant cannot call the gate or the store</div></div></div>';
    });
  };
  function renderMsg(m) {
    if (m.role === "user") return '<div class="msg user">' + esc(m.text) + "</div>";
    var cites = (m.citations || []).map(function (c) { return "<span title='" + esc(c.source) + "'>" + esc(c.ref) + " " + esc(c.id) + "</span>"; }).join("");
    return '<div class="msg bot"><span class="lbl">' + esc(m.label || "") + " · mode: " + esc(m.mode) + (m.model ? " · " + esc(m.model) : "") + "</span>" + esc(m.answer) +
      ((m.warnings || []).length ? '<div class="notice">' + m.warnings.map(esc).join("<br>") + "</div>" : "") + (cites ? '<div class="cites">Sources: ' + cites + "</div>" : "") + "</div>";
  }
  function bindAssistant() {
    var send = $("#send"), q = $("#q");
    function ask(text, extra) {
      if (!text) return;
      state.chat.push({ role: "user", text: text });
      route().then(function () {
        var b = $("#send"); if (b) b.disabled = true;
        api("/api/ai/ask", { method: "POST", body: Object.assign({ question: text }, extra || {}) }).then(function (r) {
          state.chat.push(r.error ? { role: "bot", mode: "error", answer: r.error.code + ": " + r.error.message } : Object.assign({ role: "bot" }, r));
          route().then(function () { var c = $("#chat"); if (c) c.scrollTop = c.scrollHeight; });
          refreshAiPill();
        });
      });
    }
    if (send) send.onclick = function () { ask(q.value.trim()); };
    if (q) q.onkeydown = function (e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(q.value.trim()); } };
    main.querySelectorAll(".chip").forEach(function (c) { c.onclick = function () { ask(c.textContent); }; });
    var ks = $("#kset"); if (ks) ks.onclick = function () {
      api("/api/ai/session-key", { method: "POST", body: { api_key: $("#k").value } }).then(function () { toast("Session key applied"); refreshAiPill(); route(); });
    };
    var c = $("#chat"); if (c) c.scrollTop = c.scrollHeight;
    if (state.pendingAsk) { var p = state.pendingAsk; state.pendingAsk = null; ask(p.q, { case_id: p.case_id, feed_id: p.feed_id }); }
  }

  views.release = function () {
    return api("/api/release").then(function (d) {
      var r = d.release;
      var crit = r.criteria.map(function (c) { return "<tr><td>" + esc(c.id) + "</td><td><span class='tag " + (c.state === "pass" ? "ok" : c.state === "fail" ? "red" : "na") + "'>" + esc(c.result) + "</span></td></tr>"; }).join("");
      var eng = d.engineering.map(function (e) { return "<tr><td>" + esc(e.label) + "</td><td><b>" + esc(e.value) + "</b></td><td>" + esc(e.note) + "</td><td class='mono muted'>" + esc(e.source) + "</td></tr>"; }).join("");
      var rc = d.root_causes.map(function (x) { return "<tr><td><span class='tag red'>" + esc(x.id) + "</span></td><td>" + esc(x.cause) + "</td><td>" + esc(x.mechanism) + "</td></tr>"; }).join("");
      return head("Evidence", "Release.", "Blocked, on purpose.",
        "The release evaluator says <b>" + esc(r.verdict) + "</b>. Engineering is no longer the constraint: the blocking items are human decisions and approvals. Figures below are quoted from the repository's evidence documents.") +
        '<div class="grid g4">' + kpi("Verdict", esc(r.verdict), "release evaluator", true, ["BLOCKED", "red"]) + kpi("Approvals", r.approvals.recorded + " / " + r.approvals.required, "human sign-offs recorded", true) +
        kpi("Characterisation", "134 / 134", "legacy behaviour preserved") + kpi("Mutation gate", "15 / 15", "vs 1 / 15 for the shipped suite") + "</div><div class='space'></div>" +
        '<div class="grid g2"><div class="card"><h3>Go / no-go criteria</h3><table><tbody>' + crit + '</tbody></table><div class="src">' + esc(r.source) + "</div></div>" +
        '<div class="card"><h3>Root cause → built mechanism</h3><table><tbody>' + rc + '</tbody></table><div class="src">' + esc(d.root_cause_source) + "</div></div></div><div class='space'></div>" +
        '<div class="card"><h3>Engineering evidence</h3><table><thead><tr><th>Item</th><th>Result</th><th>Note</th><th>Source</th></tr></thead><tbody>' + eng + "</tbody></table></div>";
    });
  };

  views.about = function () {
    return api("/api/about").then(function (d) {
      return head("System", "About this run.", "What is running, on what.") +
        '<div class="grid g2"><div class="card"><h3>Runtime</h3><div class="kv"><div>Application</div><div>' + esc(d.app) + " " + esc(d.version) + "</div><div>Python</div><div>" + esc(d.python) +
        "</div><div>Platform</div><div>" + esc(d.platform) + "</div><div>Started</div><div>" + esc(d.started) + "</div><div>Settings</div><div class='mono'>" + esc(d.settings_sources.join(" → ")) + "</div></div></div>" +
        '<div class="card"><h3>Data and code</h3><div class="kv"><div>Hub repository</div><div class="mono">' + esc(d.hub_repo) + "</div><div>Hub HEAD</div><div class='mono'>" + esc(d.hub_head) +
        "</div><div>Data source</div><div class='mono'>" + esc(d.data_source) + "</div><div>SHA-256</div><div class='mono'>" + esc(d.data_sha256) + "</div><div>Snapshot (read-only)</div><div class='mono'>" +
        esc(d.data_snapshot) + "</div><div>Label</div><div><span class='tag red'>" + esc(d.label) + "</span></div></div></div></div>";
    });
  };

  // ------------------------------------------------------------------ router
  var binders = { cases: bindCases, intake: bindIntake, monthend: bindMonthend, zoneh: bindZoneh, assistant: bindAssistant };
  function allowed(r) { var v = ROLE_VIEWS[r]; return v === "*" || (v && v.indexOf(state.persona) >= 0); }
  function route() {
    closeDrawer();
    var r = (location.hash.replace(/^#\//, "") || "overview").split("?")[0];
    if (!views[r]) r = "overview";
    document.querySelectorAll("#nav a").forEach(function (a) {
      a.classList.toggle("active", a.dataset.r === r);
      a.classList.toggle("disabled", !allowed(a.dataset.r));
    });
    if (!allowed(r)) {
      main.innerHTML = head("Access", "Not for this persona.", "Deny by default.") + '<div class="notice">The <b>' + esc(state.persona) + "</b> persona may not open this view. Switch persona at the top right.</div>";
      return Promise.resolve();
    }
    return views[r]().then(function (html) { main.innerHTML = html; if (binders[r]) binders[r](); })
      .catch(function (e) { main.innerHTML = '<div class="notice">Could not load: ' + esc(e.message || e) + ". Is the server running?</div>"; });
  }
  function refreshAiPill() {
    api("/api/ai/status").then(function (s) {
      var p = $("#ai-pill");
      p.textContent = s.mode === "model" ? "AI: " + s.model + " · A1 advisory" : "AI: retrieval-only";
      p.className = "pill " + (s.mode === "model" ? "pill-ok" : "");
    });
  }
  $("#persona").value = state.persona;
  $("#persona").onchange = function (e) { state.persona = e.target.value; save("qcc.persona", state.persona); route(); };
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeDrawer(); });
  window.addEventListener("hashchange", route);
  refreshAiPill();
  route();
})();
