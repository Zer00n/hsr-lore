/**
 * 矛盾档案 — 并排对照视图
 *
 * 降级渲染：跨卷矛盾缺失时不显示该分类，不报错。
 *
 * Props:
 *   discrepancies: from discrepancies.json
 */
import { useMemo } from 'react';
import CitationBadge from './CitationBadge.jsx';

const PLACEHOLDER_LEFT = {
  cite_id: 'STRY-1005-1',
  title: '卡芙卡 角色故事 1',
  clean: '卡芙卡是星核猎手的核心成员之一。她以优雅从容的姿态面对一切危险，仿佛早已预见每一个结局。',
};

const PLACEHOLDER_RIGHT = {
  cite_id: 'STRY-1005-2',
  title: '卡芙卡 角色故事 2',
  clean: '卡芙卡是星核猎手的核心成员之一。她以从<u>容</u>的姿态面对一切，仿佛早已预见每一个结局。',
};

const KIND_LABELS = {
  contradiction: '直接矛盾',
  ambiguity: '表述含混',
  gap: '官方留白',
  retcon: '设定变更',
};

const IMPACT_COLORS = {
  high: 'var(--danger)',
  medium: 'var(--warning)',
  low: 'var(--info)',
};

function simpleDiff(left, right) {
  if (!left || !right) return [];
  const ranges = [];
  let i = 0;
  while (i < Math.min(left.length, right.length)) {
    if (left[i] !== right[i]) {
      const start = i;
      while (i < Math.min(left.length, right.length) && left[i] !== right[i]) {
        i++;
      }
      ranges.push({ start, end: i, side: 'both' });
    } else {
      i++;
    }
  }
  if (left.length > right.length) {
    ranges.push({ start: right.length, end: left.length, side: 'left' });
  } else if (right.length > left.length) {
    ranges.push({ start: left.length, end: right.length, side: 'right' });
  }
  return ranges;
}

function processDiscrepancies(discrepancies) {
  if (!discrepancies || discrepancies.length === 0) {
    return {
      intra: [],
      cross: [],
      hasCross: false,
    };
  }

  const intra = [];
  const cross = [];
  for (const d of discrepancies) {
    if (d._cross_volume) {
      cross.push(d);
    } else {
      intra.push(d);
    }
  }

  return { intra, cross, hasCross: cross.length > 0 };
}

