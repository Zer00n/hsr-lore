/**
 * 命途星图 — d3-force 真实力导向图 + 演示模式
 */
import { useEffect, useRef, useState } from 'react';

const TYPE_COLORS = { AEON: '#c96f4a', PATH: '#7eb896', CHAR: '#d4a853', ORGN: '#6e9aa8', PLAC: '#c4b5fd', WRLD: '#fbbf24', CONC: '#e8a87c', ARTF: '#8cb88c', RACE: '#d4b87c' };
const TYPE_LABELS = { AEON: '星神', PATH: '命途', CHAR: '角色', ORGN: '组织', PLAC: '地点', WRLD: '世界', CONC: '概念', ARTF: '遗器', RACE: '种族' };
const PREDICATE_COLORS = { EMBODIES: '#e8a87c', EMISSARY_OF: '#d4a853', FOLLOWER_OF: '#d4a853', OPPOSES: '#c96f4a', MEMBER_OF: '#6e9aa8', LEADS: '#6e9aa8', ALLY_OF: '#7eb896', ENEMY_OF: '#c96f4a', LOCATED_IN: '#c4b5fd', RELATED_TO: '#8c8878' };

const DEMO_NODES = [
  { id: '1', canonical_name: '克里珀', type: 'AEON', _degree: 12 },
  { id: '2', canonical_name: '纳努克', type: 'AEON', _degree: 8 },
  { id: '3', canonical_name: '存护', type: 'PATH', _degree: 10 },
  { id: '4', canonical_name: '开拓', type: 'PATH', _degree: 6 },
  { id: '5', canonical_name: '三月七', type: 'CHAR', _degree: 5 },
  { id: '6', canonical_name: '丹恒', type: 'CHAR', _degree: 4 },
  { id: '7', canonical_name: '星穹列车', type: 'ORGN', _degree: 7 },
];
const DEMO_LINKS = [
  { source: '5', target: '7', predicate: 'MEMBER_OF' },
  { source: '6', target: '7', predicate: 'MEMBER_OF' },
  { source: '1', target: '3', predicate: 'EMBODIES' },
  { source: '2', target: '7', predicate: 'OPPOSES' },
  { source: '5', target: '6', predicate: 'ALLY_OF' },
  { source: '1', target: '2', predicate: 'OPPOSES' },
];

function prepData(entities, relations) {
  if (!entities || entities.length === 0) {
    return { nodes: DEMO_NODES, links: DEMO_LINKS, isDemo: true, predicates: [...new Set(DEMO_LINKS.map((l) => l.predicate))] };
  }
  const map = new Map();
  entities.forEach((e) => {
    map.set(e.id || e.entity_id, { ...e, _degree: 0 });
  });
  const ids = new Set(map.keys());
  const links = [];
  const connected = new Set();
  const predSet = new Set();
  (relations || []).slice(0, 500).forEach((r) => {
    const s = r.subject_id || r.subject_name || '';
    const o = r.object_id || r.object_name || '';
    if (ids.has(s) && ids.has(o)) {
      links.push({ source: s, target: o, predicate: r.predicate || 'RELATED_TO' });
      connected.add(s); connected.add(o);
      predSet.add(r.predicate || 'RELATED_TO');
      const sn = map.get(s); if (sn) sn._degree += 1;
      const tn = map.get(o); if (tn) tn._degree += 1;
    }
  });
  const nodes = [];
  map.forEach((n) => { if (connected.has(n.id)) nodes.push(n); });
  return { nodes, links, isDemo: false, predicates: [...predSet] };
}

