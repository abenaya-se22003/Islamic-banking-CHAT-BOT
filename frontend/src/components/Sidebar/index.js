import React, { useState } from 'react';
import styled from 'styled-components';
import {
  FiPlus,
  FiMessageSquare,
  FiTrash2,
  FiEdit2,
  FiCheck,
  FiX,
  FiSun,
  FiMoon,
  FiChevronLeft,
  FiChevronRight,
  FiShield,
  FiSearch,
} from 'react-icons/fi';

const SidebarContainer = styled.aside`
  width: ${({ isCollapsed }) => (isCollapsed ? '72px' : '280px')};
  height: 100vh;
  background: ${({ theme }) => theme.sidebarBg};
  border-right: 1px solid ${({ theme }) => theme.cardBorder};
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 30;
  user-select: none;
  flex-shrink: 0;

  @media (max-width: 768px) {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    width: 280px;
    transform: ${({ isMobileOpen }) => (isMobileOpen ? 'translateX(0)' : 'translateX(-100%)')};
    transition: transform 0.3s ease;
    box-shadow: ${({ isMobileOpen, theme }) => (isMobileOpen ? theme.shadow : 'none')};
  }
`;

const HeaderSection = styled.div`
  padding: 18px 16px;
  display: flex;
  align-items: center;
  justify-content: ${({ isCollapsed }) => (isCollapsed ? 'center' : 'space-between')};
  border-bottom: 1px solid ${({ theme }) => theme.cardBorder};
`;

const Brand = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  overflow: hidden;
`;

const LogoIcon = styled.div`
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, ${({ theme }) => theme.accentGold} 0%, #996515 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #070c18;
  font-weight: 800;
  font-size: 18px;
  box-shadow: 0 4px 12px rgba(212, 175, 55, 0.3);
  flex-shrink: 0;
`;

const BrandText = styled.div`
  display: flex;
  flex-direction: column;
  white-space: nowrap;
`;

const BrandTitle = styled.span`
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: ${({ theme }) => theme.textPrimary};
  background: linear-gradient(90deg, ${({ theme }) => theme.accentGold}, ${({ theme }) => theme.accentEmerald});
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
`;

const BrandSubtitle = styled.span`
  font-size: 11px;
  font-weight: 500;
  color: ${({ theme }) => theme.textSecondary};
  text-transform: uppercase;
  letter-spacing: 1px;
`;

const CollapseButton = styled.button`
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${({ theme }) => theme.textSecondary};
  background: ${({ theme }) => theme.sidebarItemHover};

  &:hover {
    color: ${({ theme }) => theme.accentGold};
    background: ${({ theme }) => theme.sidebarItemActive};
  }

  @media (max-width: 768px) {
    display: none;
  }
`;

const ActionSection = styled.div`
  padding: 14px 14px 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
