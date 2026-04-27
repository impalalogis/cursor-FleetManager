# 🚚 FleetManager — Django Web Application

FleetManager is a Django-based logistics and shipment management system that handles consignments, drivers, expenses, and auditing.  
This guide explains how to set up, deploy, and maintain the application on a Linux VPS (e.g., Hostinger KVM 2) using **Gunicorn**, **Nginx**, and **PostgreSQL**.

---

## 🖥️ Server Information

- **Hosting:** Hostinger KVM 2 VPS  
- **OS:** Ubuntu 22.04 LTS (64-bit)  
- **App Directory:** `/home/deploy/apps/fleet-manager/`  
- **System User:** `deploy`  
- **Web Server:** Nginx  
- **Application Server:** Gunicorn  
- **Database:** PostgreSQL  
- **Python Environment:** `.venv` (Python 3.12)  

---

## ⚙️ Project Structure

```
/home/deploy/apps/fleet-manager/
├── FleetManager/              # Main Django project directory
│   ├── wsgi.py                # WSGI entry point for Gunicorn
│   └── settings.py            # Django configuration file
├── staticfiles/               # Collected static files
├── .venv/                     # Python virtual environment
├── manage.py                  # Django management script
├── gunicorn-fleetmanager.service  # Systemd service (in /etc/systemd/system)
└── nginx config: /etc/nginx/sites-available/fleetmanager
```

---

## 🚀 Deployment Setup

### 1️⃣ Create and Activate Python Environment
```bash
cd /home/deploy/apps/fleet-manager/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2️⃣ Configure Database
Log in as PostgreSQL user and create DB + user:
```bash
sudo -u postgres psql
CREATE DATABASE myfleetmanagerdb;
CREATE USER myprojectrootuser WITH PASSWORD 'YOUR_STRONG_PASSWORD';
ALTER ROLE myprojectrootuser SET client_encoding TO 'utf8';
ALTER ROLE myprojectrootuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE myprojectrootuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE myfleetmanagerdb TO myprojectrootuser;
\q
```

Then update `settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myfleetmanagerdb',
        'USER': 'myprojectrootuser',
        'PASSWORD': 'YOUR_STRONG_PASSWORD',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

---

### 3️⃣ Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 4️⃣ Apply Migrations and Create Superuser
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

---

### command to update postal information and choice 

$env:PYTHONPATH="C:\Users\IRIS\OneDrive\Desktop\impala\Git\ranjanFleet"
$env:DJANGO_SETTINGS_MODULE="FleetManager.settings"
python utils/bin/load_postal_info.py --file utils/data/india_addresses.json --truncate
python utils/bin/load_choice_data.py --file utils/data/choice_seed_data.xlsx --truncate

### 5️⃣ Configure Gunicorn (App Server)
Gunicorn service file:  
`/etc/systemd/system/gunicorn-fleetmanager.service`
```ini
[Unit]
Description=Gunicorn for FleetManager (Django)
After=network.target

[Service]
User=deploy
Group=www-data
WorkingDirectory=/home/deploy/apps/fleet-manager
Environment="PATH=/home/deploy/apps/fleet-manager/.venv/bin"
ExecStart=/home/deploy/apps/fleet-manager/.venv/bin/gunicorn FleetManager.wsgi:application     --workers 3 --bind unix:/home/deploy/apps/fleet-manager/gunicorn.sock

[Install]
WantedBy=multi-user.target
```

Enable & start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn-fleetmanager
sudo systemctl start gunicorn-fleetmanager
```

---

### 6️⃣ Configure Nginx (Reverse Proxy)
File: `/etc/nginx/sites-available/fleetmanager`

```nginx
server {
    listen 80;
    server_name 147.79.66.63;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /home/deploy/apps/fleet-manager/staticfiles/;
    }

    location /media/ {
        alias /home/deploy/apps/fleet-manager/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/deploy/apps/fleet-manager/gunicorn.sock;
    }
}
```

Activate and restart:
```bash
sudo ln -s /etc/nginx/sites-available/fleetmanager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔁 Daily Management Commands

| Task | Command |
|------|----------|
| Restart Django backend | `sudo systemctl restart gunicorn-fleetmanager` |
| Restart Nginx | `sudo systemctl restart nginx` |
| Apply new DB migrations | `python manage.py migrate` |
| Collect static after code update | `python manage.py collectstatic --noinput` |
| Check logs (Gunicorn) | `sudo journalctl -u gunicorn-fleetmanager -n 50 --no-pager` |
| Check Nginx logs | `sudo tail -f /var/log/nginx/error.log` |
| Create superuser | `python manage.py createsuperuser` |

