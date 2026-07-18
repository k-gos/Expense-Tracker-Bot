import json
import telebot
from flask import Flask, request, Response, send_file
import os
from functools import wraps
import db
from export import export_data
from parser import parse_message
import datetime

# --- LOAD SECRETS ONCE ---
try:
    with open("config.json", "r") as f:
        _init_conf = json.load(f)
    TOKEN = _init_conf.get("telegram_token", "")
    ALLOWED_CHAT_ID = str(_init_conf.get("allowed_chat_id", ""))
    USERNAME = _init_conf.get("dashboard_username", "admin")
    PASSWORD = _init_conf.get("dashboard_password", "admin")
except Exception:
    TOKEN = ""
    ALLOWED_CHAT_ID = ""
    USERNAME = ""
    PASSWORD = ""

def get_current_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- SECURITY: BASIC AUTH FOR DASHBOARD ---
def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# --- SECURITY: TELEGRAM AUTH ---
def is_allowed(message):
    if not ALLOWED_CHAT_ID:
        return True
    return str(message.chat.id) == ALLOWED_CHAT_ID

# --- WEBHOOK ENDPOINTS ---
@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
@requires_auth
def index():
    return send_file("dashboard.html")

@app.route("/data.js")
@requires_auth
def data_js():
    export_data() 
    return send_file("data.js")

# --- BOT LOGIC ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not is_allowed(message): return
    bot.reply_to(message, f"🤖 Hello! Your Chat ID is: `{message.chat.id}`.\n\nCommands:\n/total - Month summary\n/budget - Show budgets\n/addbudget <category> <amount> - Update a budget\n/addkeyword <category> <word> - Teach bot a new word\n/undo - Delete last entry")

@bot.message_handler(commands=['total'])
def handle_total(message):
    if not is_allowed(message): return
    d = datetime.date.today()
    month_str = d.strftime("%Y-%m")
    spent = db.month_total(month_str)
    current_config = get_current_config()
    budget = current_config.get("monthlyBudget", 0)
    reply = f"📊 *Total Spent:* ₹{spent:,.2f}\n*Remaining:* ₹{budget - spent:,.2f}"
    bot.reply_to(message, reply, parse_mode="Markdown")

@bot.message_handler(commands=['budget'])
def handle_budget(message):
    if not is_allowed(message): return
    current_config = get_current_config()
    budgets = current_config.get("budgets", {})
    res = "💰 *Budgets:*\n"
    for cat, amt in budgets.items():
        if amt > 0:
            res += f"- {cat.capitalize()}: ₹{amt:,.2f}\n"
    bot.reply_to(message, res, parse_mode="Markdown")

@bot.message_handler(commands=['addbudget'])
def handle_addbudget(message):
    if not is_allowed(message): return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /addbudget <category> <amount>\nExample: /addbudget food 12000")
        return
        
    category = parts[1].lower()
    try:
        amount = float(parts[2])
    except ValueError:
        bot.reply_to(message, "❌ Please provide a valid amount.")
        return
        
    current_config = get_current_config()
    budgets = current_config.get("budgets", {})
    budgets[category] = amount
    current_config["budgets"] = budgets
    
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(current_config, f, indent=2)
        
    export_data()
    bot.reply_to(message, f"✅ Budget for {category.capitalize()} updated to ₹{amount:,.2f}.")

@bot.message_handler(commands=['addkeyword'])
def handle_addkeyword(message):
    if not is_allowed(message): return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /addkeyword <word>\nExample: /addkeyword dominos")
        return
        
    new_keyword = parts[1].lower().strip()
    
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            current_config = json.load(f)
    except:
        current_config = {}
        
    cat_keywords = current_config.get("category_keywords", {})
    categories = list(cat_keywords.keys())
    
    if not categories:
        bot.reply_to(message, "No categories found in config.")
        return
        
    markup = telebot.types.InlineKeyboardMarkup()
    for cat in categories:
        # truncate keyword if needed to fit 64 byte limit of callback_data
        cb_data = f"addkw_{cat}_{new_keyword}"[:64]
        markup.add(telebot.types.InlineKeyboardButton(cat.capitalize(), callback_data=cb_data))
        
    bot.reply_to(message, f"Select the existing category for the new keyword '{new_keyword}':", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('addkw_'))
def handle_addkw_callback(call):
    parts = call.data.split('_', 2)
    if len(parts) < 3:
        return
    category = parts[1]
    new_keyword = parts[2]
    
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            current_config = json.load(f)
    except:
        current_config = {}
        
    cat_keywords = current_config.get("category_keywords", {})
    if category not in cat_keywords:
        cat_keywords[category] = []
        
    if new_keyword not in cat_keywords[category]:
        cat_keywords[category].append(new_keyword)
        current_config["category_keywords"] = cat_keywords
        
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(current_config, f, indent=2)
            
        bot.edit_message_text(f"🧠 Got it! I will now recognize '{new_keyword}' as a '{category}' expense.", chat_id=call.message.chat.id, message_id=call.message.message_id)
    else:
        bot.edit_message_text(f"I already know '{new_keyword}' is for {category}!", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.message_handler(commands=['undo'])
def handle_undo(message):
    if not is_allowed(message): return
    if db.undo_last(str(message.chat.id)):
        export_data()
        bot.reply_to(message, "🗑️ Last transaction deleted.")
    else:
        bot.reply_to(message, "No transactions to undo.")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_allowed(message): return
    text = message.text.strip()
    parsed = parse_message(text)
    
    if not parsed:
        bot.reply_to(message, "❌ Couldn't understand. Try '500 for ola'.")
        return
        
    date_str = datetime.date.today().isoformat()
    chat_id = str(message.chat.id)
    
    if parsed.get("split_people"):
        total_amt = parsed["amount"]
        people_count = len(parsed["split_people"]) + 1
        per_person = total_amt / people_count
        
        db.add(date_str, parsed["category"], per_person, parsed["note"] + " (My share)", parsed["type"], chat_id)
        for person in parsed["split_people"]:
            db.add(date_str, "money given", per_person, f"Paid for {person} in: {parsed['note']}", parsed["type"], chat_id)
            
        export_data()
        bot.reply_to(message, f"✅ Saved! Split ₹{total_amt} among {people_count} people (₹{per_person:,.2f} each).")
    else:
        db.add(date_str, parsed["category"], parsed["amount"], parsed["note"], parsed["type"], chat_id)
        export_data()
        emoji = "📈" if parsed["type"] == "income" else "💸"
        bot.reply_to(message, f"✅ Saved {parsed['type']}: ₹{parsed['amount']} for {parsed['category'].capitalize()} {emoji}")

if __name__ == "__main__":
    db.init_db()
    export_data()
    bot.remove_webhook()
    bot.infinity_polling()
