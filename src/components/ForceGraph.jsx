/**
 * 命途星图 — d3-force 力导向图
 * - 节点按实体类型着色（色板从设计 token 派生的低饱和大地色，无高饱和新色）
 * - 边按谓词分组：RELATED_TO 虚线 + 低透明度，与确定关系区分
 * - 常驻等宽图例（类型 + 谓词线型）
 * - 点击节点：右侧侧栏，衬线实体名 + 等宽键值属性 + 引证角标
 * - 孤立节点（无连接）单独陈列，不参与主图斥力
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import CitationBadge from './CitationBadge.jsx';

const TYPE_COLORS = {
  AEON: '#cf7c59',
  PATH: '#cfa859',
  CHAR: '#cab791',
  ORGN: '#709ba9',
  PLAC: '#85ada0',
  WRLD: '#76b294',
  CONC: '#c1aa8b',
  ARTF: '#a98e60',
  RACE: '#b6887c',
};
const TYPE_LABELS = {
  AEON: '星神', PATH: '命途', CHAR: '角色', ORGN: '组织',
  PLAC: '地点', WRLD: '世界', CONC: '概念', ARTF: '遗器', RACE: '种族',
};

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
    return {
      nodes: DEMO_NODES.map((n) => ({ ...n })),
      links: DEMO_LINKS.map((l) => ({ ...l })),
      isolated: [],
      isDemo: true,
      predicates: [...new Set(DEMO_LINKS.map((l) => l.predicate))],
      types: [...new Set(DEMO_NODES.map((n) => n.type))],
    };
  }
  const map = new Map();
  entities.forEach((e) => {
    map.set(e.id || e.entity_id, { ...e, _degree: 0, _rels: [] });
  });
  const ids = new Set(map.keys());
  const links = [];
  const connected = new Set();
  const predSet = new Set();
  (relations || []).slice(0, 500).forEach((r) => {
    const s = r.subject_id || r.subject_name || '';
    const o = r.object_id || r.object_name || '';
    if (ids.has(s) && ids.has(o)) {
      const link = {
        source: s, target: o,
        subject: s, object: o,
        predicate: r.predicate || 'RELATED_TO',
        citation: r.citations?.[0] || null,
        confidence: r.confidence,
      };
      links.push(link);
      connected.add(s); connected.add(o);
      predSet.add(r.predicate || 'RELATED_TO');
      const sn = map.get(s); if (sn) { sn._degree += 1; sn._rels.push({ dir: '→', other: o, link }); }
      const tn = map.get(o); if (tn) { tn._degree += 1; tn._rels.push({ dir: '←', other: s, link }); }
    }
  });
  const nodes = [];
  const isolated = [];
  map.forEach((n) => {
    if (connected.has(n.id)) nodes.push(n);
    else isolated.push(n);
  });
  return {
    nodes, links, isolated, isDemo: false,
    predicates: [...predSet],
    types: [...new Set(entities.map((e) => e.type).filter(Boolean))],
  };
}

export default function ForceGraph({ entities = [], relations = [] }) {
  const svgRef = useRef(null);
  const wrapRef = useRef(null);
  const [sel, setSel] = useState(null);
  const renderId = useRef(0);
  const gd = useMemo(() => prepData(entities, relations), [entities, relations]);

  useEffect(() => {
    renderId.current += 1;
    const rid = renderId.current;
    const svgEl = svgRef.current;
    const wrapEl = wrapRef.current;
    if (!svgEl || !wrapEl) return;
    const W = Math.max(wrapEl.clientWidth, 400);
    const H = Math.max(wrapEl.clientHeight - 8, 300);
    let simLocal;
    let cancelled = false;
    import('d3').then((d3) => {
      if (renderId.current !== rid || cancelled) return;
      const svg = d3.select(svgEl);
      svg.selectAll('*').remove();
      svg.attr('viewBox', [0, 0, W, H]);
      const g = svg.append('g');
      const zoom = d3.zoom().scaleExtent([0.3, 4]).on('zoom', (ev) => g.attr('transform', ev.transform));
      svg.call(zoom);
      if (gd.nodes.length === 0) {
        g.append('text').attr('x', W / 2).attr('y', H / 2).attr('text-anchor', 'middle')
          .attr('fill', 'var(--text-muted)').attr('font-size', 13)
          .attr('font-family', 'var(--font-mono)').text('暂无连通节点');
        return;
      }
      const sim = d3.forceSimulation(gd.nodes)
        .force('link', d3.forceLink(gd.links).id((d) => d.id).distance(90))
        .force('charge', d3.forceManyBody().strength(-220))
        .force('center', d3.forceCenter(W / 2, H / 2))
        .force('collision', d3.forceCollide(22));
      simLocal = sim;

      const link = g.append('g').selectAll('line').data(gd.links).join('line')
        .attr('stroke', 'var(--border-light)')
        .attr('stroke-width', 1)
        .attr('stroke-opacity', (d) => (d.predicate === 'RELATED_TO' ? 0.35 : 0.7))
        .attr('stroke-dasharray', (d) => (d.predicate === 'RELATED_TO' ? '3 3' : 'none'));

      const node = g.append('g').selectAll('g').data(gd.nodes).join('g')
        .style('cursor', 'pointer')
        .call(d3.drag()
          .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
          .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
          .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }))
        .on('click', (e, d) => { e.stopPropagation(); setSel(d); });

      node.append('circle')
        .attr('r', (d) => Math.max(5, Math.min(16, (d._degree || 1) * 1.5 + 4)))
        .attr('fill', (d) => TYPE_COLORS[d.type] || 'var(--text-muted)')
        .attr('stroke', 'var(--bg-surface)')
        .attr('stroke-width', 1.5);
      node.append('title').text((d) => (d.canonical_name || d.id) + ' · ' + (TYPE_LABELS[d.type] || d.type));
      node.append('text').text((d) => (d.canonical_name || d.id).slice(0, 6))
        .attr('dy', (d) => -(Math.max(5, Math.min(16, (d._degree || 1) * 1.5 + 4)) + 10))
        .attr('text-anchor', 'middle')
        .attr('fill', 'var(--text-secondary)')
        .attr('font-size', 10)
        .attr('font-family', 'var(--font-sans)')
        .attr('pointer-events', 'none');

      svg.on('click', () => setSel(null));
      sim.on('tick', () => {
        link.attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y)
            .attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y);
        node.attr('transform', (d) => 'translate(' + d.x + ',' + d.y + ')');
      });
    }).catch((err) => console.warn('ForceGraph d3:', err));
    return () => { cancelled = true; if (simLocal) simLocal.stop(); };
  }, [gd.nodes.length, gd.links.length]);

  return (
    <div className="graph">
      <div className="graph-body">
        <div className="graph-canvas-wrap" ref={wrapRef}>
          <svg ref={svgRef} width="100%" height="100%" className="graph-svg" />
        </div>

        {/* 常驻等宽图例 */}
        <aside className="graph-legend">
        <div className="graph-legend-h">图例</div>
        <div className="graph-legend-group">
          <div className="graph-legend-sub">实体类型</div>
          {gd.types.map((t) => (
            <div key={t} className="graph-legend-row">
              <span className="graph-swatch" style={{ background: TYPE_COLORS[t] || 'var(--text-muted)' }} />
              <span className="graph-legend-name">{TYPE_LABELS[t] || t}</span>
              <span className="graph-legend-code">{t}</span>
            </div>
          ))}
        </div>
        <div className="graph-legend-group">
          <div className="graph-legend-sub">关系</div>
          <div className="graph-legend-row">
            <span className="graph-line graph-line-solid" />
            <span className="graph-legend-name">确定关系</span>
          </div>
          <div className="graph-legend-row">
            <span className="graph-line graph-line-dashed" />
            <span className="graph-legend-name">RELATED_TO</span>
          </div>
        </div>
        <div className="graph-legend-count">
          {gd.nodes.length} 节点 · {gd.links.length} 边{gd.isDemo ? ' · 演示' : ''}
        </div>
      </aside>
      </div>

      {/* 节点侧栏 */}
      {sel && (
        <aside className="graph-detail" role="complementary" aria-label="实体详情">
          <div className="graph-detail-head">
            <div>
              <span className="graph-detail-type" style={{ color: TYPE_COLORS[sel.type] }}>
                {TYPE_LABELS[sel.type] || sel.type}
              </span>
              <h3 className="graph-detail-name">{sel.canonical_name || sel.id}</h3>
            </div>
            <button className="graph-detail-close" onClick={() => setSel(null)} aria-label="关闭">×</button>
          </div>

          {sel.summary_short && (
            <p className="graph-detail-summary">{sel.summary_short}</p>
          )}

          <dl className="graph-detail-attrs">
            <div className="gda-row">
              <dt>id</dt>
              <dd className="mono">{sel.id}</dd>
            </div>
            <div className="gda-row">
              <dt>type</dt>
              <dd className="mono">{sel.type}</dd>
            </div>
            <div className="gda-row">
              <dt>degree</dt>
              <dd className="mono">{sel._degree || 0}</dd>
            </div>
          </dl>

          {sel._rels && sel._rels.length > 0 && (
            <div className="graph-detail-rels">
              <div className="graph-detail-sub">关系</div>
              <ul className="graph-rel-list">
                {sel._rels.slice(0, 12).map((r, i) => (
                  <li key={i} className="graph-rel-row">
                    <span className="mono graph-rel-pred">{r.dir} {r.link.predicate}</span>
                    <span className="graph-rel-other">{r.other}</span>
                    {r.link.citation && (
                      <CitationBadge
                        citations={[r.link.citation]}
                        claimText={`${r.link.subject} ${r.link.predicate} ${r.link.object}`}
                        sourceVolume=""
                      />
                    )}
                  </li>
                ))}
                {sel._rels.length > 12 && (
                  <li className="graph-rel-more mono">+{sel._rels.length - 12} 条更多关系</li>
                )}
              </ul>
            </div>
          )}
        </aside>
      )}

      {/* 孤立节点陈列区 */}
      {gd.isolated.length > 0 && (
        <div className="graph-isolated">
          <span className="graph-isolated-label mono">
            孤立节点 · {gd.isolated.length}
          </span>
          <div className="graph-isolated-list">
            {gd.isolated.slice(0, 30).map((n) => (
              <button
                key={n.id}
                className="graph-iso-chip"
                onClick={() => setSel(n)}
                title={n.summary_short || n.id}
              >
                <span className="graph-swatch" style={{ background: TYPE_COLORS[n.type] || 'var(--text-muted)' }} />
                {n.canonical_name || n.id}
              </button>
            ))}
            {gd.isolated.length > 30 && (
              <span className="graph-isolated-more mono">+{gd.isolated.length - 30}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
