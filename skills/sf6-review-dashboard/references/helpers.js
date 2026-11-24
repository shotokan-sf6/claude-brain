window.ST = window.ST || {};
ST.fmt = d3.format(',');
ST.pct = d3.format('.0%');
ST.cols = () => [dash.colors[0], dash.colors[1] || dash.colors[0]];
ST.P1 = '<P1 name>';
// ---- chosen set ----
ST.sets = () => { const d = dash.data('sets'); return d.status === 'ok' ? [...d.data].sort((a, b) => a.order - b.order) : []; };
ST.SET = () => { const s = document.getElementById('set-pick'); const all = ST.sets(); return (s && s.value) || (all.length ? all[all.length - 1].set_id : null); };
ST.set = () => ST.sets().find((r) => r.set_id === ST.SET()) || {};
ST.p2 = () => ST.set().p2 || 'Opponent';
ST.inSet = (r) => r.set_id === ST.SET();
ST.REDRAW = ['h_title', 'h_sub', 'leg_sit', 'leg_kind', 'kl0', 'kl1', 'kl2', 'kl3', 'kl4', 'k_burn', 'k_aa', 'k_ch', 'k_pc', 'k_pp', 'c_sit', 'c_lens', 'c_kinds',
  'arche', 'habits_p1', 'habits_p2', 'hab_p2_label', 'story', 't_punish', 'fixes', 'training', 'findings', 'hit_filter_opts', 't_hits'];
dash.draw('set_pick', (el) => { const all = ST.sets(); if (!all.length) return; const cur = ST.SET(); el.replaceChildren();
  all.forEach((r) => { const o = ST.el('option', null, `${r.set_id}: ${r.p1} vs ${r.p2} (${r.p2_char}), ${r.format}`); o.value = r.set_id; if (r.set_id === cur) o.selected = true; el.appendChild(o); });
  if (!el.dataset.bound) { el.dataset.bound = '1'; el.addEventListener('change', () => ST.REDRAW.forEach((n) => dash.draw(n))); } });
ST.swatch = (i, text) => { const s = ST.el('span'); const sw = ST.el('span', 'st-sw'); sw.style.background = ST.cols()[i]; s.append(sw, document.createTextNode(text)); return s; };
dash.draw('h_title', (el) => { const r = ST.set(); el.textContent = r.set_id ? `${r.p1} (${r.p1_char}) - ${r.p1_games} vs ${r.p2} (${r.p2_char}) - ${r.p2_games}` : '—'; });
dash.draw('h_sub', (el) => { const r = ST.set(); el.textContent = r.set_id ? `${r.sub} · ${r.set_id}: ${r.format} (BO${r.format === 'FT2' ? 3 : r.format === 'FT3' ? 5 : 9}), ${r.winner} won ${Math.max(r.p1_games, r.p2_games)}-${Math.min(r.p1_games, r.p2_games)}` : '—'; });
dash.draw('leg_sit', (el) => { el.replaceChildren(ST.swatch(0, ST.P1 + ' took'), ST.swatch(1, ST.p2() + ' took')); });
dash.draw('leg_kind', (el) => { el.replaceChildren(ST.swatch(0, ST.P1), ST.swatch(1, ST.p2())); });
[0, 1, 2, 3, 4].forEach((i) => dash.draw('kl' + i, (el) => { el.textContent = `${ST.P1} / ${ST.p2()}`; }));
dash.draw('hab_p2_label', (el) => { const r = ST.set(); el.textContent = r.set_id ? `${r.p2} (${r.p2_char})` : '—'; });
dash.draw('hit_filter_opts', (el) => { const keep = el.value; el.replaceChildren(); [['', 'Both'], [ST.P1, ST.P1], [ST.p2(), ST.p2()]].forEach(([v, t]) => { const o = ST.el('option', null, t); o.value = v; el.appendChild(o); });
  el.value = [ST.P1, ST.p2()].includes(keep) ? keep : ''; });
ST.el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
ST.kv = (k, v) => { const p = ST.el('p'); p.appendChild(ST.el('span', 'st-k', k + ': ')); p.appendChild(document.createTextNode(v == null ? '—' : v)); return p; };
ST.empty = (el, d) => { el.replaceChildren(); if (d.status !== 'ok') { el.textContent = d.status === 'error' ? 'Failed to load' : '—'; return true; } return false; };

