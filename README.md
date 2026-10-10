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

## Deploy on Ubuntu 22.04.5 LTS with Apache

Run the Python app on `127.0.0.1:8765`, then reverse-proxy with Apache (`mod_proxy` / `mod_proxy_http`). No pip packages are required for the web app.

### 1. Install packages

```bash
sudo apt update
sudo apt install -y apache2 python3
```

### 2. Put the project on the server

Clone or copy the repo somewhere durable (example: `/opt/ai_charts`):

```bash
sudo mkdir -p /opt/ai_charts
sudo chown "$USER:$USER" /opt/ai_charts
git clone <your-repo-url> /opt/ai_charts
# or: rsync / scp your tree into /opt/ai_charts
```

Confirm it starts:

```bash
cd /opt/ai_charts
python3 web-app/app.py
# Open http://127.0.0.1:8765/ then Ctrl+C
```

### 3. systemd unit (keep the app running)

```ini
# /etc/systemd/system/ai-charts.service
[Unit]
Description=AI Charts web app
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/ai_charts
ExecStart=/usr/bin/python3 web-app/app.py
Restart=on-failure
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

Ensure `www-data` can read the tree (and write `web-app/data/` if the updater runs as that user):

```bash
sudo chown -R www-data:www-data /opt/ai_charts
sudo systemctl daemon-reload
sudo systemctl enable --now ai-charts
sudo systemctl status ai-charts
```

### 4. Apache reverse proxy

Enable modules and create a site:

```bash
sudo a2enmod proxy proxy_http headers
```

```apache
# /etc/apache2/sites-available/ai-charts.conf
<VirtualHost *:80>
    ServerName charts.example.com

    ProxyPreserveHost On
    ProxyPass        / http://127.0.0.1:8765/
    ProxyPassReverse / http://127.0.0.1:8765/

    ErrorLog  ${APACHE_LOG_DIR}/ai-charts-error.log
    CustomLog ${APACHE_LOG_DIR}/ai-charts-access.log combined
</VirtualHost>
```

Enable the site and reload:

```bash
sudo a2ensite ai-charts
sudo a2dissite 000-default   # optional, if this host only serves ai-charts
sudo apache2ctl configtest
sudo systemctl reload apache2
```

Point DNS for `charts.example.com` at the server, then open `http://charts.example.com/`.

### 5. HTTPS (optional)

```bash
sudo apt install -y certbot python3-certbot-apache
sudo certbot --apache -d charts.example.com
```

Certbot adds a TLS vhost; keep proxying to `http://127.0.0.1:8765/` unchanged.

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