export default function ForceGraph({ entities = [], relations = [] }) {
  const svgRef = useRef(null);
  const wrapRef = useRef(null);
  const [sel, setSel] = useState(null);
  const renderId = useRef(0);
  const gd = prepData(entities, relations);

  useEffect(() => {
    renderId.current += 1;
    const rid = renderId.current;
    const svgEl = svgRef.current;
    const wrapEl = wrapRef.current;
    if (!svgEl || !wrapEl) return;
    const W = Math.max(wrapEl.clientWidth, 400);
    const H = Math.max(wrapEl.clientHeight - 40, 300);
    let simLocal;
    import('d3').then((d3) => {
      if (renderId.current !== rid) return;
      const svg = d3.select(svgEl);
      svg.selectAll('*').remove();
      svg.attr('viewBox', [0, 0, W, H]);
      const g = svg.append('g');
      svg.call(d3.zoom().scaleExtent([0.3, 4]).on('zoom', (ev) => g.attr('transform', ev.transform)));
      if (gd.nodes.length === 0) {
        g.append('text').attr('x', W / 2).attr('y', H / 2).attr('text-anchor', 'middle').attr('fill', 'var(--text-muted)').attr('font-size', 14).text('无数据');
        return;
      }
      const sim = d3.forceSimulation(gd.nodes)
        .force('link', d3.forceLink(gd.links).id((d) => d.id).distance(80))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(W / 2, H / 2))
        .force('collision', d3.forceCollide(20));
      simLocal = sim;
      const link = g.append('g').selectAll('line').data(gd.links).join('line')
        .attr('stroke', (d) => PREDICATE_COLORS[d.predicate] || '#8c8878').attr('stroke-opacity', 0.5).attr('stroke-width', 1.2);
      const node = g.append('g').selectAll('g').data(gd.nodes).join('g')
        .call(d3.drag()
          .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
          .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
          .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }))
        .on('click', (e, d) => { e.stopPropagation(); setSel(d); });
      node.append('circle').attr('r', (d) => Math.max(5, Math.min(18, (d._degree || 1) * 2 + 4)))
        .attr('fill', (d) => TYPE_COLORS[d.type] || 'var(--text-muted)').attr('stroke', 'var(--bg-base)').attr('stroke-width', 2);
      node.append('title').text((d) => (d.canonical_name || d.id) + '\n' + (TYPE_LABELS[d.type] || d.type));
      node.append('text').text((d) => (d.canonical_name || d.id).slice(0, 6)).attr('dy', '0.35em').attr('text-anchor', 'middle').attr('fill', 'var(--text-primary)').attr('font-size', 8).attr('pointer-events', 'none');
      svg.on('click', () => setSel(null));
      sim.on('tick', () => { link.attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y).attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y); node.attr('transform', (d) => 'translate(' + d.x + ',' + d.y + ')'); });
    }).catch((err) => console.warn('ForceGraph d3:', err));
    return () => { if (simLocal) simLocal.stop(); };
  }, [gd.nodes.length, gd.links.length]);

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '6px var(--space-3)', borderBottom: '1px solid var(--border)', display: 'flex', gap: '6px', alignItems: 'center', flexShrink: 0, fontSize: 'var(--text-xs)' }}>
        {gd.isDemo && <span style={{ color: 'var(--text-muted)' }}>（数据加载中，若持续显示请检查 data/ 目录）</span>}
        <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>{gd.nodes.length} 节点 · {gd.links.length} 边</span>
      </div>
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div ref={wrapRef} style={{ flex: 1, position: 'relative' }}>
          <svg ref={svgRef} width="100%" height="100%" style={{ display: 'block' }} />
          {sel && (
            <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, maxHeight: '35%', background: 'var(--bg-elevated)', borderTop: '1px solid var(--accent)', padding: 'var(--space-4)', overflowY: 'auto', zIndex: 10, fontSize: 'var(--text-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <strong>{sel.canonical_name || sel.id}</strong>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)' }}>{TYPE_LABELS[sel.type] || sel.type}</span>
              </div>
              {sel.summary?.text && <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: '4px 0' }}>{sel.summary.text.slice(0, 150)}</p>}
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>连接数：{sel._degree || 0}</div>
              <button onClick={() => setSel(null)} style={{ position: 'absolute', top: '8px', right: '12px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '14px' }}>✕</button>
            </div>
          )}
        </div>
        {gd.predicates.length > 0 && (
          <div style={{ width: '100px', padding: 'var(--space-2)', borderLeft: '1px solid var(--border)', fontSize: '10px', flexShrink: 0, overflowY: 'auto' }}>
            <div style={{ fontWeight: 600, marginBottom: '4px', color: 'var(--text-muted)' }}>谓词</div>
            {gd.predicates.map((p) => (<div key={p} style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '2px' }}><span style={{ width: 10, height: 3, background: PREDICATE_COLORS[p] || '#8c8878', display: 'inline-block' }} />{p}</div>))}
          </div>
        )}
      </div>
    </div>
  );
}
