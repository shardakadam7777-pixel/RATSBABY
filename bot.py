import subprocess
import time
import os
import sys
import requests
from flask import Flask
from threading import Thread

app = Flask('')

def get_server_ip():
    try:
        ip = requests.get('https://api.ipify.org', timeout=5).text.strip()
        return ip if ip else "Unknown"
    except:
        try:
            ip = requests.get('https://ifconfig.me', timeout=5).text.strip()
            return ip if ip else "Unknown"
        except:
            return "Unknown"

@app.route('/')
def home():
    ip = get_server_ip()
    return f"Bot is running! Server IP: {ip}"

@app.route('/ip')
def show_ip():
    ip = get_server_ip()
    return f"Server IP: {ip}"

@app.route('/health')
def health():
    return "OK", 200

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    ip = get_server_ip()
    print(f"\n{'='*50}")
    print(f"🌐 WEB SERVER STARTED")
    print(f"📍 Server IP: {ip}")
    print(f"{'='*50}\n")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run_web_server, daemon=True)
    t.start()

def restart_bot():
    while True:
        try:
            current_directory = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(current_directory, 'paid.py')
            
            print("=" * 50)
            print("Starting Telegram Bot...")
            print("=" * 50)
            subprocess.run([sys.executable, '-u', script_path], check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"Bot crashed: {e}. Restarting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"Error: {e}. Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    keep_alive()
    restart_bot()