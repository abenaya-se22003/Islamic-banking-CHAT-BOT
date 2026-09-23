import React, { useEffect, useRef } from 'react';
import styled, { keyframes } from 'styled-components';
import MessageItem from './MessageItem';

const ListContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
  display: flex;
  flex-direction: column;
`;

const bounce = keyframes`
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
`;

const TypingIndicatorContainer = styled.div`
  display: flex;
  gap: 14px;
  padding: 16px 24px;
  align-items: center;

  @media (max-width: 640px) {
    padding: 12px 14px;
  }
`;

const Avatar = styled.div`
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 700;
  font-size: 14px;
  background: linear-gradient(135deg, ${({ theme }) => theme.accentGold} 0%, #996515 100%);
  color: #070c18;
  border: 1px solid ${({ theme }) => theme.accentGold};
`;

const TypingBubble = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 18px;
  border-radius: 16px 16px 16px 4px;
  background: ${({ theme }) => theme.cardBg};
  border: 1px solid ${({ theme }) => theme.cardBorder};

  .dot {
    width: 7px;
    height: 7px;
    background: ${({ theme }) => theme.accentGold};
    border-radius: 50%;
    display: inline-block;
    animation: ${bounce} 1.4s infinite ease-in-out both;
  }

  .dot:nth-child(1) {
    animation-delay: -0.32s;
  }
  .dot:nth-child(2) {
    animation-delay: -0.16s;
  }

  .text {
    font-size: 12.5px;
    color: ${({ theme }) => theme.textSecondary};
    margin-left: 6px;
  }
`;

export default function MessageList({ messages, isLoading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <ListContainer>
      {messages.map((msg, index) => (
        <MessageItem key={msg.id || index} message={msg} />
      ))}

      {isLoading && (
        <TypingIndicatorContainer>
          <Avatar>AL</Avatar>
          <TypingBubble>
            <div className="dot" />
            <div className="dot" />
            <div className="dot" />
            <span className="text">Al-Falaah AI is researching Shariah knowledge...</span>
          </TypingBubble>
        </TypingIndicatorContainer>
      )}

      <div ref={bottomRef} style={{ height: 1 }} />
    </ListContainer>
  );
}
