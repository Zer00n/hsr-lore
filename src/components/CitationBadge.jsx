/**
 * 引证标记与弹出 — Portal 渲染到 body，不受卡片 overflow/z-index 限制
 * 定位: position: fixed + getBoundingClientRect() 计算坐标
 * 边界: 视口底部翻转向上、右边缘左对齐
 * 关闭: 点击外部 / Esc / 滚动 / resize
 */
import { useState, useRef, useEffect, useCallback, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';

const POPOVER_Z = 1000;
const VIEWPORT_MARGIN = 12;

function computePosition(anchorRect, popW, popH) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  let left = anchorRect.left;
  let top = anchorRect.bottom + 8;

  // Flip up if would overflow bottom
  if (top + popH + VIEWPORT_MARGIN > vh) {
    top = anchorRect.top - popH - 8;
  }
  // If still off-screen (very tall popup), pin to top
  if (top < VIEWPORT_MARGIN) top = VIEWPORT_MARGIN;

  // Shift left if would overflow right
  if (left + popW + VIEWPORT_MARGIN > vw) {
    left = vw - popW - VIEWPORT_MARGIN;
  }
  if (left < VIEWPORT_MARGIN) left = VIEWPORT_MARGIN;

  return { left, top };
}

export default function CitationBadge({ citations = [], claimText = '', sourceVolume = '', position = 'inline' }) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState(null);
  const anchorRef = useRef(null);
  const popupRef = useRef(null);

  // Recalculate position when open
  const updatePosition = useCallback(() => {
    if (!anchorRef.current || !popupRef.current) return;
    const anchorRect = anchorRef.current.getBoundingClientRect();
    const popRect = popupRef.current.getBoundingClientRect();
    setCoords(computePosition(anchorRect, popRect.width, popRect.height));
  }, []);

  useLayoutEffect(() => {
    if (open) updatePosition();
  }, [open, updatePosition]);

  // Close on scroll / resize
  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    window.addEventListener('scroll', close, true);
    window.addEventListener('resize', close);
    return () => {
      window.removeEventListener('scroll', close, true);
      window.removeEventListener('resize', close);
    };
  }, [open]);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    function onClick(e) {
      if (anchorRef.current && !anchorRef.current.contains(e.target) &&
          popupRef.current && !popupRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  // Close on Esc
  useEffect(() => {
    if (!open) return;
    function onKey(e) { if (e.key === 'Escape') setOpen(false); }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  if (!citations || citations.length === 0) return null;

  const firstCite = citations[0];
  const citeId = firstCite?.cite_id || '—';
  const quote = firstCite?.quote || '';

  const popup = open && coords ? createPortal(
    <div
      ref={popupRef}
      className="cite-popup"
      role="dialog"
      aria-label="引证详情"
      style={{
        position: 'fixed',
        left: coords.left,
        top: coords.top,
        zIndex: POPOVER_Z,
      }}
    >
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
    </div>,
    document.body
  ) : null;

  return (
    <span ref={anchorRef} className="cite-badge-wrap" style={{ position: 'relative', display: position === 'inline' ? 'inline' : 'block' }}>
      <button className="cite-badge" onClick={() => setOpen(!open)} title={`引证: ${citeId}`} type="button">
        <span className="cite-icon" aria-hidden="true">¶</span>
        <span className="cite-label">{citeId}</span>
      </button>
      {popup}
    </span>
  );
}