---

## 🧱 Data Seeding Utilities

Reusable scripts for loading reference data live under `utils/bin/`:

| Purpose | Command |
| ------- | ------- |
| Load postal information from JSON | `python utils/bin/load_postal_info.py --file utils/data/india_addresses.json --truncate` |
| Seed `configuration.Choice` records from Excel | `python utils/bin/load_choice_data.py --file utils/data/choice_seed_data.xlsx --truncate` |

Both scripts default to `DJANGO_SETTINGS_MODULE=FleetManager.settings` and support chunked updates for large datasets.

---

## 🧩 Troubleshooting

**1. 502 Bad Gateway**
```bash
sudo systemctl restart gunicorn-fleetmanager
sudo systemctl restart nginx
```

**2. CSS not loading**
Ensure `STATIC_URL` = `'/static/'` and paths match your Nginx alias.

**3. Database permission error**
```sql
ALTER DATABASE myfleetmanagerdb OWNER TO myprojectrootuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO myprojectrootuser;
```

**4. Code changed, not reflecting**
```bash
sudo systemctl restart gunicorn-fleetmanager
```

---

## 🔒 Security & Maintenance Tips

- Disable root SSH login; use `deploy` user only  
- Keep system updated:
```bash
sudo apt update && sudo apt upgrade -y
```
- Weekly PostgreSQL backup:
```bash
pg_dump myfleetmanagerdb > /home/deploy/backups/backup_$(date +%F).sql
```
- Enable HTTPS with Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## ✅ Quick Summary

| Component | Path / Command |
|------------|----------------|
| Project Root | `/home/deploy/apps/fleet-manager` |
| Gunicorn Socket | `/home/deploy/apps/fleet-manager/gunicorn.sock` |
| Nginx Config | `/etc/nginx/sites-available/fleetmanager` |
| Static Files | `/home/deploy/apps/fleet-manager/staticfiles` |
| Django Superuser | `python manage.py createsuperuser` |
| Restart All | `sudo systemctl restart gunicorn-fleetmanager nginx` |

### API Extensions

- `GET /api/v1/models/…` – model catalogue, metadata, and inference endpoints for downstream apps.
- `GET|POST /api/v1/admin/models/…` – authenticated CRUD management layer with feature-flag controls.

---

**Maintained by:** Ranjan Paul  
**Environment:** Ubuntu (Hostinger VPS)  
**App:** FleetManager (Django 5.x)



## 🔍 Django Migration Problem solution when migration not reflect in DB table 
## SQL Reference

### Purpose
During development or deployment, you may need to verify what SQL Django will run for each migration — for example, when debugging database schema issues or validating production changes.

The Django command below shows the SQL statements generated for a particular migration file:

```bash
python manage.py sqlmigrate <app_name> <migration_name>

# example
python manage.py sqlmigrate configuration 0003_alter_choice_category
```
## For multiple SQL migration bash script run
```bash

for cmd in \

"configuration 0003_alter_choice_category" \
"configuration 0004_alter_choice_category" 
do
  echo "---- $cmd ----"
  python manage.py sqlmigrate $cmd
  echo ""
done


```
## 🧩 Django Data Seed Execution (Linux Environment)

This section explains how to load initial data (such as postal info and choice data) into the database for the Fleet Manager Django application.

These scripts are used to populate essential data for configuration and location-based models, and **must be executed after successful migration**.

---

### ⚙️ Prerequisites
Before executing these commands:
1. Ensure your virtual environment is activated.  
2. Make sure your database is migrated and running.  
3. Confirm that the following files exist:
   - `utils/data/india_addresses.json`
   - `utils/data/choice_seed_data.xlsx`

---

### 🧭 Step-by-Step (For Ubuntu/Linux)

#### 1️⃣ Navigate to your project directory
```bash
cd /home/deploy/apps/fleet-manager

For Linux - 

export PYTHONPATH="/home/deploy/apps/fleet-manager"
export DJANGO_SETTINGS_MODULE="FleetManager.settings"


python utils/bin/load_postal_info.py --file utils/data/india_addresses.json --truncate
python utils/bin/load_choice_data.py --file utils/data/choice_seed_data.xlsx --truncate


windows:

$env:PYTHONPATH="C:\Users\IRIS\OneDrive\Desktop\impala\Git\ranjanFleet"
$env:DJANGO_SETTINGS_MODULE="FleetManager.settings"
python utils/bin/load_postal_info.py --file utils/data/india_addresses.json --truncate
python utils/bin/load_choice_data.py --file utils/data/choice_seed_data.xlsx --truncate