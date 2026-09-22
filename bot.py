# -*- coding: utf-8 -*-
import telebot
import json
import os
import re
from datetime import datetime
from flask import Flask
import threading
import time
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# --------------------- الإعدادات ---------------------
TOKEN = os.environ.get("8664701635:AAFU_FQ-rAVjqFR0vZ_od7knPZSaEEUfq7k")
DATA_FILE = "data.json"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --------------------- Flask Routes ---------------------
@app.route('/')
def home():
    return "🤖 البوت يعمل!", 200

@app.route('/health')
def health():
    return "OK", 200

# --------------------- قاعدة البيانات ---------------------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        except:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_or_create_user(user_id, username):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "username": username,
            "balance": 0,
            "total_in": 0,
            "total_out": 0,
            "transactions": []
        }
        save_data(data)
    return data, uid

# --------------------- معالجة العمليات ---------------------
def process_transaction(user_id, username, amount, note=""):
    """
    amount > 0  →  إيداع (جمع)
    amount < 0  →  خصم
    """
    data, uid = get_or_create_user(user_id, username)
    
    data[uid]["balance"] += amount
    
    if amount > 0:
        data[uid]["total_in"] += amount
        trans_type = "إيداع"
    else:
        data[uid]["total_out"] += abs(amount)
        trans_type = "خصم"
    
    data[uid]["transactions"].append({
        "type": trans_type,
        "amount": abs(amount),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "note": note
    })
    
    if len(data[uid]["transactions"]) > 100:
        data[uid]["transactions"] = data[uid]["transactions"][-100:]
    
    save_data(data)
    
    return {
        "balance": data[uid]["balance"],
        "total_in": data[uid]["total_in"],
        "total_out": data[uid]["total_out"],
        "trans_type": trans_type
    }

# --------------------- القوائم ---------------------
def main_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("💰 رصيدي"),
        KeyboardButton("📋 سجل معاملاتي"),
        KeyboardButton("📊 تقرير عام"),
        KeyboardButton("❓ مساعدة")
    )
    return markup

# --------------------- الأوامر ---------------------
@bot.message_handler(commands=['start'])
def start(message):
    username = message.from_user.username or message.from_user.first_name
    bot.reply_to(message,
        f"👋 *مرحباً {username}*\n\n"
        f"📌 *طريقة الاستخدام:*\n"
        f"• أرسل `+7000` لإضافة 7000 ليرة\n"
        f"• أرسل `-500` لخصم 500 ليرة\n"
        f"• أرسل `+1500 دفعة أولى` لإضافة مبلغ مع ملاحظة\n"
        f"• أرسل `رصيدي` لعرض رصيدك\n"
        f"• أرسل `سجل` لعرض آخر معاملاتك",
        parse_mode='Markdown',
        reply_markup=main_menu()
    )

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message,
        "📖 *المساعدة*\n\n"
        "🔹 `+1000` → إضافة 1000 ليرة\n"
        "🔹 `-500` → خصم 500 ليرة\n"
        "🔹 `+2000 راتب` → إضافة 2000 مع ملاحظة\n"
        "🔹 `رصيدي` → عرض الرصيد\n"
        "🔹 `سجل` → عرض آخر 10 معاملات\n"
        "🔹 `تقرير` → ملخص كامل\n"
        "🔹 `تصفير` → تصفير رصيدك",
        parse_mode='Markdown'
    )

