# -*- coding: utf-8 -*-
import telebot
import json
import os
from datetime import datetime

# --------------------- الإعدادات ---------------------
TOKEN = "8952384966:AAH6509zEqo73asesJRBzPutsuyqD-eZqzM"
GROUP_ID = -1004481566972  # ضع المعرف الجديد هنا
DATA_FILE = "data.json"

# إنشاء البوت
bot = telebot.TeleBot(TOKEN)

# --------------------- قاعدة البيانات ---------------------
def load_data():
    """تحميل البيانات من ملف JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    """حفظ البيانات في ملف JSON"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

last_reset_date = datetime.now().date()

def reset_daily_if_needed():
    """إعادة تعيين البيانات تلقائياً في منتصف الليل"""
    global last_reset_date
    today = datetime.now().date()
    if today != last_reset_date:
        data = load_data()
        if data:
            # حفظ أرشيف لليوم السابق
            archive_file = f"archive_{last_reset_date}.json"
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"📦 تم حفظ أرشيف: {archive_file}")
        
        # تصفير البيانات لليوم الجديد
        save_data({})
        last_reset_date = today
        print(f"🔄 تم إعادة تعيين البيانات لليوم {today}")

def add_transaction(user_id, username, amount, currency, note=""):
    """إضافة معاملة جديدة (إيداع أو سحب) مع تمييز العملة"""
    reset_daily_if_needed()
    
    data = load_data()
    user_id_str = str(user_id)
    
    if user_id_str not in data:
        data[user_id_str] = {
            "username": username,
            "balance_sy": 0,      # رصيد الليرة السورية
            "balance_usd": 0,     # رصيد الدولار
            "total_in_sy": 0,
            "total_out_sy": 0,
            "total_in_usd": 0,
            "total_out_usd": 0,
            "transactions": []
        }
    
    # تحديد العملة
    if currency == "sy":
        currency_symbol = "🇸🇾 ل.س"
        currency_key = "sy"
    else:
        currency_symbol = "💵 USD"
        currency_key = "usd"
    
    # تحديث الرصيد
    if amount > 0:  # إيداع
        if currency_key == "sy":
            data[user_id_str]["balance_sy"] += amount
            data[user_id_str]["total_in_sy"] += amount
        else:
            data[user_id_str]["balance_usd"] += amount
            data[user_id_str]["total_in_usd"] += amount
        trans_type = "استلام"
        emoji = "✅"
    else:  # سحب
        if currency_key == "sy":
            data[user_id_str]["balance_sy"] += amount
            data[user_id_str]["total_out_sy"] += abs(amount)
        else:
            data[user_id_str]["balance_usd"] += amount
            data[user_id_str]["total_out_usd"] += abs(amount)
        trans_type = "دفع"
        emoji = "❌"
    
    # إضافة المعاملة للسجل
    data[user_id_str]["transactions"].append({
        "type": trans_type,
        "amount": abs(amount),
        "currency": currency_symbol,
        "time": datetime.now().strftime("%H:%M:%S"),
        "note": note
    })
    
    save_data(data)
    
    # إرجاع الرصيد الجديد
    if currency_key == "sy":
        new_balance = data[user_id_str]["balance_sy"]
    else:
        new_balance = data[user_id_str]["balance_usd"]
    
    return new_balance, abs(amount), trans_type, emoji, currency_symbol

# --------------------- أوامر البوت الأساسية ---------------------

@bot.message_handler(commands=['start'])
def start(message):
    """رسالة ترحيبية"""
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
        "📊 *عرض تقرير اليوم:*\n"
        "`/report`\n\n"
        "📋 *عرض سجل معاملاتك:*\n"
        "`/history`\n\n"
        "💰 *عرض رصيدك الحالي:*\n"
        "`/balance`\n\n"
        "🔄 *تصفير الأرصدة (للمشرفين فقط):*\n"
        "`/reset` - تصفير جميع الأرصدة\n"
        "`/reset_user @username` - تصفير رصيد موظف محدد\n"
        "`/reset_confirm` - عرض ملخص قبل التصفير\n"
        "`/archive` - عرض ملفات الأرشيف",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['balance'])
