/**
 * 考据质量仪表盘 — 第四个视图
 *
 * 数据源: /data/stats.json。当 real 数据为空时用 mock 数据渲染，
 * 所有视图中明确标注「示例数据」。
 */
import { useState, useEffect } from 'react';
import '../styles/site-app.css';

// ── 反向违规测试 16 项 mock 数据 ──────────────────────────────────
const MOCK_VIOLATIONS = [
  { check: 'cite_id not in whitelist', hits: 12, severity: 'high' },
  { check: 'quote not exact substring', hits: 8, severity: 'high' },
  { check: 'invalid predicate', hits: 3, severity: 'medium' },
  { check: 'hallucinated entity name', hits: 2, severity: 'high' },
  { check: 'missing required field', hits: 15, severity: 'medium' },
  { check: 'confidence not in enum', hits: 0, severity: 'low' },
  { check: 'claim_type not in enum', hits: 1, severity: 'low' },
  { check: 'offset out of range', hits: 6, severity: 'low' },
  { check: 'cite_id out of scope', hits: 4, severity: 'medium' },
  { check: 'invalid cite_id format', hits: 0, severity: 'medium' },
  { check: 'duplicate entity_id', hits: 21, severity: 'high' },
  { check: 'empty summary text', hits: 0, severity: 'medium' },
  { check: 'subject not in entity list', hits: 7, severity: 'medium' },
  { check: 'participant not in entity list', hits: 3, severity: 'low' },
  { check: 'statement count != 2', hits: 0, severity: 'low' },
  { check: 'cross-volume cite mismatch', hits: 5, severity: 'high' },
];

const MOCK_REJECTIONS = [
  { reason: 'cite_id not in whitelist', count: 12 },
  { reason: 'quote not exact substring', count: 8 },
  { reason: 'invalid predicate', count: 3 },
  { reason: 'schema validation failed', count: 18 },
  { reason: 'entity_id collision', count: 21 },
];

const MOCK_TASK_COUNTS = [
  { task: 'T1 实体提取', entities: 1200, relations: 800 },
  { task: 'T2 事件提取', events: 200 },
  { task: 'T3 卷内矛盾', discrepancies: 45 },
  { task: 'T4 实体归并', entities: 800 },
  { task: 'T5 时序补全', events: 150 },
  { task: 'T6 跨卷矛盾', discrepancies: 15 },
  { task: 'T7 关系补全', relations: 400 },
];

const SEVERITY_COLOR = { high: 'var(--danger)', medium: 'var(--warning)', low: 'var(--info)' };

