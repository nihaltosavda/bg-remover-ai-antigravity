# ✦ AI Background Remover

> Remove image backgrounds instantly using the U2Net AI model — served via a FastAPI backend and a premium dark-mode frontend.

![Screenshot](docs/screenshot.png)

---

## 📁 Project Structure

```
bg_remover_app/
├── backend/
│   ├── main.py          # FastAPI application & API routes
│   └── utils.py         # Image validation + rembg processing
├── frontend/
│   ├── index.html       # Single-page frontend
│   ├── style.css        # Dark glassmorphism UI (vanilla CSS)
│   └── script.js        # Drag-drop, fetch, preview & download
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container build file
└── README.md
```

---

## ⚡ Quick Start

### 1 — Clone / enter the project
```bash
cd bg_remover_app
```

### 2 — Create & activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3 — Install dependencies
```bash
pip install -r requirements.txt
```

> **Note:** On first run `rembg` will automatically download the **U2Net model (~170 MB)** to `~/.u2net/`.

### 4 — Start the backend
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5 — Open the app
Navigate to **http://localhost:8000** in your browser.  
The FastAPI server also serves the frontend automatically.

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Health check |
| `POST` | `/api/remove-bg` | Upload image → transparent PNG |
| `POST` | `/api/replace-bg` | Upload image + hex color → coloured background PNG |
| `GET`  | `/docs` | Interactive Swagger UI |

### Example (cURL)
```bash
# Remove background
curl -X POST http://localhost:8000/api/remove-bg \
  -F "file=@photo.jpg" \
  --output result.png

# Replace background with red
curl -X POST http://localhost:8000/api/replace-bg \
  -F "file=@photo.jpg" \
  -F "color=#ff0000" \
  --output result_red.png
```

---

## 🐳 Docker

```bash
# Build
docker build -t bg-remover .

# Run
docker run -p 8000:8000 bg-remover
```

---

## 🧪 Testing

### Manual steps
1. Open http://localhost:8000
2. Drag and drop a JPG/PNG image onto the upload zone
3. Click **Remove Background** — wait for the AI to process
4. Verify the before/after preview
5. Click **Download PNG** to save the result

### API smoke tests (PowerShell)
```powershell
# Health check
Invoke-RestMethod http://localhost:8000/api/health

# Remove background
$form = @{ file = Get-Item ".\test_image.jpg" }
Invoke-RestMethod -Uri "http://localhost:8000/api/remove-bg" `
  -Method Post -Form $form -OutFile "result.png"
Write-Host "Saved result.png"
```

### Error-handling tests
| Test | Expected result |
|------|----------------|
| Upload a `.txt` file | 415 Unsupported Media Type |
| Upload image > 5 MB | 413 Request Entity Too Large |
| Upload 0-byte file | 422 Unprocessable Entity |

---

## 🚀 Deployment

### Render (free tier)
1. Push to a GitHub repo
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set **Build command**: `pip install -r requirements.txt`
4. Set **Start command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

### Railway
```bash
railway init
railway up
```

### Environment variables (optional)
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `info` | Uvicorn log level |

---

## 🛠 Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Uvicorn |
| AI Model | rembg (U2Net) |
| Image ops | Pillow (PIL) |
| Frontend | Vanilla HTML / CSS / JS |
| Styling | Dark glassmorphism, CSS custom properties |

---

## 📄 License
MIT — free to use, modify, and distribute.
