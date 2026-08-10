/**
 * 银河编年史 — 可缩放时间轴，带确定性等级标记与可点击引证
 *
 * 降级渲染：跨块 relative_to 缺失时，按 order_hint 排列并标注该段时序为推断。
 */
import { useState, useRef } from 'react';
import CitationBadge from './CitationBadge.jsx';

const PLACEHOLDER_EVENTS = [
  { id: '1', date: '琥珀纪 2157', title: '星穹列车启程', description: '开拓者登上星穹列车', certainty: 'certain', cite_id: 'CHRN-1000101', quote: '' },
  { id: '2', date: '琥珀纪 2157', title: '黑塔空间站遇袭', description: '反物质军团入侵空间站', certainty: 'certain', cite_id: 'CHRN-1000102', quote: '' },
  { id: '3', date: '琥珀纪 2157', title: '雅利洛-VI 星核危机', description: '贝洛伯格面临寒潮与星核双重威胁', certainty: 'certain', cite_id: 'CHRN-1000201', quote: '' },
  { id: '4', date: '琥珀纪 2158', title: '仙舟罗浮事件', description: '建木生长失控，药王秘传作乱', certainty: 'certain', cite_id: 'CHRN-1000301', quote: '' },
  { id: '5', date: '未知', title: '星核猎手起源', description: '推测与星神有关', certainty: 'doubtful', cite_id: 'TALK-5001', quote: '' },
];

const CERTAINTY_LABELS = {
  certain: '明确记载',
  inferred: '推断',
  doubtful: '存疑',
};

function buildTimelineData(events) {
  if (!events || events.length === 0) {
    return { displayEvents: PLACEHOLDER_EVENTS, inferredCount: 0 };
  }
  const sorted = [...events].sort((a, b) => {
    const aHint = a.order_hint ?? 999;
    const bHint = b.order_hint ?? 999;
    if (aHint !== bHint) return aHint - bHint;
    return (a.stated_time || '').localeCompare(b.stated_time || '');
  });

  const displayEvents = sorted.map((evt) => {
    const isInferred = evt._timeline_inferred === true;
    const firstCite = evt.citations?.[0] || evt.summary?.citations?.[0] || {};

    return {
      id: evt.event_id || evt.name,
      date: evt.stated_time || '时间未记载',
      title: evt.name || evt.event_id || '未命名事件',
      description: evt.summary?.text?.substring(0, 120) || '',
      certainty: isInferred ? 'inferred' : 'certain',
      citations: evt.citations || evt.summary?.citations || [],
      sourceVolume: evt.source_volume || '',
    };
  });

  const inferredCount = displayEvents.filter((e) => e.certainty === 'inferred').length;
  return { displayEvents, inferredCount };
}

export default function Timeline({ events = null, onEventClick = (e) => console.log('Event clicked:', e) }) {
  const [scale, setScale] = useState(1);
  const containerRef = useRef(null);
  const { displayEvents, inferredCount } = buildTimelineData(events);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {inferredCount > 0 && (
        <div style={{ background: 'var(--warning)', color: 'var(--bg-base)', padding: '4px 12px', fontSize: 'var(--text-xs)', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <span>⚠ 推断模式</span>
          <span>— {inferredCount}/{displayEvents.length} 个事件的时序为推断（pass2 T7 未运行或未补全）</span>
        </div>
      )}

      <div style={{ padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--border)', flexShrink: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button onClick={() => setScale((s) => Math.max(0.5, s - 0.25))} style={{ background: 'var(--bg-elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)', padding: '4px 12px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>− 缩小</button>
        <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>{Math.round(scale * 100)}%</span>
        <button onClick={() => setScale((s) => Math.min(3, s + 0.25))} style={{ background: 'var(--bg-elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)', padding: '4px 12px', borderRadius: 'var(--radius-sm)', cursor: 'pointer' }}>+ 放大</button>
      </div>

      <div style={{ padding: 'var(--space-4)', overflowY: 'auto', flex: 1 }}>
        {displayEvents.map((evt, i) => (
          <div key={evt.id || i} onClick={() => onEventClick(evt)}
            style={{ padding: 'var(--space-3) var(--space-4)', borderLeft: `3px solid var(--${evt.certainty === 'certain' ? 'success' : evt.certainty === 'inferred' ? 'warning' : 'danger'})`, marginBottom: 'var(--space-1)', background: 'var(--bg-surface)', cursor: 'pointer', transition: 'background var(--duration-fast)' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-surface)')}
          >
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: '2px' }}>{evt.date}</div>
            <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              {evt.title}
              <span className={`certainty-${evt.certainty}`} style={{ fontSize: 'var(--text-xs)' }}>{CERTAINTY_LABELS[evt.certainty]}</span>
              {evt.citations.length > 0 && (
                <CitationBadge citations={evt.citations} claimText={evt.description} sourceVolume={evt.sourceVolume} />
              )}
            </div>
            {evt.description && (
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: '2px', lineHeight: 'var(--leading-relaxed)' }}>{evt.description}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
