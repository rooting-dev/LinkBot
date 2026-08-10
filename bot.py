import telebot
import logging
import time
import sqlite3
import os
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8730785188:AAGivzteX0n913kIUkmpXFyassN9UlgbqHc"
ADMIN_IDS = [7955873453, 8685590890]
CHANNEL_ID = -1003934085867

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN)

invite_links = {}
next_link_number = 1
creating_links = False

DB_NAME = 'bot_stats.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS link_stats (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_number INTEGER UNIQUE,
            invite_link TEXT,
            created_at TEXT,
            join_requests INTEGER DEFAULT 0,
            approved_requests INTEGER DEFAULT 0,
            declined_requests INTEGER DEFAULT 0,
            occupied_by TEXT DEFAULT NULL,
            occupied_by_id INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            card_number TEXT,
            crypto_wallet TEXT,
            stars_username TEXT,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_joins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            link_number INTEGER,
            joined_at TEXT,
            join_type TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invited_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            link_number INTEGER,
            invited_by INTEGER,
            invited_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            link_number INTEGER,
            total_invited INTEGER,
            payment_method TEXT,
            card_number TEXT,
            crypto_wallet TEXT,
            stars_username TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ База данных создана")

if not os.path.exists(DB_NAME):
    init_db()
else:
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='link_stats'")
        if not cursor.fetchone():
            conn.close()
            os.remove(DB_NAME)
            init_db()
        else:
            conn.close()
    except:
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)
        init_db()

