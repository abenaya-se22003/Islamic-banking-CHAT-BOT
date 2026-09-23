import React, { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';
import './ChatWidget.css';

// ── Inline SVG icons (avoids external dependencies) ──────────────────────────

const SendIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

const DownloadIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

// ── Constants ────────────────────────────────────────────────────────────────

const API_URL = 'http://localhost:8000/chat';

// ── Helper: format time ──────────────────────────────────────────────────────

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ── Sub-components ───────────────────────────────────────────────────────────

/** Bot avatar shown beside bot messages */
function BotAvatar() {
  return <div className="cw-avatar">🏦</div>;
}

/** Welcome message shown when no messages yet */
function WelcomeMessage() {
  return (
    <div className="cw-welcome">
      <div className="cw-welcome-icon">☪️</div>
      <h3>Assalamu Alaikum!</h3>
      <p>
        I'm your Islamic Banking Assistant. Ask me about Shariah-compliant
        products, Murabaha, Ijara, Sukuk, or any banking query.
      </p>
    </div>
  );
}

/** Typing indicator (three bouncing dots) */
function TypingIndicator() {
  return (
    <div className="cw-typing-row">
      <BotAvatar />
      <div className="cw-typing-bubble">
        <span className="cw-typing-dot" />
        <span className="cw-typing-dot" />
        <span className="cw-typing-dot" />
      </div>
    </div>
  );
}

/** Sources tags shown under a bot message */
function SourcesList({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="cw-sources">
      <div className="cw-sources-label">Sources</div>
      <div className="cw-sources-list">
        {sources.map((src, i) => (
          <span key={i} className="cw-source-tag">{src}</span>
        ))}
      </div>
    </div>
  );
}

/** Download report button shown when a report_url is available */
function ReportButton({ url }) {
  if (!url) return null;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="cw-report-btn"
    >
      <DownloadIcon />
      Download Report
    </a>
  );
}

/** Single message bubble */
function MessageBubble({ message }) {
  const isUser = message.sender === 'user';
  const isError = message.sender === 'error';

  if (isError) {
    return (
      <div className="cw-error-bubble">
        <span className="cw-error-icon">⚠️</span>
        <div>
          <div>{message.text}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`cw-msg-row ${isUser ? 'user' : 'bot'}`}>
      {!isUser && <BotAvatar />}
      <div>
        <div className={`cw-bubble ${isUser ? 'user' : 'bot'}`}>
          {message.text}
          {!isUser && <SourcesList sources={message.sources} />}
          {!isUser && <ReportButton url={message.report_url} />}
        </div>
        <div className="cw-timestamp">{formatTime(message.timestamp)}</div>
      </div>
    </div>
  );
}

// ── Main ChatWidget Component ────────────────────────────────────────────────

/**
 * ChatWidget — A self-contained chat component for the Islamic Banking
 * Assistant. Connects to a FastAPI backend at POST /chat.
 *
 * Props:
 *   floating  (bool)   — if true, renders as a floating bottom-right widget
 *                          with a toggle button. Default: false.
 */
export default function ChatWidget({ floating = false }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(!floating); // open by default in non-floating mode

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // ── Auto-scroll to bottom when messages change ───────────────────────────

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  // ── Focus input when widget opens ────────────────────────────────────────

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // ── Send message handler ─────────────────────────────────────────────────

  const sendMessage = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    // Add user message
    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: trimmed,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(API_URL, { question: trimmed });
      const data = response.data;

      const botMsg = {
        id: Date.now() + 1,
        sender: 'bot',
        text: data.answer || 'I received your message but have no answer at this time.',
        sources: data.sources || [],
        report_url: data.report_url || null,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (error) {
      let errorText = 'Sorry, I couldn\'t reach the server. Please check your connection and try again.';

      if (error.response) {
        // Server responded with an error status
        errorText = `Server error (${error.response.status}). Please try again later.`;
      } else if (error.code === 'ERR_NETWORK') {
        errorText = 'Unable to connect to the server. Please make sure the backend is running.';
      }

      const errorMsg = {
        id: Date.now() + 1,
        sender: 'error',
        text: errorText,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading]);

  // ── Key press handler (Enter to send) ────────────────────────────────────

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // ── Chat window UI ──────────────────────────────────────────────────────

  const chatWindow = (
    <div className="cw-container" id="chat-widget-container">
      {/* Header */}
      <div className="cw-header">
        <div className="cw-header-icon">🏦</div>
        <div className="cw-header-info">
          <div className="cw-header-title">Islamic Banking Assistant</div>
          <div className="cw-header-subtitle">Shariah-compliant financial guidance</div>
        </div>
      </div>

      {/* Messages */}
      <div className="cw-messages" id="chat-messages">
        {messages.length === 0 && !isLoading && <WelcomeMessage />}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isLoading && <TypingIndicator />}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="cw-input-area">
        <input
          ref={inputRef}
          type="text"
          className="cw-input"
          id="chat-input"
          placeholder="Type your question..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          autoComplete="off"
        />
        <button
          className="cw-send-btn"
          id="chat-send-btn"
          onClick={sendMessage}
          disabled={!input.trim() || isLoading}
          title="Send message"
        >
          <SendIcon />
        </button>
      </div>
    </div>
  );

  // ── Floating mode wraps the chat window + toggle button ──────────────────

  if (floating) {
    return (
      <div className="cw-floating-wrapper" id="chat-floating-wrapper">
        {isOpen && chatWindow}
        <button
          className="cw-toggle-btn"
          id="chat-toggle-btn"
          onClick={() => setIsOpen(!isOpen)}
          title={isOpen ? 'Close chat' : 'Open chat'}
        >
          {isOpen ? '✕' : '💬'}
        </button>
      </div>
    );
  }

  return chatWindow;
}
