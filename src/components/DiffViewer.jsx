/**
 * 矛盾档案 — 两方陈述并排对照
 *
 * 左金右冷青，中间留 1px 间隙表达「互斥」。
 * 每侧分层：cite_id（等宽）→ 原文 quote（游戏原文，衬线块引）→ 陈述（结论）。
 * analysis 段用小号 + 左侧竖线，明确标注为 model interpretation，不是原文。
 *
 * 降级：跨卷矛盾缺失时不显示该分类，不报错。
 */
import CitationBadge from './CitationBadge.jsx';

const KIND_LABELS = {
  contradiction: '直接矛盾',
  ambiguity: '表述含混',
  gap: '官方留白',
  retcon: '设定变更',
};

function Statement({ stmt, side }) {
  const citeId = stmt.citation?.cite_id || '';
  const quote = stmt.citation?.quote || '';
  return (
    <div className={`diff-side diff-side-${side}`}>
      <div className="diff-side-head">
        <span className="diff-side-tag mono">{side === 'a' ? '陈述 A' : '陈述 B'}</span>
        {citeId && <span className="diff-citeid mono">{citeId}</span>}
      </div>
      {quote && (
        <blockquote className="diff-quote">
          <span className="diff-quote-mark" aria-hidden="true">「</span>
          {quote}
          <span className="diff-quote-mark" aria-hidden="true">」</span>
        </blockquote>
      )}
      {stmt.text && <p className="diff-text">{stmt.text}</p>}
    </div>
  );
}

function DiscrepancyCard({ discrepancy }) {
  const statements = discrepancy.statements || [];
  const left = statements[0] || {};
  const right = statements[1] || {};

  return (
    <article className="diff-card">
      <header className="diff-head">
        <div className="diff-head-left">
          <span className={`diff-kind kind-${discrepancy.kind}`}>
            {KIND_LABELS[discrepancy.kind] || discrepancy.kind}
          </span>
          <h3 className="diff-topic">{discrepancy.topic}</h3>
        </div>
        {discrepancy.impact && (
          <span className={`diff-impact impact-${discrepancy.impact} mono`}>
            {discrepancy.impact === 'high' ? '高影响' : discrepancy.impact === 'medium' ? '中影响' : '低影响'}
          </span>
        )}
      </header>

      <div className="diff-pair">
        <Statement stmt={left} side="a" />
        <div className="diff-gutter" aria-hidden="true" />
        <Statement stmt={right} side="b" />
      </div>

      {discrepancy.analysis?.text && (
        <div className="diff-analysis">
          <div className="diff-analysis-label mono">
            ANALYSIS · 模型解读，非原文
          </div>
          <p className="diff-analysis-text">
            {discrepancy.analysis.text}
          </p>
          {discrepancy.analysis.citations?.length > 0 && (
            <CitationBadge
              citations={discrepancy.analysis.citations}
              claimText={discrepancy.analysis.text?.slice(0, 80) || ''}
              sourceVolume={discrepancy.source_volume || ''}
            />
          )}
        </div>
      )}

      {discrepancy.related_entities?.length > 0 && (
        <footer className="diff-foot">
          <span className="diff-foot-label mono">涉及</span>
          {discrepancy.related_entities.map((e) => (
            <span key={e} className="diff-entity mono">{e}</span>
          ))}
        </footer>
      )}
    </article>
  );
}

export default function DiffViewer({ discrepancies = null }) {
  const list = discrepancies || [];
  const intra = list.filter((d) => !d._cross_volume);
  const cross = list.filter((d) => d._cross_volume);

  return (
    <div className="diff-view">
      <section>
        <div className="diff-section-head">
          <h2>卷内矛盾</h2>
          <span className="diff-count mono">{intra.length}</span>
        </div>
        {intra.length === 0 ? (
          <p className="diff-empty">无卷内矛盾记录</p>
        ) : (
          intra.slice(0, 50).map((d) => (
            <DiscrepancyCard key={d.discrepancy_id || d.topic} discrepancy={d} />
          ))
        )}
      </section>

      {cross.length > 0 && (
        <section>
          <div className="diff-section-head">
            <h2>跨卷矛盾</h2>
            <span className="diff-count mono">{cross.length}</span>
          </div>
          {cross.map((d) => (
            <DiscrepancyCard key={d.discrepancy_id || d.topic} discrepancy={d} />
          ))}
        </section>
      )}

      {cross.length === 0 && (
        <div className="diff-notice">
          跨卷矛盾分析尚未运行（pass2 T6 未执行）。目前仅显示卷内矛盾（T3 产出）。
        </div>
      )}
    </div>
  );
}
