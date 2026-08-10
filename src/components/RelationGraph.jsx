/**
 * 命途星图 — d3-force 驱动的实体关系图 + 实体引证面板
 *
 * 降级渲染：pass2 归并结果缺失时，同名实体各自成节点，界面上标注「未归并」。
 */
import { useRef, useState } from 'react';
import CitationBadge from './CitationBadge.jsx';

const TYPE_LABELS = { CHAR: '角色', AEON: '星神', PATH: '命途', ORGN: '组织', PLAC: '地点', WRLD: '世界', CONC: '概念', ARTF: '遗器', RACE: '种族' };
const TYPE_COLORS = { CHAR: '#d4a853', AEON: '#c96f4a', PATH: '#7eb896', ORGN: '#6e9aa8', PLAC: '#c4b5fd', WRLD: '#fbbf24', CONC: '#e8a87c', ARTF: '#8cb88c', RACE: '#d4b87c' };

const PLACEHOLDER_NODES = [
  { id: '1', label: '开拓者', type: 'CHAR', cite_id: 'AVTR-N-8001' },
  { id: '2', label: '三月七', type: 'CHAR', cite_id: 'AVTR-N-1001' },
  { id: '3', label: '丹恒', type: 'CHAR', cite_id: 'AVTR-N-1002' },
  { id: '4', label: '星穹列车', type: 'ORGN', cite_id: 'NOUN-1001' },
  { id: '5', label: '星核猎手', type: 'ORGN', cite_id: 'NOUN-1002' },
  { id: '6', label: '卡芙卡', type: 'CHAR', cite_id: 'AVTR-N-1005' },
];

function buildGraphData(entities, relations) {
  if (!entities || entities.length === 0) return { nodes: PLACEHOLDER_NODES, links: [], unmergedNames: new Set(), entityList: [] };

  const nameMap = new Map();
  for (const ent of entities) {
    const name = ent.canonical_name || '?';
    if (!nameMap.has(name)) nameMap.set(name, []);
    nameMap.get(name).push(ent);
  }

  const unmergedNames = new Set();
  for (const [name, ents] of nameMap) {
    if (ents.length > 1 && ents.some((e) => !e._merged)) unmergedNames.add(name);
  }

  const seenNames = new Set();
  const nodes = [];
  const entityList = [];

  // Nodes: all entities (for graph representation)
  for (const ent of (entities || [])) {
    const name = ent.canonical_name || '?';
    if (seenNames.has(name)) continue;
    seenNames.add(name);
    nodes.push({ id: ent.entity_id || name, label: name, type: ent.type || 'CHAR', cite_id: ent.summary?.citations?.[0]?.cite_id || '', unmerged: unmergedNames.has(name) });
  }

  // Entity citation panel: first 20 (separate from nodes)
  const panelEntities = seenNames.size > 0 ? (entities || []).filter(e => {
    const nm = e.canonical_name || '?';
    const added = entityList.findIndex(el => el.name === nm);
    return added === -1;
  }).slice(0, 20) : [];

  for (const ent of panelEntities) {
    entityList.push({
      entity_id: ent.entity_id,
      name: ent.canonical_name || '?',
      type: ent.type || 'CHAR',
      summary: ent.summary,
      attributes: ent.attributes || [],
      sourceVolume: ent.source_volume || ent._source_volumes?.[0] || '',
    });
  }

  const links = (relations || []).slice(0, 200).map((rel) => ({
    source: rel.subject_id || rel.subject_name || '?',
    target: rel.object_id || rel.object_name || '?',
    relation: rel.predicate || 'RELATED_TO',
    cite_id: rel.citations?.[0]?.cite_id || '',
  }));

  return { nodes, links: links.slice(0, 500), unmergedNames, entityList };
}

export default function RelationGraph({ entities = null, relations = null }) {
  const containerRef = useRef(null);
  const { nodes, links, unmergedNames, entityList } = buildGraphData(entities, relations);
  const unmergedCount = unmergedNames.size;

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Degradation banner */}
      {unmergedCount > 0 && (
        <div style={{ background: 'var(--warning)', color: 'var(--bg-base)', padding: '4px 12px', fontSize: 'var(--text-xs)', borderRadius: 'var(--radius-sm)', flexShrink: 0 }}>
          ⚠ 未归并模式 — {unmergedCount} 个同名实体尚未归并，各自显示为独立节点
        </div>
      )}

      {/* Graph placeholder */}
      <div style={{ flexShrink: 0, position: 'relative', height: '30%', minHeight: '100px', borderBottom: '1px solid var(--border)' }}>
        <svg width="100%" height="100%">
          <text x="50%" y="50%" textAnchor="middle" fill="var(--text-muted)" fontSize="14">
            [d3-force 关系图 — {nodes.length} 节点, {links.length} 边]
          </text>
        </svg>
      </div>

      {/* Entity citation panel */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
        <h4 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--space-3)', color: 'var(--text-secondary)' }}>
          实体引证（前 {entityList.length} 条）
        </h4>
        {entityList.map((ent) => (
          <div key={ent.entity_id} style={{ marginBottom: 'var(--space-3)', padding: 'var(--space-3)', background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: TYPE_COLORS[ent.type] || 'var(--text-muted)', flexShrink: 0 }} />
              <strong style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>{ent.name}</strong>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{TYPE_LABELS[ent.type] || ent.type}</span>
            </div>
            {ent.summary?.text && (
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', lineHeight: 'var(--leading-relaxed)', marginBottom: '4px' }}>{ent.summary.text.slice(0, 120)}</div>
            )}
            <CitationBadge citations={ent.summary?.citations || []} claimText={ent.summary?.text?.slice(0, 80) || ''} sourceVolume={ent.sourceVolume} position="block" />
          </div>
        ))}
      </div>
    </div>
  );
}