def balance(message):
    """عرض رصيد المستخدم الحالي بالليرة والدولار"""
    if message.chat.id != GROUP_ID:
        return
    
    reset_daily_if_needed()
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str in data:
        user_data = data[user_id_str]
        bot.reply_to(message,
            f"👤 *{user_data['username']}*\n\n"
            f"🇸🇾 *رصيد الليرة السورية:* {user_data['balance_sy']} ل.س\n"
            f"📥 إجمالي المستلم: {user_data['total_in_sy']} ل.س\n"
            f"📤 إجمالي المدفوع: {user_data['total_out_sy']} ل.س\n\n"
            f"💵 *رصيد الدولار:* {user_data['balance_usd']} USD\n"
            f"📥 إجمالي المستلم: {user_data['total_in_usd']} USD\n"
            f"📤 إجمالي المدفوع: {user_data['total_out_usd']} USD",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, "📭 لا توجد معاملات لك اليوم.")

@bot.message_handler(commands=['history'])
def history(message):
    """عرض سجل المعاملات للمستخدم"""
    if message.chat.id != GROUP_ID:
        return
    
    reset_daily_if_needed()
    data = load_data()
    user_id_str = str(message.from_user.id)
    
    if user_id_str not in data:
        bot.reply_to(message, "📭 لا توجد معاملات لك اليوم.")
        return
    
    user_data = data[user_id_str]
    transactions = user_data["transactions"][-10:]  # آخر 10 معاملات
    
    if not transactions:
        bot.reply_to(message, "📭 لا توجد معاملات.")
        return
    
    history_text = f"📋 *سجل معاملات {user_data['username']}*\n"
    history_text += "═" * 15 + "\n\n"
    
    for trans in reversed(transactions):
        if trans["type"] == "استلام":
            emoji = "📥"
        else:
            emoji = "📤"
        
        history_text += f"{emoji} {trans['type']}: *{trans['amount']} {trans['currency']}*\n"
        history_text += f"🕐 {trans['time']}\n"
        if trans.get('note'):
            history_text += f"📝 {trans['note']}\n"
        history_text += "─" * 10 + "\n"
    
    bot.reply_to(message, history_text, parse_mode='Markdown')

@bot.message_handler(commands=['report'])
def report(message):
    """عرض تقرير مفصل لليوم بالليرة والدولار"""
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
    total_in_sy = 0
    total_out_sy = 0
    total_in_usd = 0
    total_out_usd = 0
    
    for user_id, user_data in sorted_users:
        username = user_data["username"]
        balance_sy = user_data["balance_sy"]
        balance_usd = user_data["balance_usd"]
        total_in_sy_user = user_data["total_in_sy"]
        total_out_sy_user = user_data["total_out_sy"]
        total_in_usd_user = user_data["total_in_usd"]
        total_out_usd_user = user_data["total_out_usd"]
        trans_count = len(user_data["transactions"])
        
        report_text += f"👤 *{username}*\n"
        report_text += f"🇸🇾 رصيد الليرة: *{balance_sy}* ل.س\n"
        report_text += f"💵 رصيد الدولار: *{balance_usd}* USD\n"
        report_text += f"📥 إجمالي المستلم (ل.س): {total_in_sy_user}\n"
        report_text += f"📤 إجمالي المدفوع (ل.س): {total_out_sy_user}\n"
        report_text += f"📥 إجمالي المستلم (USD): {total_in_usd_user}\n"
        report_text += f"📤 إجمالي المدفوع (USD): {total_out_usd_user}\n"
        report_text += f"📝 عدد المعاملات: {trans_count}\n"
        report_text += "─" * 15 + "\n"
        
        total_balance_sy += balance_sy
        total_balance_usd += balance_usd
        total_in_sy += total_in_sy_user
        total_out_sy += total_out_sy_user
        total_in_usd += total_in_usd_user
        total_out_usd += total_out_usd_user
    
    report_text += "\n📈 *ملخص عام*\n"
    report_text += f"🇸🇾 إجمالي أرصدة الليرة: {total_balance_sy} ل.س\n"
    report_text += f"💵 إجمالي أرصدة الدولار: {total_balance_usd} USD\n"
    report_text += f"📥 إجمالي الإيداعات (ل.س): {total_in_sy}\n"
    report_text += f"📤 إجمالي السحوبات (ل.س): {total_out_sy}\n"
    report_text += f"📥 إجمالي الإيداعات (USD): {total_in_usd}\n"
    report_text += f"📤 إجمالي السحوبات (USD): {total_out_usd}\n"
    
    bot.reply_to(message, report_text, parse_mode='Markdown')

