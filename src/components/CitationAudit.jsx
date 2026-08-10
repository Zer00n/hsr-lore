/**
 * 引证审计台 — 全站最重要的一屏
 *
 * 随机抽取一条带引证的结论，并排展示「模型结论」↔「原文片段」。
 *
 * 核验：claim 携带的 quote 是否与引证索引中登记给该 cite_id 的 quote 一致。
 * 这是前端可在不随站发布语料全文的前提下完成的完整性校验；
 * quote 对语料 clean 全文的逐字匹配在构建期由校验脚本完成。
 *
 * 数据源: /data/citations.json（cite_id -> {cite_id, quote, volume}）
 */
import { useState, useMemo, useEffect, useCallback } from 'react';

// 收集所有带引证的结论
function collectClaims(data) {
  const claims = [];
  if (!data) return claims;

  const addClaim = (claimText, citeId, quote, sourceVolume, kind) => {
    if (citeId && claimText) {
      claims.push({
        claimText: String(claimText).slice(0, 240),
        citeId,
        quote: String(quote || '').slice(0, 320),
        sourceVolume: String(sourceVolume || ''),
        kind,
      });
    }
  };

  (data.entities || []).forEach((e) => {
    const sv = e.source_volume || (e._source_volumes && e._source_volumes[0]) || '';
    if (e.summary?.citations)
      e.summary.citations.forEach((c) => addClaim(e.summary.text, c.cite_id, c.quote, sv, `实体 · ${e.canonical_name}`));
    (e.attributes || []).forEach((a) => {
      if (a.citations) a.citations.forEach((c) => addClaim(`${a.key}：${a.value}`, c.cite_id, c.quote, sv, `属性 · ${e.canonical_name}`));
    });
  });

  (data.relations || []).forEach((r) => {
    const sv = r.source_volume || '';
    if (r.citations)
      r.citations.forEach((c) =>
        addClaim(`${r.subject_name || r.subject_id} ${r.predicate} ${r.object_name || r.object_id}`, c.cite_id, c.quote, sv, '关系')
      );
  });

  (data.events || []).forEach((e) => {
    const sv = e.source_volume || '';
    (e.citations || []).forEach((c) => addClaim(e.summary?.text || e.name, c.cite_id, c.quote, sv, `事件 · ${e.name}`));
  });

  (data.discrepancies || []).forEach((d) => {
    (d.statements || []).forEach((s) => {
      if (s.citation) addClaim(s.text, s.citation.cite_id, s.citation.quote, '', `矛盾 · ${d.topic}`);
    });
    if (d.analysis?.citations)
      d.analysis.citations.forEach((c) => addClaim(d.analysis.text, c.cite_id, c.quote, '', `分析 · ${d.topic}`));
  });

  return claims;
}

// 把 claim quote 在登记原文中高亮（金色底）
function highlightQuote(quote, fullText) {
  if (!quote || !fullText) return fullText || '';
  const idx = fullText.indexOf(quote);
  if (idx === -1) return fullText;
  return (
    fullText.slice(0, idx) +
    '<mark>' + fullText.slice(idx, idx + quote.length) + '</mark>' +
    fullText.slice(idx + quote.length)
  );
}

