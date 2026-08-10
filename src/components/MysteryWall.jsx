/**
 * 未解之谜墙 — 数据源为 discrepancies.json 中 kind === 'gap' 的条目
 * 面向普通玩家，文案口语化，不出现术语「gap」
 */
import { useState } from 'react';
import CitationBadge from './CitationBadge.jsx';

const KIND_LABELS_CN = { gap: '官方留白', contradiction: '说法矛盾', ambiguity: '表述含混', retcon: '设定调整' };

export default function MysteryWall({ discrepancies = [], confidenceFilter = { attested: true, inferred: true, disputed: true } }) {
  const [expandedId, setExpandedId] = useState(null);

  const gaps = (discrepancies || []).filter((d) => d.kind === 'gap');
  if (gaps.length === 0) {
    return (
      <div className="mystery-empty">
        <div className="mystery-empty-icon" aria-hidden="true">🔍</div>
        <p className="mystery-empty-title">暂无未解之谜</p>
        <p className="mystery-empty-desc">Pass1 四卷数据中未检测到 gap 类矛盾条目。pass2 跨卷分析运行后可能会出现新的未解之谜。</p>
      </div>
    );
  }

  return (
    <div className="mystery-wall" style={{ height: '100%', overflowY: 'auto', padding: 'var(--space-5)' }}>
      <div className="mystery-header">
        <h2 className="mystery-title">未解之谜墙</h2>
        <p className="mystery-subtitle">以下条目是游戏中提到但尚未完全展开的世界观线索——不是遗漏，而是叙事留白。</p>
      </div>

      <div className="mystery-grid">
        {gaps.map((d) => {
          const expanded = expandedId === d.discrepancy_id;
          const statements = d.statements || [];
          const primary = statements[0] || {};

          return (
            <div key={d.discrepancy_id} className={`mystery-card ${expanded ? 'is-expanded' : ''}`}>
              <div className="mystery-card-header" onClick={() => setExpandedId(expanded ? null : d.discrepancy_id)} style={{ cursor: 'pointer' }}>
                <div className="mystery-card-topic">
                  <span className="mystery-card-icon" aria-hidden="true">?</span>
                  <span>{d.topic}</span>
                </div>
                <span className="mystery-card-impact" style={{ color: d.impact === 'high' ? 'var(--danger)' : d.impact === 'medium' ? 'var(--warning)' : 'var(--info)' }}>
                  {d.impact === 'high' ? '核心谜题' : d.impact === 'medium' ? '值得关注' : '细节补充'}
                </span>
              </div>

              {primary.citation && (
                <div className="mystery-card-source">
                  <span className="mystery-source-label">出处：</span>
                  <span className="mystery-source-id">{primary.citation.cite_id}</span>
                  {primary.citation.quote && (
                    <span className="mystery-source-quote">「{primary.citation.quote.slice(0, 150)}」</span>
                  )}
                </div>
              )}

              {/* 展开后的详细内容 */}
              {expanded && (
                <div className="mystery-card-body">
                  {/* 为什么这是留白 */}
                  <div className="mystery-why-section">
                    <h4>为什么这不是遗漏</h4>
                    <p>
                      {d.analysis?.text
                        ? d.analysis.text
                        : `游戏文本仅给出了${d.topic}的有限线索，没有在这个点上展开完整解释——这通常是有意为之的叙事策略，为未来的剧情发展预留空间。`}
                    </p>
                    {d.analysis?.citations && d.analysis.citations.length > 0 && (
                      <CitationBadge
                        citations={d.analysis.citations}
                        claimText={d.analysis.text?.slice(0, 80) || ''}
                        sourceVolume={d.source_volume || ''}
                      />
                    )}
                  </div>

                  {/* 涉及实体 */}
                  {d.related_entities && d.related_entities.length > 0 && (
                    <div className="mystery-entities">
                      <span className="mystery-entities-label">涉及：</span>
                      {d.related_entities.map((e) => (
                        <span key={e} className="mystery-entity-tag">{e}</span>
                      ))}
                    </div>
                  )}

                  {/* 对比陈述（如有第二条） */}
                  {statements.length > 1 && statements[1].citation && (
                    <div className="mystery-extra-source">
                      <span className="mystery-source-label">另一处提及：</span>
                      <span className="mystery-source-id">{statements[1].citation.cite_id}</span>
                      {statements[1].citation.quote && (
                        <span className="mystery-source-quote">「{statements[1].citation.quote.slice(0, 150)}」</span>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="mystery-card-expand-hint" onClick={() => setExpandedId(expanded ? null : d.discrepancy_id)} style={{ cursor: 'pointer' }}>
                {expanded ? '收起 ▲' : '展开了解详情 ▼'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
