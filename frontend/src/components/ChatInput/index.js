import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import { FiSend, FiCornerDownLeft } from 'react-icons/fi';

const InputContainer = styled.div`
  padding: 12px 24px 18px;
  background: ${({ theme }) => theme.headerBg};
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid ${({ theme }) => theme.cardBorder};
  position: sticky;
  bottom: 0;
  z-index: 20;

  @media (max-width: 640px) {
    padding: 8px 14px 12px;
  }
`;

const InputWrapper = styled.div`
  max-width: 860px;
  margin: 0 auto;
  position: relative;
  display: flex;
  flex-direction: column;
  background: ${({ theme }) => theme.inputBg};
  border: 1px solid ${({ theme }) => theme.inputBorder};
  border-radius: 16px;
  box-shadow: ${({ theme }) => theme.shadow};
  transition: all 0.2s ease;

  &:focus-within {
    border-color: ${({ theme }) => theme.inputBorderFocus};
    box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.2), 0 10px 25px -5px rgba(0, 0, 0, 0.1);
  }
`;

const Textarea = styled.textarea`
  width: 100%;
  min-height: 48px;
  max-height: 180px;
  padding: 14px 56px 14px 18px;
  background: transparent;
  border: none;
  color: ${({ theme }) => theme.textPrimary};
  font-size: 14.5px;
  line-height: 1.5;
  resize: none;
  outline: none;

  &::placeholder {
    color: ${({ theme }) => theme.textMuted};
  }
`;

const SendButton = styled.button`
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${({ disabled, theme }) =>
    disabled
      ? theme.sidebarItemHover
      : `linear-gradient(135deg, ${theme.accentGold} 0%, #b8860b 100%)`};
  color: ${({ disabled, theme }) => (disabled ? theme.textMuted : '#070c18')};
  cursor: ${({ disabled }) => (disabled ? 'not-allowed' : 'pointer')};
  transition: all 0.2s ease;
  box-shadow: ${({ disabled }) =>
    disabled ? 'none' : '0 2px 10px rgba(212, 175, 55, 0.3)'};

  &:hover:not(:disabled) {
    transform: scale(1.04);
    box-shadow: 0 4px 14px rgba(212, 175, 55, 0.5);
  }

  &:active:not(:disabled) {
    transform: scale(0.96);
  }
`;

const Disclaimer = styled.div`
  max-width: 860px;
  margin: 8px auto 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
  color: ${({ theme }) => theme.textMuted};
  padding: 0 4px;

  .shariah {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .shortcut {
    display: flex;
    align-items: center;
    gap: 2px;
    font-size: 11px;
    opacity: 0.8;

    @media (max-width: 640px) {
      display: none;
    }
  }
`;

export default function ChatInput({ onSendMessage, isLoading }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  const adjustHeight = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
    }
  };

  useEffect(() => {
    adjustHeight();
  }, [text]);

  const handleSubmit = () => {
    if (!text.trim() || isLoading) return;
    onSendMessage(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '48px';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isDisabled = !text.trim() || isLoading;

  return (
    <InputContainer>
      <InputWrapper>
        <Textarea
          ref={textareaRef}
          rows={1}
          placeholder="Ask anything about LOLC Al-Falaah Islamic Banking or request a report..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <SendButton
          disabled={isDisabled}
          onClick={handleSubmit}
          title={isDisabled ? 'Type a question to send' : 'Send message (Enter)'}
        >
          <FiSend size={16} />
        </SendButton>
      </InputWrapper>

      <Disclaimer>
        <div className="shariah">
          <span>LOLC Al-Falaah Knowledge Base • Shariah Board Approved Guidelines</span>
        </div>
        <div className="shortcut">
          <span>Press</span>
          <FiCornerDownLeft size={11} />
          <span>Enter to send</span>
        </div>
      </Disclaimer>
    </InputContainer>
  );
}