export default function CitationAudit({ cache = {} }) {
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  const [tally, setTally] = useState({ match: 0, mismatch: 0, unverified: 0 });

  const allClaims = useMemo(() => collectClaims(cache), [cache]);

  // citations.json 可能是数组或 map；统一建 cite_id 索引
  const citeIndex = useMemo(() => {
    const raw = cache.citations;
    const idx = new Map();
    if (Array.isArray(raw)) {
      raw.forEach((c) => { if (c && c.cite_id) idx.set(c.cite_id, c); });
    } else if (raw && typeof raw === 'object') {
      Object.values(raw).forEach((c) => { if (c && c.cite_id) idx.set(c.cite_id, c); });
    }
    return idx;
  }, [cache.citations]);

  const doRandom = useCallback(() => {
    if (allClaims.length === 0) return;
    const claim = allClaims[Math.floor(Math.random() * allClaims.length)];
    const entry = citeIndex.get(claim.citeId);
    const registered = entry?.quote ?? '';
    const volume = claim.sourceVolume || entry?.volume || '';

    // claim 附 quote 与登记 quote 逐字一致即完整；若登记无 quote（旧数据）记为 unknown
    let verdict = 'unknown';
    if (claim.quote && registered) {
      verdict = claim.quote === registered ? 'match' : 'mismatch';
    } else if (claim.quote) {
      verdict = 'unverified';
    }

    setCurrent({ ...claim, registered, volume, verdict });
    setHistory((prev) => [{ citeId: claim.citeId, verdict }, ...prev].slice(0, 12));
    if (verdict === 'match' || verdict === 'mismatch' || verdict === 'unverified') {
      setTally((prev) => ({ ...prev, [verdict]: prev[verdict] + 1 }));
    }
  }, [allClaims, citeIndex]);

  useEffect(() => {
    if (allClaims.length > 0 && !current) doRandom();
  }, [allClaims, current, doRandom]);

  return (
    <div className="audit">
      <header className="audit-topbar">
        <div>
          <h2 className="audit-title">引证审计台</h2>
          <p className="audit-sub">
            从 <span className="mono">{allClaims.length.toLocaleString()}</span> 条带引证结论中随机抽查，核对结论所引片段与登记原文是否一致。
          </p>
        </div>
        <button onClick={doRandom} className="audit-reroll" disabled={allClaims.length === 0}>
          <span className="audit-reroll-glyph" aria-hidden="true">⟳</span>
          随机抽查
        </button>
      </header>

      <div className="audit-result">
        {allClaims.length === 0 ? (
          <div className="audit-empty">
            <span className="audit-empty-mark" aria-hidden="true" />
            <h3>暂无数据可审计</h3>
            <p>
              引证审计台随机抽查结论的引证是否与原文登记一致。当前数据管线尚未完成，
              正式数据接入后此处将逐条展示结论与原文的对照核验。
            </p>
          </div>
        ) : !current ? (
          <p className="audit-loading">正在收集引证数据…</p>
        ) : (
          <>
            <div className="audit-compare">
              <section className="audit-pane audit-pane-claim">
                <div className="audit-pane-label mono">模型结论</div>
                <div className="audit-kind">{current.kind}</div>
                <p className="audit-claim-text">{current.claimText}</p>
              </section>

              <section className="audit-pane audit-pane-source">
                <div className="audit-pane-label mono">原文片段</div>
                <div className="audit-citeid">
                  <span className="mono">{current.citeId}</span>
                  {current.volume && <span className="audit-volume mono">{current.volume}</span>}
                </div>
                <p
                  className="audit-source-text"
                  dangerouslySetInnerHTML={{ __html: highlightQuote(current.quote, current.registered || current.quote) }}
                />
              </section>
            </div>

            <div className={`audit-verdict verdict-${current.verdict}`} role="status">
              <span className="audit-verdict-glyph" aria-hidden="true">
                {current.verdict === 'match' ? '✓' : current.verdict === 'mismatch' ? '✕' : '?'}
              </span>
              <span className="audit-verdict-text">
                {current.verdict === 'match' && '引证一致'}
                {current.verdict === 'mismatch' && '引证不一致'}
                {current.verdict === 'unverified' && '未登记全文，无法比对'}
                {current.verdict === 'unknown' && '无引证片段'}
              </span>
              <span className="audit-verdict-cite mono">{current.citeId}</span>
            </div>

            {(tally.match + tally.mismatch + tally.unverified) > 0 && (
              <div className="audit-tally mono">
                本次会话抽查 {tally.match + tally.mismatch + tally.unverified} 次
                <span className="tally-sep">·</span>
                <span className="tally-match">一致 {tally.match}</span>
                <span className="tally-sep">·</span>
                <span className="tally-mismatch">不一致 {tally.mismatch}</span>
                {tally.unverified > 0 && (
                  <>
                    <span className="tally-sep">·</span>
                    <span className="tally-unknown">未登记 {tally.unverified}</span>
                  </>
                )}
              </div>
            )}

            <p className="audit-note">
              quote 对语料全文的逐字 substring 校验在构建期由校验脚本执行；此处核对结论引用片段与引证登记的一致性。
            </p>

            {history.length > 1 && (
              <div className="audit-history">
                <span className="audit-history-label mono">最近抽查</span>
                {history.slice(0, 8).map((h, i) => (
                  <span key={i} className={`audit-history-item history-${h.verdict} mono`} title={h.citeId}>
                    {h.verdict === 'match' ? '✓' : h.verdict === 'mismatch' ? '✕' : '?'} {h.citeId}
                  </span>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