`;

const NewChatButton = styled.button`
  width: 100%;
  height: 44px;
  border-radius: 10px;
  background: linear-gradient(135deg, ${({ theme }) => theme.accentGold} 0%, #b8860b 100%);
  color: #070c18;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: ${({ isCollapsed }) => (isCollapsed ? 'center' : 'flex-start')};
  padding: ${({ isCollapsed }) => (isCollapsed ? '0' : '0 16px')};
  gap: 10px;
  box-shadow: 0 4px 14px rgba(212, 175, 55, 0.25);
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(212, 175, 55, 0.4);
    background: linear-gradient(135deg, ${({ theme }) => theme.accentGoldHover} 0%, #d4af37 100%);
  }

  &:active {
    transform: translateY(0);
  }

  span {
    white-space: nowrap;
  }
`;

const SearchBox = styled.div`
  position: relative;
  display: ${({ isCollapsed }) => (isCollapsed ? 'none' : 'block')};

  input {
    width: 100%;
    padding: 8px 12px 8px 34px;
    border-radius: 8px;
    background: ${({ theme }) => theme.cardBg};
    border: 1px solid ${({ theme }) => theme.cardBorder};
    color: ${({ theme }) => theme.textPrimary};
    font-size: 13px;

    &::placeholder {
      color: ${({ theme }) => theme.textMuted};
    }

    &:focus {
      border-color: ${({ theme }) => theme.accentGold};
    }
  }

  svg {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: ${({ theme }) => theme.textMuted};
    font-size: 14px;
  }
`;

const SessionListContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const SessionCategoryLabel = styled.div`
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: ${({ theme }) => theme.textMuted};
  padding: 8px 8px 4px;
  display: ${({ isCollapsed }) => (isCollapsed ? 'none' : 'block')};
`;

const SessionItem = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: ${({ isCollapsed }) => (isCollapsed ? '10px 0' : '10px 12px')};
  justify-content: ${({ isCollapsed }) => (isCollapsed ? 'center' : 'flex-start')};
  border-radius: 8px;
  cursor: pointer;
  background: ${({ isActive, theme }) => (isActive ? theme.sidebarItemActive : 'transparent')};
  border: 1px solid ${({ isActive, theme }) => (isActive ? theme.accentGold : 'transparent')};
  color: ${({ isActive, theme }) => (isActive ? theme.textPrimary : theme.textSecondary)};
  transition: all 0.15s ease;

  &:hover {
    background: ${({ theme }) => theme.sidebarItemHover};
    color: ${({ theme }) => theme.textPrimary};

    .actions {
      opacity: 1;
    }
  }
`;

const SessionTitle = styled.span`
  font-size: 13.5px;
  font-weight: ${({ isActive }) => (isActive ? '500' : '400')};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
`;

const SessionActions = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s ease;

  button {
    color: ${({ theme }) => theme.textMuted};
    padding: 2px;
    border-radius: 4px;

    &:hover {
      color: ${({ theme }) => theme.accentGold};
    }

    &.delete:hover {
      color: #ef4444;
    }
  }
`;

const EditInput = styled.input`
  flex: 1;
  background: ${({ theme }) => theme.cardBg};
  border: 1px solid ${({ theme }) => theme.accentGold};
  border-radius: 4px;
  padding: 2px 6px;
  color: ${({ theme }) => theme.textPrimary};
  font-size: 13px;
`;

const FooterSection = styled.div`
  padding: 14px;
  border-top: 1px solid ${({ theme }) => theme.cardBorder};
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const FooterButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: ${({ isCollapsed }) => (isCollapsed ? 'center' : 'space-between')};
  padding: 10px 12px;
  border-radius: 8px;
  color: ${({ theme }) => theme.textSecondary};
  background: ${({ theme }) => theme.sidebarItemHover};
  font-size: 13px;
  transition: all 0.2s ease;

  &:hover {
    color: ${({ theme }) => theme.textPrimary};
    background: ${({ theme }) => theme.sidebarItemActive};
  }

  .left {
    display: flex;
    align-items: center;
    gap: 10px;
  }
`;

const ShariahBadge = styled.div`
  display: ${({ isCollapsed }) => (isCollapsed ? 'none' : 'flex')};
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.2);
  color: ${({ theme }) => theme.accentEmerald};
  font-size: 11.5px;
  font-weight: 500;
