// Session Storage Helper for LOLC Al-Falaah Chatbot

const SESSIONS_KEY = 'lolc_chat_sessions';
const ACTIVE_SESSION_KEY = 'lolc_active_session_id';
const THEME_KEY = 'lolc_chat_theme';

export function createNewSession(initialTitle = 'New Conversation') {
  return {
    id: 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7),
    title: initialTitle,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    messages: [],
  };
}

export function loadSessions() {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    console.error('Failed to load sessions from localStorage', e);
    return [];
  }
}

export function saveSessions(sessions) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
  } catch (e) {
    console.error('Failed to save sessions to localStorage', e);
  }
}

export function loadActiveSessionId() {
  return localStorage.getItem(ACTIVE_SESSION_KEY) || null;
}

export function saveActiveSessionId(id) {
  if (id) {
    localStorage.setItem(ACTIVE_SESSION_KEY, id);
  } else {
    localStorage.removeItem(ACTIVE_SESSION_KEY);
  }
}

export function loadTheme() {
  return localStorage.getItem(THEME_KEY) || 'dark';
}

export function saveTheme(theme) {
  localStorage.setItem(THEME_KEY, theme);
}

export function generateTitleFromMessage(message) {
  if (!message) return 'New Conversation';
  const clean = message.trim().replace(/^[\W_]+/, '');
  if (clean.length <= 32) return clean;
  return clean.substring(0, 30) + '...';
}
