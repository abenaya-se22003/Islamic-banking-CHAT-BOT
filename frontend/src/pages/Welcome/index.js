import React, { useState, useEffect } from 'react';
import styled, { ThemeProvider } from 'styled-components';
import axios from 'axios';

import GlobalStyles from '../../assets/styles/global';
import { darkTheme, lightTheme } from '../../theme';
import Sidebar from '../../components/Sidebar';
import ChatPanel from '../../components/ChatPanel';
import {
  createNewSession,
  loadSessions,
  saveSessions,
  loadActiveSessionId,
  saveActiveSessionId,
  loadTheme,
  saveTheme,
  generateTitleFromMessage,
} from '../../services/sessionStorage';

const AppLayout = styled.div`
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: ${({ theme }) => theme.bg};
`;

const MobileBackdrop = styled.div`
  display: none;

  @media (max-width: 768px) {
    display: ${({ isOpen }) => (isOpen ? 'block' : 'none')};
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    z-index: 25;
  }
`;

const API_ENDPOINT = 'http://localhost:8000/chat';

export default function Welcome() {
  const [themeMode, setThemeMode] = useState(loadTheme());
  const [sessions, setSessions] = useState(() => {
    const loaded = loadSessions();
    if (loaded && loaded.length > 0) return loaded;
    const initial = createNewSession();
    saveSessions([initial]);
    return [initial];
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    const savedId = loadActiveSessionId();
    if (savedId && sessions.some((s) => s.id === savedId)) {
      return savedId;
    }
    return sessions[0]?.id || null;
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Sync activeSessionId with storage
  useEffect(() => {
    if (activeSessionId) {
      saveActiveSessionId(activeSessionId);
    }
  }, [activeSessionId]);

  // Sync sessions with storage
  useEffect(() => {
    saveSessions(sessions);
  }, [sessions]);

  // Active session object
  const activeSession =
    sessions.find((s) => s.id === activeSessionId) || sessions[0] || null;

  const handleToggleTheme = () => {
    const nextMode = themeMode === 'dark' ? 'light' : 'dark';
    setThemeMode(nextMode);
    saveTheme(nextMode);
  };

  const handleNewChat = () => {
    const newSession = createNewSession();
    const updated = [newSession, ...sessions];
    setSessions(updated);
    setActiveSessionId(newSession.id);
  };

  const handleSelectSession = (id) => {
    setActiveSessionId(id);
  };

  const handleDeleteSession = (id) => {
    const remaining = sessions.filter((s) => s.id !== id);
    if (remaining.length === 0) {
      const fresh = createNewSession();
      setSessions([fresh]);
      setActiveSessionId(fresh.id);
    } else {
      setSessions(remaining);
      if (activeSessionId === id) {
        setActiveSessionId(remaining[0].id);
      }
    }
  };

  const handleRenameSession = (id, newTitle) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title: newTitle, updatedAt: new Date().toISOString() } : s))
    );
  };

  const handleClearAllSessions = () => {
    if (window.confirm('Are you sure you want to clear all chat conversations?')) {
      const fresh = createNewSession();
      setSessions([fresh]);
      setActiveSessionId(fresh.id);
    }
  };

  const handleClearMessages = () => {
    if (!activeSessionId) return;
    setSessions((prev) =>
      prev.map((s) => (s.id === activeSessionId ? { ...s, messages: [], updatedAt: new Date().toISOString() } : s))
    );
  };

  const handleSendMessage = async (text) => {
    if (!text || !text.trim() || isLoading) return;

    let targetSessionId = activeSessionId;
    if (!targetSessionId || !sessions.some((s) => s.id === targetSessionId)) {
      const newSession = createNewSession();
      setSessions((prev) => [newSession, ...prev]);
      targetSessionId = newSession.id;
      setActiveSessionId(newSession.id);
    }

    const userMessage = {
      id: 'msg_' + Date.now(),
      sender: 'user',
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    // Update sessions with user message
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === targetSessionId) {
          const isFirstMessage = s.messages.length === 0;
          const autoTitle = isFirstMessage ? generateTitleFromMessage(text) : s.title;
          return {
            ...s,
            title: autoTitle,
            updatedAt: new Date().toISOString(),
            messages: [...s.messages, userMessage],
          };
        }
        return s;
      })
    );

    setIsLoading(true);

    // Create a placeholder bot message that will be updated with streaming tokens
    const botMessageId = 'msg_bot_' + Date.now();
    const botMessage = {
      id: botMessageId,
      sender: 'assistant',
      text: '',
      sources: [],
      reportUrl: null,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isStreaming: true,
    };

    // Add empty bot message immediately (will be filled by stream)
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === targetSessionId) {
          return {
            ...s,
            updatedAt: new Date().toISOString(),
            messages: [...s.messages, botMessage],
          };
        }
        return s;
      })
    );

    try {
      const STREAM_ENDPOINT = 'http://localhost:8000/chat/stream';
      const response = await fetch(STREAM_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text.trim() }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedText = '';
      let streamSources = [];
      let streamReportUrl = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        let eventType = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const rawData = line.slice(6);
            try {
              const data = JSON.parse(rawData);

              if (eventType === 'token' && data.text) {
                accumulatedText += data.text;
                // Update the bot message in real-time
                setSessions((prev) =>
                  prev.map((s) => {
                    if (s.id === targetSessionId) {
                      return {
                        ...s,
                        messages: s.messages.map((m) =>
                          m.id === botMessageId
                            ? { ...m, text: accumulatedText }
                            : m
                        ),
                      };
                    }
                    return s;
                  })
                );
              } else if (eventType === 'sources' && data.sources) {
                streamSources = data.sources;
              } else if (eventType === 'report' && data.url) {
                streamReportUrl = data.url;
              } else if (eventType === 'error' && data.error) {
                accumulatedText += `\n\n⚠️ Error: ${data.error}`;
              }
            } catch {
              // Ignore JSON parse errors for incomplete data
            }
            eventType = '';
          }
        }
      }

      // Finalize the bot message (remove streaming flag, add sources)
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === targetSessionId) {
            return {
              ...s,
              updatedAt: new Date().toISOString(),
              messages: s.messages.map((m) =>
                m.id === botMessageId
                  ? {
                      ...m,
                      text: accumulatedText || 'No response generated.',
                      sources: streamSources,
                      reportUrl: streamReportUrl,
                      isStreaming: false,
                    }
                  : m
              ),
            };
          }
          return s;
        })
      );
    } catch (err) {
      console.error('Chat Stream Error:', err);
      let errorText =
        '⚠️ An error occurred while communicating with the Al-Falaah assistant. Please verify the backend server is running.';

      if (err.message && err.message.includes('Server error')) {
        errorText = `⚠️ ${err.message}`;
      }

      // Update the bot message with error, or add a new error message
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === targetSessionId) {
            const hasBotMsg = s.messages.some((m) => m.id === botMessageId);
            if (hasBotMsg) {
              return {
                ...s,
                messages: s.messages.map((m) =>
                  m.id === botMessageId
                    ? { ...m, text: errorText, isStreaming: false }
                    : m
                ),
              };
            } else {
              return {
                ...s,
                messages: [
                  ...s.messages,
                  {
                    id: 'msg_err_' + Date.now(),
                    sender: 'assistant',
                    text: errorText,
                    sources: [],
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                  },
                ],
              };
            }
          }
          return s;
        })
      );
    } finally {
      setIsLoading(false);
    }
  };

  const currentTheme = themeMode === 'dark' ? darkTheme : lightTheme;

  return (
    <ThemeProvider theme={currentTheme}>
      <GlobalStyles />
      <AppLayout>
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewChat={handleNewChat}
          onDeleteSession={handleDeleteSession}
          onRenameSession={handleRenameSession}
          onClearAllSessions={handleClearAllSessions}
          themeMode={themeMode}
          onToggleTheme={handleToggleTheme}
          isMobileOpen={isMobileSidebarOpen}
          onCloseMobile={() => setIsMobileSidebarOpen(false)}
        />

        <MobileBackdrop
          isOpen={isMobileSidebarOpen}
          onClick={() => setIsMobileSidebarOpen(false)}
        />

        <ChatPanel
          activeSession={activeSession}
          onRenameSession={handleRenameSession}
          onClearMessages={handleClearMessages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)}
        />
      </AppLayout>
    </ThemeProvider>
  );
}
