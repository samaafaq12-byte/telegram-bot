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

# --------------------- الإعدادات ---------------------
TOKEN = "8998053211:AAHULMw1lmGRxcvxg_KzQZhG93yOdH6mENU"
GROUP_ID = -1004481566972
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
            "payment_code": "",
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

# --------------------- أوامر الملف الشخصي للموظف ---------------------

@bot.message_handler(commands=['myprofile'])
def my_profile(message):
    """عرض الملف الشخصي للموظف"""
    if message.chat.id != GROUP_ID:
        return
    
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str not in data:
        bot.reply_to(message, "📭 لا توجد بيانات لك. قم بأول عملية مبلغ أولاً.")
        return
    
    user_data = data[user_id_str]
    
    profile = f"📋 *الملف الشخصي لـ {user_data['username']}*\n"
    profile += "═" * 25 + "\n\n"
    profile += f"👤 الاسم الثلاثي: {user_data.get('full_name', 'غير مسجل')}\n"
    profile += f"📱 رقم الهاتف: {user_data.get('phone', 'غير مسجل')}\n"
    profile += f"🔑 كود الاستقبال: {user_data.get('payment_code', 'غير مسجل')}\n"
    profile += f"💰 رصيد الليرة: *{user_data['balance_sy']}* ل.س\n"
    profile += f"💰 رصيد الدولار: *{user_data['balance_usd']}* USD\n"
    profile += f"📥 إجمالي المستلم: {user_data['total_in_sy']} ل.س / {user_data['total_in_usd']} USD\n"
    profile += f"📤 إجمالي المدفوع: {user_data['total_out_sy']} ل.س / {user_data['total_out_usd']} USD\n"
    profile += f"📝 عدد المعاملات: {len(user_data['transactions'])}"
    
    bot.reply_to(message, profile, parse_mode='Markdown')

@bot.message_handler(commands=['setprofile'])
def set_profile(message):
    """تعيين الملف الشخصي للموظف (الاسم الثلاثي، رقم الهاتف، كود الاستقبال)"""
    if message.chat.id != GROUP_ID:
        return
    
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        bot.reply_to(message, 
            "⚠️ *استخدم:* `/setprofile الاسم_الثلاثي رقم_الهاتف كود_الاستقبال`\n\n"
            "مثال:\n"
            "`/setprofile أحمد محمد علي 0912345678 8324217cd72dae144243c7010390d636`",
            parse_mode='Markdown'
        )
        return
    
    full_name = parts[1].strip()
    phone = parts[2].strip()
    payment_code = parts[3].strip()
    
    if not phone.isdigit():
        bot.reply_to(message, "⚠️ رقم الهاتف يجب أن يحتوي على أرقام فقط.")
        return
    
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str not in data:
        data[user_id_str] = {
            "username": message.from_user.username or message.from_user.first_name,
            "full_name": full_name,
            "phone": phone,
            "payment_code": payment_code,
            "balance_sy": 0,
            "balance_usd": 0,
            "total_in_sy": 0,
            "total_out_sy": 0,
            "total_in_usd": 0,
            "total_out_usd": 0,
            "transactions": []
        }
    else:
        data[user_id_str]["full_name"] = full_name
        data[user_id_str]["phone"] = phone
        data[user_id_str]["payment_code"] = payment_code
    
    save_data(data)
    
    bot.reply_to(message,
        f"✅ *تم تحديث الملف الشخصي بنجاح*\n\n"
        f"👤 الاسم الثلاثي: {full_name}\n"
        f"📱 رقم الهاتف: {phone}\n"
        f"🔑 كود الاستقبال: `{payment_code}`",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['profile'])