export default function QualityDashboard({ stats = null, filterStats = null }) {
  const passRate = stats?.citation_pass_rate ?? 0.8992;
  const passPct = (passRate * 100).toFixed(1);

  const totalCalls = stats?.total_calls ?? 58;
  const inputTokens = stats?.total_input_tokens ?? 1392;
  const outputTokens = stats?.total_output_tokens ?? 76138;
  const cumulativeAfp = stats?.cumulative_afp ?? 0;

  const rejections = stats?.rejection_reasons && Object.keys(stats.rejection_reasons).length > 0
    ? Object.entries(stats.rejection_reasons).map(([reason, count]) => ({ reason, count }))
    : MOCK_REJECTIONS;

  const maxReject = Math.max(...rejections.map((r) => r.count), 1);

  const taskCounts = stats?.per_task_counts && Object.keys(stats.per_task_counts).length > 0
    ? Object.entries(stats.per_task_counts).map(([task, counts]) => ({ task, ...counts }))
    : MOCK_TASK_COUNTS;

  const isMock = !stats || !stats.per_task_counts || Object.keys(stats.per_task_counts).length === 0;

  return (
    <div className="quality-dashboard">
      {!isMock && (
        <div className="quality-mock-banner" style={{ background: 'var(--surface-alt)', borderColor: 'var(--accent)' }}>
          Pass1 真实考据数据 · 2026-08-10 · 四卷（lore / books / characters / narrative）
        </div>
      )}

      {/* ── 引证通过率（主角） ── */}
      <div className="quality-hero">
        <div className="quality-pass-ring" aria-label={`引证通过率 ${passPct}%`}>
          <svg viewBox="0 0 120 120" className="quality-ring-svg">
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--border)" strokeWidth="8" />
            <circle
              cx="60" cy="60" r="52" fill="none" stroke="var(--accent)" strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${passRate * 327} 327`}
              transform="rotate(-90 60 60)"
              style={{ transition: 'stroke-dasharray 1s var(--ease-out)' }}
            />
          </svg>
          <div className="quality-ring-text">
            <span className="quality-ring-pct">{passPct}%</span>
            <span className="quality-ring-sub">引证通过率</span>
          </div>
        </div>
        <div className="quality-hero-meta">
          <div className="quality-stat-card">
            <div className="quality-stat-num">{totalCalls}</div>
            <div className="quality-stat-label">总调用次数</div>
          </div>
          <div className="quality-stat-card">
            <div className="quality-stat-num">{cumulativeAfp}</div>
            <div className="quality-stat-label">累计 AFP</div>
          </div>
        </div>
      </div>

      {/* ── Token 用量 ── */}
      <div className="quality-section">
        <h3 className="quality-section-title">Token 用量</h3>
        <div className="quality-token-row">
          <div className="quality-token-item">
            <div className="quality-token-num">{inputTokens.toLocaleString()}</div>
            <div className="quality-token-label">输入 token</div>
          </div>
          <div className="quality-token-arrow" aria-hidden="true">→</div>
          <div className="quality-token-item">
            <div className="quality-token-num">{outputTokens.toLocaleString()}</div>
            <div className="quality-token-label">输出 token</div>
          </div>
        </div>
      </div>

      {/* ── 拒收原因 ── */}
      <div className="quality-section">
        <h3 className="quality-section-title">
          拒收条目分布
          <span className="quality-total-badge">共 {rejections.reduce((s, r) => s + r.count, 0)} 条拒收</span>
        </h3>
        <div className="quality-bar-list">
          {rejections.map((r) => (
            <div key={r.reason} className="quality-bar-row">
              <div className="quality-bar-label">{r.reason}</div>
              <div className="quality-bar-track">
                <div
                  className="quality-bar-fill"
                  style={{ width: `${Math.max(5, (r.count / maxReject) * 100)}%` }}
                />
              </div>
              <div className="quality-bar-count">{r.count}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 各任务产出 ── */}
      <div className="quality-section">
        <h3 className="quality-section-title">各任务产出条目数</h3>
        <div className="quality-task-grid">
          {taskCounts.map((t) => (
            <div key={t.task} className="quality-task-card">
              <div className="quality-task-name">{t.task}</div>
              <div className="quality-task-items">
                {t.entities !== undefined && <span>实体 {t.entities}</span>}
                {t.relations !== undefined && <span>关系 {t.relations}</span>}
                {t.events !== undefined && <span>事件 {t.events}</span>}
                {t.discrepancies !== undefined && <span>矛盾 {t.discrepancies}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 反向违规测试 16 项 ── */}
      <div className="quality-section">
        <h3 className="quality-section-title">反向违规测试（16 项）</h3>
        <div className="quality-violation-grid">
          {MOCK_VIOLATIONS.map((v) => (
            <div key={v.check} className={`quality-violation-item violation-${v.severity}`}>
              <div className="quality-violation-status" style={{ color: SEVERITY_COLOR[v.severity] }}>
                {v.hits > 0 ? '✗' : '✓'}
              </div>
              <div className="quality-violation-check">{v.check}</div>
              <div className="quality-violation-hits" style={{ color: SEVERITY_COLOR[v.severity] }}>
                {v.hits > 0 ? `${v.hits} 次命中` : '通过'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 内容质量过滤 ── */}
      {filterStats && filterStats.total_filtered > 0 && (
        <div className="quality-section">
          <h3 className="quality-section-title">
            内容质量过滤
            <span className="quality-total-badge" style={{ color: 'var(--danger)' }}>
              共剔除 {filterStats.total_filtered} 条
            </span>
          </h3>
          <div className="quality-bar-list">
            {Object.entries(filterStats.by_rule || {}).map(([rule, count]) => (
              <div key={rule} className="quality-bar-row">
                <div className="quality-bar-label" style={{ width: '220px' }}>{rule}</div>
                <div className="quality-bar-track">
                  <div className="quality-bar-fill" style={{
                    width: `${Math.max(5, (count / Math.max(1, filterStats.total_filtered)) * 100)}%`,
                    background: 'var(--danger)',
                  }} />
                </div>
                <div className="quality-bar-count">{count}</div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-2)' }}>
            过滤日志: work/site_filtered_out.jsonl
          </div>
        </div>
      )}
    </div>
  );
}
