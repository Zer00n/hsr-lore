/**
 * 置信度全局过滤器 — 全站顶部开关组
 * attested / inferred / disputed 可分别开关
 */
export default function ConfidenceFilter({ filter, onChange, hiddenCounts = {} }) {
  const items = [
    { key: 'attested', label: '确证', desc: '有原文直接支撑' },
    { key: 'inferred', label: '推断', desc: '基于上下文推理' },
    { key: 'disputed', label: '存疑', desc: '存在矛盾或不确定' },
  ];

  const totalHidden = Object.values(hiddenCounts).reduce((a, b) => a + b, 0);

  return (
    <div className="confidence-filter-bar">
      <span className="conf-filter-label">置信度</span>
      {items.map((item) => {
        const active = filter[item.key];
        return (
          <button
            key={item.key}
            className={`conf-filter-btn ${active ? 'is-active' : 'is-off'}`}
            onClick={() => onChange({ ...filter, [item.key]: !active })}
            title={item.desc}
            type="button"
          >
            <span className={`conf-filter-dot conf-dot-${item.key}`} aria-hidden="true" />
            <span className="conf-filter-text">{item.label}</span>
            {hiddenCounts[item.key] > 0 && (
              <span className="conf-filter-hidden-count">{hiddenCounts[item.key]} 条隐藏</span>
            )}
          </button>
        );
      })}
      {totalHidden > 0 && (
        <span className="conf-filter-summary">共隐藏 {totalHidden} 条</span>
      )}
    </div>
  );
}

export const DEFAULT_FILTER = { attested: true, inferred: true, disputed: true };
