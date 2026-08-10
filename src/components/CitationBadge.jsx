/**
 * 引证标记与弹出 — 点击后并排展示结论文本 / 原文 quote / cite_id / 所属卷
 */
import { useState, useRef, useEffect } from 'react';

export default function CitationBadge({ citations = [], claimText = '', sourceVolume = '', position = 'inline' }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    function onClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  if (!citations || citations.length === 0) return null;

  const firstCite = citations[0];
  const citeId = firstCite?.cite_id || '—';
  const quote = firstCite?.quote || '';

  return (
    <span ref={ref} className="cite-badge-wrap" style={{ position: 'relative', display: position === 'inline' ? 'inline' : 'block' }}>
      <button className="cite-badge" onClick={() => setOpen(!open)} title={`引证: ${citeId}`} type="button">
        <span className="cite-icon" aria-hidden="true">¶</span>
        <span className="cite-label">{citeId}</span>
      </button>

      {open && (
        <div className="cite-popup" role="dialog" aria-label="引证详情">
          <div className="cite-popup-section">
            <div className="cite-popup-label">结论文本</div>
            <div className="cite-popup-text">{claimText || '(无结论文本)'}</div>
          </div>
          <div className="cite-popup-section">
            <div className="cite-popup-label">原文引用</div>
            <div className="cite-popup-quote">「{quote || '(无原文引用)'}」</div>
          </div>
          <div className="cite-popup-meta">
            <span>cite_id: {citeId}</span>
            {sourceVolume && <span>卷: {sourceVolume}</span>}
            {citations.length > 1 && <span>+{citations.length - 1} 条更多引证</span>}
          </div>
        </div>
      )}
    </span>
  );
}
