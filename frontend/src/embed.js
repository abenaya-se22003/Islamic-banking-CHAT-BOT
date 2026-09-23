/**
 * embed.js — Standalone entry point for embedding the Islamic Banking
 * chatbot widget on any website via a single <script> tag.
 *
 * Usage on a non-React site:
 *   <div id="chatbot-root"></div>
 *   <script src="path/to/chatbot-widget.js"></script>
 *
 * This script auto-renders the FloatingChatWidget into #chatbot-root.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import FloatingChatWidget from './components/FloatingChatWidget';

// Configurable mount-point ID
const MOUNT_ID = 'chatbot-root';

function mount() {
  let container = document.getElementById(MOUNT_ID);

  // Auto-create the container if it doesn't exist
  if (!container) {
    container = document.createElement('div');
    container.id = MOUNT_ID;
    document.body.appendChild(container);
  }

  const root = ReactDOM.createRoot(container);
  root.render(
    <React.StrictMode>
      <FloatingChatWidget />
    </React.StrictMode>
  );
}

// Mount when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mount);
} else {
  mount();
}