def add_columns():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(link_stats)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'occupied_by' not in columns:
            cursor.execute('ALTER TABLE link_stats ADD COLUMN occupied_by TEXT DEFAULT NULL')
        if 'occupied_by_id' not in columns:
            cursor.execute('ALTER TABLE link_stats ADD COLUMN occupied_by_id INTEGER DEFAULT NULL')
        
        cursor.execute("PRAGMA table_info(withdraw_requests)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'payment_method' not in columns:
            cursor.execute('ALTER TABLE withdraw_requests ADD COLUMN payment_method TEXT DEFAULT NULL')
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка: {e}")

add_columns()

def save_link_to_db(link_number, invite_link):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO link_stats (link_number, invite_link, created_at) VALUES (?, ?, ?)',
                      (link_number, invite_link, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

def get_link_stats(link_number):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM link_stats WHERE link_number = ?', (link_number,))
        data = cursor.fetchone()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return None

def get_all_links_stats():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''SELECT link_number, invite_link, created_at, 
                          join_requests, approved_requests, declined_requests, occupied_by, occupied_by_id
                          FROM link_stats WHERE status = 'active' ORDER BY link_number''')
        data = cursor.fetchall()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return []

def get_invited_count(link_number):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM invited_users WHERE link_number = ?', (link_number,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return 0

def get_occupied_by(link_number):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT occupied_by, occupied_by_id FROM link_stats WHERE link_number = ?', (link_number,))
        data = cursor.fetchone()
        conn.close()
        if data:
            return data[0], data[1]
        return None, None
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return None, None

def occupy_link(link_number, username, user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE link_stats SET occupied_by = ?, occupied_by_id = ? WHERE link_number = ?', 
                      (username, user_id, link_number))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

def free_link(link_number):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE link_stats SET occupied_by = NULL, occupied_by_id = NULL WHERE link_number = ?', 
                      (link_number,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

def save_user_profile(user_id, card_number=None, crypto_wallet=None, stars_username=None):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles (user_id, card_number, crypto_wallet, stars_username, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, card_number, crypto_wallet, stars_username, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

def get_user_profile(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,))
        data = cursor.fetchone()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return None

def create_withdraw_request(user_id, username, first_name, link_number, total_invited, payment_method, card, crypto, stars):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO withdraw_requests 
            (user_id, username, first_name, link_number, total_invited, payment_method, card_number, crypto_wallet, stars_username, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, link_number, total_invited, payment_method, card, crypto, stars, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

def get_withdraw_requests(status='pending'):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM withdraw_requests WHERE status = ? ORDER BY created_at DESC', (status,))
        data = cursor.fetchall()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return []

def get_withdraw_requests_all():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM withdraw_requests ORDER BY created_at DESC')
        data = cursor.fetchall()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return []

def update_withdraw_status(request_id, status):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE withdraw_requests SET status = ?, processed_at = ? WHERE id = ?',
                      (status, datetime.now().isoformat(), request_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

def is_admin(user_id):
    return user_id in ADMIN_IDS

def create_channel_link(request_required=True):
    try:
        link = bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            creates_join_request=request_required,
            name=f"Ссылка #{len(invite_links) + 1}"
        )
        return link
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return None

def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_links = KeyboardButton("📋 Список ссылок")
    btn_get_link = KeyboardButton("🔗 Получить ссылку")
    btn_profile = KeyboardButton("👤 Мой профиль")
    btn_status = KeyboardButton("📊 Статус")
    btn_help = KeyboardButton("❓ Помощь")
    keyboard.row(btn_links, btn_get_link)
    keyboard.row(btn_profile, btn_status)
    keyboard.row(btn_help)
    return keyboard

def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_links = KeyboardButton("📋 Список ссылок")
    btn_get_link = KeyboardButton("🔗 Получить ссылку")
    btn_create = KeyboardButton("➕ Создать ссылки")
    btn_stats = KeyboardButton("📈 Статистика")
    btn_clear = KeyboardButton("🗑 Удалить все")
    btn_profile = KeyboardButton("👤 Мой профиль")
    btn_status = KeyboardButton("📊 Статус")
    btn_withdraw = KeyboardButton("💰 Заявки")
    btn_help = KeyboardButton("❓ Помощь")
    keyboard.row(btn_links, btn_get_link)
    keyboard.row(btn_create, btn_stats)
    keyboard.row(btn_clear, btn_profile)
    keyboard.row(btn_withdraw, btn_status)
    keyboard.row(btn_help)
    return keyboard

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    is_admin_user = is_admin(user_id)
    
    welcome = (
        "🌟 *Добро пожаловать!*\n\n"
        "📌 *Я бот для управления ссылками на канал*\n"
        "✅ Создавай и занимай ссылки\n"
        "📊 Смотри статистику приглашений\n"
        "💰 Получай выплаты за приглашённых\n\n"
        f"👑 *Статус:* {'🔑 Администратор' if is_admin_user else '👤 Пользователь'}"
    )
    
    if is_admin_user:
        bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['profile'])
def cmd_profile(message):
    user_id = message.from_user.id
    profile = get_user_profile(user_id)
    
    if profile:
        uid, card, crypto, stars, created = profile
        text = (
            f"👤 *Мой профиль*\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"💳 Карта: {card if card else '❌ Не указана'}\n"
            f"🪙 Крипто: {crypto if crypto else '❌ Не указан'}\n"
            f"⭐ Звёзды: {stars if stars else '❌ Не указан'}"
        )
    else:
        text = (
            f"👤 *Мой профиль*\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"💳 Карта: ❌ Не указана\n"
            f"🪙 Крипто: ❌ Не указан\n"
            f"⭐ Звёзды: ❌ Не указан"
        )
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("✏️ Заполнить профиль", callback_data="edit_profile"),
        InlineKeyboardButton("💰 Подать заявку", callback_data="withdraw")
    )
    
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=keyboard)

@bot.message_handler(commands=['links'])
def cmd_links(message):
    if not invite_links:
        bot.reply_to(message, "📭 *Нет ссылок*\n\nСоздай через '➕ Создать ссылки'", parse_mode="Markdown")
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    total = len(invite_links)
    used = 0
    free = 0
    
    for num in list(invite_links.keys()):
        occupied_name, occupied_id = get_occupied_by(num)
        
        if occupied_name:
            status = f"🔴 Занята @{occupied_name}"
            used += 1
        else:
            invited = get_invited_count(num)
            if invited > 0:
                status = f"🔴 Занята ({invited} чел)"
                used += 1
            else:
                status = "🟢 Свободна"
                free += 1
        
        keyboard.row(
            InlineKeyboardButton(
                f"#{num} - {status}", 
                callback_data=f"get_{num}"
            )
        )
    
    keyboard.row(
        InlineKeyboardButton("📊 Статистика", callback_data="total_stats"),
        InlineKeyboardButton("🔄 Обновить", callback_data="refresh_links")
    )
    
    if is_admin(message.from_user.id):
        keyboard.row(
            InlineKeyboardButton("➕ Создать ссылки", callback_data="show_create_menu")
        )
    
    text = (
        f"📋 *Список ссылок*\n\n"
        f"📌 Всего: {total}\n"
        f"🟢 Свободных: {free}\n"
        f"🔴 Занятых: {used}\n"
        f"👤 Приглашено: {sum(get_invited_count(n) for n in invite_links)}\n\n"
        f"👇 *Нажми на ссылку для управления*"
    )
    
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=keyboard)

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ *Нет прав*", parse_mode="Markdown")
        return
    
    all_stats = get_all_links_stats()
    if not all_stats:
        bot.reply_to(message, "📭 *Нет данных*", parse_mode="Markdown")
        return
    
    text = "📊 *Статистика*\n\n"
    total_invited = 0
    total_occupied = 0
    
    for data in all_stats:
        if len(data) >= 7:
            num = data[0]
            occupied_name = data[6] if len(data) > 6 else None
            invited = get_invited_count(num)
            total_invited += invited
            
            if occupied_name:
                status = f"🔴 @{occupied_name}"
                total_occupied += 1
            elif invited > 0:
                status = "🔴 Занята"
                total_occupied += 1
            else:
                status = "🟢 Свободна"
            
            text += f"*#{num}*: {status} | 👤{invited}\n"
    
    text += f"\n📌 *Всего приглашено:* {total_invited}"
    text += f"\n🔴 *Занято:* {total_occupied}"
    text += f"\n📌 *Ссылок:* {len(all_stats)}"
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['linksser'])
def cmd_create_links(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ *Нет прав*", parse_mode="Markdown")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.row(
        InlineKeyboardButton("1️⃣", callback_data="create_1"),
        InlineKeyboardButton("2️⃣", callback_data="create_2"),
        InlineKeyboardButton("3️⃣", callback_data="create_3"),
        InlineKeyboardButton("5️⃣", callback_data="create_5"),
        InlineKeyboardButton("🔟", callback_data="create_10"),
        InlineKeyboardButton("15️⃣", callback_data="create_15")
    )
    keyboard.row(
        InlineKeyboardButton("20️⃣", callback_data="create_20"),
        InlineKeyboardButton("25️⃣", callback_data="create_25"),
        InlineKeyboardButton("30️⃣", callback_data="create_30"),
        InlineKeyboardButton("50️⃣", callback_data="create_50")
    )
    keyboard.row(
        InlineKeyboardButton("✏️ Своё", callback_data="custom_count"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
    )
    
    bot.reply_to(
        message,
        "🔧 *Создание ссылок*\n\nВыбери количество:\n⚠️ *Максимум:* 50",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['withdraws'])
def cmd_withdraws(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ *Нет прав*", parse_mode="Markdown")
        return
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("📋 Активные", callback_data="show_pending"),
        InlineKeyboardButton("📜 История", callback_data="show_all_withdraws")
    )
    
    pending = get_withdraw_requests('pending')
    bot.reply_to(
        message,
        f"💰 *Заявки*\n\n📌 Активных: {len(pending)}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    global invite_links, next_link_number, creating_links
    
    try:
        if call.data.startswith("create_"):
            count = int(call.data.split("_")[1])
            create_links_with_settings(call.message, count)
            bot.answer_callback_query(call.id, f"✅ Создаю {count} ссылок")
            return
        
        elif call.data == "custom_count":
            bot.answer_callback_query(call.id, "✏️ Введите число")
            msg = bot.send_message(call.message.chat.id, "✏️ Введите число (1-50):")
            bot.register_next_step_handler(msg, process_custom_count)
            return
        
        elif call.data == "show_create_menu":
            cmd_create_links(call.message)
            bot.answer_callback_query(call.id, "🔧 Меню создания")
            return
        
        elif call.data.startswith("occupy_"):
            link_number = int(call.data.split("_")[1])
            if link_number in invite_links:
                username = call.from_user.username or f"user_{call.from_user.id}"
                user_id = call.from_user.id
                occupied_name, occupied_id = get_occupied_by(link_number)
                if occupied_name:
                    bot.answer_callback_query(call.id, f"❌ Уже занята @{occupied_name}")
                    return
                if occupy_link(link_number, username, user_id):
                    bot.answer_callback_query(call.id, f"✅ Занята @{username}")
                    cmd_links(call.message)
                else:
                    bot.answer_callback_query(call.id, "❌ Ошибка")
            return
        
        elif call.data.startswith("free_"):
            link_number = int(call.data.split("_")[1])
            if link_number in invite_links:
                if free_link(link_number):
                    bot.answer_callback_query(call.id, "✅ Освобождена")
                    cmd_links(call.message)
                else:
                    bot.answer_callback_query(call.id, "❌ Ошибка")
            return
        
        elif call.data.startswith("get_"):
            link_number = int(call.data.split("_")[1])
            if link_number in invite_links:
                link = invite_links[link_number]
                occupied_name, occupied_id = get_occupied_by(link_number)
                invited = get_invited_count(link_number)
                
                if occupied_name:
                    status = f"🔴 Занята @{occupied_name}"
                elif invited > 0:
                    status = f"🔴 Занята ({invited} чел)"
                else:
                    status = "🟢 Свободна"
                
                keyboard = InlineKeyboardMarkup()
                keyboard.row(InlineKeyboardButton("📋 Копировать", callback_data=f"copy_{link_number}"))
                
                if occupied_name:
                    if is_admin(call.from_user.id):
                        keyboard.row(InlineKeyboardButton("🔓 Освободить", callback_data=f"free_{link_number}"))
                else:
                    keyboard.row(InlineKeyboardButton("🔒 Занять", callback_data=f"occupy_{link_number}"))
                
                keyboard.row(
                    InlineKeyboardButton("📊 Статистика", callback_data=f"info_{link_number}"),
                    InlineKeyboardButton("🔙 Назад", callback_data="back_to_links")
                )
                
                bot.edit_message_text(
                    f"🔗 *Ссылка #{link_number}*\n`{link.invite_link}`\n\n📊 {status}\n👤 Приглашено: {invited}",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                bot.answer_callback_query(call.id, "✅ Готово")
            return
        
        elif call.data.startswith("copy_"):
            link_number = int(call.data.split("_")[1])
            if link_number in invite_links:
                link = invite_links[link_number]
                bot.answer_callback_query(call.id, "✅ Скопировано")
                bot.send_message(call.message.chat.id, f"🔗 `{link.invite_link}`", parse_mode="Markdown")
            return
        
        elif call.data.startswith("info_"):
            link_number = int(call.data.split("_")[1])
            if link_number in invite_links:
                stats = get_link_stats(link_number)
                invited = get_invited_count(link_number)
                occupied_name, occupied_id = get_occupied_by(link_number)
                if stats:
                    if occupied_name:
                        st = f"🔴 Занята @{occupied_name}"
                    elif invited > 0:
                        st = f"🔴 Занята ({invited} чел)"
                    else:
                        st = "🟢 Свободна"
                    
                    text = (
                        f"📊 *Статистика #{link_number}*\n\n"
                        f"🔗 `{stats[2]}`\n"
                        f"📅 {stats[3][:16] if stats[3] else 'Неизвестно'}\n"
                        f"👤 Приглашено: {invited}\n"
                        f"📊 {st}"
                    )
                    bot.answer_callback_query(call.id, "📊 Статистика")
                    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
            return
        
        elif call.data == "edit_profile":
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.row(
                InlineKeyboardButton("💳 Карта РФ", callback_data="set_card"),
                InlineKeyboardButton("🪙 Крипто", callback_data="set_crypto"),
                InlineKeyboardButton("⭐ Юзернейм", callback_data="set_stars")
            )
            keyboard.row(InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile"))
            bot.edit_message_text(
                "✏️ *Выбери что заполнить:*",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            bot.answer_callback_query(call.id, "✏️ Редактирование")
            return
        
        elif call.data == "set_card":
            bot.answer_callback_query(call.id, "💳 Введите карту")
            msg = bot.send_message(call.message.chat.id, "💳 Введите номер карты (16 цифр):")
            bot.register_next_step_handler(msg, set_card_handler)
            return
        
        elif call.data == "set_crypto":
            bot.answer_callback_query(call.id, "🪙 Введите кошелек")
            msg = bot.send_message(call.message.chat.id, "🪙 Введите адрес крипто кошелька:")
            bot.register_next_step_handler(msg, set_crypto_handler)
            return
        
        elif call.data == "set_stars":
            bot.answer_callback_query(call.id, "⭐ Введите юзернейм")
            msg = bot.send_message(call.message.chat.id, "⭐ Введите юзернейм для звёзд (с @):")
            bot.register_next_step_handler(msg, set_stars_handler)
            return
        
        elif call.data == "withdraw":
            user_id = call.from_user.id
            profile = get_user_profile(user_id)
            
            if not profile or (not profile[1] and not profile[2] and not profile[3]):
                bot.answer_callback_query(call.id, "❌ Сначала заполни профиль!")
                return
            
            link_number = None
            total_invited = 0
            for num in invite_links:
                occupied_name, occupied_id = get_occupied_by(num)
                if occupied_id == user_id:
                    invited = get_invited_count(num)
                    total_invited = invited
                    link_number = num
                    break
            
            if not link_number:
                for num in invite_links:
                    invited = get_invited_count(num)
                    if invited > 0:
                        occupied_name, occupied_id = get_occupied_by(num)
                        if not occupied_name:
                            link_number = num
                            total_invited = invited
                            break
            
            if not link_number:
                bot.answer_callback_query(call.id, "❌ Нет активной ссылки!")
                return
            
            if total_invited < 150:
                bot.answer_callback_query(call.id, f"❌ Нужно 150+ человек! У тебя {total_invited}")
                return
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.row(
                InlineKeyboardButton("💳 На карту", callback_data=f"pay_method_card_{link_number}"),
                InlineKeyboardButton("🪙 Крипто", callback_data=f"pay_method_crypto_{link_number}")
            )
            keyboard.row(
                InlineKeyboardButton("⭐ Звёзды", callback_data=f"pay_method_stars_{link_number}"),
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")
            )
            
            bot.edit_message_text(
                f"💰 *Выбери способ получения выплаты*\n\n"
                f"🔗 Ссылка #{link_number}\n"
                f"👥 Приглашено: {total_invited} чел\n\n"
                f"👇 *Куда получить выплату?*",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            bot.answer_callback_query(call.id, "💰 Выбор способа")
            return
        
        elif call.data.startswith("pay_method_"):
            parts = call.data.split("_")
            method = parts[2]
            link_number = int(parts[3])
            user_id = call.from_user.id
            
            profile = get_user_profile(user_id)
            if not profile:
                bot.answer_callback_query(call.id, "❌ Ошибка профиля!")
                return
            
            username = call.from_user.username or f"user_{user_id}"
            first_name = call.from_user.first_name or "Unknown"
            total_invited = get_invited_count(link_number)
            
            card = profile[1] if profile[1] else "Не указана"
            crypto = profile[2] if profile[2] else "Не указан"
            stars = profile[3] if profile[3] else "Не указан"
            
            method_names = {
                'card': '💳 На карту',
                'crypto': '🪙 Крипто',
                'stars': '⭐ Звёзды'
            }
            
            if create_withdraw_request(user_id, username, first_name, link_number, total_invited, method_names[method], card, crypto, stars):
                bot.answer_callback_query(call.id, "✅ Заявка отправлена!")
                
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM withdraw_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 1', (user_id,))
                req_data = cursor.fetchone()
                conn.close()
                
                if req_data:
                    req_id = req_data[0]
                    for admin_id in ADMIN_IDS:
                        try:
                            keyboard = InlineKeyboardMarkup()
                            keyboard.row(
                                InlineKeyboardButton("✅ Выплатить", callback_data=f"approve_{req_id}"),
                                InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{req_id}")
                            )
                            
                            bot.send_message(
                                admin_id,
                                f"💰 *НОВАЯ ЗАЯВКА!*\n\n"
                                f"👤 {first_name} (@{username})\n"
                                f"🆔 `{user_id}`\n"
                                f"🔗 Ссылка #{link_number}\n"
                                f"👥 Приглашено: {total_invited} чел\n"
                                f"💳 Способ: {method_names[method]}\n"
                                f"💳 Карта: {card}\n"
                                f"🪙 Крипто: {crypto}\n"
                                f"⭐ Звёзды: {stars}",
                                parse_mode="Markdown",
                                reply_markup=keyboard
                            )
                        except Exception as e:
                            logger.error(f"Ошибка уведомления: {e}")
                
                bot.edit_message_text(
                    f"✅ *Заявка отправлена!*\n\n"
                    f"👤 {total_invited} человек приглашено\n"
                    f"💳 Способ: {method_names[method]}\n"
                    f"📌 Ожидай подтверждения",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown"
                )
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка!")
            return
        
        elif call.data == "show_pending":
            if not is_admin(call.from_user.id):
                bot.answer_callback_query(call.id, "⛔ Нет прав")
                return
            show_withdraws(call.message, 'pending')
            bot.answer_callback_query(call.id, "📋 Активные")
            return
        
        elif call.data == "show_all_withdraws":
            if not is_admin(call.from_user.id):
                bot.answer_callback_query(call.id, "⛔ Нет прав")
                return
            show_withdraws(call.message, 'all')
            bot.answer_callback_query(call.id, "📜 История")
            return
        
        elif call.data.startswith("approve_"):
            if not is_admin(call.from_user.id):
                bot.answer_callback_query(call.id, "⛔ Нет прав")
                return
            req_id = int(call.data.split("_")[1])
            if update_withdraw_status(req_id, 'paid'):
                bot.answer_callback_query(call.id, "✅ Выплачено!")
                bot.edit_message_text(
                    "✅ *Заявка выплачена*",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown"
                )
                show_withdraws(call.message, 'pending')
            return
        
        elif call.data.startswith("reject_"):
            if not is_admin(call.from_user.id):
                bot.answer_callback_query(call.id, "⛔ Нет прав")
                return
            req_id = int(call.data.split("_")[1])
            if update_withdraw_status(req_id, 'rejected'):
                bot.answer_callback_query(call.id, "❌ Отказано")
                bot.edit_message_text(
                    "❌ *Заявка отклонена*",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown"
                )
                show_withdraws(call.message, 'pending')
            return
        
        elif call.data == "back_to_profile":
            cmd_profile(call.message)
            bot.answer_callback_query(call.id, "🔙 Назад")
            return
        
        elif call.data == "back_to_links":
            cmd_links(call.message)
            bot.answer_callback_query(call.id, "📋 Список")
            return
        
        elif call.data == "back_to_menu":
            user_id = call.from_user.id
            if is_admin(user_id):
                bot.send_message(call.message.chat.id, "📋 *Меню*", parse_mode="Markdown", reply_markup=get_admin_keyboard())
            else:
                bot.send_message(call.message.chat.id, "📋 *Меню*", parse_mode="Markdown", reply_markup=get_main_keyboard())
            bot.answer_callback_query(call.id, "🔙 Меню")
            return
        
        elif call.data == "total_stats":
            cmd_stats(call.message)
            bot.answer_callback_query(call.id, "📊 Статистика")
            return
        
        elif call.data == "refresh_links":
            cmd_links(call.message)
            bot.answer_callback_query(call.id, "🔄 Обновлено")
            return
        
        elif call.data == "confirm_clear_all":
            if not is_admin(call.from_user.id):
                bot.answer_callback_query(call.id, "⛔ Нет прав")
                return
            
            deleted = 0
            for num, link in list(invite_links.items()):
                try:
                    bot.revoke_chat_invite_link(CHANNEL_ID, link.invite_link)
                    deleted += 1
                    time.sleep(0.1)
                except:
                    pass
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM link_stats')
            cursor.execute('DELETE FROM user_joins')
            cursor.execute('DELETE FROM invited_users')
            conn.commit()
            conn.close()
            
            invite_links = {}
            next_link_number = 1
            
            bot.answer_callback_query(call.id, f"✅ Удалено {deleted}")
            bot.edit_message_text(
                f"✅ *ВСЕ УДАЛЕНО!*\n\n🗑 {deleted} ссылок",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
            return
        
        elif call.data == "cancel_clear":
            bot.answer_callback_query(call.id, "❌ Отменено")
            bot.edit_message_text("❌ Отменено", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return
    
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, f"❌ Ошибка")

def show_withdraws(message, mode='pending'):
    if mode == 'pending':
        requests = get_withdraw_requests('pending')
        title = "📋 *Активные заявки*"
    else:
        requests = get_withdraw_requests_all()
        title = "📜 *История заявок*"
    
    if not requests:
        bot.send_message(message.chat.id, "📭 *Пусто*", parse_mode="Markdown")
        return
    
    for req in requests:
        if len(req) >= 12:
            req_id, user_id, username, first_name, link_num, total, method, card, crypto, stars, status, created, processed = req
        else:
            continue
        
        if status == 'pending':
            st = "⏳ Ожидает"
        elif status == 'paid':
            st = "✅ Выплачено"
        else:
            st = "❌ Отказано"
        
        text = (
            f"📋 *Заявка #{req_id}*\n\n"
            f"👤 {first_name} (@{username or user_id})\n"
            f"🆔 `{user_id}`\n"
            f"🔗 Ссылка #{link_num}\n"
            f"👥 Приглашено: {total} чел\n"
            f"💳 Способ: {method}\n"
            f"💳 Карта: {card}\n"
            f"🪙 Крипто: {crypto}\n"
            f"⭐ Звёзды: {stars}\n"
            f"📅 {created[:16] if created else 'Неизвестно'}\n"
            f"📊 {st}"
        )
        
        if status == 'pending':
            keyboard = InlineKeyboardMarkup()
            keyboard.row(
                InlineKeyboardButton("✅ Выплатить", callback_data=f"approve_{req_id}"),
                InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{req_id}")
            )
            bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            if processed:
                text += f"\n📅 Обработано: {processed[:16]}"
            bot.send_message(message.chat.id, text, parse_mode="Markdown")

def set_card_handler(message):
    user_id = message.from_user.id
    card = message.text.strip().replace(' ', '')
    if len(card) == 16 and card.isdigit():
        profile = get_user_profile(user_id)
        if profile:
            save_user_profile(user_id, card, profile[2], profile[3])
        else:
            save_user_profile(user_id, card, None, None)
        bot.reply_to(message, "✅ *Карта сохранена!*", parse_mode="Markdown")
        cmd_profile(message)
    else:
        bot.reply_to(message, "❌ *Неверный формат! Нужно 16 цифр*", parse_mode="Markdown")

def set_crypto_handler(message):
    user_id = message.from_user.id
    crypto = message.text.strip()
    if len(crypto) > 5:
        profile = get_user_profile(user_id)
        if profile:
            save_user_profile(user_id, profile[1], crypto, profile[3])
        else:
            save_user_profile(user_id, None, crypto, None)
        bot.reply_to(message, "✅ *Кошелек сохранен!*", parse_mode="Markdown")
        cmd_profile(message)
    else:
        bot.reply_to(message, "❌ *Слишком короткий адрес*", parse_mode="Markdown")

def set_stars_handler(message):
    user_id = message.from_user.id
    stars = message.text.strip()
    if stars.startswith('@') and len(stars) > 1:
        profile = get_user_profile(user_id)
        if profile:
            save_user_profile(user_id, profile[1], profile[2], stars)
        else:
            save_user_profile(user_id, None, None, stars)
        bot.reply_to(message, "✅ *Юзернейм сохранен!*", parse_mode="Markdown")
        cmd_profile(message)
    else:
        bot.reply_to(message, "❌ *Введи юзернейм с @*", parse_mode="Markdown")

def process_custom_count(message):
    try:
        count = int(message.text)
        if count <= 0 or count > 50:
            bot.reply_to(message, "❌ *От 1 до 50*", parse_mode="Markdown")
            return
        create_links_with_settings(message, count)
    except:
        bot.reply_to(message, "❌ *Введи число*", parse_mode="Markdown")

def create_links_with_settings(message, count):
    global next_link_number, creating_links
    
    if creating_links:
        bot.send_message(message.chat.id, "⏳ *Подожди...*", parse_mode="Markdown")
        return
    
    creating_links = True
    status_msg = bot.send_message(message.chat.id, f"⏳ *Создаю {count} ссылок...*", parse_mode="Markdown")
    
    created = 0
    for i in range(count):
        try:
            link = create_channel_link(True)
            if link:
                invite_links[next_link_number] = link
                save_link_to_db(next_link_number, link.invite_link)
                next_link_number += 1
                created += 1
                time.sleep(0.3)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
    
    creating_links = False
    
    bot.edit_message_text(
        f"✅ *Создано: {created}*\n📊 Всего: {len(invite_links)}",
        chat_id=status_msg.chat.id,
        message_id=status_msg.message_id,
        parse_mode="Markdown"
    )
    
    if created > 0:
        cmd_links(message)

def save_invited_user(user_id, username, first_name, last_name, link_number, invited_by):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO invited_users (user_id, username, first_name, last_name, link_number, invited_by, invited_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, link_number, invited_by, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

@bot.chat_member_handler()
def handle_chat_member(update):
    try:
        cm = update.chat_member
        if cm.new_chat_member.status in ['member', 'administrator']:
            user = cm.new_chat_member.user
            if user.is_bot:
                return
            
            link_number = None
            for num, link in invite_links.items():
                if get_invited_count(num) == 0:
                    link_number = num
                    break
            
            if link_number is None and invite_links:
                for num, link in invite_links.items():
                    link_number = num
                    break
            
            if link_number:
                save_invited_user(user.id, user.username, user.first_name, user.last_name, link_number, user.id)
                invited = get_invited_count(link_number)
                
                name = user.first_name or user.username or f"ID:{user.id}"
                uname = f" (@{user.username})" if user.username else ""
                
                for admin_id in ADMIN_IDS:
                    try:
                        bot.send_message(
                            admin_id,
                            f"✅ *Новый участник!*\n\n👤 {name}{uname}\n🔗 Ссылка #{link_number}\n👥 Всего: {invited}",
                            parse_mode="Markdown"
                        )
                    except:
                        pass
                
                try:
                    bot.send_message(
                        CHANNEL_ID,
                        f"🎉 {name}{uname} присоединился по ссылке #{link_number}!",
                        parse_mode="Markdown"
                    )
                except:
                    pass
                
                logger.info(f"Новый участник {user.id} по ссылке #{link_number}")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

@bot.chat_join_request_handler()
def handle_join_request(update):
    try:
        link_number = None
        for num, link in invite_links.items():
            if link.invite_link in update.invite_link.invite_link:
                link_number = num
                break
        
        if link_number:
            logger.info(f"Запрос от {update.from_user.id} по ссылке #{link_number}")
            
            for admin_id in ADMIN_IDS:
                try:
                    keyboard = InlineKeyboardMarkup()
                    keyboard.row(
                        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{update.from_user.id}_{link_number}"),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_{update.from_user.id}_{link_number}")
                    )
                    bot.send_message(
                        admin_id,
                        f"📨 *Запрос на вступление*\n\n👤 {update.from_user.first_name or 'Unknown'}\n🔗 Ссылка #{link_number}",
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                except:
                    pass
    except Exception as e:
        logger.error(f"Ошибка: {e}")

def check_bot_permissions():
    try:
        bot_info = bot.get_me()
        logger.info(f"🤖 Бот: @{bot_info.username}")
        chat = bot.get_chat(CHANNEL_ID)
        logger.info(f"📌 Канал: {chat.title}")
        
        member = bot.get_chat_member(CHANNEL_ID, bot_info.id)
        if member.status in ['creator', 'administrator']:
            logger.info("✅ Бот админ в канале")
            if member.can_invite_users:
                logger.info("✅ Может создавать ссылки")
            else:
                logger.warning("⚠️ Нет права создавать ссылки!")
        else:
            logger.warning("⚠️ Бот не админ!")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

def cmd_get_link(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ *Укажи номер:* `/getlink 5`", parse_mode="Markdown")
        return
    
    try:
        link_number = int(args[1])
        if link_number in invite_links:
            link = invite_links[link_number]
            occupied_name, occupied_id = get_occupied_by(link_number)
            invited = get_invited_count(link_number)
            
            if occupied_name:
                status = f"🔴 Занята @{occupied_name}"
            elif invited > 0:
                status = f"🔴 Занята ({invited} чел)"
            else:
                status = "🟢 Свободна"
            
            keyboard = InlineKeyboardMarkup()
            keyboard.row(InlineKeyboardButton("📋 Копировать", callback_data=f"copy_{link_number}"))
            
            if occupied_name:
                if is_admin(message.from_user.id):
                    keyboard.row(InlineKeyboardButton("🔓 Освободить", callback_data=f"free_{link_number}"))
            else:
                keyboard.row(InlineKeyboardButton("🔒 Занять", callback_data=f"occupy_{link_number}"))
            
            bot.reply_to(
                message,
                f"🔗 *Ссылка #{link_number}*\n`{link.invite_link}`\n\n📊 {status}",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            bot.reply_to(message, "❌ *Не найдена*", parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ *Введи число*", parse_mode="Markdown")

def cmd_clear(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ *Нет прав*", parse_mode="Markdown")
        return
    
    if not invite_links:
        bot.reply_to(message, "📭 *Нет ссылок*", parse_mode="Markdown")
        return
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("✅ Да, удалить всё", callback_data="confirm_clear_all"),
        InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel_clear")
    )
    
    bot.reply_to(
        message,
        f"⚠️ *УДАЛИТЬ ВСЁ?*\n\n📌 {len(invite_links)} ссылок\n❗️ *Безвозвратно*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    is_admin_user = is_admin(user_id)
    
    if message.text == "📋 Список ссылок":
        cmd_links(message)
    elif message.text == "🔗 Получить ссылку":
        bot.reply_to(
            message,
            "🔗 *Как получить ссылку:*\n\n"
            "1️⃣ Нажми '📋 Список ссылок'\n"
            "2️⃣ Выбери свободную\n"
            "3️⃣ Нажми на неё\n"
            "4️⃣ Скопируй\n\n"
            "Или: `/getlink НОМЕР`",
            parse_mode="Markdown"
        )
    elif message.text == "👤 Мой профиль":
        cmd_profile(message)
    elif message.text == "📊 Статус":
        bot.reply_to(
            message,
            f"📊 *Статус*\n\n"
            f"📌 Ссылок: {len(invite_links)}\n"
            f"👤 Приглашено: {sum(get_invited_count(n) for n in invite_links)}\n"
            f"🔴 Занято: {sum(1 for n in invite_links if get_occupied_by(n)[0])}\n"
            f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="Markdown"
        )
    elif message.text == "❓ Помощь":
        help_text = (
            "❓ *Помощь*\n\n"
            "📌 *Кнопки меню:*\n"
            "📋 Список ссылок - все ссылки\n"
            "🔗 Получить ссылку - инструкция\n"
            "👤 Мой профиль - реквизиты\n"
            "📊 Статус - статистика\n\n"
            "🔑 *Админ-панель:*\n"
            "➕ Создать ссылки - новые\n"
            "📈 Статистика - полная\n"
            "🗑 Удалить все - очистка\n"
            "💰 Заявки - управление выплатами"
        )
        bot.reply_to(message, help_text, parse_mode="Markdown")
    elif is_admin_user:
        if message.text == "➕ Создать ссылки":
            cmd_create_links(message)
        elif message.text == "📈 Статистика":
            cmd_stats(message)
        elif message.text == "🗑 Удалить все":
            cmd_clear(message)
        elif message.text == "💰 Заявки":
            cmd_withdraws(message)

if __name__ == "__main__":
    logger.info("🚀 Запуск бота...")
    check_bot_permissions()
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"Ошибка: {e}")