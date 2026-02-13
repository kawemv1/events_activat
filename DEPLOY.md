# Развёртывание бота на сервере

## Быстрый старт

1. **Создайте бота в @BotFather** и получите API-токен.

2. **Скопируйте проект на сервер** (VPS, облако).

3. **Установка:**
```bash
cd EventsBot\(Activat\)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

4. **Создайте `.env`:**
```env
API_KEY=ваш_токен_от_BotFather
```

5. **Запуск:**
```bash
python bot.py
```

## Запуск в фоне (systemd)

Создайте `/etc/systemd/system/eventsbot.service`:

```ini
[Unit]
Description=EventsBot Telegram
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/EventsBot(Activat)
Environment="PATH=/path/to/EventsBot(Activat)/venv/bin"
ExecStart=/path/to/EventsBot(Activat)/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable eventsbot
sudo systemctl start eventsbot
sudo systemctl status eventsbot
```

## Передача исходного кода

Соберите архив для отправки в Telegram @ukunyaa:

```bash
cd ..
zip -r EventsBot.zip "EventsBot(Activat)" -x "*.pyc" -x "*__pycache__*" -x "*.db" -x ".env" -x "venv/*"
```

Или отправьте папку через Git/облако. **Не включайте `.env`** с токеном в архив!
