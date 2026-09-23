import React from 'react';
import styled from 'styled-components';
import {
  FiBookOpen,
  FiFileText,
  FiDollarSign,
  FiShield,
  FiArrowUpRight,
  FiStar,
} from 'react-icons/fi';

const EmptyContainer = styled.div`
  max-width: 860px;
  margin: 0 auto;
  padding: 40px 20px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-height: 60vh;
`;

const HeroBadge = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 9999px;
  background: rgba(212, 175, 55, 0.12);
  border: 1px solid rgba(212, 175, 55, 0.3);
  color: ${({ theme }) => theme.accentGold};
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 20px;

  svg {
    color: ${({ theme }) => theme.accentEmerald};
  }
`;

const HeroTitle = styled.h1`
  font-size: 32px;
  font-weight: 700;
  line-height: 1.25;
  color: ${({ theme }) => theme.textPrimary};
  margin-bottom: 12px;

  span {
    background: linear-gradient(135deg, ${({ theme }) => theme.accentGold} 0%, #00a86b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  @media (max-width: 640px) {
    font-size: 24px;
  }
`;

const HeroDescription = styled.p`
  font-size: 15px;
  color: ${({ theme }) => theme.textSecondary};
  max-width: 600px;
  line-height: 1.6;
  margin-bottom: 36px;
`;

const CardsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  width: 100%;

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
`;

const PromptCard = styled.button`
  background: ${({ theme }) => theme.cardBg};
  border: 1px solid ${({ theme }) => theme.cardBorder};
  border-radius: 14px;
  padding: 18px 20px;
  text-align: left;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: ${({ theme }) => theme.shadow};

  &:hover {
    transform: translateY(-2px);
    border-color: ${({ theme }) => theme.accentGold};
    background: ${({ theme }) => theme.cardHover};
    box-shadow: 0 12px 24px -6px rgba(212, 175, 55, 0.15);

    .icon-wrapper {
      background: linear-gradient(135deg, ${({ theme }) => theme.accentGold} 0%, #b8860b 100%);
      color: #070c18;
    }

    .arrow {
      color: ${({ theme }) => theme.accentGold};
      transform: translate(2px, -2px);
    }
  }
`;

const CardTop = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
`;

const IconWrapper = styled.div`
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: ${({ theme }) => theme.sidebarItemHover};
  color: ${({ theme }) => theme.accentGold};
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.2s ease;
`;

const CardArrow = styled.div`
  color: ${({ theme }) => theme.textMuted};
  transition: all 0.2s ease;
`;

const CardContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const CardTitle = styled.h3`
  font-size: 14.5px;
  font-weight: 600;
  color: ${({ theme }) => theme.textPrimary};
`;

const CardSubtitle = styled.p`
  font-size: 12.5px;
  color: ${({ theme }) => theme.textSecondary};
  line-height: 1.4;
`;

const STARTER_PROMPTS = [
  {
    icon: <FiBookOpen />,
    title: 'Murabaha Financing',
    description: 'Explain the cost-plus profit structure, rules, and payment terms.',
    prompt: 'What is Murabaha financing and what are its key Shariah rules and payment terms at LOLC Al-Falaah?',
  },
  {
    icon: <FiDollarSign />,
    title: 'Ijarah (Islamic Leasing)',
    description: 'How does asset and vehicle leasing work without interest (Riba)?',
    prompt: 'How does Ijarah leasing operate at LOLC Al-Falaah and how is it different from conventional leasing?',
  },
  {
    icon: <FiShield />,
    title: 'Mudharabah & Wakalah Savings',
    description: 'Compare profit-sharing investment accounts vs fixed terms.',
    prompt: 'Explain the difference between Mudharabah and Wakalah savings and investment accounts.',
  },
  {
    icon: <FiFileText />,
    title: 'Generate Compliance Report',
    description: 'Create an official Word document on Murabaha Shariah guidelines.',
    prompt: 'Generate a detailed Shariah compliance report on Murabaha Financing including guidelines and document structure.',
  },
];

export default function EmptyState({ onSelectPrompt }) {
  return (
    <EmptyContainer>
      <HeroBadge>
        <FiStar size={14} />
        <span>LOLC Al-Falaah Islamic Banking Intelligence</span>
      </HeroBadge>

      <HeroTitle>
        How can we guide your <span>Shariah Finances</span> today?
      </HeroTitle>

      <HeroDescription>
        Ask questions about Islamic financial products, calculations, Shariah rulings, or generate official compliance reports directly from our verified knowledge base.
      </HeroDescription>

      <CardsGrid>
        {STARTER_PROMPTS.map((item, idx) => (
          <PromptCard key={idx} onClick={() => onSelectPrompt(item.prompt)}>
            <CardTop>
              <IconWrapper className="icon-wrapper">{item.icon}</IconWrapper>
              <CardArrow className="arrow">
                <FiArrowUpRight size={18} />
              </CardArrow>
            </CardTop>
            <CardContent>
              <CardTitle>{item.title}</CardTitle>
              <CardSubtitle>{item.description}</CardSubtitle>
            </CardContent>
          </PromptCard>
        ))}
      </CardsGrid>
    </EmptyContainer>
  );
}
