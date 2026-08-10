/**
 * 银河编年史 — 垂直时间轴
 *
 * 确定性三档：
 *   certain   明确记载 — 实心金色节点
 *   inferred  可推断   — 空心节点
 *   doubtful  存疑     — 赭红描边节点
 *
 * 降级：pass2 T7 未运行时所有事件 _timeline_inferred=true，
 * 节点统一显示为「推断」并在顶部给出等宽说明条。
 *
 * 数据源: /data/events.json
 */
import CitationBadge from './CitationBadge.jsx';

const CERTAINTY = {
  certain:  { label: '明确记载', tier: 'certain' },
  inferred: { label: '可推断',   tier: 'inferred' },
  doubtful: { label: '存疑',     tier: 'doubtful' },
};

function buildTimelineData(events) {
  if (!events || events.length === 0) return { displayEvents: [], inferredCount: 0 };

  const sorted = [...events].sort((a, b) => {
    const aHint = a.order_hint ?? 999;
    const bHint = b.order_hint ?? 999;
    if (aHint !== bHint) return aHint - bHint;
    return (a.stated_time || '').localeCompare(b.stated_time || '', 'zh');
  });

  const displayEvents = sorted.map((evt) => {
    const isInferred =
      evt._timeline_inferred === true ||
      evt.confidence === 'inferred' ||
      !evt.stated_time;
    const isDoubtful = evt.confidence === 'disputed';
    const certainty = isDoubtful ? 'doubtful' : isInferred ? 'inferred' : 'certain';

    return {
      id: evt.event_id || evt.name,
      date: evt.stated_time || '时间未记载',
      title: evt.name || evt.event_id || '未命名事件',
      description: evt.summary?.text?.substring(0, 160) || '',
      certainty,
      citations: evt.citations || evt.summary?.citations || [],
      sourceVolume: evt.source_volume || '',
      participants: evt.participants || [],
      locations: evt.locations || [],
    };
  });

  const inferredCount = displayEvents.filter((e) => e.certainty !== 'certain').length;
  return { displayEvents, inferredCount };
}

export default function Timeline({ events = null }) {
  const { displayEvents, inferredCount } = buildTimelineData(events);

  if (displayEvents.length === 0) {
    return (
      <div className="chrono-empty">
        <p>暂无编年史数据</p>
      </div>
    );
  }

  return (
    <div className="chrono">
      {inferredCount > 0 && (
        <div className="chrono-banner">
          <span className="mono">TIMING INFERRED</span>
          <span>
            {inferredCount}/{displayEvents.length} 个事件时序为推断
            （pass2 T7 时序补全未运行）
          </span>
        </div>
      )}

      <ol className="chrono-list">
        {displayEvents.map((evt, i) => {
          const c = CERTAINTY[evt.certainty];
          return (
            <li key={evt.id || i} className={`chrono-row is-${c.tier}`}>
              <span className="chrono-node" aria-hidden="true" />
              <article className="chrono-card">
                <div className="chrono-meta">
                  <time className="chrono-time mono">{evt.date}</time>
                  <span className={`chrono-tier mono tier-${c.tier}`}>{c.label}</span>
                </div>
                <h3 className="chrono-title">{evt.title}</h3>
                {evt.description && <p className="chrono-desc">{evt.description}</p>}
                {(evt.participants.length > 0 || evt.citations.length > 0) && (
                  <div className="chrono-foot">
                    {evt.participants.length > 0 && (
                      <span className="chrono-actors">
                        {evt.participants.slice(0, 4).join(' · ')}
                        {evt.participants.length > 4 ? ' · …' : ''}
                      </span>
                    )}
                    {evt.citations.length > 0 && (
                      <CitationBadge
                        citations={evt.citations}
                        claimText={evt.description}
                        sourceVolume={evt.sourceVolume}
                      />
                    )}
                  </div>
                )}
              </article>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