// ---- calcs (all from hits + events) ----
ST.p2of = (sets, sid) => (sets.find((r) => r.set_id === sid) || {}).p2;
dash.calc('kpis', { title: 'Per-player counts by set', description: 'Burnouts, anti-airs, counter hits, punish counters and perfect parries per player, one row per set.', inputs: ['hits', 'events', 'sets'],
  fn: (allHits, allEv, sets) => sets.map((st) => { const hits = allHits.filter((h) => h.set_id === st.set_id), ev = allEv.filter((e) => e.set_id === st.set_id);
   const o = { set_id: st.set_id }; [ST.P1, st.p2].forEach((p, i) => { const k = i ? 'p2_' : 'p1_';
    o[k + 'burnouts'] = ev.filter((e) => e.player === p && e.type === 'burnout').length;
    o[k + 'perfect_parries'] = ev.filter((e) => e.player === p && e.type === 'perfect parry').length;
    o[k + 'anti_airs'] = hits.filter((h) => h.attacker === p && h.anti_air === true).length;
    o[k + 'counter_hits'] = hits.filter((h) => h.attacker === p && h.hit_kind === 'counter hit').length;
    o[k + 'punish_counters'] = hits.filter((h) => h.attacker === p && h.hit_kind === 'punish counter').length; }); return o; }) });
dash.calc('sit_pct', { title: 'Damage taken by situation (%)', description: 'Share of each player\'s damage taken, by situation, per set.', inputs: ['hits', 'sets'],
  fn: (allHits, sets) => sets.flatMap((st) => { const hits = allHits.filter((h) => h.set_id === st.set_id); const sits = ['neutral', 'pressure', 'oki', 'punish', 'defense'];
    const tot = (p) => d3.sum(hits.filter((h) => h.victim === p), (h) => +h.damage) || 1;
    return sits.map((s) => { const r = { set_id: st.set_id, label: s }; [ST.P1, st.p2].forEach((p, i) => { const hs = hits.filter((h) => h.victim === p && h.situation === s);
      r['v' + i] = d3.sum(hs, (h) => +h.damage) / tot(p); r['n' + i] = hs.length; }); return r; }).filter((r) => r.n0 + r.n1 > 0); }) });
dash.calc('lens_pct', { title: 'Where P1\'s damage taken came from (%)', description: 'Share of P1 damage taken by what P1 was doing, per set.', inputs: ['hits', 'sets'],
  fn: (allHits, sets) => sets.flatMap((st) => { const mine = allHits.filter((h) => h.set_id === st.set_id && h.victim === ST.P1); const tot = d3.sum(mine, (h) => +h.damage) || 1;
    return d3.rollups(mine, (v) => ({ v0: d3.sum(v, (h) => +h.damage) / tot, n0: v.length }), (h) => h.lens || 'Unclear / super')
      .map(([label, o]) => ({ set_id: st.set_id, label, ...o })).sort((a, b) => b.v0 - a.v0); }) });
dash.calc('kind_counts', { title: 'Hits landed by kind', description: 'Hits each attacker landed per hit kind, per set.', inputs: ['hits', 'sets'],
  fn: (allHits, sets) => sets.flatMap((st) => { const hits = allHits.filter((h) => h.set_id === st.set_id);
    return ['clean hit', 'counter hit', 'punish counter', 'throw', 'reversal'].map((k) => ({ set_id: st.set_id, kind: k,
      p1: hits.filter((h) => h.attacker === ST.P1 && h.hit_kind === k).length, p2: hits.filter((h) => h.attacker === st.p2 && h.hit_kind === k).length })); }) });
ST.pair = (f) => (el) => { const k = dash.data('kpis'); const r = k.status === 'ok' ? k.data.find(ST.inSet) : null; el.textContent = r ? `${r['p1_' + f]} / ${r['p2_' + f]}` : '—'; };

// ---- tables ----
ST.table = (name, id, opts = {}) => dash.draw(name, (tb) => {
  const d = dash.data(id); const table = tb.closest('table');
  const ths = table ? [...table.querySelectorAll('th')] : []; const key = table ? table.getAttribute('data-row-key') : null;
  tb.replaceChildren();
  if (d.status !== 'ok') { const tr = ST.el('tr'); const td = ST.el('td', null, d.status === 'error' ? 'Failed to load' : '—'); td.colSpan = ths.length || 1; tr.appendChild(td); tb.appendChild(tr); return; }
  let rows = d.data; if (opts.filter) rows = rows.filter(opts.filter);
  rows.forEach((r) => { const tr = ST.el('tr'); if (key) tr.setAttribute('data-key', encodeURIComponent(String(r[key])));
    ths.forEach((th) => { const f = th.getAttribute('data-field'); let v = r[f];
      if (v == null || v === '') v = '—'; else if (typeof v === 'number' && !/round|order|rank|game_no/.test(f)) v = ST.fmt(v);
      const td = ST.el('td', th.classList.contains('n') ? 'n' : null, String(v));
      if (f === 'winner') td.classList.add(r[f] === ST.P1 ? 'st-ok' : 'st-bad'); tr.appendChild(td); });
    tb.appendChild(tr); }); });
