/**
 * 引证审计台 — 交互式抽查。每次随机取一条带引证的结论，
 * 并排展示结论文本 ↔ 原文 quote，显示匹配状态。
 */
import { useState, useMemo, useEffect } from 'react';

// 收集所有带引证的条目
function collectClaims(data) {
  const claims = [];
  if (!data) return claims;

  const addClaim = (claimText, citeId, quote, sourceVolume, kind) => {
    if (citeId && claimText) {
      claims.push({ claimText: String(claimText).slice(0, 200), citeId, quote: String(quote || '').slice(0, 300), sourceVolume: String(sourceVolume || ''), kind });
    }
  };

  // entities
  (data.entities || []).forEach((e) => {
    const sv = e.source_volume || (e._source_volumes && e._source_volumes[0]) || '';
    if (e.summary?.citations)
      e.summary.citations.forEach((c) => addClaim(e.summary.text, c.cite_id, c.quote, sv, `实体「${e.canonical_name}」简介`));
    (e.attributes || []).forEach((a) => {
      if (a.citations) a.citations.forEach((c) => addClaim(`${a.key}: ${a.value}`, c.cite_id, c.quote, sv, `实体「${e.canonical_name}」属性`));
    });
  });

  // relations
  (data.relations || []).forEach((r) => {
    const sv = r.source_volume || '';
    if (r.citations)
      r.citations.forEach((c) =>
        addClaim(`${r.subject_name || r.subject_id} ${r.predicate} ${r.object_name || r.object_id}`, c.cite_id, c.quote, sv, '关系')
      );
  });

  // events
  (data.events || []).forEach((e) => {
    const sv = e.source_volume || '';
    (e.citations || []).forEach((c) => addClaim(e.summary?.text || e.name, c.cite_id, c.quote, sv, `事件「${e.name}」`));
  });

  // discrepancies
  (data.discrepancies || []).forEach((d) => {
    (d.statements || []).forEach((s) => {
      if (s.citation) addClaim(s.text, s.citation.cite_id, s.citation.quote, '', `矛盾「${d.topic}」陈述`);
    });
    if (d.analysis?.citations)
      d.analysis.citations.forEach((c) => addClaim(d.analysis.text, c.cite_id, c.quote, '', `矛盾「${d.topic}」分析`));
  });

  return claims;
}

function highlightQuote(quote, fullText) {
  if (!quote || !fullText) return fullText || '';
  const idx = fullText.indexOf(quote);
  if (idx === -1) {
    // fuzzy: try first 20 chars of quote
    const short = quote.slice(0, 20);
    const idx2 = fullText.indexOf(short);
    if (idx2 === -1) return fullText;
    return fullText.slice(0, idx2) + '<mark>' + fullText.slice(idx2, idx2 + quote.length) + '</mark>' + fullText.slice(idx2 + quote.length);
  }
  return fullText.slice(0, idx) + '<mark>' + fullText.slice(idx, idx + quote.length) + '</mark>' + fullText.slice(idx + quote.length);
}

