# PrintFarm Tracker

A locally-hosted 3D print farm tracker designed to run on a Raspberry Pi. Track filament inventory, calculate per-print costs (filament + electricity), monitor printer runtime, and integrate with Moonraker/Klipper, Govee smart plugs, Amazon order history, and slicer file exports.

## Features

- **Filament Inventory** — Track spools by brand, material, color, weight, and cost with visual progress bars
- **Cost Calculation** — Automatic filament + energy cost per job using spool cost-per-gram and configurable kWh rate
- **Moonraker Integration** — Polls Klipper/Moonraker printers every 30 s; auto-creates and closes job records on state transitions
- **Govee Integration** — Polls Govee energy-monitoring smart plugs every 60 s to accumulate kWh per job
- **Slicer File Watcher** — Watchdog monitors a folder for `.gcode` / `.3mf` files and creates draft job records with estimated filament pre-filled
- **Amazon Order History** — Playwright-based scraper stub for importing filament purchase records
- **React Dashboard** — Live overview, spool inventory, printer status cards, paginated job history, and settings form

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | `python3 --version` |
| Node 18+ | `node --version` |
| Klipper + Moonraker | Running on each printer; accessible from the Pi |
| Govee API key | Optional — for power monitoring via Govee H5080 or similar plug |

## Setup

### 1. Clone and enter the repo

```bash
git clone https://github.com/Bajascot/simple-scott-learns-printfarm-tracker.git
cd simple-scott-learns-printfarm-tracker
```

### 2. Backend

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values
```

### 3. Frontend

```bash
cd frontend
npm install
npm run build                     # Outputs to frontend/dist/
cd ..
```

### 4. Run the server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in a browser.

**Development mode** (hot-reload frontend at `http://localhost:3000`):

```bash
# Terminal 1
uvicorn backend.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./printfarm.db` | SQLAlchemy database URL |
| `GOVEE_API_KEY` | — | Govee Developer API key |
| `AMAZON_EMAIL` | — | Amazon account email (scraper stub) |
| `AMAZON_PASSWORD` | — | Amazon account password (scraper stub) |
| `SLICER_WATCH_DIR` | `/home/pi/slicer-output` | Folder watched for `.gcode` / `.3mf` files |
| `ENERGY_RATE_PER_KWH` | `0.12` | Fallback electricity rate (USD/kWh) |
| `SECRET_KEY` | `changeme` | Application secret key |

## API Routes

All routes are prefixed with `/api`.

| Prefix | Resource |
|---|---|
| `/api/printers` | Printer CRUD |
| `/api/spools` | Filament spool CRUD |
| `/api/jobs` | Print job log with cost calculation |
| `/api/costs` | Monthly summaries, totals, energy rates |

Interactive API docs: `http://localhost:8000/docs`

## Raspberry Pi / systemd Deployment

```bash
# Copy project to Pi
scp -r . pi@raspberrypi:/home/pi/printfarm-tracker

# On the Pi
cd /home/pi/printfarm-tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..

# Install systemd service
sudo cp printfarm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable printfarm
sudo systemctl start printfarm
sudo systemctl status printfarm
```

The tracker will now start automatically on boot and be accessible at `http://<pi-ip>:8000`.

## Integrations

### Moonraker
Add each printer via the Printers page with its Moonraker URL. The scheduler polls `/printer/objects/query?print_stats&display_status` every 30 s and automatically creates/closes `print_jobs` records on state transitions.

### Govee Smart Plugs
Set your `GOVEE_API_KEY` in `.env` and enter the Govee Device ID on each printer record. The scheduler accumulates kWh on running jobs every 60 s.

### Slicer File Watcher
Configure `SLICER_WATCH_DIR` in `.env` to your slicer's export folder. Drop a `.gcode` or `.3mf` file and a draft job record is created with filament weight extracted from the file metadata.

### Amazon Order History
Set `AMAZON_EMAIL` and `AMAZON_PASSWORD` in `.env`. The scraper implementation is stubbed in `backend/integrations/amazon.py` — see the TODO comments for the full approach. Run `playwright install chromium` when ready to implement.