ST.table('t_punish', 'punish', { filter: ST.inSet });
ST.table('t_hits', 'hits', { filter: (r) => { const s = document.getElementById('hit-filter'); return ST.inSet(r) && (!s || !s.value || r.attacker === s.value); } });
document.querySelectorAll('#hit-filter').forEach((s) => s.addEventListener('change', () => dash.draw('t_hits')));

// ---- horizontal % bars: rows {label, v0, n0, [v1, n1]}; series = number of players shown ----
ST.hbars = (el, rows, series, names, aria) => {
  el.replaceChildren(); const W = el.clientWidth || 500, bh = 12, gap = 3, gh = series * (bh + gap) + 12;
  const svg = d3.select(el).append('svg').attr('width', '100%').attr('role', 'img').attr('aria-label', aria);
  const tip = d3.select(el).append('div').attr('class', 'st-tip').style('display', 'none');
  const lab = svg.append('g'); lab.selectAll('text').data(rows).join('text').attr('x', 0).text((r) => r.label);
  let lw = 0; lab.selectAll('text').each(function () { lw = Math.max(lw, this.getComputedTextLength()); });
  const narrow = W < 460, left = narrow ? 0 : lw + 10, top = narrow ? 16 : 0, rowH = gh + top;
  lab.selectAll('text').attr('y', (r, i) => i * rowH + (narrow ? 11 : bh));
  svg.attr('height', rows.length * rowH + 4);
  const x = d3.scaleLinear().domain([0, d3.max(rows, (r) => Math.max(r.v0 || 0, r.v1 || 0)) || 1]).range([0, Math.max(40, W - left - 80)]);
  rows.forEach((r, i) => { for (let s = 0; s < series; s++) { const y = i * rowH + top + s * (bh + gap), v = r['v' + s] || 0, n = r['n' + s] || 0;
    svg.append('rect').attr('x', left).attr('y', y).attr('height', bh).attr('rx', 2).attr('width', Math.max(2, x(v))).style('fill', ST.cols()[s])
      .on('pointermove', (ev) => { const [mx, my] = d3.pointer(ev, el); tip.style('display', null).text(`${r.label} · ${names[s]}: ${ST.pct(v)} (${n} hits)`);
        tip.style('left', Math.min(mx + 12, el.clientWidth - tip.node().offsetWidth - 4) + 'px').style('top', (my - 34) + 'px'); })
      .on('pointerleave', () => tip.style('display', 'none'));
    svg.append('text').attr('class', 'st-val').attr('x', left + Math.max(2, x(v)) + 6).attr('y', y + bh - 2).text(`${ST.pct(v)} (${n})`); } });
};
dash.draw('c_sit', (el) => { const d = dash.data('sit_pct'); if (ST.empty(el, d)) return; ST.hbars(el, d.data.filter(ST.inSet), 2, [ST.P1 + ' took', ST.p2() + ' took'], 'Share of damage taken by situation'); });
dash.draw('c_lens', (el) => { const d = dash.data('lens_pct'); if (ST.empty(el, d)) return; ST.hbars(el, d.data.filter(ST.inSet), 1, [ST.P1 + ' took'], 'Share of damage taken by what ' + ST.P1 + ' was doing'); });