function DiscrepancyCard({ discrepancy }) {
  const statements = discrepancy.statements || [];
  const left = statements[0] || {};
  const right = statements[1] || {};

  const leftCiteId = left.citation?.cite_id || '';
  const rightCiteId = right.citation?.cite_id || '';
  const leftQuote = left.citation?.quote || '';
  const rightQuote = right.citation?.quote || '';

  const diffRanges = useMemo(
    () => simpleDiff(left.text || '', right.text || ''),
    [left.text, right.text]
  );

  const buildHighlighted = (text, side) => {
    if (!text) return '';
    const segments = [];
    let cursor = 0;
    for (const r of diffRanges) {
      if (r.side === 'both' || r.side === side) {
        if (cursor < r.start) {
          segments.push({ text: text.slice(cursor, r.start), highlight: false, key: cursor });
        }
        segments.push({
          text: text.slice(r.start, Math.min(r.end, text.length)),
          highlight: true,
          key: r.start,
        });
        cursor = r.end;
      }
    }
    if (cursor < text.length) {
      segments.push({ text: text.slice(cursor), highlight: false, key: cursor });
    }
    return segments;
  };

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      padding: 'var(--space-4)',
      marginBottom: 'var(--space-4)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
        <div>
          <span style={{
            fontSize: 'var(--text-xs)',
            background: 'var(--accent-muted)',
            color: 'var(--accent)',
            padding: '1px 6px',
            borderRadius: 'var(--radius-sm)',
            marginRight: '8px',
          }}>
            {KIND_LABELS[discrepancy.kind] || discrepancy.kind}
          </span>
          <strong style={{ fontSize: 'var(--text-sm)' }}>{discrepancy.topic}</strong>
        </div>
        <span style={{
          fontSize: 'var(--text-xs)',
          color: IMPACT_COLORS[discrepancy.impact] || 'var(--text-muted)',
        }}>
          {discrepancy.impact === 'high' ? '⚠ 高影响' : discrepancy.impact === 'medium' ? '中影响' : '低影响'}
        </span>
      </div>

      {/* Side-by-side */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
        {/* Left */}
        <div style={{
          background: 'var(--bg-base)',
          padding: 'var(--space-3)',
          borderRadius: 'var(--radius-sm)',
        }}>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: '4px' }}>
            {leftCiteId || '来源A'}
          </div>
          {leftQuote && (
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--accent-alt)', marginBottom: '6px', padding: '2px 6px', background: 'var(--accent-muted)', borderRadius: 'var(--radius-sm)', lineHeight: 'var(--leading-relaxed)' }}>
              原文：「{leftQuote.slice(0, 200)}」
            </div>
          )}
          <div style={{ lineHeight: 'var(--leading-relaxed)', fontSize: 'var(--text-sm)' }}>
            {left.text ? buildHighlighted(left.text, 'left').map(s =>
              s.highlight
                ? <mark key={s.key} style={{ background: 'var(--warning)', color: 'var(--bg-base)', borderRadius: '2px', padding: '0 2px' }}>{s.text}</mark>
                : <span key={s.key}>{s.text}</span>
            ) : '(无内容)'}
          </div>
        </div>

        {/* Right */}
        <div style={{
          background: 'var(--bg-base)',
          padding: 'var(--space-3)',
          borderRadius: 'var(--radius-sm)',
        }}>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: '4px' }}>
            {rightCiteId || '来源B'}
          </div>
          {rightQuote && (
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--accent-alt)', marginBottom: '6px', padding: '2px 6px', background: 'var(--accent-muted)', borderRadius: 'var(--radius-sm)', lineHeight: 'var(--leading-relaxed)' }}>
              原文：「{rightQuote.slice(0, 200)}」
            </div>
          )}
          <div style={{ lineHeight: 'var(--leading-relaxed)', fontSize: 'var(--text-sm)' }}>
            {right.text ? buildHighlighted(right.text, 'right').map(s =>
              s.highlight
                ? <mark key={s.key} style={{ background: 'var(--warning)', color: 'var(--bg-base)', borderRadius: '2px', padding: '0 2px' }}>{s.text}</mark>
                : <span key={s.key}>{s.text}</span>
            ) : '(无内容)'}
          </div>
        </div>
      </div>

      {/* Analysis */}
      {discrepancy.analysis?.text && (
        <div style={{
          marginTop: 'var(--space-3)',
          padding: 'var(--space-3)',
          background: 'var(--bg-elevated)',
          borderRadius: 'var(--radius-sm)',
          fontSize: 'var(--text-sm)',
          color: 'var(--text-secondary)',
        }}>
          <strong style={{ color: 'var(--text-primary)' }}>分析：</strong>
          {discrepancy.analysis.text}
          <CitationBadge
            citations={discrepancy.analysis.citations || []}
            claimText={discrepancy.analysis.text?.slice(0, 80) || ''}
            sourceVolume={discrepancy.source_volume || ''}
            position="block"
          />
        </div>
      )}

      {/* Related entities */}
      {discrepancy.related_entities?.length > 0 && (
        <div style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
          涉及：{discrepancy.related_entities.join('、')}
        </div>
      )}
    </div>
  );
}

export default function DiffViewer({
  discrepancies = null,
}) {
  const { intra, cross, hasCross } = processDiscrepancies(discrepancies);

  return (
    <div style={{ width: '100%', height: '100%', overflowY: 'auto', padding: 'var(--space-4)' }}>
      {/* Vol Intra section (always visible) */}
      <h3 style={{ fontSize: 'var(--text-lg)', marginBottom: 'var(--space-4)' }}>
        卷内矛盾 <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>({intra.length})</span>
      </h3>
      {intra.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
          无卷内矛盾记录
        </p>
      ) : (
        intra.slice(0, 50).map((d) => (
          <DiscrepancyCard key={d.discrepancy_id || d.topic} discrepancy={d} />
        ))
      )}

      {/* Cross-volume section (hidden if no pass2 data) */}
      {hasCross && (
        <>
          <h3 style={{ fontSize: 'var(--text-lg)', marginTop: 'var(--space-8)', marginBottom: 'var(--space-4)' }}>
            跨卷矛盾 <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>({cross.length})</span>
          </h3>
          {cross.map((d) => (
            <DiscrepancyCard key={d.discrepancy_id || d.topic} discrepancy={d} />
          ))}
        </>
      )}

      {/* Degradation note */}
      {!hasCross && (
        <div style={{
          marginTop: 'var(--space-8)',
          padding: 'var(--space-4)',
          background: 'var(--bg-elevated)',
          borderRadius: 'var(--radius-md)',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: 'var(--text-sm)',
        }}>
          跨卷矛盾分析尚未运行（pass2 T6 未执行）<br />
          目前仅显示卷内矛盾（T3 产出）
        </div>
      )}
    </div>
  );
}
