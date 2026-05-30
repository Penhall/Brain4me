# Fase 3: Electron Desktop App para Brain4me

## Contexto

Brain4me é um sistema CLI + Streamlit. Queremos um app Electron desktop que sirva como cliente de ingestão — file picker nativo para selecionar PDF/DOCX/TXT/MD e enviar para o Brain4me processar.

## Objetivo

Criar um app Electron minimalista em `/home/petto/brain4me/electron/` com:
- File picker nativo para selecionar documentos
- Execução do CLI `brain4me ingest-file` para cada arquivo
- Configuração de db_path persistente
- System tray com menu rápido

## Tarefas

### 1. Criar electron/package.json

```json
{
  "name": "brain4me-electron",
  "version": "0.1.0",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder"
  },
  "dependencies": {
    "electron-store": "^8.1.0"
  },
  "devDependencies": {
    "electron": "^35.0.0"
  }
}
```

### 2. Criar electron/main.js

Processo principal (~200 linhas):
- Cria `BrowserWindow` 800x600 com `index.html`
- Configura `electron-store` para persistir `db_path`
- IPC handlers:
  - `dialog:openFiles` — abre native dialog com filtros (PDF, DOCX, TXT, MD, All)
  - `config:get` — retorna db_path
  - `config:set` — salva db_path
  - `ingest:file` — executa `brain4me ingest-file --db <db_path> --file <file_path>` via `child_process.exec`
  - `ingest:batch` — executa múltiplos arquivos sequencialmente, reporta progresso por IPC
- System tray:
  - Ícone na bandeja
  - Menu: Open, Ingest Files, Quit
  - Minimizar para tray (não fechar)

### 3. Criar electron/preload.js

Context bridge expondo APIs seguras:
```js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('brain4me', {
  openFiles: () => ipcRenderer.invoke('dialog:openFiles'),
  getConfig: () => ipcRenderer.invoke('config:get'),
  setConfig: (key, value) => ipcRenderer.invoke('config:set', key, value),
  ingestFile: (filePath) => ipcRenderer.invoke('ingest:file', filePath),
  onIngestProgress: (callback) => ipcRenderer.on('ingest:progress', (event, data) => callback(data)),
});
```

### 4. Criar electron/index.html

HTML minimalista com Pico CSS para estilização:
- Header: "Brain4me Desktop"
- Seção de configuração: campo db_path + botão salvar
- Seção de ingestão: botão "Add Files" + área de drop
- Lista de arquivos selecionados
- Barra de progresso
- Log de últimas ingestões
- Status bar: "X entities, Y relations in database"

### 5. Criar electron/renderer.js

Lógica da UI (~150 linhas):
- Ao clicar "Add Files": chama `window.brain4me.openFiles()` → popula lista
- Ao clicar "Ingest All": itera arquivos, chama `window.brain4me.ingestFile(path)`, atualiza progresso
- Ao carregar: chama `window.brain4me.getConfig()` para preencher db_path
- Drop zone: aceita drag & drop de arquivos
- Estilo: brutalista/clean, cores escuras, sem glassmorphism, bordas retas

### 6. Criar electron/styles.css

Baseado em Pico CSS dark theme:
- Cores: background #0e1117, cards #1a1a2e, accent #3b82f6
- Sem border-radius (zero)
- Fonte: system-ui ou Space Grotesk
- Alta densidade de informação
- Sem glassmorphism, sem sombras elaboradas

### 7. Criar electron/.gitignore

```
node_modules/
dist/
out/
```

### 8. Criar electron/README.md

Instruções de setup e build:
```bash
cd electron
npm install
npm start        # desenvolvimento
npm run build    # build para distribuição
```

## Design notes

- **Sem React/Next.js** — vanilla HTML/JS/CSS como o Khoj Electron app
- **Pico CSS** para estilização base (leve, sem framework pesado)
- **electron-store** para persistência local (db_path, configurações)
- O app NÃO precisa de um servidor — ele chama o CLI `brain4me` diretamente via subprocess
- Assumir que `brain4me` está no PATH
- Se `brain4me` não for encontrado, mostrar erro amigável com instruções de instalação

## Fluxo do usuário

```
1. Abre Brain4me Desktop
2. Configura db_path: /home/user/brain4me/brain4me.db (salvo para sempre)
3. Clica "Add Files" → seleciona 3 PDFs e 2 DOCs
4. Clica "Ingest All" → barra de progresso: 1/5, 2/5, ...
5. Concluído: "5 files ingested. 23 entities, 18 relations detected."
6. Abre Streamlit → grafo mostra as novas entidades
```

## Validação

- `cd electron && npm install` sem erros
- `npm start` abre janela
- Botão "Add Files" abre dialog nativo
- Com brain4me instalado, ingestão funciona e mostra entidades criadas
- Configuração db_path persiste entre reinícios

## Restrições

- Não usar React, Vue, Angular — vanilla JS
- Tamanho do app enxuto — sem dependências desnecessárias
- Design brutalista/clean, alinhado com preferências do usuário
- Compatível com Linux (primary), macOS, Windows
