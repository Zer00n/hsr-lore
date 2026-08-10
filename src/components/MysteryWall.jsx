/**
 * 未解之谜墙 — 数据源为 discrepancies.json 中 kind === 'gap' 的条目
 * 面向普通玩家，文案口语化，不出现术语「gap」。
 */
import { useState } from 'react';
import CitationBadge from './CitationBadge.jsx';

const IMPACT_LABEL = { high: '核心谜题', medium: '值得关注', low: '细节补充' };

export default function MysteryWall({ discrepancies = [] }) {
  const [expandedId, setExpandedId] = useState(null);
  const gaps = (discrepancies || []).filter((d) => d.kind === 'gap');

  if (gaps.length === 0) {
    return (
      <div className="mystery-empty">
        <span className="mystery-empty-mark" aria-hidden="true" />
        <p className="mystery-empty-title">暂无未解之谜</p>
        <p className="mystery-empty-desc">
          Pass1 四卷数据中未检测到留白类条目。pass2 跨卷分析运行后可能会出现新的未解之谜。
        </p>
      </div>
    );
  }

  return (
    <div className="mystery-wall">
      <header className="mystery-header">
        <h2 className="mystery-title">未解之谜墙</h2>
        <p className="mystery-subtitle">
          以下条目是游戏中提到但尚未完全展开的世界观线索——不是遗漏，而是叙事留白。
        </p>
      </header>

      <div className="mystery-grid">
        {gaps.map((d) => {
          const expanded = expandedId === d.discrepancy_id;
          const statements = d.statements || [];
          const primary = statements[0] || {};

          return (
            <article key={d.discrepancy_id} className={`mystery-card ${expanded ? 'is-expanded' : ''}`}>
              <button
                className="mystery-card-header"
                onClick={() => setExpandedId(expanded ? null : d.discrepancy_id)}
                aria-expanded={expanded}
              >
                <span className="mystery-mark" aria-hidden="true" />
                <span className="mystery-card-topic">{d.topic}</span>
                <span className={`mystery-card-impact impact-${d.impact}`}>
                  {IMPACT_LABEL[d.impact] || d.impact}
                </span>
              </button>

              {primary.citation && (
                <div className="mystery-card-source">
                  <span className="mystery-source-id mono">{primary.citation.cite_id}</span>
                  {primary.citation.quote && (
                    <span className="mystery-source-quote">
                      「{primary.citation.quote.slice(0, 150)}」
                    </span>
                  )}
                </div>
              )}

              {expanded && (
                <div className="mystery-card-body">
                  <div className="mystery-why-section">
                    <h4 className="mystery-h4">为什么这不是遗漏</h4>
                    {d.analysis?.text ? (
                      <>
                        <p className="mystery-analysis-text">{d.analysis.text}</p>
                        {d.analysis.citations?.length > 0 && (
                          <CitationBadge
                            citations={d.analysis.citations}
                            claimText={d.analysis.text?.slice(0, 80) || ''}
                            sourceVolume={d.source_volume || ''}
                          />
                        )}
                      </>
                    ) : (
                      <p className="mystery-analysis-text">
                        游戏文本仅给出了{d.topic}的有限线索，没有在这个点上展开完整解释——这通常是有意为之的叙事策略，为未来的剧情发展预留空间。
                      </p>
                    )}
                  </div>

                  {d.related_entities?.length > 0 && (
                    <div className="mystery-entities">
                      <span className="mystery-entities-label mono">涉及</span>
                      {d.related_entities.map((e) => (
                        <span key={e} className="mystery-entity-tag mono">{e}</span>
                      ))}
                    </div>
                  )}

                  {statements.length > 1 && statements[1].citation && (
                    <div className="mystery-extra-source">
                      <span className="mystery-source-label">另一处提及</span>
                      <span className="mystery-source-id mono">{statements[1].citation.cite_id}</span>
                      {statements[1].citation.quote && (
                        <span className="mystery-source-quote">
                          「{statements[1].citation.quote.slice(0, 150)}」
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}

              <button
                className="mystery-card-expand-hint"
                onClick={() => setExpandedId(expanded ? null : d.discrepancy_id)}
              >
                {expanded ? '收起' : '展开了解详情'}
                <span className="mystery-caret" aria-hidden="true">{expanded ? '−' : '+'}</span>
              </button>
            </article>
          );
        })}
      </div>
    </div>
  );
}
