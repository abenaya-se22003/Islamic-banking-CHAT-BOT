import React, { useState } from 'react';
import styled, { keyframes } from 'styled-components';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  FiUser,
  FiCopy,
  FiCheck,
  FiFileText,
  FiDownload,
  FiBookmark,
} from 'react-icons/fi';

const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const MessageRow = styled.div`
  display: flex;
  gap: 16px;
  padding: 16px 24px;
  animation: ${fadeIn} 0.25s ease-out;
  justify-content: ${({ isUser }) => (isUser ? 'flex-end' : 'flex-start')};

  &:hover {
    .msg-actions {
      opacity: 1;
    }
  }

  @media (max-width: 640px) {
    padding: 12px 14px;
    gap: 10px;
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
  background: ${({ isUser, theme }) =>
    isUser
      ? theme.userBubbleBg
      : `linear-gradient(135deg, ${theme.accentGold} 0%, #996515 100%)`};
  color: ${({ isUser, theme }) => (isUser ? theme.userBubbleText : '#070c18')};
  border: 1px solid ${({ isUser, theme }) => (isUser ? theme.cardBorder : theme.accentGold)};
  box-shadow: ${({ isUser }) =>
    isUser ? 'none' : '0 4px 12px rgba(212, 175, 55, 0.25)'};
`;

const ContentWrapper = styled.div`
  display: flex;
  flex-direction: column;
  max-width: ${({ isUser }) => (isUser ? '75%' : '850px')};
  min-width: 0;
  align-items: ${({ isUser }) => (isUser ? 'flex-end' : 'flex-start')};
  gap: 6px;

  @media (max-width: 640px) {
    max-width: 90%;
  }
`;

const SenderMeta = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: ${({ theme }) => theme.textMuted};
  padding: 0 4px;

  .name {
    font-weight: 600;
    color: ${({ isUser, theme }) => (isUser ? theme.textSecondary : theme.accentGold)};
  }
`;

const MessageBubble = styled.div`
  padding: ${({ isUser }) => (isUser ? '12px 18px' : '6px 4px 12px')};
  border-radius: ${({ isUser }) => (isUser ? '16px 4px 16px 16px' : '0')};
  background: ${({ isUser, theme }) => (isUser ? theme.userBubbleBg : 'transparent')};
  color: ${({ isUser, theme }) => (isUser ? theme.userBubbleText : theme.aiBubbleText)};
  font-size: 14.5px;
  line-height: 1.65;
  word-break: break-word;
  box-shadow: ${({ isUser, theme }) => (isUser ? theme.shadow : 'none')};

  /* Markdown Styles inside AI bubble */
  p {
    margin-bottom: 12px;
    &:last-child {
      margin-bottom: 0;
    }
  }

  h1, h2, h3, h4 {
    color: ${({ theme }) => theme.textPrimary};
    margin-top: 16px;
    margin-bottom: 8px;
    font-weight: 600;
  }

  h1 { font-size: 1.3em; }
  h2 { font-size: 1.18em; }
  h3 { font-size: 1.05em; }

  ul, ol {
    margin-left: 20px;
    margin-bottom: 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  li {
    list-style: disc;
  }

  ol li {
    list-style: decimal;
  }

  strong {
    color: ${({ theme }) => theme.textPrimary};
    font-weight: 600;
  }

  code {
    background: ${({ theme }) => theme.codeBlockBg};
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 0.9em;
    color: ${({ theme }) => theme.accentGold};
    border: 1px solid ${({ theme }) => theme.cardBorder};
  }

  pre {
    background: ${({ theme }) => theme.codeBlockBg};
    padding: 12px 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 12px 0;
    border: 1px solid ${({ theme }) => theme.cardBorder};

    code {
      background: transparent;
      padding: 0;
      border: none;
      color: ${({ theme }) => theme.textPrimary};
    }
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 13.5px;
  }

  th, td {
    padding: 8px 12px;
    border: 1px solid ${({ theme }) => theme.cardBorder};
    text-align: left;
  }

  th {
    background: ${({ theme }) => theme.sidebarItemHover};
    color: ${({ theme }) => theme.accentGold};
    font-weight: 600;
  }

  blockquote {
    border-left: 3px solid ${({ theme }) => theme.accentGold};
    padding-left: 12px;
    color: ${({ theme }) => theme.textSecondary};
    margin: 10px 0;
    font-style: italic;
  }
`;

const ReportCard = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: ${({ theme }) => theme.cardBg};
  border: 1px solid ${({ theme }) => theme.accentGold};
  border-radius: 12px;
  padding: 14px 18px;
  margin-top: 14px;
  width: 100%;
  max-width: 480px;
  gap: 12px;
  box-shadow: 0 6px 18px rgba(212, 175, 55, 0.12);

  .left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }

  .file-icon {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    background: rgba(43, 114, 186, 0.15);
    color: #2b72ba;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
  }

  .file-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .filename {
    font-size: 13.5px;
    font-weight: 600;
    color: ${({ theme }) => theme.textPrimary};
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .filetype {
    font-size: 11.5px;
    color: ${({ theme }) => theme.textMuted};
  }
`;

const DownloadButton = styled.a`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  background: linear-gradient(135deg, ${({ theme }) => theme.accentGold} 0%, #b8860b 100%);
  color: #070c18 !important;
  font-size: 12.5px;
  font-weight: 600;
  text-decoration: none !important;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(212, 175, 55, 0.25);
  transition: all 0.2s ease;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(212, 175, 55, 0.4);
  }
`;

const SourcesContainer = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed ${({ theme }) => theme.cardBorder};
`;

const SourceTag = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  padding: 3px 8px;
  border-radius: 6px;
  background: ${({ theme }) => theme.sidebarItemHover};
  border: 1px solid ${({ theme }) => theme.cardBorder};
  color: ${({ theme }) => theme.textSecondary};

  svg {
    color: ${({ theme }) => theme.accentGold};
    font-size: 10px;
  }
`;

const MessageActions = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.2s ease;
  padding: 0 4px;
`;

const ActionButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  color: ${({ theme }) => theme.textMuted};
  background: ${({ theme }) => theme.sidebarItemHover};
  transition: all 0.15s ease;

  &:hover {
    color: ${({ theme }) => theme.accentGold};
    background: ${({ theme }) => theme.sidebarItemActive};
  }

  &.copied {
    color: ${({ theme }) => theme.accentEmerald};
  }
`;

export default function MessageItem({ message }) {
  const isUser = message.sender === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const API_BASE = 'http://localhost:8000';
  const reportUrl = message.reportUrl
    ? message.reportUrl.startsWith('http')
      ? message.reportUrl
      : `${API_BASE}${message.reportUrl}`
    : null;

  const fileName = message.reportUrl
    ? message.reportUrl.split('/').pop()
    : 'Islamic_Banking_Report.docx';

  return (
    <MessageRow isUser={isUser}>
      {!isUser && <Avatar isUser={false}>AL</Avatar>}

      <ContentWrapper isUser={isUser}>
        <SenderMeta isUser={isUser}>
          <span className="name">{isUser ? 'You' : 'LOLC Al-Falaah Assistant'}</span>
          <span>{message.timestamp || ''}</span>
        </SenderMeta>

        <MessageBubble isUser={isUser}>
          {isUser ? (
            message.text
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.text}
            </ReactMarkdown>
          )}

          {/* Generated Document Report Download Card */}
          {reportUrl && (
            <ReportCard>
              <div className="left">
                <div className="file-icon">
                  <FiFileText />
                </div>
                <div className="file-info">
                  <span className="filename" title={fileName}>
                    {fileName}
                  </span>
                  <span className="filetype">Microsoft Word Document (.docx)</span>
                </div>
              </div>
              <DownloadButton href={reportUrl} target="_blank" rel="noreferrer" download>
                <FiDownload size={14} />
                <span>Download</span>
              </DownloadButton>
            </ReportCard>
          )}

          {/* Knowledge Grounding Sources */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <SourcesContainer>
              <span style={{ fontSize: '11px', color: '#94a3b8', marginRight: '4px' }}>
                Grounding Sources:
              </span>
              {message.sources.map((src, i) => (
                <SourceTag key={i}>
                  <FiBookmark />
                  {src}
                </SourceTag>
              ))}
            </SourcesContainer>
          )}
        </MessageBubble>

        {/* Message Action Toolbar */}
        {!isUser && (
          <MessageActions className="msg-actions">
            <ActionButton
              className={copied ? 'copied' : ''}
              onClick={handleCopy}
              title="Copy answer to clipboard"
            >
              {copied ? <FiCheck size={13} /> : <FiCopy size={13} />}
              <span>{copied ? 'Copied!' : 'Copy'}</span>
            </ActionButton>
          </MessageActions>
        )}
      </ContentWrapper>

      {isUser && (
        <Avatar isUser={true}>
          <FiUser size={16} />
        </Avatar>
      )}
    </MessageRow>
  );
}