# --------------------- أوامر التصفير ---------------------

@bot.message_handler(commands=['reset'])
def reset_balances(message):
    """تصفير جميع الأرصدة (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
        return
    
    # التحقق من صلاحية المشرف
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    # حفظ نسخة احتياطية قبل التصفير
    data = load_data()
    if data:
        backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        bot.reply_to(message, f"📦 تم حفظ نسخة احتياطية: `{backup_file}`", parse_mode='Markdown')
    
    # تصفير البيانات
    save_data({})
    bot.reply_to(message, "🔄 تم تصفير جميع الأرصدة بنجاح.")

@bot.message_handler(commands=['reset_user'])
def reset_user_balance(message):
    """تصفير رصيد موظف معين (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
        return
    
    # التحقق من صلاحية المشرف
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    # استخراج اسم المستخدم من الأمر
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استخدم: `/reset_user @username`", parse_mode='Markdown')
        return
    
    target_username = parts[1].replace('@', '')
    
    data = load_data()
    found = False
    
    for user_id, user_data in data.items():
        if user_data["username"].lower() == target_username.lower():
            old_balance_sy = user_data["balance_sy"]
            old_balance_usd = user_data["balance_usd"]
            user_data["balance_sy"] = 0
            user_data["balance_usd"] = 0
            user_data["total_in_sy"] = 0
            user_data["total_out_sy"] = 0
            user_data["total_in_usd"] = 0
            user_data["total_out_usd"] = 0
            user_data["transactions"] = []
            
            save_data(data)
            found = True
            bot.reply_to(message, 
                f"✅ تم تصفير رصيد {target_username}\n"
                f"🇸🇾 كان: {old_balance_sy} ل.س\n"
                f"💵 كان: {old_balance_usd} USD"
            )
            break
    
    if not found:
        bot.reply_to(message, f"❌ لم يتم العثور على {target_username}")

@bot.message_handler(commands=['reset_confirm'])
def reset_confirm(message):
    """تأكيد تصفير جميع الأرصدة (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
        return
    
    # التحقق من صلاحية المشرف
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    # استعراض البيانات قبل التصفير
    data = load_data()
    if not data:
        bot.reply_to(message, "📭 لا توجد بيانات لتصفيرها.")
        return
    
    # عرض ملخص قبل التصفير
    summary = "📊 *ملخص البيانات قبل التصفير*\n"
    summary += "═" * 15 + "\n\n"
    
    total_balance_sy = 0
    total_balance_usd = 0
    
    for user_id, user_data in data.items():
        summary += f"👤 {user_data['username']}:\n"
        summary += f"   🇸🇾 {user_data['balance_sy']} ل.س\n"
        summary += f"   💵 {user_data['balance_usd']} USD\n"
        total_balance_sy += user_data['balance_sy']
        total_balance_usd += user_data['balance_usd']
    
    summary += f"\n💰 إجمالي أرصدة الليرة: *{total_balance_sy}* ل.س"
    summary += f"\n💰 إجمالي أرصدة الدولار: *{total_balance_usd}* USD"
    summary += "\n\n⚠️ *هل أنت متأكد؟* استخدم `/reset` للتأكيد."
    
    bot.reply_to(message, summary, parse_mode='Markdown')

@bot.message_handler(commands=['archive'])
def show_archive(message):
    """عرض ملفات الأرشيف المتاحة (للمشرفين فقط)"""
    if message.chat.id != GROUP_ID:
        return
    
    # التحقق من صلاحية المشرف
    try:
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "⛔ هذا الأمر للمشرفين فقط.")
            return
    except:
        bot.reply_to(message, "⛔ يرجى التأكد من صلاحياتك.")
        return
    
    # البحث عن ملفات الأرشيف
    archive_files = [f for f in os.listdir('.') if f.startswith('archive_') and f.endswith('.json')]
    
    if not archive_files:
        bot.reply_to(message, "📭 لا توجد ملفات أرشيف.")
        return
    
    files_text = "📁 *ملفات الأرشيف المتاحة*\n"
    files_text += "═" * 15 + "\n\n"
    
    for file in sorted(archive_files, reverse=True):
        size = os.path.getsize(file) / 1024  # حجم الملف بالكيلوبايت
        files_text += f"📄 `{file}` ({size:.1f} KB)\n"
    
    bot.reply_to(message, files_text, parse_mode='Markdown')

# --------------------- معالجة الرسائل النصية ---------------------

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """معالجة الرسائل النصية للبحث عن +رقم أو -رقم مع تمييز العملة"""
    # التأكد من أن الرسالة من المجموعة الصحيحة
    if message.chat.id != GROUP_ID:
        return
    
    text = message.text.strip()
    user = message.from_user
    username = user.username or user.first_name
    
    amount = None
    currency = "sy"  # افتراضي: ليرة سورية
    note = ""
    
    # -------------------- معالجة الليرة السورية --------------------
    # +1000 أو -500
    if text.startswith('+') or text.startswith('-'):
        try:
            parts = text.split()
            # التحقق من وجود علامة دولار
            if '$' in parts[0] or 'دولار' in text:
                currency = "usd"
                amount_str = parts[0].replace('$', '').replace('+', '').replace('-', '')
                if '-' in parts[0]:
                    amount = -float(amount_str)
                else:
                    amount = float(amount_str)
            else:
                amount = float(parts[0])
            
            if len(parts) > 1:
                note = ' '.join(parts[1:])
        except:
            pass
    
    # -------------------- معالجة الكلمات المفتاحية --------------------
    elif "استلام" in text or "دفع" in text:
        try:
            parts = text.split()
            for i, part in enumerate(parts):
                if part in ["استلام", "دفع"]:
                    if i + 1 < len(parts):
                        amount_str = parts[i + 1]
                        # التحقق من وجود علامة دولار
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
    
    # -------------------- معالجة الرقم مع $ --------------------
    elif '$' in text:
        try:
            # استخراج الرقم قبل علامة $
            import re
            match = re.search(r'([+-]?\d+\.?\d*)\s*\$', text)
            if match:
                amount = float(match.group(1))
                currency = "usd"
                # استخراج الملاحظة
                parts = text.split()
                for i, part in enumerate(parts):
                    if '$' in part:
                        if len(parts) > i + 1:
                            note = ' '.join(parts[i+1:])
                        break
        except:
            pass
    
    if amount is None or amount == 0:
        return
    
    try:
        new_balance, trans_amount, trans_type, emoji, currency_symbol = add_transaction(
            user.id, username, amount, currency, note
        )
        
        reply = (
            f"{emoji} *تم تسجيل العملية*\n\n"
            f"👤 {username}\n"
            f"📌 {trans_type}: *{trans_amount} {currency_symbol}*\n"
            f"💰 الرصيد الحالي: *{new_balance} {currency_symbol}*\n"
        )
        if note:
            reply += f"📝 ملاحظة: {note}\n"
        
        bot.reply_to(message, reply, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ حدث خطأ: {str(e)}")

# --------------------- تشغيل البوت ---------------------

if __name__ == "__main__":
    print("=" * 40)
    print("🤖 بوت تتبع الأرصدة (ليرة سورية + دولار)")
    print("=" * 40)
    print(f"✅ معرف المجموعة: {GROUP_ID}")
    print("🔄 البوت يعمل...")
    print("=" * 40)
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")
        print("\nتأكد من:")
        print("1. التوكن صحيح")
        print("2. البوت مشرف في المجموعة")
        print("3. الاتصال بالإنترنت")