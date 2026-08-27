# V0.91 Internationalization And Packaging

V0.91 introduces a frontend i18n system with English and Simplified Chinese locale files, a language selector, browser-language fallback, and localStorage persistence. Translation coverage tests verify that both locale files contain the same keys and no empty values.

The release also adds a Windows packaging route. The frontend remains a Vite/React web app for development, while a staged Electron shell can load the built frontend. The FastAPI backend is packaged through PyInstaller, selects an available localhost port, writes the selected port to a runtime file, and exposes `/health` for startup polling.

This packaging path improves deployment readiness for non-developer users without breaking the normal developer workflow. Credentials are not bundled; `.env` remains external. Installer creation, code signing, and auto-update are left for a later release.
