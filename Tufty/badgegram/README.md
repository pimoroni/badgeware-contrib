Change the SERVER_IP and CHAT_ID (get from http://server_ip/api/chats ) in the __init__.py and api_id and api_hash in proxy.py (get from https://my.telegram.org/apps ).

This needs a PROXY SERVER:
`pip install telethon fastapi uvicorn`
then in a directory with proxy.py run
`uvicorn proxy:app --host 0.0.0.0 --port 8080`
And log into telegram.

I use a proxmox lxc as a server but any linux device with debian shall be okay.
