/**
 * 归并溯源 — 展示 pass2 实体归并记录（T4 输出）
 * 数据源: site/public/data/merges.json（由 build_site_data.py 从 pass2 merge_records 生成）
 * T4 格式: {merged_name, source_names, method, rationale, confidence}
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
        <p className="merge-subtitle">下表展示 pass2 实体归并的每一步判定与原文依据。共 {merges.length} 条记录。</p>
      </header>

      <div className="merge-list">
        {merges.map((m, idx) => (
          <article key={m.merged_name || idx} className="merge-card">
            <div className="merge-card-top">
              <span className="merge-target">
                归并至 <strong>{m.merged_name}</strong>
              </span>
              <span className="merge-method">{TYPE_LABELS[m.method] || m.method}</span>
              <span className={`merge-confidence conf-${m.confidence}`}>
                {CONFIDENCE_LABELS[m.confidence] || m.confidence}
              </span>
            </div>
            <div className="merge-card-sources">
              <span className="merge-sources-label mono">来源</span>
              {(m.source_names || []).map((sn) => (
                <span key={sn} className="merge-source-item mono">{sn}</span>
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
