# 🤖 Jarvis OS

[![Jarvis CI](https://github.com/vuppala/Jarvis/actions/workflows/ci.yml/badge.svg)](https://github.com/vuppala/Jarvis/actions/workflows/ci.yml)

> AI Operating System — Think. Remember. Plan. Execute. Automate.

Jarvis OS is a production-grade AI Operating System with a stunning, cross-platform interface. It can understand, plan, execute, learn, remember, and automate tasks. 

Built with **Python & FastAPI** on the backend, and **React, Vite, Three.js & Tailwind CSS** on the frontend. It natively supports the **Web**, **Desktop (Electron)**, and **Mobile (Android via Capacitor)**.

---

## ⚡ Quick Start: Backend

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

2. **Install Jarvis OS:**
   ```bash
   pip install uv
   uv pip install -e ".[dev]"
   ```

3. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your desired API keys (e.g. JARVIS_API_KEY)
   ```

4. **Run the API Server:**
   ```bash
   python -m jarvis serve --reload
   ```
   *The backend will be available at `http://localhost:8000`*

---

## 💻 Quick Start: Frontend (Web & Desktop)

Open a new terminal window and navigate to the frontend directory:

1. **Install Node dependencies:**
   ```bash
   cd jarvis/frontend
   npm install
   ```

2. **Run in Web Browser:**
   ```bash
   npm run dev
   ```

3. **Run as Desktop App (Electron):**
   ```bash
   npm run dev:electron
   ```

---

## 📱 Quick Start: Mobile (Android)

Jarvis OS uses Ionic Capacitor to run natively on Android.

1. **Configure Network:**
   Create a `.env.production` file in `jarvis/frontend` and point it to your computer's local Wi-Fi IP address so the phone can reach the backend:
   ```env
   VITE_API_BASE_URL=http://192.168.1.X:8000
   ```
2. **Build and Sync:**
   ```bash
   npm run build
   npm run cap:sync
   ```
3. **Run in Android Studio:**
   ```bash
   npx cap open android
   ```
   *From Android Studio, you can launch the app on an Emulator or a connected physical device.*

---

## 📁 Project Structure

```
jarvis/
├── brain/              # Core orchestrator and reasoning engine
├── frontend/           # React, Vite, Three.js User Interface
│   ├── android/        # Capacitor Android project
│   ├── electron/       # Electron desktop wrapper
│   └── src/            # UI components and 3D canvas
├── memory/             # Multi-tier memory with ChromaDB
├── server/             # FastAPI backend routes and logic
├── tools/              # Extensible capability system
├── providers/          # AI provider implementations (Local & Cloud)
└── ...
```

## 📄 License

MIT