def profile(message):
    """عرض الملف الشخصي لموظف معين (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
        return
    
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استخدم: `/profile @موظف`", parse_mode='Markdown')
        return
    
    target_username = parts[1].replace('@', '')
    
    data = load_data()
    found = False
    
    for user_id, user_data in data.items():
        if user_data["username"].lower() == target_username.lower():
            profile = f"📋 *الملف الشخصي لـ {user_data['username']}*\n"
            profile += "═" * 25 + "\n\n"
            profile += f"👤 الاسم الثلاثي: {user_data.get('full_name', 'غير مسجل')}\n"
            profile += f"📱 رقم الهاتف: {user_data.get('phone', 'غير مسجل')}\n"
            profile += f"🔑 كود الاستقبال: {user_data.get('payment_code', 'غير مسجل')}\n"
            profile += f"💰 رصيد الليرة: *{user_data['balance_sy']}* ل.س\n"
            profile += f"💰 رصيد الدولار: *{user_data['balance_usd']}* USD\n"
            profile += f"📥 إجمالي المستلم: {user_data['total_in_sy']} ل.س / {user_data['total_in_usd']} USD\n"
            profile += f"📤 إجمالي المدفوع: {user_data['total_out_sy']} ل.س / {user_data['total_out_usd']} USD\n"
            profile += f"📝 عدد المعاملات: {len(user_data['transactions'])}"
            
            bot.reply_to(message, profile, parse_mode='Markdown')
            found = True
            break
    
    if not found:
        bot.reply_to(message, f"❌ لم يتم العثور على {target_username}")

# --------------------- أوامر أكواد استقبال الراتب ---------------------

@bot.message_handler(commands=['setcode'])
def set_payment_code(message):
    """تعيين كود استقبال الراتب لموظف (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
        return
    
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ استخدم: `/setcode @موظف الكود`", parse_mode='Markdown')
        return
    
    target_username = parts[1].replace('@', '')
    payment_code = parts[2].strip()
    
    if not payment_code:
        bot.reply_to(message, "⚠️ الكود لا يمكن أن يكون فارغاً.")
        return
    
    data = load_data()
    found = False
    
    for user_id, user_data in data.items():
        if user_data["username"].lower() == target_username.lower():
            user_data["payment_code"] = payment_code
            save_data(data)
            found = True
            bot.reply_to(message, 
                f"✅ *تم تعيين كود استقبال الراتب لـ {target_username}*\n\n"
                f"🔑 `{payment_code}`",
                parse_mode='Markdown'
            )
            break
    
    if not found:
        bot.reply_to(message, f"❌ لم يتم العثور على {target_username}\n\n💡 تأكد من أن الموظف قام بعملية مبلغ واحدة على الأقل.")

@bot.message_handler(commands=['delcode'])
def delete_payment_code(message):
    """حذف كود استقبال الراتب لموظف (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
        return
    
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استخدم: `/delcode @موظف`", parse_mode='Markdown')
        return
    
    target_username = parts[1].replace('@', '')
    
    data = load_data()
    found = False
    
    for user_id, user_data in data.items():
        if user_data["username"].lower() == target_username.lower():
            user_data["payment_code"] = ""
            save_data(data)
            found = True
            bot.reply_to(message, f"🗑️ تم حذف كود استقبال {target_username}")
            break
    
    if not found:
        bot.reply_to(message, f"❌ لم يتم العثور على {target_username}")

@bot.message_handler(commands=['code'])
def get_payment_code(message):
    """عرض كود استقبال الراتب لموظف"""
    if message.chat.id != GROUP_ID:
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استخدم: `/code @موظف`", parse_mode='Markdown')
        return
    
    target_username = parts[1].replace('@', '')
    
    data = load_data()
    found = False
    
    for user_id, user_data in data.items():
        if user_data["username"].lower() == target_username.lower():
            found = True
            payment_code = user_data.get("payment_code", "")
            
            if payment_code:
                bot.reply_to(message,
                    f"🔑 *كود استقبال الراتب لـ {target_username}*\n\n"
                    f"`{payment_code}`",
                    parse_mode='Markdown'
                )
            else:
                bot.reply_to(message, f"📭 لا يوجد كود استقبال مسجل لـ {target_username}")
            break
    
    if not found:
        bot.reply_to(message, f"❌ لم يتم العثور على {target_username}")

@bot.message_handler(commands=['mycode'])
def my_payment_code(message):
    """عرض كود استقبال الراتب الخاص بي"""
    if message.chat.id != GROUP_ID:
        return
    
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str not in data:
        bot.reply_to(message, "📭 لا توجد بيانات لك. قم بأول عملية مبلغ أولاً.")
        return
    
    user_data = data[user_id_str]
    payment_code = user_data.get("payment_code", "")
    
    if payment_code:
        bot.reply_to(message,
            f"🔑 *كود استقبال الراتب الخاص بك*\n\n"
            f"`{payment_code}`",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, 
            "📭 لا يوجد كود استقبال مسجل لك.\n\n"
            "💡 استخدم الأمر التالي لتسجيل ملفك الشخصي:\n"
            "`/setprofile الاسم_الثلاثي رقم_الهاتف كود_الاستقبال`",
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['listcodes'])
def list_all_codes(message):
    """عرض جميع الأكواد المسجلة (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
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
        payment_code = user_data.get("payment_code", "")
        if payment_code:
            codes_list.append({
                "username": user_data["username"],
                "code": payment_code,
                "full_name": user_data.get("full_name", "غير مسجل"),
                "phone": user_data.get("phone", "غير مسجل")
            })
    
    if not codes_list:
        bot.reply_to(message, "📭 لا توجد أكواد مسجلة.")
        return
    
    report = "📋 *قائمة أكواد استقبال الراتب*\n"
    report += "═" * 20 + "\n\n"
    
    for item in codes_list:
        report += f"👤 *{item['username']}*\n"
        report += f"   الاسم: {item['full_name']}\n"
        report += f"   📱 هاتف: {item['phone']}\n"
        report += f"   🔑 `{item['code']}`\n"
        report += "─" * 15 + "\n"
    
    bot.reply_to(message, report, parse_mode='Markdown')

# --------------------- أوامر التقارير ---------------------

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "👋 *مرحباً! أنا بوت تتبع الأرصدة*\n\n"
        "📌 *لإضافة مبلغ مستلم بالليرة السورية:*\n"
        "`+1000` أو `استلام 1000`\n\n"
        "📌 *لخصم مبلغ مدفوع بالليرة السورية:*\n"
        "`-500` أو `دفع 500`\n\n"
        "📌 *لإضافة مبلغ مستلم بالدولار:*\n"
        "`+100$` أو `استلام 100 دولار`\n\n"
        "📌 *لخصم مبلغ مدفوع بالدولار:*\n"
        "`-50$` أو `دفع 50 دولار`\n\n"
        "📋 *الملف الشخصي:*\n"
        "`/setprofile الاسم_الثلاثي رقم_الهاتف كود_الاستقبال` - تسجيل ملفك الشخصي\n"
        "`/myprofile` - عرض ملفك الشخصي\n"
        "`/profile @موظف` - عرض ملف موظف (للمشرفين)\n\n"
        "🔑 *أكواد استقبال الراتب:*\n"
        "`/code @موظف` - عرض كود موظف\n"
        "`/mycode` - عرض كودك\n"
        "`/listcodes` - عرض جميع الأكواد (للمشرفين)\n\n"
        "📊 *أوامر التقارير:*\n"
        "`/balance` - عرض رصيدك فقط\n"
        "`/myreport` - تقريرك المفصل\n"
        "`/history` - سجل معاملاتك\n"
        "`/report` - تقرير اليوم للجميع\n"
        "`/fullreport` - تقرير كامل\n\n"
        "👑 *أوامر المشرفين:*\n"
        "`/user_report @username` - تقرير موظف محدد\n"
        "`/all_transactions` - جميع المعاملات\n"
        "`/reset` - تصفير الأرصدة فقط (الملف الشخصي محفوظ)\n"
        "`/reset_user @username` - تصفير رصيد موظف (الملف الشخصي محفوظ)\n"
        "`/reset_confirm` - عرض ملخص قبل التصفير\n"
        "`/archive` - عرض ملفات الأرشيف\n\n"
        "📌 *ملاحظة:* الملفات الشخصية والأكواد **لا تُحذف** عند التصفير أو مسح المحادثات",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['balance'])
def balance(message):
    if message.chat.id != GROUP_ID:
        return
    
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str in data:
        user_data = data[user_id_str]
        bot.reply_to(message,
            f"👤 *{user_data['username']}*\n\n"
            f"🇸🇾 *رصيد الليرة:* {user_data['balance_sy']} ل.س\n"
            f"💵 *رصيد الدولار:* {user_data['balance_usd']} USD",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, "📭 لا توجد معاملات لك اليوم.")

@bot.message_handler(commands=['myreport'])
def my_report(message):
    if message.chat.id != GROUP_ID:
        return
    
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str not in data:
        bot.reply_to(message, "📭 لا توجد معاملات لك اليوم.")
        return
    
    user_data = data[user_id_str]
    
    report = f"📊 *تقرير رصيد {user_data['username']}*\n"
    report += "═" * 20 + "\n\n"
    
    report += "🇸🇾 *الليرة السورية:*\n"
    report += f"   💰 الرصيد: *{user_data['balance_sy']}* ل.س\n"
    report += f"   📥 إجمالي المستلم: {user_data['total_in_sy']} ل.س\n"
    report += f"   📤 إجمالي المدفوع: {user_data['total_out_sy']} ل.س\n\n"
    
    report += "💵 *الدولار الأمريكي:*\n"
    report += f"   💰 الرصيد: *{user_data['balance_usd']}* USD\n"
    report += f"   📥 إجمالي المستلم: {user_data['total_in_usd']} USD\n"
    report += f"   📤 إجمالي المدفوع: {user_data['total_out_usd']} USD\n\n"
    
    report += f"📝 عدد المعاملات: {len(user_data['transactions'])}"
    
    payment_code = user_data.get("payment_code", "")
    if payment_code:
        report += f"\n\n🔑 *كود استقبال الراتب:*\n`{payment_code}`"
    
    bot.reply_to(message, report, parse_mode='Markdown')

@bot.message_handler(commands=['history'])
def history(message):
    if message.chat.id != GROUP_ID:
        return
    
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str not in data:
        bot.reply_to(message, "📭 لا توجد معاملات لك اليوم.")
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

@bot.message_handler(commands=['report'])
def report(message):
    """تقرير اليوم: إجمالي ما تم استلامه وإرساله للجميع"""
    if message.chat.id != GROUP_ID:
        return
    
    data = load_data()
    
    if not data:
        bot.reply_to(message, "📭 لا توجد معاملات اليوم.")
        return
    
    report_text = "📊 *تقرير إجمالي اليوم*\n"
    report_text += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
    report_text += "═" * 20 + "\n\n"
    
    total_in_sy_all = 0
    total_out_sy_all = 0
    total_in_usd_all = 0
    total_out_usd_all = 0
    total_balance_sy = 0
    total_balance_usd = 0
    
    for user_id, user_data in data.items():
        username = user_data["username"]
        full_name = user_data.get("full_name", "")
        
        report_text += f"👤 *{username}*"
        if full_name:
            report_text += f" ({full_name})"
        report_text += "\n"
        report_text += f"   📥 استلام (ل.س): {user_data['total_in_sy']}\n"
        report_text += f"   📤 إرسال (ل.س): {user_data['total_out_sy']}\n"
        report_text += f"   💰 الرصيد (ل.س): *{user_data['balance_sy']}*\n"
        
        if user_data['total_in_usd'] > 0 or user_data['total_out_usd'] > 0 or user_data['balance_usd'] != 0:
            report_text += f"   📥 استلام (USD): {user_data['total_in_usd']}\n"
            report_text += f"   📤 إرسال (USD): {user_data['total_out_usd']}\n"
            report_text += f"   💰 الرصيد (USD): *{user_data['balance_usd']}*\n"
        
        report_text += "─" * 15 + "\n"
        
        total_in_sy_all += user_data['total_in_sy']
        total_out_sy_all += user_data['total_out_sy']
        total_in_usd_all += user_data['total_in_usd']
        total_out_usd_all += user_data['total_out_usd']
        total_balance_sy += user_data['balance_sy']
        total_balance_usd += user_data['balance_usd']
    
    report_text += "\n📈 *ملخص عام*\n"
    report_text += f"🇸🇾 إجمالي الاستلام (ل.س): {total_in_sy_all}\n"
    report_text += f"🇸🇾 إجمالي الإرسال (ل.س): {total_out_sy_all}\n"
    report_text += f"🇸🇾 إجمالي الأرصدة (ل.س): *{total_balance_sy}*\n"
    
    if total_in_usd_all > 0 or total_out_usd_all > 0 or total_balance_usd != 0:
        report_text += f"\n💵 إجمالي الاستلام (USD): {total_in_usd_all}\n"
        report_text += f"💵 إجمالي الإرسال (USD): {total_out_usd_all}\n"
        report_text += f"💵 إجمالي الأرصدة (USD): *{total_balance_usd}*\n"
    
    bot.reply_to(message, report_text, parse_mode='Markdown')

@bot.message_handler(commands=['fullreport'])
def full_report(message):
    """تقرير كامل مع تفاصيل كل موظف"""
    if message.chat.id != GROUP_ID:
        return
    
    data = load_data()
    
    if not data:
        bot.reply_to(message, "📭 لا توجد معاملات اليوم.")
        return
    
    sorted_users = sorted(data.items(), key=lambda x: x[1]["balance_sy"] + x[1]["balance_usd"] * 15000, reverse=True)
    
    report_text = "📊 *تقرير كامل*\n"
    report_text += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
    report_text += "═" * 20 + "\n\n"
    
    total_in_sy_all = 0
    total_out_sy_all = 0
    total_in_usd_all = 0
    total_out_usd_all = 0
    total_balance_sy = 0
    total_balance_usd = 0
    
    for user_id, user_data in sorted_users:
        username = user_data["username"]
        full_name = user_data.get("full_name", "")
        
        report_text += f"👤 *{username}*"
        if full_name:
            report_text += f" ({full_name})"
        report_text += "\n"
        report_text += f"   📥 استلام (ل.س): {user_data['total_in_sy']}\n"
        report_text += f"   📤 إرسال (ل.س): {user_data['total_out_sy']}\n"
        report_text += f"   💰 الرصيد (ل.س): *{user_data['balance_sy']}*\n"
        report_text += f"   📝 عدد المعاملات: {len(user_data['transactions'])}\n"
        
        if user_data['total_in_usd'] > 0 or user_data['total_out_usd'] > 0 or user_data['balance_usd'] != 0:
            report_text += f"   📥 استلام (USD): {user_data['total_in_usd']}\n"
            report_text += f"   📤 إرسال (USD): {user_data['total_out_usd']}\n"
            report_text += f"   💰 الرصيد (USD): *{user_data['balance_usd']}*\n"
        
        payment_code = user_data.get("payment_code", "")
        if payment_code:
            report_text += f"   🔑 كود: `{payment_code}`\n"
        
        report_text += "─" * 15 + "\n"
        
        total_in_sy_all += user_data['total_in_sy']
        total_out_sy_all += user_data['total_out_sy']
        total_in_usd_all += user_data['total_in_usd']
        total_out_usd_all += user_data['total_out_usd']
        total_balance_sy += user_data['balance_sy']
        total_balance_usd += user_data['balance_usd']
    
    report_text += "\n📈 *ملخص عام*\n"
    report_text += f"🇸🇾 إجمالي الاستلام (ل.س): {total_in_sy_all}\n"
    report_text += f"🇸🇾 إجمالي الإرسال (ل.س): {total_out_sy_all}\n"
    report_text += f"🇸🇾 إجمالي الأرصدة (ل.س): *{total_balance_sy}*\n"
    
    if total_in_usd_all > 0 or total_out_usd_all > 0 or total_balance_usd != 0:
        report_text += f"\n💵 إجمالي الاستلام (USD): {total_in_usd_all}\n"
        report_text += f"💵 إجمالي الإرسال (USD): {total_out_usd_all}\n"
        report_text += f"💵 إجمالي الأرصدة (USD): *{total_balance_usd}*\n"
    
    bot.reply_to(message, report_text, parse_mode='Markdown')

# --------------------- أوامر المشرفين (التقارير المتقدمة) ---------------------

@bot.message_handler(commands=['user_report'])
def user_report(message):
    """عرض تقرير مفصل لموظف معين (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
        return
    
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استخدم: `/user_report @username`", parse_mode='Markdown')
        return
    
    target_username = parts[1].replace('@', '')
    
    data = load_data()
    found = False
    
    for user_id, user_data in data.items():
        if user_data["username"].lower() == target_username.lower():
            full_name = user_data.get("full_name", "")
            phone = user_data.get("phone", "")
            
            report = f"📊 *تقرير الموظف: {user_data['username']}*\n"
            if full_name:
                report += f"👤 الاسم: {full_name}\n"
            if phone:
                report += f"📱 الهاتف: {phone}\n"
            report += "═" * 25 + "\n\n"
            
            report += "🇸🇾 *الليرة السورية:*\n"
            report += f"   💰 الرصيد: *{user_data['balance_sy']}* ل.س\n"
            report += f"   📥 إجمالي المستلم: {user_data['total_in_sy']} ل.س\n"
            report += f"   📤 إجمالي المدفوع: {user_data['total_out_sy']} ل.س\n\n"
            
            report += "💵 *الدولار الأمريكي:*\n"
            report += f"   💰 الرصيد: *{user_data['balance_usd']}* USD\n"
            report += f"   📥 إجمالي المستلم: {user_data['total_in_usd']} USD\n"
            report += f"   📤 إجمالي المدفوع: {user_data['total_out_usd']} USD\n\n"
            
            payment_code = user_data.get("payment_code", "")
            if payment_code:
                report += f"🔑 *كود استقبال الراتب:*\n`{payment_code}`\n\n"
            
            report += f"📝 عدد المعاملات: {len(user_data['transactions'])}\n"
            report += "─" * 15 + "\n\n"
            
            if user_data['transactions']:
                report += "📋 *آخر 5 معاملات:*\n"
                for trans in reversed(user_data['transactions'][-5:]):
                    emoji = "📥" if trans["type"] == "استلام" else "📤"
                    report += f"{emoji} {trans['type']}: *{trans['amount']} {trans['currency']}*\n"
                    report += f"   🕐 {trans['time']}\n"
                    if trans.get('note'):
                        report += f"   📝 {trans['note']}\n"
            
            bot.reply_to(message, report, parse_mode='Markdown')
            found = True
            break
    
    if not found:
        bot.reply_to(message, f"❌ لم يتم العثور على {target_username}")

@bot.message_handler(commands=['all_transactions'])
def all_transactions(message):
    if message.chat.id != GROUP_ID:
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
    if not data:
        bot.reply_to(message, "📭 لا توجد معاملات اليوم.")
        return
    
    report = "📋 *جميع المعاملات*\n"
    report += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
    report += "═" * 20 + "\n\n"
    
    for user_id, user_data in data.items():
        full_name = user_data.get("full_name", "")
        report += f"👤 *{user_data['username']}*"
        if full_name:
            report += f" ({full_name})"
        report += f" - {len(user_data['transactions'])} معاملات\n"
        
        if user_data['transactions']:
            for trans in user_data['transactions']:
                emoji = "📥" if trans["type"] == "استلام" else "📤"
                report += f"   {emoji} {trans['type']}: *{trans['amount']} {trans['currency']}*"
                report += f" [{trans['time']}]\n"
                if trans.get('note'):
                    report += f"      📝 {trans['note']}\n"
        else:
            report += "   📭 لا توجد معاملات\n"
        
        report += "─" * 10 + "\n"
    
    bot.reply_to(message, report, parse_mode='Markdown')

# --------------------- أوامر التصفير (تصفير الأرصدة فقط - الملف الشخصي محفوظ) ---------------------

@bot.message_handler(commands=['reset'])
def reset_balances(message):
    """تصفير الأرصدة فقط - الملف الشخصي والأكواد محفوظة (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
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
    
    if data:
        backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        bot.reply_to(message, f"📦 تم حفظ نسخة احتياطية: `{backup_file}`", parse_mode='Markdown')
    
    for user_id, user_data in data.items():
        # تصفير الأرصدة والإحصائيات فقط
        user_data["balance_sy"] = 0
        user_data["balance_usd"] = 0
        user_data["total_in_sy"] = 0
        user_data["total_out_sy"] = 0
        user_data["total_in_usd"] = 0
        user_data["total_out_usd"] = 0
        user_data["transactions"] = []
        # ✅ الملف الشخصي (full_name, phone, payment_code) لا يتم حذفه!
    
    save_data(data)
    
    # عرض عدد الملفات الشخصية المحفوظة
    profiles_count = sum(1 for u in data.values() if u.get("full_name", ""))
    codes_count = sum(1 for u in data.values() if u.get("payment_code", ""))
    
    bot.reply_to(message, 
        f"🔄 *تم تصفير الأرصدة بنجاح*\n\n"
        f"📋 عدد الملفات الشخصية المحفوظة: {profiles_count}\n"
        f"🔑 عدد الأكواد المحفوظة: {codes_count}\n\n"
        f"📌 *ملاحظة:* الملفات الشخصية والأكواد **لم تُحذف**",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['reset_user'])
def reset_user_balance(message):
    """تصفير رصيد موظف معين فقط - الملف الشخصي محفوظ (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
        return
    
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استخدم: `/reset_user @username`", parse_mode='Markdown')
        return
    
    target_username = parts[1].replace('@', '')
    
    data = load_data()
    found = False
    
    for user_id, user_data in data.items():
        if user_data["username"].lower() == target_username.lower():
            full_name = user_data.get("full_name", "")
            phone = user_data.get("phone", "")
            payment_code = user_data.get("payment_code", "")
            
            # تصفير الأرصدة فقط
            user_data["balance_sy"] = 0
            user_data["balance_usd"] = 0
            user_data["total_in_sy"] = 0
            user_data["total_out_sy"] = 0
            user_data["total_in_usd"] = 0
            user_data["total_out_usd"] = 0
            user_data["transactions"] = []
            # ✅ الملف الشخصي لا يتم حذفه!
            
            save_data(data)
            found = True
            
            bot.reply_to(message, 
                f"✅ *تم تصفير رصيد {target_username}*\n\n"
                f"👤 الاسم: {full_name or 'غير مسجل'}\n"
                f"📱 الهاتف: {phone or 'غير مسجل'}\n"
                f"🔑 الكود: `{payment_code or 'غير مسجل'}`\n\n"
                f"📌 *ملاحظة:* الملف الشخصي **لم يُحذف**",
                parse_mode='Markdown'
            )
            break
    
    if not found:
        bot.reply_to(message, f"❌ لم يتم العثور على {target_username}")

@bot.message_handler(commands=['reset_confirm'])
def reset_confirm(message):
    """تأكيد تصفير الأرصدة فقط (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
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
    if not data:
        bot.reply_to(message, "📭 لا توجد بيانات لتصفيرها.")
        return
    
    summary = "📊 *ملخص البيانات قبل التصفير*\n"
    summary += "═" * 15 + "\n\n"
    
    total_balance_sy = 0
    total_balance_usd = 0
    profiles_count = 0
    codes_count = 0
    
    for user_id, user_data in data.items():
        full_name = user_data.get("full_name", "")
        summary += f"👤 {user_data['username']}"
        if full_name:
            summary += f" ({full_name})"
        summary += ":\n"
        summary += f"   🇸🇾 الرصيد: {user_data['balance_sy']} ل.س\n"
        summary += f"   💵 الرصيد: {user_data['balance_usd']} USD\n"
        if user_data.get("payment_code", ""):
            codes_count += 1
        if full_name:
            profiles_count += 1
        
        total_balance_sy += user_data['balance_sy']
        total_balance_usd += user_data['balance_usd']
    
    summary += f"\n💰 إجمالي أرصدة الليرة: *{total_balance_sy}* ل.س"
    summary += f"\n💰 إجمالي أرصدة الدولار: *{total_balance_usd}* USD"
    summary += f"\n📋 عدد الملفات الشخصية: *{profiles_count}*"
    summary += f"\n🔑 عدد الأكواد: *{codes_count}*"
    summary += "\n\n⚠️ *هل أنت متأكد؟* استخدم `/reset` للتأكيد.\n"
    summary += "📌 ملاحظة: **سيتم تصفير الأرصدة فقط**، الملفات الشخصية والأكواد **محفوظة**."
    
    bot.reply_to(message, summary, parse_mode='Markdown')

@bot.message_handler(commands=['archive'])
def show_archive(message):
    if message.chat.id != GROUP_ID:
        return
    
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    archive_files = [f for f in os.listdir('.') if f.startswith('archive_') and f.endswith('.json')]
    
    if not archive_files:
        bot.reply_to(message, "📭 لا توجد ملفات أرشيف.")
        return
    
    files_text = "📁 *ملفات الأرشيف المتاحة*\n"
    files_text += "═" * 15 + "\n\n"
    
    for file in sorted(archive_files, reverse=True):
        size = os.path.getsize(file) / 1024
        files_text += f"📄 `{file}` ({size:.1f} KB)\n"
    
    bot.reply_to(message, files_text, parse_mode='Markdown')

# --------------------- معالجة الرسائل النصية ---------------------

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.chat.id != GROUP_ID:
        return
    
    text = message.text.strip()
    user = message.from_user
    username = user.username or user.first_name
    
    # --------------------- معالجة طلب "رابط @موظف" أو "كود @موظف" ---------------------
    if text.lower().startswith("رابط") or text.lower().startswith("كود"):
        parts = text.split()
        if len(parts) >= 2:
            target_username = parts[1].replace('@', '')
            data = load_data()
            found = False
            for user_id, user_data in data.items():
                if user_data["username"].lower() == target_username.lower():
                    found = True
                    payment_code = user_data.get("payment_code", "")
                    if payment_code:
                        bot.reply_to(message,
                            f"🔑 *كود استقبال الراتب لـ {target_username}*\n\n"
                            f"`{payment_code}`",
                            parse_mode='Markdown'
                        )
                    else:
                        bot.reply_to(message, f"📭 لا يوجد كود استقبال مسجل لـ {target_username}")
                    break
            if not found:
                bot.reply_to(message, f"❌ لم يتم العثور على {target_username}")
        return
    
    # --------------------- معالجة المبالغ ---------------------
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
    
    elif '$' in text:
        try:
            match = re.search(r'([+-]?\d+\.?\d*)\s*\$', text)
            if match:
                amount = float(match.group(1))
                currency = "usd"
                parts = text.split()
                for i, part in enumerate(parts):
                    if '$' in part and len(parts) > i + 1:
                        note = ' '.join(parts[i+1:])
                        break
        except:
            pass
    
    if amount is None or amount == 0:
        return
    
    try:
        new_balance, trans_amount, trans_type, emoji, currency_symbol, total_in, total_out, username = add_transaction(
            user.id, username, amount, currency, note
        )
        
        reply = f"{emoji} *تم تسجيل العملية بنجاح*\n\n"
        reply += f"👤 {username}\n"
        reply += f"📌 {trans_type}: *{trans_amount} {currency_symbol}*\n"
        reply += f"💰 الرصيد الحالي: *{new_balance} {currency_symbol}*\n"
        
        if note:
            reply += f"📝 ملاحظة: {note}\n"
        
        reply += "\n" + "─" * 15 + "\n"
        reply += "📊 *تقريرك السريع:*\n"
        reply += f"📥 إجمالي المستلم: {total_in} {currency_symbol}\n"
        reply += f"📤 إجمالي المدفوع: {total_out} {currency_symbol}\n"
        
        user_data = get_user_full_report(user.id)
        if user_data:
            if currency == "sy":
                other_balance = user_data["balance_usd"]
                other_symbol = "💵 USD"
            else:
                other_balance = user_data["balance_sy"]
                other_symbol = "🇸🇾 ل.س"
            
            if other_balance != 0:
                reply += f"\n💡 *رصيدك بالعملة الأخرى:* {other_balance} {other_symbol}"
        
        bot.reply_to(message, reply, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ حدث خطأ: {str(e)}")

# --------------------- تشغيل البوت ---------------------

if __name__ == "__main__":
    print("=" * 40)
    print("🤖 بوت تتبع الأرصدة (مع الملفات الشخصية - تصفير الأرصدة فقط)")
    print("=" * 40)
    print(f"✅ معرف المجموعة: {GROUP_ID}")
    print("🔄 البوت يعمل مع إعادة تشغيل تلقائي...")
    print("📋 الملفات الشخصية محفوظة ولا تُحذف عند التصفير")
    print("📌 التصفير يمسح الأرصدة فقط - الملفات الشخصية والأكواد محفوظة")
    print("=" * 40)
    
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    print("✅ تم تشغيل خدمة الإبقاء على النشاط")
    
    bot_thread = threading.Thread(target=run_bot_with_retry, daemon=True)
    bot_thread.start()
    print("✅ تم تشغيل البوت مع إعادة تشغيل تلقائي")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
