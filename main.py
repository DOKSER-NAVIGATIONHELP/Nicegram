import telebot
from telebot import types
import sqlite3
import time

# === НАСТРОЙКИ ===
TOKEN = '8636495498:AAHg4f2kdBeNoLYqZ5m17DgdOcHriZxoXTw'
ADMIN_IDS = [5379659751] 
USERBOT_ID = 8137569879  
DB_PATH = 'happy_rp.db'

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# === ТОВАРЫ И ЦЕНЫ (RP) ===
ITEMS = {
    'cigs': {'name': '🚬 Happy-Сигары', 'price': 50, 'min': 2, 'desc': 'Легкий расслабляющий эффект. Идеальный выбор для вечерних тусовок.'},
    'pills': {'name': '💊 Happy-Таблетки', 'price': 80, 'min': 2, 'desc': 'Дает мощный заряд энергии на несколько часов.'},
    'powder': {'name': '🍚 Happy-Порошок', 'price': 120, 'min': 3, 'desc': 'Элитный товар для VIP-клиентов. Максимальный эффект, полное погружение.'}
}

# === ИНИЦИАЛИЗАЦИЯ БД ===
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    return conn

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, role TEXT DEFAULT 'user', shift INTEGER DEFAULT 0, drops INTEGER DEFAULT 0, earned INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS job_apps (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, fio TEXT, age TEXT, photo TEXT, status TEXT DEFAULT 'pending')''')
        c.execute('''CREATE TABLE IF NOT EXISTS inventory (user_id INTEGER, item TEXT, qty INTEGER, PRIMARY KEY (user_id, item))''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, item TEXT, qty INTEGER, price INTEGER, check_id TEXT, status TEXT, worker_id INTEGER, photo TEXT, description TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS weight_drops (id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER, item TEXT, qty INTEGER, photo TEXT, description TEXT, status TEXT DEFAULT 'pending')''')
        c.execute('''CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, order_id INTEGER, text TEXT, status TEXT DEFAULT 'open')''')
        conn.commit()

init_db()

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def get_user(user_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        conn.commit()
        return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

def log_to_admins(text):
    for adm in ADMIN_IDS:
        try: bot.send_message(adm, f"🛡 <b>LOG-СИСТЕМА:</b>\n{text}")
        except: pass

# === КОМАНДЫ (СЛЭШ-МЕНЮ) ===
@bot.message_handler(commands=['support'])
def cmd_support(message):
    call_mock = type('obj', (object,), {'message': message, 'from_user': message.from_user})
    support_menu(call_mock)

@bot.message_handler(commands=['orders'])
def cmd_orders(message):
    call_mock = type('obj', (object,), {'message': message, 'from_user': message.from_user, 'id': '0'})
    my_orders(call_mock)

@bot.message_handler(commands=['faq', 'help'])
def cmd_faq(message):
    call_mock = type('obj', (object,), {'message': message, 'from_user': message.from_user})
    faq_menu(call_mock)

@bot.message_handler(commands=['work'])
def cmd_work(message):
    call_mock = type('obj', (object,), {'message': message, 'from_user': message.from_user, 'id': '0'})
    job_menu(call_mock)

# === ГЛАВНОЕ МЕНЮ ===
@bot.message_handler(commands=['start', 'menu'])
def start_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    role = user[1]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Ассортимент | Купить", callback_data="shop_menu"))
    
    row2 = [
        types.InlineKeyboardButton("Мои заказы", callback_data="my_orders"),
        types.InlineKeyboardButton("Помощь", callback_data="faq_menu")
    ]
    markup.row(*row2)
    markup.add(types.InlineKeyboardButton("Тех. Поддержка", callback_data="support_menu"))
    markup.add(types.InlineKeyboardButton("Трудоустройство", callback_data="job_menu"))
    
    if role == 'worker' or uid in ADMIN_IDS:
        markup.add(types.InlineKeyboardButton("Панель Курьера", callback_data="worker_menu"))
    if uid in ADMIN_IDS:
        markup.add(types.InlineKeyboardButton("👑 ПАНЕЛЬ УПРАВЛЕНИЯ", callback_data="admin_menu"))
        
    text = (
        "<b>Добро пожаловать в HAPPY SHOP</b>\n\n"
        "Лучший маркет в Штате Надежные клады, моментальная выдача, "
        "высшее качество стаффа.\n\n"
        "<i>Выбери нужный раздел в меню ниже или используй команды:</i>\n"
        "<code>/support</code> - Поддержка\n"
        "<code>/orders</code> - Твои заказы\n"
        "<code>/faq</code> - Правила\n"
        "<code>/work</code> - Работа"
    )
    
    if hasattr(message, 'data'):
        bot.edit_message_text(text, message.message.chat.id, message.message.message_id, reply_markup=markup)
    else:
        bot.send_message(uid, text, reply_markup=markup)

# === ТЕХ. ПОДДЕРЖКА И ТИКЕТЫ ===
@bot.callback_query_handler(func=lambda call: call.data == 'support_menu')
def support_menu(call):
    msg = bot.send_message(call.message.chat.id, "<b>Служба поддержки</b>\n\nОпиши свою проблему максимально подробно одним сообщением:")
    bot.register_next_step_handler(msg, process_support_ticket, None)

def process_support_ticket(message, oid):
    text = message.text
    uid = message.from_user.id
    
    with get_db_connection() as conn:
        conn.execute("INSERT INTO tickets (user_id, order_id, text) VALUES (?, ?, ?)", (uid, oid, text))
        ticket_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        
    bot.send_message(uid, f"<b>Обращение #{ticket_id} успешно создано!</b>\nАдминистрация ответит тебе прямо в этого бота.")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Ответить юзеру", callback_data=f"adm_reply_ticket|{ticket_id}"))
    
    for adm in ADMIN_IDS:
        order_info = f"\n<b>Заказ:</b> #{oid} (ДИСПУТ)" if oid else ""
        try:
            bot.send_message(adm, f"🚨 <b>НОВЫЙ ТИКЕТ #{ticket_id}</b>\n👤 <b>От:</b> {uid}{order_info}\n\n📝 <b>Суть:</b> {text}", reply_markup=markup)
        except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_reply_ticket|'))
def adm_reply_ticket(call):
    ticket_id = call.data.split('|')[1]
    msg = bot.send_message(call.message.chat.id, f"Пиши свой ответ на тикет #{ticket_id}:")
    bot.register_next_step_handler(msg, send_ticket_reply, ticket_id)

def send_ticket_reply(message, ticket_id):
    with get_db_connection() as conn:
        ticket = conn.execute("SELECT user_id, status FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if ticket and ticket[1] == 'open':
            conn.execute("UPDATE tickets SET status='closed' WHERE id=?", (ticket_id,))
            conn.commit()
            try:
                bot.send_message(ticket[0], f"🎧 <b>Ответ поддержки по твоему обращению #{ticket_id}:</b>\n\n{message.text}")
                bot.send_message(message.chat.id, f"✅ Ответ отправлен юзеру {ticket[0]}, тикет закрыт.")
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Ошибка отправки: {e}")
        else:
            bot.send_message(message.chat.id, "⚠️ Этот тикет уже закрыт или не существует.")

# === FAQ И ПРАВИЛА ===
@bot.callback_query_handler(func=lambda call: call.data == 'faq_menu')
def faq_menu(call):
    text = (
        "📖 <b>Справочник HAPPY SHOP</b>\n\n"
        "<b>1. Как купить?</b>\n"
        "Заходишь в 'Ассортимент', выбираешь товар, вводишь количество. Бот выдаст реквизиты для оплаты. Оплачиваешь, кидаешь номер чека — и ждешь назначения курьера.\n\n"
        "<b>2. Что делать, если ненаход?</b>\n"
        "После того как курьер загрузит фото, у тебя будут кнопки. Жми 'Диспут', и бот автоматически создаст обращение к администрации.\n\n"
        "<b>3. Хочу работать!</b>\n"
        "Жми 'Трудоустройство'. Оплата <b>80$</b> за каждый успешно снятый клиентом клад."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 В главное меню", callback_data="start_menu_return"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

# === ТРУДОУСТРОЙСТВО ===
@bot.callback_query_handler(func=lambda call: call.data == 'job_menu')
def job_menu(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[1] == 'worker':
        return bot.answer_callback_query(call.id, "❌ Ты уже в штате!", show_alert=True)
    
    msg = bot.send_message(call.message.chat.id, "📝 <b>Анкета курьера</b>\n\nВведи свое полное Имя и Фамилию:")
    bot.register_next_step_handler(msg, job_step_fio)

def job_step_fio(message):
    fio = message.text
    msg = bot.send_message(message.chat.id, "⏳ Сколько тебе лет?")
    bot.register_next_step_handler(msg, job_step_age, fio)

def job_step_age(message, fio):
    age = message.text
    photo_url = "https://ibb.co.com/GQgjpL0h"
    text = "📸 Пришли селфи с паспортом (игровым скриншотом):\n\n☝️ <i>Сверху пример как надо, без головных уборов и очков.</i>"
    
    msg = bot.send_photo(message.chat.id, photo_url, caption=text)
    bot.register_next_step_handler(msg, job_step_photo, fio, age)

def job_step_photo(message, fio, age):
    if not message.photo:
        return bot.send_message(message.chat.id, "❌ Ошибка: ожидалось фото. Начни заново /start")
    
    photo_id = message.photo[-1].file_id
    with get_db_connection() as conn:
        conn.execute("INSERT INTO job_apps (user_id, fio, age, photo) VALUES (?, ?, ?, ?)", (message.from_user.id, fio, age, photo_id))
        app_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    bot.send_message(message.chat.id, "✅ <b>Анкета отправлена!</b> Ожидай решения отдела кадров.")
    for adm in ADMIN_IDS:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Принять", callback_data=f"job_accept|{app_id}"),
                   types.InlineKeyboardButton("❌ Отказать", callback_data=f"job_deny|{app_id}"))
        bot.send_photo(adm, photo_id, caption=f"🆕 <b>НОВАЯ ЗАЯВКА НА КУРЬЕРА</b>\n\nID: {message.from_user.id}\nФИО: {fio}\nВозраст: {age}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('job_accept|'))
def job_accept(call):
    app_id = call.data.split('|')[1]
    with get_db_connection() as conn:
        res = conn.execute("SELECT user_id FROM job_apps WHERE id=?", (app_id,)).fetchone()
        if res:
            uid = res[0]
            conn.execute("UPDATE users SET role='worker' WHERE id=?", (uid,))
            conn.execute("UPDATE job_apps SET status='accepted' WHERE id=?", (app_id,))
            bot.send_message(uid, "🎉 <b>Поздравляем!</b> Твоя заявка одобрена.\nОткрой меню курьера: /menu")
            bot.edit_message_caption("✅ <b>Принят в штат</b>", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('job_deny|'))
def job_deny(call):
    app_id = call.data.split('|')[1]
    bot.edit_message_caption("❌ <b>Отклонено</b>", call.message.chat.id, call.message.message_id)

# === МАГАЗИН ===
@bot.callback_query_handler(func=lambda call: call.data == 'shop_menu')
def shop_menu(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, data in ITEMS.items():
        markup.add(types.InlineKeyboardButton(f"{data['name']} — {data['price']}$", callback_data=f"buy_item|{key}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="start_menu_return"))
    bot.edit_message_text("🛒 <b>Ассортимент HAPPY SHOP</b>\n\nВыбирай товар с умом:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_item|'))
def item_info(call):
    item_key = call.data.split('|')[1]
    item = ITEMS[item_key]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 Оформить заказ", callback_data=f"buy_qty|{item_key}"))
    markup.add(types.InlineKeyboardButton("🔙 К витрине", callback_data="shop_menu"))
    bot.edit_message_text(f"🛍 <b>{item['name']}</b>\n\n💵 Цена: <b>{item['price']}$</b> за шт.\n⚡️ Мин. заказ: <b>{item['min']} шт.</b>\n\n📝 <i>{item['desc']}</i>", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_qty|'))
def buy_quantity(call):
    item_key = call.data.split('|')[1]
    msg = bot.send_message(call.message.chat.id, f"⚖️ Введи количество (минимум {ITEMS[item_key]['min']}):")
    bot.register_next_step_handler(msg, process_buy_qty, item_key)

def process_buy_qty(message, item_key):
    if not message.text.isdigit(): 
        return bot.send_message(message.chat.id, "❌ Нужно ввести число.")
    qty = int(message.text)
    if qty < ITEMS[item_key]['min']: 
        return bot.send_message(message.chat.id, f"❌ Минимальный заказ: {ITEMS[item_key]['min']}")
    total = qty * ITEMS[item_key]['price']
    
    with get_db_connection() as conn:
        conn.execute("INSERT INTO orders (client_id, item, qty, price, status) VALUES (?, ?, ?, ?, 'awaiting_check')", 
                     (message.from_user.id, item_key, qty, total))
        oid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    text = (
        f"🧾 <b>ЗАКАЗ #{oid} сформирован!</b>\n\n"
        f"К оплате: <b>{total}$</b>\n"
        f"Перевод на ID: <code>{USERBOT_ID}</code>\n"
        f"Команда: <code>/check {USERBOT_ID} {total}</code>\n\n"
        f"👇 <i>Отправь мне номер чека (без #) в ответ на это сообщение:</i>"
    )
    bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(message, process_check_id, oid, total)

def process_check_id(message, oid, price):
    check_str = message.text.replace('#', '').strip()
    with get_db_connection() as conn:
        conn.execute("UPDATE orders SET check_id=?, status='verifying' WHERE id=?", (check_str, oid))
    bot.send_message(message.chat.id, "⏳ Чек отправлен на проверку. Ожидай...")
    bot.send_message(USERBOT_ID, f"/verify_check {check_str} {price} {oid} {message.from_user.id}")

@bot.callback_query_handler(func=lambda call: call.data == 'my_orders')
def my_orders(call):
    uid = call.from_user.id
    with get_db_connection() as conn:
        orders = conn.execute("SELECT id, item, qty, status FROM orders WHERE client_id=? ORDER BY id DESC LIMIT 5", (uid,)).fetchall()
    
    if not orders: 
        return bot.answer_callback_query(call.id, "У тебя пока нет заказов.", show_alert=True)
    
    status_emoji = {
        'awaiting_check': '⏳ Не оплачен', 'verifying': '🔄 Проверка',
        'paid': '✅ В поиске курьера', 'assigned': '🏃 В работе',
        'delivered': '📍 Ждет тебя', 'completed': '🤝 Успешно', 'dispute': '⚖️ Диспут'
    }
    
    text = "📦 <b>Твои последние заказы:</b>\n\n"
    for o in orders: 
        item_name = ITEMS.get(o[1], {}).get('name', o[1])
        st = status_emoji.get(o[3], o[3])
        text += f"🔹 <b>#{o[0]}</b> | {item_name} (x{o[2]}) — {st}\n"
        
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="start_menu_return"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

# === МЕНЮ КУРЬЕРА ===
@bot.callback_query_handler(func=lambda call: call.data == 'worker_menu')
def worker_menu_upd(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[1] != 'worker' and uid not in ADMIN_IDS: return
    
    text = (
        f"<b>Панель Курьера</b>\n\n"
        f"Баланс: <b>{user[4]}$</b>\n"
        f"Успешных кладов: <b>{user[3]}</b>\n\n"
        f"<b>Твой ассортимент (Вес):</b>"
    )
    with get_db_connection() as conn:
        inv = conn.execute("SELECT item, qty FROM inventory WHERE user_id=?", (uid,)).fetchall()
        if not inv:
            text += "\n<i>Пусто. Запроси мастер-клад у админа.</i>"
        for i in inv: 
            text += f"\n➖ {ITEMS.get(i[0],{}).get('name', i[0])}: <b>{i[1]} шт.</b>"
            
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Активные задания", callback_data="w_active_orders"))
    markup.add(types.InlineKeyboardButton("Запросить мастер-клад", callback_data="w_request_master")) 
    markup.add(types.InlineKeyboardButton("Вывести средства", callback_data="w_withdraw")) # НОВАЯ КНОПКА ВЫВОДА
    markup.add(types.InlineKeyboardButton("🔙 Выйти из панели", callback_data="start_menu_return"))
    
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        pass

# === ВЫВОД СРЕДСТВ ДЛЯ КУРЬЕРА ===
@bot.callback_query_handler(func=lambda call: call.data == 'w_withdraw')
def w_withdraw_start(call):
    uid = call.from_user.id
    user = get_user(uid)
    balance = user[4]
    
    if balance <= 0:
        return bot.answer_callback_query(call.id, "❌ Твой баланс пуст.", show_alert=True)
        
    msg = bot.send_message(call.message.chat.id, f"💸 <b>Вывод Зарплаты</b>\n\nДоступно: <b>{balance}$</b>\nВведи сумму, которую хочешь вывести (только число):")
    bot.register_next_step_handler(msg, w_withdraw_amount, balance)

def w_withdraw_amount(message, max_amount):
    if not message.text.isdigit():
        return bot.send_message(message.chat.id, "❌ Ошибка! Нужно ввести просто число (например: 100). Начни заново в панели.")
        
    amount = int(message.text)
    if amount <= 0 or amount > max_amount:
        return bot.send_message(message.chat.id, f"❌ Ошибка! Сумма должна быть больше 0 и не превышать твой баланс ({max_amount}$).")
        
    msg = bot.send_message(message.chat.id, "👤 <b>Отлично!</b>\nТеперь введи @username, куда перевести деньги (например: @username):")
    bot.register_next_step_handler(msg, w_withdraw_target, amount)

def w_withdraw_target(message, amount):
    target = message.text.strip()
    uid = message.from_user.id
    
    # Сразу списываем баланс чтобы не абузили
    with get_db_connection() as conn:
        conn.execute("UPDATE users SET earned = earned - ? WHERE id = ?", (amount, uid))
        conn.commit()
        
    bot.send_message(message.chat.id, f"⏳ Запрос на вывод <b>{amount}$</b> для <b>{target}</b> отправлен банку.\nОжидай зачисления...")
    
    # Отправляем команду юзерботу
    bot.send_message(USERBOT_ID, f"/withdraw {uid} {target} {amount}")


@bot.callback_query_handler(func=lambda call: call.data == 'w_request_master')
def w_request_master(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id, "✅ Запрос на вес успешно отправлен администраторам!", show_alert=True)
    
    for adm in ADMIN_IDS:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⚖️ Выдать вес", callback_data="adm_give_weight"))
        bot.send_message(adm, f"🔔 <b>ЗАПРОС ВЕСА!</b>\n\nКурьер <code>{uid}</code> запрашивает мастер-клад. Перейди в панель, чтобы загрузить его.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'w_active_orders')
def w_active_orders(call):
    uid = call.from_user.id
    with get_db_connection() as conn:
        orders = conn.execute("SELECT id, item, qty FROM orders WHERE worker_id=? AND status='assigned'", (uid,)).fetchall()
    
    if not orders:
        return bot.answer_callback_query(call.id, "💤 Сейчас нет активных заданий.", show_alert=True)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for o in orders:
        markup.add(types.InlineKeyboardButton(f"Заказ #{o[0]} | x{o[2]} шт.", callback_data=f"w_order_view|{o[0]}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="worker_menu"))
    bot.edit_message_text("📋 <b>Твои текущие задачи:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('w_order_view|'))
def w_order_view(call):
    oid = call.data.split('|')[1]
    with get_db_connection() as conn:
        o = conn.execute("SELECT item, qty FROM orders WHERE id=?", (oid,)).fetchone()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📸 Сдать клад", callback_data=f"w_finish_photo|{oid}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="w_active_orders"))
    bot.edit_message_text(f"📦 <b>ЗАКАЗ #{oid}</b>\n\nТовар: {ITEMS[o[0]]['name']}\nКол-во: <b>{o[1]} шт.</b>\n\n<i>Нужно надежно спрятать и отправить фото.</i>", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('w_finish_photo|'))
def w_finish_1(call):
    oid = call.data.split('|')[1]
    msg = bot.send_message(call.message.chat.id, "📸 Отправь <b>ФОТО</b> места клада (отчетливо):")
    bot.register_next_step_handler(msg, w_finish_2, oid)

def w_finish_2(message, oid):
    if not message.photo:
        msg = bot.send_message(message.chat.id, "❌ Это не фото! Пожалуйста, пришли фото места клада:")
        return bot.register_next_step_handler(msg, w_finish_2, oid)
    
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "📍 Теперь введи <b>подробное описание</b> (координаты, ориентиры, и т.д):")
    bot.register_next_step_handler(msg, w_finish_3, oid, photo_id)

def w_finish_3(message, oid, photo_id):
    desc = message.text
    uid = message.from_user.id
    
    with get_db_connection() as conn:
        order = conn.execute("SELECT client_id, item, qty FROM orders WHERE id=?", (oid,)).fetchone()
        cid = order[0]
        conn.execute("UPDATE orders SET photo=?, description=?, status='delivered' WHERE id=?", (photo_id, desc, oid))
        conn.commit()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Забрал (Успех)", callback_data=f"client_pickup|{oid}"),
               types.InlineKeyboardButton("❌ Ненаход", callback_data=f"client_dispute|{oid}"))
               
    bot.send_photo(cid, photo_id, caption=f"📍 <b>ВАШ КЛАД ГОТОВ! (Заказ #{oid})</b>\n\n📦 <b>Стафф:</b> {ITEMS[order[1]]['name']} (x{order[2]})\n📝 <b>Описание:</b> {desc}\n\n<i>Сходите и заберите его.Обязательно подтвердите находку кнопкой ниже, иначе вы не сможете делать заказы в будущем.</i>", reply_markup=markup)
    
    bot.send_message(uid, f"✅ Координаты заказа #{oid} переданы клиенту. Деньги (80$) поступят на твой баланс, как только он подтвердит находку.")

# === ПОДТВЕРЖДЕНИЕ ОТ КЛИЕНТА ===
@bot.callback_query_handler(func=lambda call: call.data.startswith('client_pickup|'))
def client_pickup(call):
    oid = call.data.split('|')[1]
    
    with get_db_connection() as conn:
        order = conn.execute("SELECT worker_id, status FROM orders WHERE id=?", (oid,)).fetchone()
        if order[1] != 'delivered':
            return bot.answer_callback_query(call.id, "Статус заказа уже изменен.", show_alert=True)
            
        worker_id = order[0]
        conn.execute("UPDATE orders SET status='completed' WHERE id=?", (oid,))
        conn.execute("UPDATE users SET earned = earned + 80, drops = drops + 1 WHERE id=?", (worker_id,))
        conn.commit()
        
    bot.edit_message_caption(f"🤝 <b>Сделка закрыта.</b> Спасибо за покупку в Happy Shop!\nЗаказ #{oid}", call.message.chat.id, call.message.message_id)
    bot.send_message(worker_id, f"💸 <b>Оплата получена!</b>\nКлиент снял клад #{oid}. На твой баланс зачислено <b>80$</b>.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('client_dispute|'))
def client_dispute(call):
    oid = call.data.split('|')[1]
    
    with get_db_connection() as conn:
        order = conn.execute("SELECT worker_id, status FROM orders WHERE id=?", (oid,)).fetchone()
        if order[1] != 'delivered':
            return bot.answer_callback_query(call.id, "Статус заказа уже изменен.", show_alert=True)
            
        conn.execute("UPDATE orders SET status='dispute' WHERE id=?", (oid,))
        conn.commit()
        
    bot.edit_message_caption(f"⚖️ <b>Открыт диспут.</b> Заполните обращение ниже.\nЗаказ #{oid}", call.message.chat.id, call.message.message_id)
    bot.send_message(order[0], f"⚠️ <b>АХТУНГ!</b> Клиент не нашел клад #{oid}. Открыт диспут. Жди решения админа.")
    log_to_admins(f"⚖️ <b>ОТКРЫТ ДИСПУТ!</b>\nЗаказ: #{oid}\nКурьер: {order[0]}\nКлиент: {call.from_user.id}")
    
    msg = bot.send_message(call.message.chat.id, f"📝 <b>Диспут по заказу #{oid}</b>\n\nПожалуйста, подробно опиши проблему одним сообщением (почему ненаход, приложи ссылки на фото если есть):")
    bot.register_next_step_handler(msg, process_support_ticket, oid)

# === АДМИН-ПАНЕЛЬ ===
@bot.callback_query_handler(func=lambda call: call.data == 'admin_menu')
def admin_menu(call):
    if call.from_user.id not in ADMIN_IDS: return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🛒 Назначить курьера", callback_data="adm_orders"))
    markup.add(types.InlineKeyboardButton("⚖️ Мастер-клад (Выдать вес)", callback_data="adm_give_weight"))
    markup.add(types.InlineKeyboardButton("👥 Штат сотрудников", callback_data="adm_staff"))
    markup.add(types.InlineKeyboardButton("💰 Запросить баланс шопа", callback_data="adm_balance"))
    markup.add(types.InlineKeyboardButton("🔙 Главное меню", callback_data="start_menu_return"))
    bot.edit_message_text("👑 <b>Shadow-Панель Администратора</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'adm_orders')
def adm_orders_list(call):
    with get_db_connection() as conn:
        orders = conn.execute("SELECT id, item, qty FROM orders WHERE status='paid'").fetchall()
    
    if not orders:
        return bot.answer_callback_query(call.id, "Нет оплаченных заказов без курьера.", show_alert=True)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for o in orders:
        item_name = ITEMS.get(o[1], {}).get('name', o[1])
        markup.add(types.InlineKeyboardButton(f"Заказ #{o[0]}: {item_name} (x{o[2]})", callback_data=f"adm_assign_sel|{o[0]}"))
    markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_menu"))
    bot.edit_message_text("🎯 Выбери заказ для выдачи:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_assign_sel|'))
def adm_assign_select_worker(call):
    order_id = call.data.split('|')[1]
    with get_db_connection() as conn:
        order = conn.execute("SELECT item, qty FROM orders WHERE id=?", (order_id,)).fetchone()
        item, qty = order[0], order[1]
        
        workers = conn.execute("""
            SELECT users.id, inventory.qty FROM users 
            JOIN inventory ON users.id = inventory.user_id 
            WHERE users.role='worker' AND inventory.item=? AND inventory.qty >= ?
        """, (item, qty)).fetchall()
        
    if not workers:
        return bot.send_message(call.message.chat.id, f"❌ У курьеров нет нужного веса: {ITEMS[item]['name']} (x{qty}).\nСделай Мастер-клад.")
        
    markup = types.InlineKeyboardMarkup(row_width=1)
    for w in workers:
        markup.add(types.InlineKeyboardButton(f"Кура ID: {w[0]} (В наличии: {w[1]})", callback_data=f"adm_do_assign|{order_id}|{w[0]}"))
    
    bot.edit_message_text(f"Кому передаем заказ на {ITEMS[item]['name']} (x{qty})?", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_do_assign|'))
def adm_do_assign_finish(call):
    _, oid, wid = call.data.split('|')
    with get_db_connection() as conn:
        order = conn.execute("SELECT client_id, item, qty FROM orders WHERE id=?", (oid,)).fetchone()
        conn.execute("UPDATE inventory SET qty = qty - ? WHERE user_id=? AND item=?", (order[2], wid, order[1]))
        conn.execute("UPDATE orders SET worker_id=?, status='assigned' WHERE id=?", (wid, oid))
        conn.commit()
    
    bot.send_message(wid, f"🚨 <b>НОВЫЙ ЗАКАЗ В РАБОТЕ!</b>\nТебе назначен заказ #{oid}: {ITEMS[order[1]]['name']} (x{order[2]}).\nЗайди в 'Активные задания'.")
    bot.send_message(order[0], "✅ <b>Курьер выехал!</b> Твой заказ в надежных руках.")
    bot.edit_message_text(f"✅ Заказ #{oid} передан курьеру {wid}", call.message.chat.id, call.message.message_id)

# === МАСТЕР-КЛАД (АДМИН -> КУРЬЕР) ===
@bot.callback_query_handler(func=lambda call: call.data == 'adm_give_weight')
def adm_gw_start(call):
    msg = bot.send_message(call.message.chat.id, "Введи ID курьера, которому делаем мастер-клад:")
    bot.register_next_step_handler(msg, adm_gw_id)

def adm_gw_id(message):
    worker_id = message.text
    if not worker_id.isdigit(): return bot.send_message(message.chat.id, "ID должен быть числом.")
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, data in ITEMS.items():
        markup.add(types.InlineKeyboardButton(data['name'], callback_data=f"adm_gw_item|{worker_id}|{key}"))
    bot.send_message(message.chat.id, "Выбери товар для загрузки:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_gw_item|'))
def adm_gw_qty(call):
    _, wid, item = call.data.split('|')
    msg = bot.send_message(call.message.chat.id, f"Сколько {ITEMS[item]['name']} фасуем?")
    bot.register_next_step_handler(msg, adm_gw_photo, wid, item)

def adm_gw_photo(message, wid, item):
    qty = message.text
    msg = bot.send_message(message.chat.id, "📸 Загрузи <b>фото</b> локации мастер-клада:")
    bot.register_next_step_handler(msg, adm_gw_desc, wid, item, qty)

def adm_gw_desc(message, wid, item, qty):
    if not message.photo: return bot.send_message(message.chat.id, "Нужно фото. Отмена.")
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "📍 Введи <b>описание</b> тайника для курьера:")
    bot.register_next_step_handler(msg, adm_gw_finish, wid, item, qty, photo_id)

def adm_gw_finish(message, wid, item, qty, photo_id):
    desc = message.text
    with get_db_connection() as conn:
        conn.execute("INSERT INTO weight_drops (worker_id, item, qty, photo, description) VALUES (?, ?, ?, ?, ?)", 
                     (wid, item, qty, photo_id, desc))
        drop_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    bot.send_message(message.chat.id, f"✅ Мастер-клад #{drop_id} для {wid} успешно сформирован.")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎒 Поднять вес", callback_data=f"w_pickup_weight|{drop_id}"))
    bot.send_photo(wid, photo_id, caption=f"🎁 <b>ПОСТУПЛЕНИЕ ВЕСА! (Мастер-клад)</b>\n\nТовар: {ITEMS[item]['name']} (x{qty})\nЛокация: {desc}\n\n<i>Жми кнопку ниже, когда заберешь вес в инвентарь.</i>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('w_pickup_weight|'))
def w_pickup_weight(call):
    drop_id = call.data.split('|')[1]
    uid = call.from_user.id
    
    with get_db_connection() as conn:
        drop = conn.execute("SELECT item, qty, status FROM weight_drops WHERE id=?", (drop_id,)).fetchone()
        if not drop or drop[2] != 'pending':
            return bot.answer_callback_query(call.id, "Уже собрано или не найдено.", show_alert=True)
            
        item, qty = drop[0], drop[1]
        cur = conn.execute("SELECT qty FROM inventory WHERE user_id=? AND item=?", (uid, item)).fetchone()
        if cur: conn.execute("UPDATE inventory SET qty = qty + ? WHERE user_id=? AND item=?", (qty, uid, item))
        else: conn.execute("INSERT INTO inventory (user_id, item, qty) VALUES (?, ?, ?)", (uid, item, qty))
        
        conn.execute("UPDATE weight_drops SET status='picked' WHERE id=?", (drop_id,))
        conn.commit()
        
    bot.edit_message_caption(f"✅ Вес успешно добавлен в инвентарь: {ITEMS[item]['name']} (x{qty})", call.message.chat.id, call.message.message_id)
    log_to_admins(f"🎒 Курьер {uid} поднял мастер-клад #{drop_id} ({item} x{qty})")

# === РАЗНОЕ ===
@bot.callback_query_handler(func=lambda call: call.data == 'start_menu_return')
def back_to_start(call):
    start_cmd(call)

@bot.callback_query_handler(func=lambda call: call.data == 'adm_balance')
def adm_balance(call):
    bot.send_message(call.message.chat.id, "⏳ Стучусь к юзерботу...")
    bot.send_message(USERBOT_ID, f"/check_balance {call.from_user.id}")

@bot.callback_query_handler(func=lambda call: call.data == 'adm_staff')
def adm_staff(call):
    with get_db_connection() as conn:
        staff = conn.execute("SELECT id, shift, drops, earned FROM users WHERE role='worker'").fetchall()
    if not staff: return bot.answer_callback_query(call.id, "В штате пусто.", show_alert=True)
    text = "👥 <b>База сотрудников:</b>\n\n"
    for s in staff: text += f"🆔 <code>{s[0]}</code> | 🏆 Клады: {s[2]} | 💸 Баланс: {s[3]}$\n"
    bot.send_message(call.message.chat.id, text)

@bot.message_handler(func=lambda message: message.from_user.id == USERBOT_ID)
def handle_userbot_responses(message):
    text = message.text
    if text.startswith('/resp_verify'):
        _, check_id, oid, cid, status = text.split()
        if status == 'success':
            with get_db_connection() as conn: conn.execute("UPDATE orders SET status='paid' WHERE id=?", (oid,))
            bot.send_message(cid, "✅ <b>Оплата прошла!</b> Ищем свободного курьера.")
            log_to_admins(f"✅ Заказ #{oid} оплачен. Нужно назначить куру.")
        else:
            bot.send_message(cid, "❌ <b>Оплата не найдена.</b> Проверьте данные чека.")
            
    elif text.startswith('/resp_balance'):
        bot.send_message(text.split()[1], f"🏦 <b>Касса шопа:</b>\n{' '.join(text.split()[2:])}")
        
    # ОТВЕТ ОТ ЮЗЕРБОТА ПО ВЫВОДУ ЗП
    elif text.startswith('/resp_withdraw'):
        parts = text.split()
        uid = int(parts[1])
        status = parts[2]
        amount = int(parts[3])
        
        if status == 'success':
            bot.send_message(uid, f"✅ <b>Отличные новости!</b>\nПеревод на <b>{amount}$</b> успешно выполнен банком.")
            log_to_admins(f"💸 Курьер {uid} успешно вывел {amount}$.")
        else:
            # Если банк отклонил, возвращаем бабки на базу
            with get_db_connection() as conn:
                conn.execute("UPDATE users SET earned = earned + ? WHERE id=?", (amount, uid))
                conn.commit()
            bot.send_message(uid, f"❌ <b>Отказ перевода от Montana GOV!</b>\nПроверь правильность @username. Твои <b>{amount}$</b> возвращены на баланс.")

bot.polling(none_stop=True)
