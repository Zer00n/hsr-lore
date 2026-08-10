/**
 * 站点主应用 — 7 视图 + 置信度过滤 + 内容质量过滤统计
 * 首屏视图使用 ForceGraph (d3-force)，其余视图按需懒加载
 */
import { useEffect, useState, useMemo, lazy, Suspense } from 'react';
import '../styles/site-app.css';
import ConfidenceFilter, { DEFAULT_FILTER } from './ConfidenceFilter.jsx';
import QualityDashboard from './QualityDashboard.jsx';

const ForceGraph = lazy(() => import('./ForceGraph.jsx'));

const Timeline = lazy(() => import('./Timeline.jsx'));
const DiffViewer = lazy(() => import('./DiffViewer.jsx'));
const MysteryWall = lazy(() => import('./MysteryWall.jsx'));
const MergeTrace = lazy(() => import('./MergeTrace.jsx'));
const CitationAudit = lazy(() => import('./CitationAudit.jsx'));

const ALL_TABS = [
  { key: 'graph', label: '命途星图', desc: '实体关系图谱' },
  { key: 'timeline', label: '银河编年史', desc: '事件时序' },
  { key: 'diff', label: '矛盾档案', desc: '考据矛盾与悬案' },
  { key: 'mystery', label: '未解之谜', desc: '官方留白' },
  { key: 'merge', label: '归并溯源', desc: '实体归并记录', needsPass2: true },
  { key: 'audit', label: '引证审计', desc: '随机抽查验证' },
  { key: 'quality', label: '考据质量', desc: '引证校验·生产指标' },
];

const LOADERS = {
  graph: ['entities-core', 'relations'],
  timeline: ['events'],
  diff: ['discrepancies'],
  mystery: ['discrepancies'],
  merge: ['merges'],
  audit: ['entities', 'relations', 'events', 'discrepancies', 'citations'],
  quality: ['stats'],
};

async function fetchJson(name) {
  const res = await fetch(`/data/${name}.json`);
  if (!res.ok) throw new Error(`加载 /data/${name}.json 失败（HTTP ${res.status}）`);
  return res.json();
}

function loadTab(keys) {
  return Promise.all(keys.map((k) => fetchJson(k).then((d) => [k, d]))).then((pairs) => Object.fromEntries(pairs));
}

function ViewFallback() {
  return <div className="view-loading"><span className="spinner" /> 正在加载组件…</div>;
}

