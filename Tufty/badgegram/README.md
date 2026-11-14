# Installation and Setup

Requires Python 3, pip, and a Telegram account. Compatible with Linux, Windows, macOS, and BSD systems. A Proxmox LXC container can also be used.

Edit `__init__.py` and configure:

- `SERVER_IP` – Server IP address.
- `CHAT_ID` – Retrieved from `http://SERVER_IP/api/chats`.

In `proxy.py`, configure `api_id` and `api_hash` using https://my.telegram.org/apps.

Install Python 3 and pip if necessary, then install the dependencies:

```bash
pip install telethon fastapi uvicorn
```

In the directory containing `proxy.py`, start the proxy:

```bash
uvicorn proxy:app --host 0.0.0.0 --port 8080
```

Log in to Telegram when prompted.

**Security warning:** The server does not implement authentication. Only run it on trusted networks. Do not expose port `8080` to the public internet.
