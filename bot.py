# -*- coding: utf-8 -*-
import telebot
import json
import os
from datetime import datetime
from flask import Flask
import threading

# --------------------- الإعدادات ---------------------
TOKEN = "8952384966:AAH6509zEqo73asesJRBzPutsuyqD-eZqzM"
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

# --------------------- قاعدة البيانات ---------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

last_reset_date = datetime.now().date()

def reset_daily_if_needed():
    global last_reset_date
    today = datetime.now().date()
    if today != last_reset_date:
        data = load_data()
        if data:
            archive_file = f"archive_{last_reset_date}.json"
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"📦 تم حفظ أرشيف: {archive_file}")
        save_data({})
        last_reset_date = today
        print(f"🔄 تم إعادة تعيين البيانات لليوم {today}")

def add_transaction(user_id, username, amount, currency, note=""):
    reset_daily_if_needed()
    
    data = load_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data:
        data[user_id_str] = {
            "username": username,
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

# --------------------- دوال عرض التقرير المخصص ---------------------

def get_user_full_report(user_id):
    """الحصول على تقرير كامل للمستخدم"""
    data = load_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data:
        return None
    
    user_data = data[user_id_str]
    return user_data

def format_balance_report(username, balance_sy, balance_usd, total_in_sy, total_out_sy, total_in_usd, total_out_usd, transactions_count):
    """تنسيق تقرير الرصيد بشكل جميل"""
    report = f"📊 *تقرير رصيد {username}*\n"
    report += "═" * 20 + "\n\n"
    
    report += "🇸🇾 *الليرة السورية:*\n"
    report += f"   💰 الرصيد: *{balance_sy}* ل.س\n"
    report += f"   📥 إجمالي المستلم: {total_in_sy} ل.س\n"
    report += f"   📤 إجمالي المدفوع: {total_out_sy} ل.س\n\n"
    
    report += "💵 *الدولار الأمريكي:*\n"
    report += f"   💰 الرصيد: *{balance_usd}* USD\n"
    report += f"   📥 إجمالي المستلم: {total_in_usd} USD\n"
    report += f"   📤 إجمالي المدفوع: {total_out_usd} USD\n\n"
    
    report += f"📝 عدد المعاملات اليوم: {transactions_count}"
    
    return report

# --------------------- أوامر البوت ---------------------

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
        "📊 *عرض تقرير مفصل:*\n"
        "`/report` - تقرير اليوم للجميع\n"
        "`/myreport` - تقريرك المفصل\n\n"
        "📋 *عرض سجل معاملاتك:*\n"
        "`/history`\n\n"
        "💰 *عرض رصيدك الحالي:*\n"
        "`/balance`",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['balance'])
def balance(message):
    """عرض الرصيد فقط"""
    if message.chat.id != GROUP_ID:
        return
    
    reset_daily_if_needed()
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
    """عرض تقرير مفصل للمستخدم نفسه"""
    if message.chat.id != GROUP_ID:
        return
    
    reset_daily_if_needed()
    user_data = get_user_full_report(message.from_user.id)
    
    if not user_data:
        bot.reply_to(message, "📭 لا توجد معاملات لك اليوم.")
        return
    
    report = format_balance_report(
        user_data["username"],
        user_data["balance_sy"],
        user_data["balance_usd"],
        user_data["total_in_sy"],
        user_data["total_out_sy"],
        user_data["total_in_usd"],
        user_data["total_out_usd"],
        len(user_data["transactions"])
    )
    
    bot.reply_to(message, report, parse_mode='Markdown')

@bot.message_handler(commands=['history'])
def history(message):
    if message.chat.id != GROUP_ID:
        return
    
    reset_daily_if_needed()
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
    if message.chat.id != GROUP_ID:
        return
    
    reset_daily_if_needed()
    data = load_data()
    
    if not data:
        bot.reply_to(message, "📭 لا توجد معاملات اليوم.")
        return
    
    sorted_users = sorted(data.items(), key=lambda x: x[1]["balance_sy"] + x[1]["balance_usd"] * 15000, reverse=True)
    
    report_text = "📊 *تقرير نهاية اليوم*\n"
    report_text += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n"
    report_text += "═" * 20 + "\n\n"
    
    total_balance_sy = 0
    total_balance_usd = 0
    
    for user_id, user_data in sorted_users:
        username = user_data["username"]
        report_text += f"👤 *{username}*\n"
        report_text += f"   🇸🇾 رصيد الليرة: *{user_data['balance_sy']}* ل.س\n"
        report_text += f"   💵 رصيد الدولار: *{user_data['balance_usd']}* USD\n"
        report_text += "─" * 10 + "\n"
        
        total_balance_sy += user_data['balance_sy']
        total_balance_usd += user_data['balance_usd']
    
    report_text += "\n📈 *ملخص عام*\n"
    report_text += f"🇸🇾 إجمالي أرصدة الليرة: {total_balance_sy} ل.س\n"
    report_text += f"💵 إجمالي أرصدة الدولار: {total_balance_usd} USD"
    
    bot.reply_to(message, report_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.chat.id != GROUP_ID:
        return
    
    text = message.text.strip()
    user = message.from_user
    username = user.username or user.first_name
    
    amount = None
    currency = "sy"
    note = ""
    
    # معالجة الليرة السورية
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
            import re
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
        
        # بناء رسالة التأكيد مع التقرير
        reply = f"{emoji} *تم تسجيل العملية بنجاح*\n\n"
        reply += f"👤 {username}\n"
        reply += f"📌 {trans_type}: *{trans_amount} {currency_symbol}*\n"
        reply += f"💰 الرصيد الحالي: *{new_balance} {currency_symbol}*\n"
        
        if note:
            reply += f"📝 ملاحظة: {note}\n"
        
        reply += "\n" + "─" * 15 + "\n"
        reply += "📊 *تقريرك السريع:*\n"
        reply += f"📥 إجمالي المستلم اليوم: {total_in} {currency_symbol}\n"
        reply += f"📤 إجمالي المدفوع اليوم: {total_out} {currency_symbol}\n"
        
        # عرض تقرير كامل مع العملتين إذا كان المستخدم لديه رصيد في العملة الأخرى
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

def run_bot():
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ خطأ في البوت: {e}")

if __name__ == "__main__":
    print("=" * 40)
    print("🤖 بوت تتبع الأرصدة (مع عرض الرصيد التلقائي)")
    print("=" * 40)
    print(f"✅ معرف المجموعة: {GROUP_ID}")
    print("🔄 البوت يعمل...")
    print("=" * 40)
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