// ---- grouped vertical bars (hits by kind) ----
ST.bars = (el, rows, cat, fields, labels, aria) => {
  el.replaceChildren(); const W = el.clientWidth || 600, H = 220, m = { t: 18, r: 8, b: 26, l: 36 };
  const svg = d3.select(el).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', aria);
  const x0 = d3.scaleBand().domain(rows.map((r) => r[cat])).range([m.l, W - m.r]).padding(0.25);
  const x1 = d3.scaleBand().domain(fields).range([0, x0.bandwidth()]).padding(0.08);
  const y = d3.scaleLinear().domain([0, d3.max(rows, (r) => d3.max(fields, (f) => +r[f])) || 1]).nice().range([H - m.b, m.t]);
  svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4).tickFormat(d3.format('d'))).call((g) => g.select('.domain').remove()).call((g) => g.selectAll('line').attr('stroke', 'var(--cds-chart-grid)'));
  svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x0).tickSizeOuter(0)).call((g) => g.selectAll('line,path').attr('stroke', 'var(--cds-chart-axis)'));
  const tip = d3.select(el).append('div').attr('class', 'st-tip').style('display', 'none');
  const g = svg.append('g').selectAll('g').data(rows).join('g').attr('transform', (r) => `translate(${x0(r[cat])},0)`);
  g.selectAll('rect').data((r) => fields.map((f, i) => ({ r, f, i, v: +r[f] }))).join('rect')
    .attr('x', (d) => x1(d.f)).attr('width', x1.bandwidth()).attr('y', (d) => y(d.v)).attr('height', (d) => y(0) - y(d.v)).style('fill', (d) => ST.cols()[d.i]).attr('rx', 2)
    .on('pointermove', (ev, d) => { const [px, py] = d3.pointer(ev, el); tip.style('display', null).style('left', Math.min(px + 10, W - 160) + 'px').style('top', (py - 30) + 'px').text(`${d.r[cat]} · ${labels[d.i]}: ${d.v}`); })
    .on('pointerleave', () => tip.style('display', 'none'));
  g.selectAll('text.st-val').data((r) => fields.map((f) => ({ f, v: +r[f] }))).join('text').attr('class', 'st-val')
    .attr('x', (d) => x1(d.f) + x1.bandwidth() / 2).attr('y', (d) => y(d.v) - 4).attr('text-anchor', 'middle').text((d) => d.v);
};
dash.draw('c_kinds', (el) => { const d = dash.data('kind_counts'); if (ST.empty(el, d)) return; ST.bars(el, d.data.filter(ST.inSet), 'kind', ['p1', 'p2'], [ST.P1, ST.p2()], 'Hits landed by kind'); });

// ---- cards ----
ST.cards = (name, id, build, filter) => dash.draw(name, (el) => { const d = dash.data(id); if (ST.empty(el, d)) return; d.data.filter((r) => ST.inSet(r) && (!filter || filter(r))).forEach((r) => el.appendChild(build(r))); });
ST.cards('arche', 'archetypes', (r) => { const c = ST.el('div', 'st-card'); c.appendChild(ST.el('h3', null, `${r.player} · ${r.character}`));
  [['Archetype', `${r.archetype} (${r.lean}), confidence ${r.confidence}`], ['Risk tolerance', r.doc_risk_tolerance], ['Temperament', r.doc_temperament], ['Evidence', r.evidence], ['How to beat this', r.counter_note]].forEach(([k, v]) => c.appendChild(ST.kv(k, v))); return c; });
ST.habits = (player) => (el) => { const d = dash.data('habits'); if (ST.empty(el, d)) return;
  d.data.filter((r) => ST.inSet(r) && r.player === (typeof player === 'function' ? player() : player)).forEach((r) => { const it = ST.el('div', 'st-item'); const h = ST.el('div', 'st-head');
    h.append(ST.el('span', 'st-tag' + (r.kind === 'Strength' ? ' good' : r.kind === 'Leak' ? ' bad' : ''), `${r.kind} · ${r.area}`), document.createTextNode(r.habit));
    it.append(h, ST.el('p', null, 'Seen: ' + r.seen + (r.times ? ` (${r.times}×)` : '')), ST.el('div', 'st-try', r.fix), ST.el('div', 'st-muted', `Source: ${r.origin} · confidence ${r.confidence}`)); el.append(it); }); };
dash.draw('habits_p1', ST.habits(ST.P1)); dash.draw('habits_p2', ST.habits(() => ST.p2()));
ST.cards('fixes', 'fixes', (r) => { const c = ST.el('div', 'st-card'); c.append(ST.el('div', 'st-label', `#${r.rank} · ${r.player}`), ST.el('h3', null, r.fix), ST.el('div', 'st-try', 'Drill: ' + r.drill), ST.kv('Why', r.why)); return c; });
dash.draw('training', (el) => { const d = dash.data('training'); if (ST.empty(el, d)) return; const c = ST.el('div', 'st-card');
  d.data.filter(ST.inSet).forEach((r) => { const it = ST.el('div', 'st-item'); it.append(ST.el('div', 'st-head', `${r.block} · ${r.minutes} min · ${r.focus}`), ST.el('p', null, r.drills)); c.append(it); }); el.append(c); });
