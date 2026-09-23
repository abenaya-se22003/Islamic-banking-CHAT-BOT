import { createGlobalStyle } from 'styled-components';

export default createGlobalStyle`
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@400;500;600&display=swap');

  * {
    margin: 0;
    padding: 0;
    outline: 0;
    box-sizing: border-box;
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  }

  html,
  body,
  #root {
    height: 100%;
    width: 100%;
    overflow: hidden;
    font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: ${({ theme }) => theme?.bg || '#0a0f1d'};
    color: ${({ theme }) => theme?.textPrimary || '#f8fafc'};
  }

  body {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  /* Custom styled scrollbars */
  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  ::-webkit-scrollbar-track {
    background: transparent;
  }

  ::-webkit-scrollbar-thumb {
    background: ${({ theme }) => theme?.scrollbarThumb || '#1e293b'};
    border-radius: 9999px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: ${({ theme }) => theme?.accentGold || '#d4af37'};
  }

  button {
    font-family: inherit;
    cursor: pointer;
    border: none;
    background: none;
  }

  input, textarea {
    font-family: inherit;
  }

  a {
    color: ${({ theme }) => theme?.accentGold || '#d4af37'};
    text-decoration: none;
  }

  a:hover {
    text-decoration: underline;
  }
`;
