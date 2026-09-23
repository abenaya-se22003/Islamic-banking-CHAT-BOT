import React, { useState } from 'react';
import styled from 'styled-components';
import {
  FiMenu,
  FiEdit3,
  FiCheck,
  FiX,
  FiTrash2,
  FiDownload,
  FiZap,
} from 'react-icons/fi';

const HeaderContainer = styled.header`
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: ${({ theme }) => theme.headerBg};
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid ${({ theme }) => theme.cardBorder};
  position: sticky;
  top: 0;
  z-index: 20;

  @media (max-width: 768px) {
    padding: 0 16px;
  }
`;

const LeftSection = styled.div`
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  flex: 1;
`;

const MobileMenuButton = styled.button`
  display: none;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  align-items: center;
  justify-content: center;
  color: ${({ theme }) => theme.textPrimary};
  background: ${({ theme }) => theme.sidebarItemHover};

  @media (max-width: 768px) {
    display: flex;
  }
`;

const TitleWrapper = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
`;

const TitleText = styled.h2`
  font-size: 16px;
  font-weight: 600;
  color: ${({ theme }) => theme.textPrimary};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 380px;

  @media (max-width: 768px) {
    max-width: 180px;
    font-size: 14px;
  }
`;

const EditButton = styled.button`
  color: ${({ theme }) => theme.textMuted};
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    color: ${({ theme }) => theme.accentGold};
  }
`;

const InlineEditInput = styled.input`
  font-size: 15px;
  font-weight: 600;
  background: ${({ theme }) => theme.cardBg};
  border: 1px solid ${({ theme }) => theme.accentGold};
  border-radius: 6px;
  padding: 4px 8px;
  color: ${({ theme }) => theme.textPrimary};
  outline: none;
  width: 260px;
`;

const RightSection = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
`;

const ModelBadge = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 9999px;
  background: rgba(212, 175, 55, 0.1);
  border: 1px solid rgba(212, 175, 55, 0.25);
  color: ${({ theme }) => theme.accentGold};
  font-size: 12px;
  font-weight: 600;

  svg {
    color: ${({ theme }) => theme.accentEmerald};
  }

  @media (max-width: 640px) {
    display: none;
  }
`;

const HeaderActionButton = styled.button`
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${({ theme }) => theme.textSecondary};
  background: ${({ theme }) => theme.sidebarItemHover};
  transition: all 0.2s ease;

  &:hover {
    color: ${({ theme }) => theme.textPrimary};
    background: ${({ theme }) => theme.sidebarItemActive};
  }

  &.danger:hover {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.1);
  }
`;

export default function ChatHeader({
  activeSession,
  onRenameSession,
  onClearMessages,
  onOpenMobileSidebar,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [tempTitle, setTempTitle] = useState(activeSession ? activeSession.title : 'New Conversation');

  const handleSave = () => {
    if (tempTitle.trim() && activeSession) {
      onRenameSession(activeSession.id, tempTitle.trim());
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setTempTitle(activeSession ? activeSession.title : 'New Conversation');
    setIsEditing(false);
  };

  const handleExport = () => {
    if (!activeSession || !activeSession.messages.length) return;
    const textContent = activeSession.messages
      .map(
        (m) =>
          `[${m.sender === 'user' ? 'USER' : 'LOLC AL-FALAAH ASSISTANT'}] (${m.timestamp || ''})\n${m.text}\n\n`
      )
      .join('---\n\n');

    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeSession.title.replace(/[\W_]+/g, '_')}_transcript.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <HeaderContainer>
      <LeftSection>
        <MobileMenuButton onClick={onOpenMobileSidebar} title="Open Sidebar">
          <FiMenu size={20} />
        </MobileMenuButton>

        <TitleWrapper>
          {isEditing ? (
            <>
              <InlineEditInput
                autoFocus
                value={tempTitle}
                onChange={(e) => setTempTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSave();
                  if (e.key === 'Escape') handleCancel();
                }}
              />
              <EditButton onClick={handleSave} title="Save Title">
                <FiCheck size={16} />
              </EditButton>
              <EditButton onClick={handleCancel} title="Cancel">
                <FiX size={16} />
              </EditButton>
            </>
          ) : (
            <>
              <TitleText>{activeSession ? activeSession.title : 'New Conversation'}</TitleText>
              {activeSession && (
                <EditButton
                  onClick={() => {
                    setTempTitle(activeSession.title);
                    setIsEditing(true);
                  }}
                  title="Rename Conversation"
                >
                  <FiEdit3 size={15} />
                </EditButton>
              )}
            </>
          )}
        </TitleWrapper>
      </LeftSection>

      <RightSection>
        <ModelBadge>
          <FiZap size={13} />
          <span>Gemini 2.5 Flash Grounded</span>
        </ModelBadge>

        {activeSession && activeSession.messages && activeSession.messages.length > 0 && (
          <>
            <HeaderActionButton onClick={handleExport} title="Export Conversation Transcript">
              <FiDownload size={16} />
            </HeaderActionButton>
            <HeaderActionButton
              className="danger"
              onClick={onClearMessages}
              title="Clear Current Messages"
            >
              <FiTrash2 size={16} />
            </HeaderActionButton>
          </>
        )}
      </RightSection>
    </HeaderContainer>
  );
}
