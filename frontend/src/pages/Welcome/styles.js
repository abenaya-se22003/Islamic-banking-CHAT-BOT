import styled from 'styled-components';

export const Container = styled.div`
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
`;

export const PageTitle = styled.h1`
  font-size: 28px;
  font-weight: 700;
  color: #0e7c6b;
  margin-bottom: 12px;
  text-align: center;
`;

export const PageSubtitle = styled.p`
  font-size: 16px;
  color: #64748b;
  text-align: center;
  line-height: 1.6;
  max-width: 480px;
`;