# --------------------- عرض الرصيد ---------------------
@bot.message_handler(func=lambda m: m.text in ["💰 رصيدي", "رصيدي", "رصيد"])
def show_balance(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    data, uid = get_or_create_user(user_id, username)
    user = data[uid]
    
    balance = user["balance"]
    sign = "🟢" if balance >= 0 else "🔴"
    
    bot.reply_to(message,
        f"💰 *رصيدك الحالي*\n\n"
        f"{sign} الرصيد: *{balance:,}* ل.س\n"
        f"📥 إجمالي الإيداع: {user['total_in']:,} ل.س\n"
        f"📤 إجمالي الخصم: {user['total_out']:,} ل.س\n"
        f"📝 عدد المعاملات: {len(user['transactions'])}",
        parse_mode='Markdown'
    )

# --------------------- سجل المعاملات ---------------------
@bot.message_handler(func=lambda m: m.text in ["📋 سجل معاملاتي", "سجل", "سجلي"])
def show_history(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    data, uid = get_or_create_user(user_id, username)
    transactions = data[uid]["transactions"]
    
    if not transactions:
        bot.reply_to(message, "📭 لا توجد معاملات بعد.")
        return
    
    recent = transactions[-10:]
    text = "📋 *آخر 10 معاملات*\n" + "═" * 15 + "\n\n"
    
    for t in reversed(recent):
        emoji = "📥" if t["type"] == "إيداع" else "📤"
        sign = "+" if t["type"] == "إيداع" else "-"
        text += f"{emoji} {sign}{t['amount']:,} ل.س\n"
        text += f"🕐 {t['time']}\n"
        if t.get("note"):
            text += f"📝 {t['note']}\n"
        text += "─" * 10 + "\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# --------------------- التقرير العام ---------------------
@bot.message_handler(func=lambda m: m.text in ["📊 تقرير عام", "تقرير"])
def general_report(message):
    data = load_data()
    
    if not data:
        bot.reply_to(message, "📭 لا توجد بيانات بعد.")
        return
    
    total_balance = 0
    total_in = 0
    total_out = 0
    count = 0
    
    for uid, user in data.items():
        total_balance += user.get("balance", 0)
        total_in += user.get("total_in", 0)
        total_out += user.get("total_out", 0)
        count += 1
    
    text = "📊 *التقرير العام*\n" + "═" * 15 + "\n\n"
    text += f"👥 عدد المستخدمين: *{count}*\n"
    text += f"💰 إجمالي الأرصدة: *{total_balance:,}* ل.س\n"
    text += f"📥 إجمالي الإيداعات: *{total_in:,}* ل.س\n"
    text += f"📤 إجمالي الخصومات: *{total_out:,}* ل.س\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# --------------------- تصفير الرصيد ---------------------
@bot.message_handler(func=lambda m: m.text in ["تصفير", "تصفير رصيدي"])
def reset_balance(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    data, uid = get_or_create_user(user_id, username)
    data[uid]["balance"] = 0
    data[uid]["total_in"] = 0
    data[uid]["total_out"] = 0
    data[uid]["transactions"] = []
    save_data(data)
    
    bot.reply_to(message, "✅ تم تصفير رصيدك وسجل معاملاتك.")

# --------------------- المعالج الرئيسي ---------------------
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    if not message.text:
        return
    
    text = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # تجاهل أوامر القائمة
    if text in ["💰 رصيدي", "رصيدي", "رصيد", "📋 سجل معاملاتي", "سجل", "سجلي",
                "📊 تقرير عام", "تقرير", "❓ مساعدة", "تصفير", "تصفير رصيدي"]:
        return
    
    # ✅ تجاهل أي رسالة لا تبدأ برقم أو + أو -
    if not re.match(r'^[+-]?\s*\d', text):
        return
    
    pattern = r'^([+-]?)\s*(\d+(?:[.,]\d+)?)\s*(.*)$'
    match = re.match(pattern, text)
    
    if not match:
        return
    
    sign = match.group(1)
    amount_str = match.group(2).replace(',', '.')
    note = match.group(3).strip()
    
    try:
        amount = float(amount_str)
    except ValueError:
        return
    
    if sign == '-':
        amount = -amount
    else:
        amount = abs(amount)
    
    if amount == 0:
        return
    
    if abs(amount) > 1_000_000_000:
        return
    
    result = process_transaction(user_id, username, amount, note)
    
    if amount > 0:
        emoji = "✅"
        action = "تمت الإضافة"
        sign_display = "+"
    else:
        emoji = "❌"
        action = "تم الخصم"
        sign_display = "-"
    
    text_reply = (
        f"{emoji} *{action}*\n\n"
        f"👤 {username}\n"
        f"💵 المبلغ: *{sign_display}{abs(amount):,.0f}* ل.س\n"
    )
    if note:
        text_reply += f"📝 الملاحظة: {note}\n"
    text_reply += f"\n💰 *الرصيد الجديد: {result['balance']:,.0f} ل.س*"
    
    bot.reply_to(message, text_reply, parse_mode='Markdown')

# --------------------- تشغيل البوت ---------------------
def run_bot():
    while True:
        try:
            print("🧹 حذف Webhook قديم...")
            bot.remove_webhook()
            time.sleep(2)
            print("🔄 بدء تشغيل البوت...")
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            print(f"❌ خطأ: {type(e).__name__}: {e}")
            time.sleep(10)

if __name__ == "__main__":
    print("=" * 40)
    print("🤖 بوت إدارة الليرة السورية")
    print("=" * 40)
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ تم تشغيل البوت")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