export default function CitationAudit({ cache = {} }) {
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  const [matchResult, setMatchResult] = useState(null);
  const [isMock, setIsMock] = useState(false);

  const allClaims = useMemo(() => collectClaims(cache), [cache]);

  // Check for citations index data
  const citationsIdx = cache.citations || {};
  const hasFullText = Object.keys(citationsIdx).length > 0;

  const doRandom = () => {
    if (allClaims.length === 0) return;
    const idx = Math.floor(Math.random() * allClaims.length);
    const claim = allClaims[idx];

    // Look up full text from citations index
    const citeEntry = citationsIdx[claim.citeId];
    const fullClean = citeEntry?.clean || citeEntry?.quote || claim.quote;
    const quote = claim.quote;

    // Check if quote is in the full text
    const isMatch = quote && fullClean && fullClean.includes(quote);

    setCurrent({ ...claim, fullClean });
    setMatchResult({ match: !!isMatch, citeId: claim.citeId, sourceVolume: claim.sourceVolume || (citeEntry?.volume || '') });
    setHistory((prev) => [claim.citeId, ...prev].slice(0, 20));

    // Check if this is mock data
    if (citeEntry && !citeEntry.clean && citeEntry.quote && citeEntry.quote.length < 40) {
      setIsMock(true);
    }
  };

  // Auto-run first spot check
  useEffect(() => {
    if (allClaims.length > 0 && !current) doRandom();
  }, [allClaims]);

  // Inject highlight marker style
  useEffect(() => {
    if (typeof document === 'undefined') return;
    if (document.getElementById('audit-mark-style')) return;
    const style = document.createElement('style');
    style.id = 'audit-mark-style';
    style.textContent = 'mark { background: var(--warning); color: var(--bg-base); border-radius: 2px; padding: 0 2px; }';
    document.head.appendChild(style);
  }, []);

  return (
    <div className="audit-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Top bar */}
      <div className="audit-topbar" style={{ padding: 'var(--space-4)', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div>
          <h2 className="audit-title" style={{ fontSize: 'var(--text-lg)', fontWeight: 700, margin: 0 }}>引证审计台</h2>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', margin: '4px 0 0' }}>
            从 {allClaims.length.toLocaleString()} 条带引证结论中随机抽查
          </p>
        </div>
        <button
          onClick={doRandom}
          className="audit-reroll-btn"
          style={{
            background: 'var(--accent)', color: 'var(--bg-base)', border: 'none',
            padding: 'var(--space-3) var(--space-5)', borderRadius: 'var(--radius-md)',
            fontWeight: 600, fontSize: 'var(--text-sm)', cursor: 'pointer',
          }}
        >
          随机抽查
        </button>
      </div>

      {/* Result area */}
      <div className="audit-result" style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-5)' }}>
        {allClaims.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center', gap: 'var(--space-4)', padding: 'var(--space-8)' }}>
            <img src="/images/empty-state.png" alt="" style={{ width: '200px', height: '150px', objectFit: 'contain', opacity: 0.6 }} />
            <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, color: 'var(--text-primary)' }}>暂无数据可审计</h3>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', maxWidth: '480px', lineHeight: 'var(--leading-relaxed)' }}>
              引证审计台用于随机抽查结论的引证是否与游戏原文逐字匹配。
              当前数据管线尚未运行完成，待正式数据接入后，这里将展示每一条结论与原文的对照验证。
            </p>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              提示：每个结论旁的金色 ¶ 标记可随时点击查看引证详情。
            </p>
          </div>
        ) : !current ? (
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: 'var(--space-12)' }}>正在收集引证数据…</p>
        ) : (
          <>
            {/* Claim + Original side by side */}
            <div className="audit-compare" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-5)', marginBottom: 'var(--space-5)' }}>
              {/* Left: claim */}
              <div className="audit-left" style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-4)' }}>
                <div className="audit-section-label" style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }}>模型结论文本</div>
                <div className="audit-kind-badge" style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)', marginBottom: 'var(--space-2)' }}>{current.kind}</div>
                <p style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-relaxed)', color: 'var(--text-primary)' }}>{current.claimText}</p>
              </div>

              {/* Right: original */}
              <div className="audit-right" style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--space-4)' }}>
                <div className="audit-section-label" style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }}>语料原文 {isMock && <span style={{ color: 'var(--text-muted)' }}>（未找到完整原文）</span>}</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }}>cite_id: {current.citeId}</div>
                <p
                  style={{ fontSize: 'var(--text-sm)', lineHeight: 'var(--leading-relaxed)', color: 'var(--text-secondary)' }}
                  dangerouslySetInnerHTML={{ __html: highlightQuote(current.quote, current.fullClean) }}
                />
              </div>
            </div>

            {/* Match status */}
            <div className="audit-verdict" style={{
              padding: 'var(--space-4)', borderRadius: 'var(--radius-md)',
              background: matchResult?.match ? 'var(--success)' : 'var(--danger)',
              color: matchResult?.match ? 'var(--bg-base)' : 'var(--bg-base)',
              fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--space-4)',
            }}>
              {matchResult?.match ? '✓ 引证匹配' : '✗ 引证未匹配'} — cite_id: {matchResult?.citeId}
              {matchResult?.sourceVolume && <span> · 卷: {matchResult.sourceVolume}</span>}
            </div>

            {/* History */}
            {history.length > 1 && (
              <div className="audit-history" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                最近抽查：{history.slice(0, 10).join(' → ')}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
