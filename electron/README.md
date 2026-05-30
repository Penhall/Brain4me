# Brain4me Electron Desktop

Minimalist Electron desktop app for ingesting documents into [Brain4me](https://github.com/petto/brain4me).

## Features

- Native file picker for PDF, DOCX, TXT, and Markdown files
- Drag & drop support
- Runs `brain4me ingest` CLI for each file
- Persistent `db_path` configuration via `electron-store`
- System tray with quick-access menu (Open, Ingest Files, Quit)
- Activity log and progress bar

## Prerequisites

- [Node.js](https://nodejs.org/) >= 18
- [Brain4me](https://github.com/petto/brain4me) Python package installed and `brain4me` available in PATH

## Setup

```bash
cd electron
npm install
```

## Usage

```bash
npm start       # development
npm run build   # build for distribution (requires electron-builder)
```

## Configuration

1. Open the app.
2. Enter the full path to your Brain4me SQLite database (e.g., `/home/user/brain4me/brain4me.db`).
3. Click **Save** — the path persists across restarts.

## Ingest Flow

1. Click **+ Add Files** (or drag files into the drop zone).
2. Click **Ingest All** to process all queued files sequentially.
3. Monitor progress via the progress bar, per-file status, and activity log.
4. The status bar shows current entity and relation counts.

## Troubleshooting

- **"brain4me CLI not found"** — ensure the Python package is installed (`pip install -e .` in the project root) and that the virtual environment's `bin` directory is in your PATH.
- **Database errors** — verify the `db_path` points to an existing or initializable SQLite database. Run `brain4me init-db --db /path/to/brain4me.db` to create one.

## Project Structure

```
electron/
├── main.js        # Electron main process (window, tray, IPC, subprocess)
├── preload.js     # Context bridge (secure IPC exposure)
├── index.html     # UI (Pico CSS + custom brutalist theme)
├── renderer.js    # UI logic
├── styles.css     # Custom styles
├── package.json   # Dependencies and scripts
├── README.md      # This file
└── .gitignore
```

## License

Same as the parent Brain4me project.
