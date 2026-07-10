# -*- coding: utf-8 -*-
import telebot
import json
import os
from datetime import datetime
from flask import Flask
import threading
import re
import time
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --------------------- الإعدادات ---------------------
TOKEN = "8855886445:AAE7PhgeUauhQ9rQ4mjJqQmhOg9ccRGreYo"
# البوت يعمل في جميع المجموعات - لا حاجة لتحديد معرفات
DATA_FILE = "data.json"

# إنشاء البوت
bot = telebot.TeleBot(TOKEN)

# إنشاء تطبيق Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 البوت يعمل!", 200

@app.route('/health')
def health():
    return "OK", 200

# --------------------- دوال الإبقاء على النشاط وإعادة التشغيل ---------------------

def keep_alive():
    """إبقاء البوت نشطاً عن طريق إرسال طلبات دورية"""
    hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "localhost")
    url = f"https://{hostname}/" if hostname != "localhost" else "http://localhost:5000/"
    
    while True:
        try:
            response = requests.get(url, timeout=10)
            print(f"🔄 تم إرسال طلب إبقاء النشاط - الحالة: {response.status_code}")
        except Exception as e:
            print(f"⚠️ فشل طلب الإبقاء على النشاط: {e}")
        time.sleep(300)

def run_bot_with_retry():
    """تشغيل البوت مع إعادة تشغيل تلقائي عند التوقف"""
    while True:
        try:
            print("🔄 بدء تشغيل البوت...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"❌ البوت توقف: {e}")
            print("🔄 إعادة التشغيل بعد 5 ثوانٍ...")
            time.sleep(5)
            continue

# --------------------- قاعدة البيانات ---------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_transaction(user_id, username, amount, currency, note=""):
    data = load_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data:
        data[user_id_str] = {
            "username": username,
            "full_name": "",
            "phone": "",
            "shamcash_code": "",
            "balance_sy": 0,
            "balance_usd": 0,
            "total_in_sy": 0,
            "total_out_sy": 0,
            "total_in_usd": 0,
            "total_out_usd": 0,
            "transactions": []
        }
    
    if currency == "sy":
        if amount > 0:
            data[user_id_str]["balance_sy"] += amount
            data[user_id_str]["total_in_sy"] += amount
        else:
            data[user_id_str]["balance_sy"] += amount
            data[user_id_str]["total_out_sy"] += abs(amount)
    else:
        if amount > 0:
            data[user_id_str]["balance_usd"] += amount
            data[user_id_str]["total_in_usd"] += amount
        else:
            data[user_id_str]["balance_usd"] += amount
            data[user_id_str]["total_out_usd"] += abs(amount)
    
    trans_type = "استلام" if amount > 0 else "دفع"
    emoji = "✅" if amount > 0 else "❌"
    
    data[user_id_str]["transactions"].append({
        "type": trans_type,
        "amount": abs(amount),
        "currency": "🇸🇾 ل.س" if currency == "sy" else "💵 USD",
        "time": datetime.now().strftime("%H:%M:%S"),
        "note": note
    })
    
    save_data(data)
    
    if currency == "sy":
        new_balance = data[user_id_str]["balance_sy"]
        total_in = data[user_id_str]["total_in_sy"]
        total_out = data[user_id_str]["total_out_sy"]
        currency_symbol = "🇸🇾 ل.س"
    else:
        new_balance = data[user_id_str]["balance_usd"]
        total_in = data[user_id_str]["total_in_usd"]
        total_out = data[user_id_str]["total_out_usd"]
        currency_symbol = "💵 USD"
    
    return new_balance, abs(amount), trans_type, emoji, currency_symbol, total_in, total_out, data[user_id_str]["username"]

def get_user_full_report(user_id):
    data = load_data()
    user_id_str = str(user_id)
    if user_id_str not in data:
        return None
    return data[user_id_str]

# --------------------- دوال الأزرار ---------------------

def main_menu():
    """القائمة الرئيسية - أزرار دائمة"""
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton("➕ إيداع")
    btn2 = KeyboardButton("➖ سحب")
    btn3 = KeyboardButton("💰 رصيدي")
    btn4 = KeyboardButton("📊 تقارير")
    btn5 = KeyboardButton("👤 ملفي الشخصي")
    btn6 = KeyboardButton("🔑 كود الشام كاش")
    btn7 = KeyboardButton("📋 قائمة الأكواد")
    btn8 = KeyboardButton("⚙️ إدارة")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
    return markup

def admin_menu():
    """قائمة المشرفين"""
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton("📋 تقرير موظف")
    btn2 = KeyboardButton("📊 جميع المعاملات")
    btn3 = KeyboardButton("🔄 تصفير الكل")
    btn4 = KeyboardButton("🔄 تصفير موظف")
    btn5 = KeyboardButton("🔙 رجوع")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

def currency_menu():
    """اختيار العملة"""
    markup = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("🇸🇾 ليرة سورية", callback_data="currency_sy")
    btn2 = InlineKeyboardButton("💵 دولار أمريكي", callback_data="currency_usd")
    btn3 = InlineKeyboardButton("🔙 إلغاء", callback_data="cancel")
    markup.add(btn1, btn2, btn3)
    return markup

def report_menu():
    """قائمة التقارير"""
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton("📊 تقرير اليوم")
    btn2 = KeyboardButton("📊 تقرير كامل")
    btn3 = KeyboardButton("📋 سجل معاملاتي")
    btn4 = KeyboardButton("🔙 رجوع")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# --------------------- حالة المستخدمين ---------------------
user_states = {}

# --------------------- أوامر البوت والأزرار ---------------------

@bot.message_handler(commands=['start'])
def start(message):
    """رسالة ترحيبية مع أزرار"""
    # التحقق من أن البوت يعمل في مجموعة
    if message.chat.type not in ["group", "supergroup"]:
        bot.reply_to(message, "👋 مرحباً بك! هذا البوت يعمل فقط في المجموعات.")
        return
    
    bot.reply_to(message, 
        "👋 *مرحباً بك في بوت تتبع الأرصدة*\n\n"
        "📌 *الأزرار المتاحة:*\n"
        "• ➕ إيداع - لإضافة مبلغ مستلم\n"
        "• ➖ سحب - لخصم مبلغ مدفوع\n"
        "• 💰 رصيدي - لعرض رصيدك\n"
        "• 📊 تقارير - لعرض التقارير\n"
        "• 👤 ملفي الشخصي - لتسجيل أو تحديث بياناتك\n"
        "• 🔑 كود الشام كاش - لعرض كود الشام كاش الخاص بك\n"
        "• 📋 قائمة الأكواد - لعرض جميع الأكواد (للمشرفين)\n"
        "• ⚙️ إدارة - لأوامر المشرفين",
        parse_mode='Markdown',
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda message: message.text == "➕ إيداع")
def deposit(message):
    """زر الإيداع"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    user_states[message.from_user.id] = "waiting_deposit_amount"
    bot.reply_to(message, 
        "📥 *إيداع مبلغ*\n\n"
        "أرسل المبلغ الذي تريد إضافته:\n"
        "مثال: `1000` أو `500$`",
        parse_mode='Markdown',
        reply_markup=currency_menu()
    )

@bot.message_handler(func=lambda message: message.text == "➖ سحب")
def withdraw(message):
    """زر السحب"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    user_states[message.from_user.id] = "waiting_withdraw_amount"
    bot.reply_to(message, 
        "📤 *سحب مبلغ*\n\n"
        "أرسل المبلغ الذي تريد خصمه:\n"
        "مثال: `500` أو `50$`",
        parse_mode='Markdown',
        reply_markup=currency_menu()
    )

@bot.message_handler(func=lambda message: message.text == "💰 رصيدي")
def my_balance(message):
    """عرض الرصيد"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str not in data:
        bot.reply_to(message, "📭 لا توجد معاملات لك.")
        return
    
    user_data = data[user_id_str]
    bot.reply_to(message,
        f"💰 *رصيد {user_data['username']}*\n\n"
        f"🇸🇾 ليرة سورية: *{user_data['balance_sy']}* ل.س\n"
        f"💵 دولار أمريكي: *{user_data['balance_usd']}* USD",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "📊 تقارير")
def reports(message):
    """قائمة التقارير"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    bot.reply_to(message, "📊 *اختر نوع التقرير:*", parse_mode='Markdown', reply_markup=report_menu())

@bot.message_handler(func=lambda message: message.text == "📊 تقرير اليوم")
def report_today(message):
    """تقرير اليوم"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    data = load_data()
    if not data:
        bot.reply_to(message, "📭 لا توجد معاملات اليوم.")
        return
    
    report_text = "📊 *تقرير اليوم*\n"
    report_text += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
    report_text += "═" * 20 + "\n\n"
    
    total_in_sy = 0
    total_out_sy = 0
    total_in_usd = 0
    total_out_usd = 0
    
    for user_id, user_data in data.items():
        username = user_data["username"]
        full_name = user_data.get("full_name", "")
        
        report_text += f"👤 *{username}*"
        if full_name:
            report_text += f" ({full_name})"
        report_text += "\n"
        report_text += f"   📥 استلام: {user_data['total_in_sy']} ل.س"
        if user_data['total_in_usd'] > 0:
            report_text += f" / {user_data['total_in_usd']} USD"
        report_text += "\n"
        report_text += f"   📤 دفع: {user_data['total_out_sy']} ل.س"
        if user_data['total_out_usd'] > 0:
            report_text += f" / {user_data['total_out_usd']} USD"
        report_text += "\n"
        report_text += f"   💰 الرصيد: *{user_data['balance_sy']}* ل.س"
        if user_data['balance_usd'] != 0:
            report_text += f" / *{user_data['balance_usd']}* USD"
        report_text += "\n─" * 10 + "\n"
        
        total_in_sy += user_data['total_in_sy']
        total_out_sy += user_data['total_out_sy']
        total_in_usd += user_data['total_in_usd']
        total_out_usd += user_data['total_out_usd']
    
    report_text += "\n📈 *ملخص*\n"
    report_text += f"📥 إجمالي الاستلام: {total_in_sy} ل.س"
    if total_in_usd > 0:
        report_text += f" / {total_in_usd} USD"
    report_text += "\n"
    report_text += f"📤 إجمالي الدفع: {total_out_sy} ل.س"
    if total_out_usd > 0:
        report_text += f" / {total_out_usd} USD"
    
    bot.reply_to(message, report_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "📊 تقرير كامل")
def full_report(message):
    """تقرير كامل"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    data = load_data()
    if not data:
        bot.reply_to(message, "📭 لا توجد معاملات.")
        return
    
    sorted_users = sorted(data.items(), key=lambda x: x[1]["balance_sy"] + x[1]["balance_usd"] * 15000, reverse=True)
    
    report_text = "📊 *تقرير كامل*\n"
    report_text += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
    report_text += "═" * 20 + "\n\n"
    
    for user_id, user_data in sorted_users:
        full_name = user_data.get("full_name", "")
        report_text += f"👤 *{user_data['username']}*"
        if full_name:
            report_text += f" ({full_name})"
        report_text += "\n"
        report_text += f"   📥 استلام: {user_data['total_in_sy']} ل.س"
        if user_data['total_in_usd'] > 0:
            report_text += f" / {user_data['total_in_usd']} USD"
        report_text += "\n"
        report_text += f"   📤 دفع: {user_data['total_out_sy']} ل.س"
        if user_data['total_out_usd'] > 0:
            report_text += f" / {user_data['total_out_usd']} USD"
        report_text += "\n"
        report_text += f"   💰 الرصيد: *{user_data['balance_sy']}* ل.س"
        if user_data['balance_usd'] != 0:
            report_text += f" / *{user_data['balance_usd']}* USD"
        report_text += f"\n   📝 معاملات: {len(user_data['transactions'])}"
        report_text += "\n─" * 10 + "\n"
    
    bot.reply_to(message, report_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "📋 سجل معاملاتي")
def my_history(message):
    """سجل معاملاتي"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str not in data:
        bot.reply_to(message, "📭 لا توجد معاملات لك.")
        return
    
    user_data = data[user_id_str]
    transactions = user_data["transactions"][-10:]
    
    if not transactions:
        bot.reply_to(message, "📭 لا توجد معاملات.")
        return
    
    history_text = f"📋 *سجل معاملات {user_data['username']}*\n"
    history_text += "═" * 15 + "\n\n"
    
    for trans in reversed(transactions):
        emoji = "📥" if trans["type"] == "استلام" else "📤"
        history_text += f"{emoji} {trans['type']}: *{trans['amount']} {trans['currency']}*\n"
        history_text += f"🕐 {trans['time']}\n"
        if trans.get('note'):
            history_text += f"📝 {trans['note']}\n"
        history_text += "─" * 10 + "\n"
    
    bot.reply_to(message, history_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "👤 ملفي الشخصي")
def my_profile_menu(message):
    """قائمة الملف الشخصي"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton("📋 عرض ملفي")
    btn2 = KeyboardButton("✏️ تسجيل / تحديث")
    btn3 = KeyboardButton("🔙 رجوع")
    markup.add(btn1, btn2, btn3)
    bot.reply_to(message, "👤 *الملف الشخصي*\nاختر الإجراء المناسب:", parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📋 عرض ملفي")
def show_my_profile(message):
    """عرض الملف الشخصي"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str not in data:
        bot.reply_to(message, "📭 لا توجد بيانات لك. استخدم ✏️ تسجيل / تحديث لإضافة بياناتك.")
        return
    
    user_data = data[user_id_str]
    profile = f"📋 *الملف الشخصي*\n"
    profile += "═" * 20 + "\n\n"
    profile += f"👤 الاسم: {user_data.get('full_name', 'غير مسجل')}\n"
    profile += f"📱 رقم الهاتف: {user_data.get('phone', 'غير مسجل')}\n"
    profile += f"🔑 كود الشام كاش: {user_data.get('shamcash_code', 'غير مسجل')}\n"
    profile += f"💰 رصيد: {user_data['balance_sy']} ل.س"
    if user_data['balance_usd'] != 0:
        profile += f" / {user_data['balance_usd']} USD"
    profile += f"\n📥 استلام: {user_data['total_in_sy']} ل.س"
    if user_data['total_in_usd'] > 0:
        profile += f" / {user_data['total_in_usd']} USD"
    profile += f"\n📤 دفع: {user_data['total_out_sy']} ل.س"
    if user_data['total_out_usd'] > 0:
        profile += f" / {user_data['total_out_usd']} USD"
    profile += f"\n📝 معاملات: {len(user_data['transactions'])}"
    
    bot.reply_to(message, profile, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "✏️ تسجيل / تحديث")
def update_profile_start(message):
    """بدء تسجيل الملف الشخصي"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    user_states[message.from_user.id] = "waiting_full_name"
    bot.reply_to(message, 
        "✏️ *تسجيل / تحديث الملف الشخصي*\n\n"
        "📌 *الرجاء إدخال الاسم:*\n"
        "(يمكنك إدخال اسم واحد فقط بالعربية أو الإنجليزية)\n"
        "مثال: `أحمد` أو `Ahmed`",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "🔑 كود الشام كاش")
def my_shamcash_code(message):
    """عرض كود الشام كاش"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str not in data:
        bot.reply_to(message, "📭 لا توجد بيانات لك. استخدم ✏️ تسجيل / تحديث لإضافة بياناتك.")
        return
    
    user_data = data[user_id_str]
    shamcash_code = user_data.get("shamcash_code", "")
    
    if shamcash_code:
        bot.reply_to(message,
            f"🔑 *كود الشام كاش الخاص بك*\n\n"
            f"`{shamcash_code}`\n\n"
            f"📌 يمكنك مشاركة هذا الكود لاستقبال المدفوعات.",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, 
            "📭 لا يوجد كود شام كاش مسجل.\n\n"
            "💡 استخدم ✏️ تسجيل / تحديث لإضافة كود الشام كاش الخاص بك.",
            reply_markup=main_menu()
        )

@bot.message_handler(func=lambda message: message.text == "📋 قائمة الأكواد")
def list_codes(message):
    """عرض قائمة الأكواد (للمشرفين)"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    data = load_data()
    codes_list = []
    for user_id, user_data in data.items():
        shamcash_code = user_data.get("shamcash_code", "")
        if shamcash_code:
            codes_list.append({
                "username": user_data["username"],
                "full_name": user_data.get("full_name", "غير مسجل"),
                "phone": user_data.get("phone", "غير مسجل"),
                "code": shamcash_code
            })
    
    if not codes_list:
        bot.reply_to(message, "📭 لا توجد أكواد شام كاش مسجلة.")
        return
    
    report = "📋 *قائمة أكواد الشام كاش*\n"
    report += "═" * 20 + "\n\n"
    for item in codes_list:
        report += f"👤 {item['username']}\n"
        report += f"   الاسم: {item['full_name']}\n"
        report += f"   📱 هاتف: {item['phone']}\n"
        report += f"   🔑 `{item['code']}`\n"
        report += "─" * 10 + "\n"
    
    bot.reply_to(message, report, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "⚙️ إدارة")
def admin_panel(message):
    """لوحة التحكم (للمشرفين فقط)"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    bot.reply_to(message, "⚙️ *لوحة التحكم*\nاختر الإجراء المناسب:", parse_mode='Markdown', reply_markup=admin_menu())

@bot.message_handler(func=lambda message: message.text == "📋 تقرير موظف")
def admin_user_report(message):
    """تقرير موظف معين"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    user_states[message.from_user.id] = "admin_waiting_username"
    bot.reply_to(message, "👤 أدخل اسم المستخدم المراد التقرير عنه:\nمثال: `@أحمد`")

@bot.message_handler(func=lambda message: message.text == "📊 جميع المعاملات")
def admin_all_transactions(message):
    """جميع المعاملات"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    data = load_data()
    if not data:
        bot.reply_to(message, "📭 لا توجد معاملات.")
        return
    
    report = "📋 *جميع المعاملات*\n"
    report += "═" * 20 + "\n\n"
    
    for user_id, user_data in data.items():
        full_name = user_data.get("full_name", "")
        report += f"👤 *{user_data['username']}*"
        if full_name:
            report += f" ({full_name})"
        report += f"\n   📝 {len(user_data['transactions'])} معاملة\n"
        if user_data['transactions']:
            for trans in user_data['transactions'][-3:]:
                emoji = "📥" if trans["type"] == "استلام" else "📤"
                report += f"   {emoji} {trans['type']}: {trans['amount']} {trans['currency']} [{trans['time']}]\n"
        report += "─" * 10 + "\n"
    
    bot.reply_to(message, report, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🔄 تصفير الكل")
def admin_reset_all(message):
    """تصفير الأرصدة فقط"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    user_states[message.from_user.id] = "admin_confirm_reset"
    bot.reply_to(message, "⚠️ *تأكيد تصفير الكل*\n\nهل أنت متأكد من تصفير جميع الأرصدة؟\n📌 الملفات الشخصية والأكواد محفوظة.\n\nأرسل `نعم` للتأكيد أو `لا` للإلغاء.", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🔄 تصفير موظف")
def admin_reset_user(message):
    """تصفير موظف معين"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    user_states[message.from_user.id] = "admin_waiting_reset_user"
    bot.reply_to(message, "👤 أدخل اسم المستخدم المراد تصفير رصيده:\nمثال: `@أحمد`")

@bot.message_handler(func=lambda message: message.text == "🔙 رجوع")
def go_back(message):
    """العودة للقائمة الرئيسية"""
    if message.chat.type not in ["group", "supergroup"]:
        return
    bot.reply_to(message, "🔙 تم العودة للقائمة الرئيسية", reply_markup=main_menu())

# --------------------- معالجة الكولباك (الأزرار التفاعلية) ---------------------

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "currency_sy":
        user_states[call.from_user.id] = user_states.get(call.from_user.id, "").replace("currency", "sy")
        bot.answer_callback_query(call.id, "✅ تم اختيار الليرة السورية")
        bot.edit_message_text("🇸🇾 تم اختيار الليرة السورية.\nأرسل المبلغ:", call.message.chat.id, call.message.message_id)
    
    elif call.data == "currency_usd":
        user_states[call.from_user.id] = user_states.get(call.from_user.id, "").replace("currency", "usd")
        bot.answer_callback_query(call.id, "✅ تم اختيار الدولار")
        bot.edit_message_text("💵 تم اختيار الدولار الأمريكي.\nأرسل المبلغ:", call.message.chat.id, call.message.message_id)
    
    elif call.data == "cancel":
        user_states[call.from_user.id] = ""
        bot.answer_callback_query(call.id, "❌ تم الإلغاء")
        bot.edit_message_text("❌ تم الإلغاء.", call.message.chat.id, call.message.message_id)

# --------------------- معالجة الرسائل النصية ---------------------

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    # السماح للبوت بالعمل في أي مجموعة
    if message.chat.type not in ["group", "supergroup"]:
        return
    
    text = message.text.strip()
    user = message.from_user
    username = user.username or user.first_name
    user_id = user.id
    
    # --------------------- معالجة طلب "رابط @موظف" أو "كود @موظف" ---------------------
    if text.lower().startswith("رابط") or text.lower().startswith("كود"):
        parts = text.split()
        if len(parts) >= 2:
            target_username = parts[1].replace('@', '')
            data = load_data()
            for user_id_data, user_data in data.items():
                if user_data["username"].lower() == target_username.lower():
                    shamcash_code = user_data.get("shamcash_code", "")
                    if shamcash_code:
                        bot.reply_to(message,
                            f"🔑 *كود الشام كاش لـ {target_username}*\n\n`{shamcash_code}`",
                            parse_mode='Markdown'
                        )
                    else:
                        bot.reply_to(message, f"📭 لا يوجد كود شام كاش لـ {target_username}")
                    return
            bot.reply_to(message, f"❌ لم يتم العثور على {target_username}")
        return
    
    # --------------------- معالجة المبالغ المكتوبة يدوياً ---------------------
    amount = None
    currency = "sy"
    note = ""
    
    if text.startswith('+') or text.startswith('-'):
        try:
            parts = text.split()
            if '$' in parts[0] or 'دولار' in text:
                currency = "usd"
                amount_str = parts[0].replace('$', '').replace('+', '').replace('-', '')
                amount = -float(amount_str) if '-' in parts[0] else float(amount_str)
            else:
                amount = float(parts[0])
            if len(parts) > 1:
                note = ' '.join(parts[1:])
        except:
            pass
    
    elif "استلام" in text or "دفع" in text:
        try:
            parts = text.split()
            for i, part in enumerate(parts):
                if part in ["استلام", "دفع"]:
                    if i + 1 < len(parts):
                        amount_str = parts[i + 1]
                        if '$' in amount_str or 'دولار' in text:
                            currency = "usd"
                            amount_str = amount_str.replace('$', '')
                        amount = float(amount_str)
                        if part == "دفع":
                            amount = -amount
                        if len(parts) > i + 2:
                            note = ' '.join(parts[i+2:])
                        break
        except:
            pass
    
    if amount is not None and amount != 0:
        try:
            new_balance, trans_amount, trans_type, emoji, currency_symbol, total_in, total_out, username = add_transaction(
                user.id, username, amount, currency, note
            )
            
            bot.reply_to(message,
                f"{emoji} *تم تسجيل العملية*\n\n"
                f"👤 {username}\n"
                f"📌 {trans_type}: *{trans_amount} {currency_symbol}*\n"
                f"💰 الرصيد: *{new_balance} {currency_symbol}*",
                parse_mode='Markdown'
            )
            return
        except:
            pass
    
    # --------------------- معالجة حالة المستخدم ---------------------
    state = user_states.get(user_id, "")
    
    # معالجة الإيداع عبر الأزرار
    if state == "waiting_deposit_amount" or state == "waiting_deposit_sy" or state == "waiting_deposit_usd":
        try:
            amount_str = text.replace('$', '').strip()
            amount = float(amount_str)
            currency = "usd" if '$' in text else "sy"
            
            if amount <= 0:
                bot.reply_to(message, "⚠️ المبلغ يجب أن يكون أكبر من صفر.")
                return
            
            new_balance, trans_amount, trans_type, emoji, currency_symbol, total_in, total_out, username = add_transaction(
                user.id, username, amount, currency, ""
            )
            
            bot.reply_to(message,
                f"✅ *تم الإيداع*\n\n"
                f"👤 {username}\n"
                f"📥 المبلغ: *{trans_amount} {currency_symbol}*\n"
                f"💰 الرصيد: *{new_balance} {currency_symbol}*",
                parse_mode='Markdown'
            )
            user_states[user_id] = ""
            
        except ValueError:
            bot.reply_to(message, "⚠️ يرجى إدخال رقم صحيح.")
        return
    
    # معالجة السحب عبر الأزرار
    if state == "waiting_withdraw_amount" or state == "waiting_withdraw_sy" or state == "waiting_withdraw_usd":
        try:
            amount_str = text.replace('$', '').strip()
            amount = float(amount_str)
            currency = "usd" if '$' in text else "sy"
            
            if amount <= 0:
                bot.reply_to(message, "⚠️ المبلغ يجب أن يكون أكبر من صفر.")
                return
            
            new_balance, trans_amount, trans_type, emoji, currency_symbol, total_in, total_out, username = add_transaction(
                user.id, username, -amount, currency, ""
            )
            
            bot.reply_to(message,
                f"✅ *تم السحب*\n\n"
                f"👤 {username}\n"
                f"📤 المبلغ: *{trans_amount} {currency_symbol}*\n"
                f"💰 الرصيد: *{new_balance} {currency_symbol}*",
                parse_mode='Markdown'
            )
            user_states[user_id] = ""
            
        except ValueError:
            bot.reply_to(message, "⚠️ يرجى إدخال رقم صحيح.")
        return
    
    # معالجة تحديث الملف الشخصي - الاسم (اسم واحد فقط)
    if state == "waiting_full_name":
        # قبول أي اسم (عربي أو إنجليزي) بشرط ألا يكون فارغاً أو أرقام فقط
        if len(text.strip()) < 2:
            bot.reply_to(message, "⚠️ الرجاء إدخال اسم صحيح (حروف فقط، وليس أرقاماً).")
            return
        
        # التحقق من أن الاسم ليس أرقاماً فقط
        if text.strip().isdigit():
            bot.reply_to(message, "⚠️ الاسم لا يمكن أن يكون أرقاماً فقط. الرجاء إدخال اسم صحيح.")
            return
        
        user_states[user_id] = f"waiting_phone|{text.strip()}"
        bot.reply_to(message, 
            "📱 *أدخل رقم الهاتف:*\n"
            "مثال: `0912345678`",
            parse_mode='Markdown'
        )
        return
    
    if state.startswith("waiting_phone|"):
        name = state.split("|")[1]
        phone = text.strip()
        if not phone.isdigit():
            bot.reply_to(message, "⚠️ رقم الهاتف يجب أن يحتوي على أرقام فقط.")
            return
        if len(phone) < 9:
            bot.reply_to(message, "⚠️ رقم الهاتف قصير جداً. تأكد من إدخاله بشكل صحيح.")
            return
        user_states[user_id] = f"waiting_shamcash|{name}|{phone}"
        bot.reply_to(message, 
            "🔑 *أدخل كود الشام كاش الخاص بك:*\n"
            "مثال: `8324217cd72dae144243c7010390d636`",
            parse_mode='Markdown'
        )
        return
    
    if state.startswith("waiting_shamcash|"):
        parts = state.split("|")
        name = parts[1]
        phone = parts[2]
        shamcash_code = text.strip()
        
        if len(shamcash_code) < 5:
            bot.reply_to(message, "⚠️ كود الشام كاش قصير جداً. تأكد من إدخاله بشكل صحيح.")
            return
        
        data = load_data()
        user_id_str = str(user.id)
        
        if user_id_str not in data:
            data[user_id_str] = {
                "username": username,
                "full_name": name,
                "phone": phone,
                "shamcash_code": shamcash_code,
                "balance_sy": 0,
                "balance_usd": 0,
                "total_in_sy": 0,
                "total_out_sy": 0,
                "total_in_usd": 0,
                "total_out_usd": 0,
                "transactions": []
            }
        else:
            data[user_id_str]["full_name"] = name
            data[user_id_str]["phone"] = phone
            data[user_id_str]["shamcash_code"] = shamcash_code
        
        save_data(data)
        user_states[user_id] = ""
        
        bot.reply_to(message,
            f"✅ *تم تسجيل الملف الشخصي بنجاح*\n\n"
            f"👤 الاسم: {name}\n"
            f"📱 رقم الهاتف: {phone}\n"
            f"🔑 كود الشام كاش: `{shamcash_code}`",
            parse_mode='Markdown',
            reply_markup=main_menu()
        )
        return
    
    # معالجة تقرير موظف (للمشرفين)
    if state == "admin_waiting_username":
        target_username = text.replace('@', '')
        data = load_data()
        found = False
        
        for user_id_data, user_data in data.items():
            if user_data["username"].lower() == target_username.lower():
                found = True
                full_name = user_data.get("full_name", "")
                phone = user_data.get("phone", "")
                shamcash_code = user_data.get("shamcash_code", "")
                
                report = f"📊 *تقرير {user_data['username']}*\n"
                report += "═" * 20 + "\n\n"
                if full_name:
                    report += f"👤 الاسم: {full_name}\n"
                if phone:
                    report += f"📱 الهاتف: {phone}\n"
                if shamcash_code:
                    report += f"🔑 الشام كاش: `{shamcash_code}`\n"
                report += f"💰 رصيد: {user_data['balance_sy']} ل.س"
                if user_data['balance_usd'] != 0:
                    report += f" / {user_data['balance_usd']} USD"
                report += f"\n📥 استلام: {user_data['total_in_sy']} ل.س"
                if user_data['total_in_usd'] > 0:
                    report += f" / {user_data['total_in_usd']} USD"
                report += f"\n📤 دفع: {user_data['total_out_sy']} ل.س"
                if user_data['total_out_usd'] > 0:
                    report += f" / {user_data['total_out_usd']} USD"
                report += f"\n📝 معاملات: {len(user_data['transactions'])}"
                
                bot.reply_to(message, report, parse_mode='Markdown')
                user_states[user_id] = ""
                break
        
        if not found:
            bot.reply_to(message, f"❌ لم يتم العثور على {target_username}")
        return
    
    # معالجة تصفير موظف (للمشرفين)
    if state == "admin_waiting_reset_user":
        target_username = text.replace('@', '')
        data = load_data()
        found = False
        
        for user_id_data, user_data in data.items():
            if user_data["username"].lower() == target_username.lower():
                full_name = user_data.get("full_name", "")
                shamcash_code = user_data.get("shamcash_code", "")
                
                user_data["balance_sy"] = 0
                user_data["balance_usd"] = 0
                user_data["total_in_sy"] = 0
                user_data["total_out_sy"] = 0
                user_data["total_in_usd"] = 0
                user_data["total_out_usd"] = 0
                user_data["transactions"] = []
                
                save_data(data)
                found = True
                user_states[user_id] = ""
                
                bot.reply_to(message,
                    f"✅ *تم تصفير رصيد {target_username}*\n"
                    f"👤 الاسم: {full_name or 'غير مسجل'}\n"
                    f"🔑 الشام كاش: `{shamcash_code or 'غير مسجل'}`",
                    parse_mode='Markdown'
                )
                break
        
        if not found:
            bot.reply_to(message, f"❌ لم يتم العثور على {target_username}")
        return
    
    # معالجة تأكيد تصفير الكل
    if state == "admin_confirm_reset":
        if text == "نعم" or text == "yes":
            data = load_data()
            for user_id_data, user_data in data.items():
                user_data["balance_sy"] = 0
                user_data["balance_usd"] = 0
                user_data["total_in_sy"] = 0
                user_data["total_out_sy"] = 0
                user_data["total_in_usd"] = 0
                user_data["total_out_usd"] = 0
                user_data["transactions"] = []
            
            save_data(data)
            user_states[user_id] = ""
            bot.reply_to(message, "🔄 *تم تصفير جميع الأرصدة*\n📌 الملفات الشخصية وأكواد الشام كاش محفوظة.", parse_mode='Markdown')
        
        elif text == "لا" or text == "no":
            user_states[user_id] = ""
            bot.reply_to(message, "❌ تم إلغاء التصفير.")
        else:
            bot.reply_to(message, "⚠️ أرسل `نعم` للتأكيد أو `لا` للإلغاء.", parse_mode='Markdown')
        return

# --------------------- تشغيل البوت ---------------------

if __name__ == "__main__":
    print("=" * 40)
    print("🤖 بوت تتبع الأرصدة - يعمل في جميع المجموعات")
    print("=" * 40)
    print("✅ البوت يعمل في جميع المجموعات (بدون تحديد معرفات)")
    print("🔄 البوت يعمل مع إعادة تشغيل تلقائي...")
    print("📋 الملفات الشخصية وأكواد الشام كاش محفوظة")
    print("=" * 40)
    
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    print("✅ تم تشغيل خدمة الإبقاء على النشاط")
    
    bot_thread = threading.Thread(target=run_bot_with_retry, daemon=True)
    bot_thread.start()
    print("✅ تم تشغيل البوت مع إعادة تشغيل تلقائي")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
