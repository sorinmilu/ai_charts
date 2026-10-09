# AI Charts

Two apps in one repo:

| Path | Role |
|------|------|
| `web-app/` | Chart UI and API (`app.py`, `static/`, shared `data/`) |
| `updater/` | Research CSV updater (prompts, CLI, OpenAI research runs) |

The web app reads talking-points CSVs from `web-app/data/` on every request. The updater researches new rows and appends them to those CSVs when validation passes.

## Start the web app locally

The chart server is stdlib-only (no pip packages required).

```bash
cd /path/to/ai_charts
python3 web-app/app.py
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/). Stop with Ctrl+C.

The process binds to `127.0.0.1:8765` and serves:

- static UI from `web-app/static/`
- JSON APIs: `/api/points`, `/api/definitions`, `/api/buckets` (from `web-app/data/`)

## Deploy behind Apache

Run the Python app on localhost, then reverse-proxy with Apache (`mod_proxy` / `mod_proxy_http`).

1. Keep the app running (example systemd unit):

```ini
# /etc/systemd/system/ai-charts.service
[Unit]
Description=AI Charts web app
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/ai_charts
ExecStart=/usr/bin/python3 web-app/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now ai-charts
```

2. Apache virtual host (adapt `ServerName` and paths):

```apache
# Enable modules once: a2enmod proxy proxy_http headers
<VirtualHost *:80>
    ServerName charts.example.com

    ProxyPreserveHost On
    ProxyPass        / http://127.0.0.1:8765/
    ProxyPassReverse / http://127.0.0.1:8765/

    ErrorLog  ${APACHE_LOG_DIR}/ai-charts-error.log
    CustomLog ${APACHE_LOG_DIR}/ai-charts-access.log combined
</VirtualHost>
```

Reload Apache after enabling the site:

```bash
sudo apachectl configtest && sudo systemctl reload apache2
```

For HTTPS, terminate TLS on Apache (e.g. Certbot) and keep the same `ProxyPass` to `127.0.0.1:8765`.

## Deploy behind nginx

Same pattern: Python app on localhost, nginx as reverse proxy.

```nginx
# /etc/nginx/sites-available/ai-charts
server {
    listen 80;
    server_name charts.example.com;

    location / {
        proxy_pass         http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ai-charts /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Use the same systemd unit as in the Apache section to keep `web-app/app.py` running. For HTTPS, add a `listen 443 ssl` server block (or Certbot) and proxy to `127.0.0.1:8765` unchanged.

## Run the update script

Install updater dependencies and set OpenAI credentials. From the project root:

```bash
pip install -r updater/requirements.txt
cp updater/.env.example updater/.env
# Edit updater/.env — set OPENAI_API_KEY
# Optional: OPENAI_MODEL, OPENAI_REASONING_EFFORT, RESEARCH_MAX_NEW_ROWS, …
```

Dry run (wiring check only; no API call, no CSV change):

```bash
python updater/update_data_csv.py updater/prompts/practical_utility_prompt.md --dry-run
```

Real run (calls OpenAI + web search; appends validated new rows to the live CSV if any):

```bash
python updater/update_data_csv.py updater/prompts/practical_utility_prompt.md
```

Other prompts:

```bash
python updater/update_data_csv.py updater/prompts/current_capability_prompt.md
python updater/update_data_csv.py updater/prompts/middle_class_economics_prompt.md
python updater/update_data_csv.py updater/prompts/intellectual_jobs_Prompt.md
python updater/update_data_csv.py updater/prompts/future_trajectory_prompt.md
```

Each run logs one line to `updater/output/runs.log`. More detail: [`updater/README.md`](updater/README.md).

## Tests

```bash
pytest updater/tests/ -q
```