`;

export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onRenameSession,
  onClearAllSessions,
  themeMode,
  onToggleTheme,
  isMobileOpen,
  onCloseMobile,
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitleValue, setEditTitleValue] = useState('');

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const startRenaming = (session, e) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditTitleValue(session.title);
  };

  const saveRenaming = (sessionId, e) => {
    e.stopPropagation();
    if (editTitleValue.trim()) {
      onRenameSession(sessionId, editTitleValue.trim());
    }
    setEditingSessionId(null);
  };

  const cancelRenaming = (e) => {
    e.stopPropagation();
    setEditingSessionId(null);
  };

  return (
    <SidebarContainer isCollapsed={isCollapsed} isMobileOpen={isMobileOpen}>
      <HeaderSection isCollapsed={isCollapsed}>
        <Brand>
          <LogoIcon>AL</LogoIcon>
          {!isCollapsed && (
            <BrandText>
              <BrandTitle>LOLC Al-Falaah</BrandTitle>
              <BrandSubtitle>Islamic AI Banking</BrandSubtitle>
            </BrandText>
          )}
        </Brand>

        <CollapseButton
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isCollapsed ? <FiChevronRight size={16} /> : <FiChevronLeft size={16} />}
        </CollapseButton>
      </HeaderSection>

      <ActionSection>
        <NewChatButton
          isCollapsed={isCollapsed}
          onClick={() => {
            onNewChat();
            if (onCloseMobile) onCloseMobile();
          }}
          title="Start New Chat"
        >
          <FiPlus size={18} />
          {!isCollapsed && <span>New Chat</span>}
        </NewChatButton>

        {!isCollapsed && (
          <SearchBox isCollapsed={isCollapsed}>
            <FiSearch />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </SearchBox>
        )}
      </ActionSection>

      <SessionListContainer>
        {!isCollapsed && <SessionCategoryLabel>Recent Chats</SessionCategoryLabel>}
        {filteredSessions.map((session) => {
          const isActive = session.id === activeSessionId;
          const isEditing = editingSessionId === session.id;

          return (
            <SessionItem
              key={session.id}
              isActive={isActive}
              isCollapsed={isCollapsed}
              onClick={() => {
                onSelectSession(session.id);
                if (onCloseMobile) onCloseMobile();
              }}
              title={session.title}
            >
              <FiMessageSquare size={16} style={{ flexShrink: 0 }} />

              {!isCollapsed && (
                <>
                  {isEditing ? (
                    <>
                      <EditInput
                        autoFocus
                        value={editTitleValue}
                        onChange={(e) => setEditTitleValue(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') saveRenaming(session.id, e);
                          if (e.key === 'Escape') cancelRenaming(e);
                        }}
                      />
                      <SessionActions style={{ opacity: 1 }}>
                        <button onClick={(e) => saveRenaming(session.id, e)} title="Save">
                          <FiCheck size={14} />
                        </button>
                        <button onClick={cancelRenaming} title="Cancel">
                          <FiX size={14} />
                        </button>
                      </SessionActions>
                    </>
                  ) : (
                    <>
                      <SessionTitle isActive={isActive}>{session.title}</SessionTitle>
                      <SessionActions className="actions">
                        <button onClick={(e) => startRenaming(session, e)} title="Rename">
                          <FiEdit2 size={13} />
                        </button>
                        <button
                          className="delete"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(session.id);
                          }}
                          title="Delete Session"
                        >
                          <FiTrash2 size={13} />
                        </button>
                      </SessionActions>
                    </>
                  )}
                </>
              )}
            </SessionItem>
          );
        })}
      </SessionListContainer>

      <FooterSection>
        {!isCollapsed && (
          <ShariahBadge isCollapsed={isCollapsed}>
            <FiShield size={14} />
            <span>100% Shariah Compliant AI</span>
          </ShariahBadge>
        )}

        <FooterButton
          isCollapsed={isCollapsed}
          onClick={onToggleTheme}
          title={themeMode === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
        >
          <div className="left">
            {themeMode === 'dark' ? <FiSun size={16} /> : <FiMoon size={16} />}
            {!isCollapsed && <span>{themeMode === 'dark' ? 'Light Theme' : 'Dark Theme'}</span>}
          </div>
        </FooterButton>

        {!isCollapsed && sessions.length > 0 && (
          <FooterButton
            isCollapsed={isCollapsed}
            onClick={onClearAllSessions}
            title="Clear all conversations"
            style={{ color: '#ef4444' }}
          >
            <div className="left">
              <FiTrash2 size={16} />
              <span>Clear History</span>
            </div>
          </FooterButton>
        )}
      </FooterSection>
    </SidebarContainer>
  );
}
