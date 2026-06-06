# ArCh — AI-Powered Search Engine
> **Search Smarter. Think Faster.**

ArCh (Aryan Search Engine) is a production-ready, AI-powered desktop search engine. It behaves as a hybrid of Google Search, Perplexity AI, and ChatGPT, packaged as a premium frameless desktop software. 

The application runs a lightweight **FastAPI** Python backend that handles internet scraping and coordinates LLM generation via the **Groq API**, wrapped in a sleek, hardware-accelerated **Electron.js** desktop application.

---

## Key Features

- **Real-Time Web Search**: Queries the internet dynamically via multiple search providers.
- **Pluggable Search Architecture**: Easily switch between Tavily AI Search, Brave Search, SerpAPI (Google), or our **Custom Web Crawler**.
- **Out-of-the-Box Functionality (Free)**: Works immediately using the built-in Custom Web Crawler (which scrapes DuckDuckGo results) without needing paid API keys.
- **AI-Powered Cited Summaries**: Synthesizes search results into highly detailed markdown reports with instant-link citation pills (`[1]`, `[2]`, etc.).
- **Conversational Follow-ups**: Remembers search history, allowing you to ask follow-up questions (e.g. *"Who is Atif Aslam?"* -> *"When was he born?"* -> *"What are his top songs?"*).
- **Search History & Saved Searches**: History and bookmarked searches are stored locally in JSON files (`storage/`) and can be loaded or cleared at any time.
- **Premium Frameless UI**: A gorgeous, modern Perplexity-style dark interface featuring glassmorphism, glowing accents, auto-resizing textareas, custom scrollbars, and window drag/control operations.
- **Splash Screen**: Displays a premium startup window with text glows and progress loaders during backend bootup.
- **Light & Auto Theme**: Support for Dark, Light, and System Default themes, updated in real time.

---

## Tech Stack

- **Desktop Framework**: Electron.js
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript (ES6)
- **Backend Framework**: Python 3.9+, FastAPI, Uvicorn
- **AI Processing**: Groq Cloud SDK (Fast, cited Llama-3.3-70b-versatile summaries)
- **Networking**: `aiohttp` (Async search calls)
- **Scraping**: `BeautifulSoup4` (Async custom HTML scraping)

---

## Installation & Setup

### Prerequisites
Make sure you have the following installed on your machine:
- **Node.js** (v16.0.0 or higher)
- **Python** (v3.9 or higher, with `pip`)

### 1. Clone & Initialize Project
Navigate to the root directory of the project:
```bash
# Install Node.js dependencies
npm install

# Install Python backend dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional)
You can configure your API keys by creating a `.env` file in the root directory or by copying the template:
```env
GROQ_API_KEY=gsk_your_groq_key_here
TAVILY_API_KEY=tvly-your_tavily_key_here
BRAVE_API_KEY=your_brave_subscription_token
SERPAPI_API_KEY=your_serpapi_google_key
```
*Note: You can also easily paste and update these keys dynamically inside the app's **Settings** panel.*

---

## How to Run

To start the application in development mode:
```bash
npm start
```
**What happens behind the scenes:**
1. Electron boots up and displays the transparent **ArCh Splash Screen**.
2. Electron checks if a FastAPI backend is already running on port `8000`.
3. If not, Electron spawns `python backend/app.py` in a child process and logs standard output.
4. Electron polls the backend status endpoint `/api/status`. Once the server is ready, the splash screen closes, and the main frameless window is displayed.
5. Closing the Electron window automatically kills the Python process tree using `tree-kill` to prevent dangling processes.

---

## Packaging the App for Windows (Executable)

To build a production standalone Windows executable (`.exe`) that packages both the Python backend and the Electron frontend:

### Step 1: Package the Python Backend
Use **PyInstaller** to freeze the FastAPI backend into a standalone executable:
```bash
pip install pyinstaller

# Package app.py as a single directory (or single file)
pyinstaller --noconsole --name arch-backend --distpath ./electron/bin backend/app.py
```
This places a compiled `arch-backend.exe` folder inside `electron/bin/arch-backend/`.

### Step 2: Update Electron to Spawn the Packaged Executable
Modify the backend spawn logic in [main.js](file:///c:/Users/aryan/OneDrive/Desktop/Antigravity%20Projects/ArCh/electron/main.js) to execute the pre-compiled binary when running in production:
```javascript
const isDev = !app.isPackaged;
const binaryPath = isDev 
  ? 'python' 
  : path.join(process.resourcesPath, 'bin', 'arch-backend', 'arch-backend.exe');
```

### Step 3: Bundle the Electron App
Use **electron-builder** to package the application:
1. Add `electron-builder` as a devDependency:
   ```bash
   npm install --save-dev electron-builder
   ```
2. Configure `build` configurations in your `package.json`:
   ```json
   "build": {
     "appId": "com.aryan.arch",
     "productName": "ArCh",
     "directories": {
       "output": "dist"
     },
     "files": [
       "electron/**/*",
       "frontend/**/*",
       "storage/**/*",
       "package.json"
     ],
     "extraResources": [
       {
         "from": "electron/bin/arch-backend",
         "to": "bin/arch-backend",
         "filter": ["**/*"]
       }
     ],
     "win": {
       "target": "nsis",
       "requestedExecutionLevel": "asInvoker"
     }
   }
   ```
3. Run the packager:
   ```bash
   npx electron-builder --win
   ```
This generates a standalone installers/executables in the `dist/` directory.

---

## Code Directory Structure

```
ArCh/
├── electron/
│   ├── main.js        # Main Electron process (app lifecycles, backend spawning)
│   └── preload.js     # Exposes safe desktop APIs (window resizing, URL opening)
│
├── backend/
│   ├── app.py         # FastAPI REST Router (history, settings, bookmarks)
│   ├── searchbot.py   # AI query rewriting & Groq LLM integration
│   └── providers/
│       ├── base.py    # SearchProvider base interface
│       ├── brave.py   # Brave Search API integration
│       ├── tavily.py  # Tavily Search API integration
│       ├── serpapi.py # SerpAPI Google Search integration
│       └── custom_crawler.py  # Zero-key DuckDuckGo web scraping crawler
│
├── frontend/
│   ├── index.html     # Single-page interface structure (sidebar, chat log)
│   ├── splash.html    # App bootup window
│   ├── style.css      # Neon-accented styling, markdown layout, themes
│   └── script.js      # App controller (REST fetch, markdown compilation, citation glows)
│
├── storage/
│   ├── settings.json  # Saved settings persistence
│   ├── history.json   # Search query history logs
│   └── bookmarks.json # Saved bookmarks logs
│
├── .env               # Secrets configuration
├── package.json       # Electron dependencies
└── requirements.txt   # Python dependencies
```

---

## Developer
Developed with ❤️ by **Aryan Singh**.
*Tagline: Search Smarter. Think Faster.*
