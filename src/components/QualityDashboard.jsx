/**
 * 考据质量仪表盘
 *
 * 数据源: /data/stats.json。真实数据优先；pass1 未产出的分块指标
 * （per_task_counts / rejection_reasons）显示为空状态而非伪造数字。
 * 全站主张可追溯，质量屏不得用假数据填充。
 */
import { useState, useMemo } from 'react';

const TASK_LABELS = {
  T1: '实体提取', T2: '事件提取', T3: '卷内矛盾', T4: '实体归并',
  T5: '时序补全', T6: '跨卷矛盾', T7: '关系补全',
};

function fmt(n) {
  return typeof n === 'number' ? n.toLocaleString('en-US') : '—';
}

export default function QualityDashboard({ stats = null, filterStats = null }) {
  const passRate = stats?.citation_pass_rate ?? 0;
  const passPct = (passRate * 100).toFixed(1);
  const totalCalls = stats?.total_calls ?? 0;
  const inputTokens = stats?.total_input_tokens ?? 0;
  const outputTokens = stats?.total_output_tokens ?? 0;
  const cumulativeAfp = stats?.cumulative_afp ?? 0;
  const totals = stats?.totals ?? {};

  const rejections = useMemo(
    () => Object.entries(stats?.rejection_reasons ?? {}).map(([reason, count]) => ({ reason, count })),
    [stats]
  );
  const maxReject = Math.max(...rejections.map((r) => r.count), 1);

  const taskRows = useMemo(
    () => Object.entries(stats?.per_task_counts ?? {}).map(([task, counts]) => {
      const m = task.match(/^T(\d+)/);
      const label = m ? `T${m[1]} · ${TASK_LABELS[`T${m[1]}`] || task}` : task;
      return { task, label, ...counts };
    }),
    [stats]
  );

  const [sortKey, setSortKey] = useState('task');
  const [sortDir, setSortDir] = useState('asc');
  const sortedRows = useMemo(() => {
    const cols = ['entities', 'relations', 'events', 'discrepancies'];
    return [...taskRows].sort((a, b) => {
      let cmp;
      if (sortKey === 'task') cmp = a.task.localeCompare(b.task);
      else cmp = (a[sortKey] || 0) - (b[sortKey] || 0);
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [taskRows, sortKey, sortDir]);

  function toggleSort(key) {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else { setSortKey(key); setSortDir('desc'); }
  }

  const filterEntries = Object.entries(filterStats?.by_rule ?? {}).filter(([, v]) => v > 0);

  return (
    <div className="quality">
      {/* 主角：超大等宽通过率 */}
      <section className="q-hero">
        <div className="q-hero-num">
          <span className="q-pct">{passPct}</span>
          <span className="q-pct-sign" aria-hidden="true">%</span>
        </div>
        <div className="q-hero-meta">
          <h2 className="q-hero-title">引证校验通过率</h2>
          <p className="q-hero-sub mono">
            {totalCalls} calls · {fmt(cumulativeAfp)} AFP
          </p>
          <div className="q-totals">
            {Object.entries(totals).map(([k, v]) => (
              <div key={k} className="q-total">
                <span className="q-total-num mono">{fmt(v)}</span>
                <span className="q-total-label">{({ entities: '实体', relations: '关系', events: '事件', discrepancies: '矛盾' })[k] || k}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Token 用量 */}
      <section className="q-section">
        <h3 className="q-section-title">Token 用量</h3>
        <div className="q-token-row">
          <div className="q-token">
            <span className="q-token-num mono">{fmt(inputTokens)}</span>
            <span className="q-token-label">输入</span>
          </div>
          <span className="q-token-arrow" aria-hidden="true">→</span>
          <div className="q-token">
            <span className="q-token-num mono">{fmt(outputTokens)}</span>
            <span className="q-token-label">输出</span>
          </div>
        </div>
      </section>

      {/* 拒收原因：横向条形 */}
      <section className="q-section">
        <h3 className="q-section-title">
          拒收条目分布
          {rejections.length > 0 && (
            <span className="q-section-count mono">
              {rejections.reduce((s, r) => s + r.count, 0)} 条
            </span>
          )}
        </h3>
        {rejections.length === 0 ? (
          <p className="q-empty">pass1 未记录拒收条目，pass2 校验接入后展示。</p>
        ) : (
          <div className="q-bar-list">
            {rejections.map((r) => (
              <div key={r.reason} className="q-bar-row">
                <div className="q-bar-label">{r.reason}</div>
                <div className="q-bar-track">
                  <div className="q-bar-fill" style={{ width: `${(r.count / maxReject) * 100}%` }} />
                </div>
                <div className="q-bar-count mono">{r.count}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 各任务产出：等宽紧凑可排序表格 */}
      <section className="q-section">
        <h3 className="q-section-title">各任务产出条目数</h3>
        {taskRows.length === 0 ? (
          <p className="q-empty">pass1 未按任务分桶统计，pass2 接入后展示可排序明细。</p>
        ) : (
          <div className="q-table-wrap">
            <table className="q-table">
              <thead>
                <tr>
                  <th onClick={() => toggleSort('task')} className={sortKey === 'task' ? 'is-sorted' : ''}>
                    任务 <span className="q-caret">{sortKey === 'task' ? (sortDir === 'asc' ? '▲' : '▼') : ''}</span>
                  </th>
                  {['entities', 'relations', 'events', 'discrepancies'].map((col) => (
                    <th key={col} onClick={() => toggleSort(col)}
                        className={`num ${sortKey === col ? 'is-sorted' : ''}`}>
                      {({ entities: '实体', relations: '关系', events: '事件', discrepancies: '矛盾' })[col]}
                      <span className="q-caret">{sortKey === col ? (sortDir === 'asc' ? '▲' : '▼') : ''}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((t) => (
                  <tr key={t.task}>
                    <td className="q-task-name">{t.label}</td>
                    {['entities', 'relations', 'events', 'discrepancies'].map((col) => (
                      <td key={col} className="num mono">{t[col] != null ? fmt(t[col]) : '—'}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 内容质量过滤 */}
      {filterStats && filterStats.total_filtered > 0 && (
        <section className="q-section">
          <h3 className="q-section-title">
            内容质量过滤
            <span className="q-section-count q-count-danger mono">剔除 {filterStats.total_filtered} 条</span>
          </h3>
          <div className="q-bar-list">
            {filterEntries.map(([rule, count]) => (
              <div key={rule} className="q-bar-row">
                <div className="q-bar-label">{rule}</div>
                <div className="q-bar-track">
                  <div className="q-bar-fill q-bar-fill-danger" style={{ width: `${(count / filterStats.total_filtered) * 100}%` }} />
                </div>
                <div className="q-bar-count mono">{count}</div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
