/**
 * 归并溯源 — 展示 pass2 实体归并记录
 * 数据源: output/pass2/merges.jsonl（由 build_site_data.py 处理为 merges.json）
 * pass2 数据缺失时整屏隐藏（在 SiteApp 中控制），不报错
 */
export default function MergeTrace({ merges = [] }) {
  if (!merges || merges.length === 0) {
    return (
      <div className="merge-empty">
        <span className="merge-empty-mark" aria-hidden="true" />
        <p className="merge-empty-title">归并溯源数据暂缺</p>
        <p className="merge-empty-desc">pass2 实体归并尚未运行。运行后将在此展示每组归并的判定方法与原文依据。</p>
      </div>
    );
  }

  const TYPE_LABELS = { exact_name: '同名精确匹配', alias_match: '别名匹配', contextual: '上下文推断' };
  const CONFIDENCE_LABELS = { attested: '确认', inferred: '推断', disputed: '存疑' };

  return (
    <div className="merge-trace">
      <header className="merge-header">
        <h2 className="merge-title">归并溯源</h2>
        <p className="merge-subtitle">下表展示 pass2 实体归并的每一步判定与原文依据。</p>
      </header>

      <div className="merge-list">
        {merges.map((m) => (
          <article key={m.merge_id || m.merged_entity_id} className="merge-card">
            <div className="merge-card-top">
              <span className="merge-target">
                归并至 <strong>{m.merged_entity_id || m.canonical_name}</strong>
              </span>
              <span className="merge-method">{TYPE_LABELS[m.method] || m.method}</span>
              <span className={`merge-confidence conf-${m.confidence}`}>
                {CONFIDENCE_LABELS[m.confidence] || m.confidence}
              </span>
            </div>
            <div className="merge-card-sources">
              <span className="merge-sources-label mono">来源</span>
              {(m.source_entity_ids || []).map((sid) => (
                <span key={sid} className="merge-source-item mono">{sid}</span>
              ))}
            </div>
            {m.rationale?.text && (
              <p className="merge-card-rationale">{m.rationale.text}</p>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
