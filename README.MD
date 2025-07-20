# VPSphere v3.3 - Telegram Server Manager Bot

Bot Telegram untuk mengelola server (VPS) langsung dari Telegram.

### Fitur Utama
- Jalankan perintah shell (`ls`, `nmap`, `sqlmap`, dll.).
- Upload & download file (maksimal 2GB).
- Notifikasi **login SSH baru** secara real-time.
- Monitoring uptime, memori, dan disk server.

---

## Instalasi

### 1. Clone Repository
```bash
git clone https://github.com/Azyyyl/VPSphere.git
cd VPSphere
```

### 2. Buat Virtual Environment & Install Dependency
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Buat File `.env`
Buat file `.env` di folder proyek, lalu isi dengan:
```env
BOT_TOKEN=token_bot_telegram
USER_ID=user_id_telegram
```

### 4. Jalankan Bot Secara Manual (Opsional)
```bash
python3 bot.py
```

---

## Menjalankan Sebagai Service (systemd)

### 1. Buat Service File
Buat file service:
```bash
sudo nano /etc/systemd/system/vpsphere-bot.service
```

Isi dengan:
```ini
[Unit]
Description=VPSphere Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/vpsphere-bot
ExecStart=/opt/vpsphere-bot/venv/bin/python3 /opt/vpsphere-bot/bot.py
Restart=always
RestartSec=5
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

**Catatan:**
- Ganti `User=ubuntu` dengan user yang sesuai.
- Pastikan path `/opt/vpsphere-bot` sesuai lokasi clone project.

---

### 2. Aktifkan & Jalankan Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable vpsphere-bot
sudo systemctl start vpsphere-bot
sudo systemctl status vpsphere-bot
```

### 3. Cek Log Bot
```bash
journalctl -u vpsphere-bot -f
```

---

## Struktur Project
```
vpsphere-bot/
├── bot.py
├── requirements.txt
├── README.md
└── .env (dibuat manual)
```

---

## Lisensi
Proyek ini dikembangkan oleh **Azylx001**.  
Gunakan dengan bijak untuk keperluan manajemen server.