ST.cards('findings', 'findings', (r) => { const c = ST.el('div', 'st-card'); c.append(ST.el('div', 'st-label', [r.skill, r.category, r.applies_to, r.confidence].join(' · ')), ST.el('p', null, r.finding), ST.kv('Evidence', r.evidence)); return c; });

// ---- Story of the Set ----
ST.CATS = ['Neutral', 'Offense', 'Defense', 'Player reads / profile'];
ST.storyItem = (r) => { const it = ST.el('div', 'st-item' + (r.confidence === 'High' ? ' st-hi' : '')); const h = ST.el('div', 'st-head');
  if (r.change) h.append(ST.el('span', 'st-tag' + (r.change === 'Improved' ? ' good' : r.change === 'Regressed' ? ' bad' : ''), r.change));
  if (r.polarity !== 'Change') h.append(ST.el('span', 'st-tag' + (r.polarity === 'Worked well' ? ' good' : ' bad'), r.polarity));
  if (r.confidence === 'High') h.append(ST.el('span', 'st-tag', 'High'));
  h.append(document.createTextNode(r.headline)); it.append(h, ST.el('p', null, r.detail), ST.el('div', 'st-muted', `${r.evidence} · ${r.skills}`));
  if (r.try_this) it.append(ST.el('div', 'st-try', 'Try this: ' + r.try_this)); return it; };
ST.storyBody = (card, items) => { ST.CATS.forEach((cat) => { const xs = items.filter((r) => r.category === cat && r.confidence !== 'Low').sort((a, b) => a.rank - b.rank);
    if (!xs.length) return; card.append(ST.el('h4', null, cat)); xs.forEach((r) => card.append(ST.storyItem(r))); });
  const low = items.filter((r) => r.confidence === 'Low'); if (low.length) { const det = ST.el('details'); det.append(ST.el('summary', null, `Low-confidence notes (${low.length})`)); low.forEach((r) => det.append(ST.storyItem(r))); card.append(det); } };
dash.draw('story', (el) => { const s = dash.data('story'), sets = dash.data('sets'), games = dash.data('story_games');
  if (ST.empty(el, s) || sets.status !== 'ok' || games.status !== 'ok') return;
  [...sets.data].filter(ST.inSet).forEach((st) => { const wrap = ST.el('div', 'st-story'); const ov = ST.el('div', 'st-card');
    const mine = s.data.filter((r) => r.set_id === st.set_id), setRows = mine.filter((r) => r.scope === 'set');
    const hd = ST.el('h3', null, `${st.set_id} · ${st.format} · `); hd.append(ST.el('span', st.winner === ST.P1 ? 'st-ok' : 'st-bad', `${st.winner} wins ${Math.max(st.p1_games, st.p2_games)}-${Math.min(st.p1_games, st.p2_games)}`)); ov.append(hd);
    ov.append(ST.kv('Set score by game', st.progression + (st.max_deficit_overcome ? ` · came back ${st.max_deficit_overcome}` : '')));
    const two = ST.el('div', 'st-two'); [['Top 3 highs', 'Worked well'], ['Top 3 lows', 'To improve']].forEach(([t, pol]) => { const col = ST.el('div'); col.append(ST.el('h4', null, t));
      setRows.filter((r) => r.polarity === pol && r.confidence !== 'Low').sort((a, b) => (a.confidence === 'High' ? 0 : 1) - (b.confidence === 'High' ? 0 : 1) || a.rank - b.rank).slice(0, 3).forEach((r) => col.append(ST.storyItem(r))); two.append(col); });
    ov.append(two); const top = new Set(); ['Worked well', 'To improve'].forEach((pol) => setRows.filter((r) => r.polarity === pol && r.confidence !== 'Low').sort((a, b) => (a.confidence === 'High' ? 0 : 1) - (b.confidence === 'High' ? 0 : 1) || a.rank - b.rank).slice(0, 3).forEach((r) => top.add(r.story_id)));
    ST.storyBody(ov, setRows.filter((r) => !top.has(r.story_id))); wrap.append(ov);
    games.data.filter((g) => g.set_id === st.set_id).sort((a, b) => a.game_no - b.game_no).forEach((g) => { const c = ST.el('div', 'st-card');
      c.append(ST.el('h3', null, `Game ${g.game_no} · ${g.game_id} · ${g.result} · set ${g.set_score_after}`), ST.el('p', null, g.summary), ST.kv('Turning point', g.turning_point));
      ST.storyBody(c, mine.filter((r) => r.scope === g.game_id)); wrap.append(c); });
    el.append(wrap); }); });
