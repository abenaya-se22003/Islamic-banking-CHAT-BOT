import React from 'react';
import styled from 'styled-components';
import ChatHeader from '../ChatHeader';
import MessageList from '../MessageList';
import EmptyState from '../EmptyState';
import ChatInput from '../ChatInput';

const PanelContainer = styled.main`
  flex: 1;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: ${({ theme }) => theme.bg};
  position: relative;
  overflow: hidden;
  min-width: 0;
`;

const ContentArea = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  min-height: 0;
`;

export default function ChatPanel({
  activeSession,
  onRenameSession,
  onClearMessages,
  onSendMessage,
  isLoading,
  onOpenMobileSidebar,
}) {
  const messages = activeSession ? activeSession.messages : [];

  return (
    <PanelContainer>
      <ChatHeader
        activeSession={activeSession}
        onRenameSession={onRenameSession}
        onClearMessages={onClearMessages}
        onOpenMobileSidebar={onOpenMobileSidebar}
      />

      <ContentArea>
        {messages.length === 0 ? (
          <EmptyState onSelectPrompt={onSendMessage} />
        ) : (
          <MessageList messages={messages} isLoading={isLoading} />
        )}
      </ContentArea>

      <ChatInput onSendMessage={onSendMessage} isLoading={isLoading} />
    </PanelContainer>
  );
}