export default function SiteApp() {
  const [activeTab, setActiveTab] = useState('graph');
  const [summary, setSummary] = useState(null);
  const [stats, setStats] = useState(null);
  const [cache, setCache] = useState({});
  const [loadingKey, setLoadingKey] = useState(null);
  const [errors, setErrors] = useState({});
  const [confFilter, setConfFilter] = useState(DEFAULT_FILTER);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchJson('build_summary').catch(() => null), fetchJson('stats').catch(() => null)]).then(([s, t]) => {
      if (!cancelled) { setSummary(s); setStats(t); }
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const keys = LOADERS[activeTab];
    if (!keys) return;
    const needed = keys.filter((k) => cache[k] === undefined && !errors[k]);
    if (needed.length === 0) return;
    let cancelled = false;
    setLoadingKey(activeTab);
    loadTab(needed)
      .then((data) => { if (cancelled) return; setCache((prev) => ({ ...prev, ...data })); setErrors((prev) => { const n = { ...prev }; needed.forEach((k) => delete n[k]); return n; }); })
      .catch((err) => { if (cancelled) return; setErrors((prev) => { const n = { ...prev }; needed.forEach((k) => { n[k] = err.message || String(err); }); return n; }); })
      .finally(() => { if (!cancelled) setLoadingKey(null); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const degraded = summary?.degradation ?? null;
  const counts = summary?.outputs ?? null;
  const pass2Available = summary?.build_args?.pass2_enabled ?? false;
  const filterStats = summary?.quality_filter ?? null;

  const hiddenCounts = useMemo(() => {
    const keys = LOADERS[activeTab]; if (!keys) return {};
    const totals = { attested: 0, inferred: 0, disputed: 0 };
    keys.forEach((k) => {
      if (cache[k] && Array.isArray(cache[k]))
        cache[k].forEach((obj) => { const conf = obj.confidence || obj.analysis?.confidence; if (conf && !confFilter[conf]) totals[conf] = (totals[conf] || 0) + 1; });
    });
    return totals;
  }, [activeTab, cache, confFilter]);

  const renderView = () => {
    const keys = LOADERS[activeTab] || [];
    const hasError = keys.some((k) => errors[k]);
    const isLoading = loadingKey === activeTab;
    const missing = keys.filter((k) => cache[k] === undefined);
    if (hasError) return <div className="view-error"><p>数据加载失败：{keys.map((k) => errors[k]).join('；')}</p><p className="view-error-hint">请确认 JSON 文件已生成。</p></div>;
    if (isLoading || missing.length > 0) return <div className="view-loading"><span className="spinner" /> 正在加载数据…</div>;

    if (activeTab === 'graph')
      return <Suspense fallback={<ViewFallback />}><div className="view-panel graph-panel"><ForceGraph entities={cache['entities-core'] || cache.entities || []} relations={cache.relations || []} /></div></Suspense>;
    if (activeTab === 'timeline')
      return <Suspense fallback={<ViewFallback />}><div className="view-panel timeline-panel"><Timeline events={cache.events} confidenceFilter={confFilter} /></div></Suspense>;
    if (activeTab === 'diff')
      return <Suspense fallback={<ViewFallback />}><div className="view-panel diff-panel"><DiffViewer discrepancies={cache.discrepancies} confidenceFilter={confFilter} /></div></Suspense>;
    if (activeTab === 'mystery')
      return <Suspense fallback={<ViewFallback />}><div className="view-panel diff-panel"><MysteryWall discrepancies={cache.discrepancies} confidenceFilter={confFilter} /></div></Suspense>;
    if (activeTab === 'merge') {
      if (!pass2Available)
        return <div className="view-panel diff-panel"><MergeTrace merges={null} /></div>;
      return <Suspense fallback={<ViewFallback />}><div className="view-panel diff-panel"><MergeTrace merges={cache.merges || []} /></div></Suspense>;
    }
    if (activeTab === 'audit')
      return <Suspense fallback={<ViewFallback />}><div className="view-panel diff-panel"><CitationAudit cache={cache} /></div></Suspense>;
    if (activeTab === 'quality')
      return <div className="view-panel quality-panel"><QualityDashboard stats={cache.stats || stats} filterStats={summary?.quality_filter} /></div>;
    return null;
  };

  const tabs = ALL_TABS.map((tab) => ({
    ...tab,
    disabled: tab.needsPass2 && !pass2Available,
  }));

  return (
    <section className="app">
      <ConfidenceFilter filter={confFilter} onChange={setConfFilter} hiddenCounts={hiddenCounts} />

      {degraded && (
        <div className="status-strip">
          {degraded.pass2_missing && <span className="status-chip">pass1-only 数据</span>}
          {degraded.entities_unmerged > 0 && <span className="status-chip">未归并实体 {degraded.entities_unmerged}</span>}
          {degraded.timeline_inferred > 0 && <span className="status-chip">时间轴推断 {degraded.timeline_inferred}</span>}
          {degraded.cross_volume_discrepancies === 0 && <span className="status-chip">无跨卷矛盾</span>}
          {counts && <span className="status-meta">实体 {counts.entities} · 关系 {counts.relations} · 事件 {counts.events} · 矛盾 {counts.discrepancies}</span>}
        </div>
      )}

      {/* 质量过滤状态条 */}
      {filterStats && filterStats.total_filtered > 0 && (
        <div className="status-strip filter-strip">
          <span className="status-chip" style={{ color: 'var(--danger)' }}>质量过滤 {filterStats.total_filtered} 条</span>
          {Object.entries(filterStats.by_rule || {}).filter(([, v]) => v > 0).map(([rule, count]) => (
            <span key={rule} className="status-chip">{rule}: {count}</span>
          ))}
          <span className="status-meta">过滤日志: work/site_filtered_out.jsonl</span>
        </div>
      )}

      <nav className="tabs" role="tablist" aria-label="考据视图">
        {tabs.map((tab) => (
          <button key={tab.key} role="tab" aria-selected={activeTab === tab.key}
            className={`tab ${activeTab === tab.key ? 'is-active' : ''} ${tab.disabled ? 'tab-disabled' : ''}`}
            onClick={() => !tab.disabled && setActiveTab(tab.key)}
            title={tab.disabled ? '该模块需要 pass2 数据，正在生成中' : ''}
          >
            <span className="tab-label">{tab.label}{tab.disabled ? ' (待接入)' : ''}</span>
            <span className="tab-desc">{tab.disabled ? '需要 pass2 数据' : tab.desc}</span>
          </button>
        ))}
      </nav>

      <div className="view" role="tabpanel">{renderView()}</div>
    </section>
  );
}
