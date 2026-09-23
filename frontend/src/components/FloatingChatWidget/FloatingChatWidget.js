import React, { useState, useCallback, useRef } from 'react';
import ChatWidget from '../ChatWidget';
import './FloatingChatWidget.css';

// ── Inline SVG icons ─────────────────────────────────────────────────────────

const ChatIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

const CloseIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

// ── FloatingChatWidget ───────────────────────────────────────────────────────

/**
 * FloatingChatWidget — A polished floating chat bubble that opens the
 * ChatWidget in a fixed-position window. Designed for embedding on any
 * bank website page.
 *
 * Props:
 *   triggerLabel  (string) — Text shown next to the chat icon. Default: "Chat with us"
 *   headerTitle   (string) — Title in the chat window header. Default: "Islamic Banking Assistant"
 *   headerStatus  (string) — Status text below the title. Default: "Online — typically replies instantly"
 */
export default function FloatingChatWidget({
  triggerLabel = 'Chat with us',
  headerTitle = 'Islamic Banking Assistant',
  headerStatus = 'Online — typically replies instantly',
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const windowRef = useRef(null);

  // ── Open handler ─────────────────────────────────────────────────────────

  const handleOpen = useCallback(() => {
    setIsClosing(false);
    setIsOpen(true);
  }, []);

  // ── Close handler with exit animation ────────────────────────────────────

  const handleClose = useCallback(() => {
    setIsClosing(true);
    // Wait for the CSS exit animation to finish before unmounting
    setTimeout(() => {
      setIsOpen(false);
      setIsClosing(false);
    }, 220); // matches fcwSlideDown duration
  }, []);

  // ── Toggle ───────────────────────────────────────────────────────────────

  const handleToggle = useCallback(() => {
    if (isOpen) {
      handleClose();
    } else {
      handleOpen();
    }
  }, [isOpen, handleOpen, handleClose]);

  return (
    <div className="fcw-wrapper" id="floating-chat-wrapper">
      {/* ── Chat Window ─────────────────────────────────────────────── */}
      {isOpen && (
        <div
          ref={windowRef}
          className={`fcw-window ${isClosing ? 'fcw-closing' : ''}`}
          id="floating-chat-window"
        >
          {/* Custom header with close button */}
          <div className="fcw-header">
            <div className="fcw-header-icon">🏦</div>
            <div className="fcw-header-text">
              <div className="fcw-header-title">{headerTitle}</div>
              <div className="fcw-header-status">
                <span className="fcw-status-dot" />
                {headerStatus}
              </div>
            </div>
            <button
              className="fcw-close-btn"
              onClick={handleClose}
              title="Close chat"
              id="floating-chat-close-btn"
            >
              <CloseIcon />
            </button>
          </div>

          {/* The actual ChatWidget (non-floating mode, header hidden via CSS) */}
          <ChatWidget floating={false} />
        </div>
      )}

      {/* ── Trigger Button ──────────────────────────────────────────── */}
      <button
        className="fcw-trigger"
        onClick={handleToggle}
        title={isOpen ? 'Close chat' : 'Chat with us'}
        id="floating-chat-trigger"
      >
        <span className="fcw-trigger-icon">
          {isOpen ? <CloseIcon /> : <ChatIcon />}
        </span>
        <span className="fcw-trigger-label">{isOpen ? 'Close' : triggerLabel}</span>
      </button>
    </div>
  );
}
