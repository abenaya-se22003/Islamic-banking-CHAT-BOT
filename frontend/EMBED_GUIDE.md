# Floating Chat Widget — Embed Guide

> How to embed the Islamic Banking Assistant chatbot on any website.

---

## Option A: React-based Website

If your bank website is already a React app, simply import and render the component:

```jsx
import FloatingChatWidget from './components/FloatingChatWidget';

function App() {
  return (
    <div>
      {/* Your existing page content */}
      <FloatingChatWidget />
    </div>
  );
}
```

### Available Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `triggerLabel` | `string` | `"Chat with us"` | Text on the floating button |
| `headerTitle` | `string` | `"Islamic Banking Assistant"` | Title in the chat window header |
| `headerStatus` | `string` | `"Online — typically replies instantly"` | Status text below the title |

### Example with custom props:

```jsx
<FloatingChatWidget
  triggerLabel="Need help?"
  headerTitle="LOLC Islamic Banking"
  headerStatus="We're here to help"
/>
```

---

## Option B: Non-React Website (HTML / WordPress / PHP)

For plain HTML, WordPress, or any non-React site, build the widget as a standalone JS bundle and embed it with a single `<script>` tag.

### Step 1: Build the widget bundle

The project includes an `src/embed.js` entry point. To build it as a standalone bundle, we use a custom webpack config:

```bash
cd frontend

# Install the build dependency (one-time)
npm install --save-dev html-webpack-plugin

# Build the standalone widget
npx react-scripts build
```

> [!NOTE]
> The default CRA build produces `build/static/js/main.*.js` and `build/static/css/main.*.css` files.
> For a truly single-file embed, see the **Advanced: Single-file bundle** section below.

### Step 2: Embed on your website

Copy the built files from `frontend/build/static/` to your web server, then add this to your HTML:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LOLC Islamic Banking</title>

  <!-- Widget CSS -->
  <link rel="stylesheet" href="/static/css/main.css" />
</head>
<body>

  <!-- Your existing website content here -->
  <h1>Welcome to Our Bank</h1>

  <!-- Chatbot mount point -->
  <div id="chatbot-root"></div>

  <!-- Widget JS (place at end of body) -->
  <script src="/static/js/main.js"></script>

</body>
</html>
```

> [!IMPORTANT]
> The `<div id="chatbot-root"></div>` is optional — `embed.js` will auto-create it if missing.
> The widget attaches itself to the page as a fixed-position overlay and won't affect your page layout.

### Step 3: Configure the backend URL

By default the widget calls `http://localhost:8000/chat`. For production, update the `API_URL` constant in `src/components/ChatWidget/ChatWidget.js` before building:

```js
const API_URL = 'https://your-api-domain.com/chat';
```

---

## Advanced: Single-file Bundle with Vite

For a cleaner single-file embed (no separate CSS file), you can migrate to Vite's library mode:

### 1. Install Vite

```bash
npm install --save-dev vite @vitejs/plugin-react
```

### 2. Create `vite.config.embed.js`

```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist-widget',
    lib: {
      entry: resolve(__dirname, 'src/embed.js'),
      name: 'IslamicBankingChatbot',
      fileName: 'chatbot-widget',
      formats: ['iife'],   // single self-executing file
    },
    cssCodeSplit: false,    // inline CSS into the JS bundle
    rollupOptions: {
      // Don't externalize React — bundle it into the widget
      external: [],
    },
  },
  define: {
    'process.env.NODE_ENV': '"production"',
  },
});
```

### 3. Build

```bash
npx vite build --config vite.config.embed.js
```

This produces a single `dist-widget/chatbot-widget.iife.js` file.

### 4. Embed with one line

```html
<script src="https://your-cdn.com/chatbot-widget.iife.js"></script>
```

That's it — no `<div>`, no CSS file, no other dependencies needed.

---

## WordPress Integration

For WordPress sites, add this to your theme's `footer.php` or use a plugin like **Insert Headers and Footers**:

```php
<!-- Islamic Banking Chatbot Widget -->
<div id="chatbot-root"></div>
<script src="<?php echo get_template_directory_uri(); ?>/assets/js/chatbot-widget.js"></script>
```

Or if using the single-file Vite build:

```php
<script src="<?php echo get_template_directory_uri(); ?>/assets/js/chatbot-widget.iife.js"></script>
```

---

## CORS Configuration

Make sure your FastAPI backend allows requests from the bank website domain. In `main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-bank-website.com"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)
```

---

## Testing Locally

1. Start the FastAPI backend:
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

2. Start the React dev server:
   ```bash
   cd frontend
   npm start
   ```

3. Open `http://localhost:3000` — you'll see the bank page with the floating "Chat with us" button in the bottom-right corner.
