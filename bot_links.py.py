# -*- coding: utf-8 -*-
import telebot
import json
import os
from flask import Flask
import threading

# --------------------- الإعدادات ---------------------
TOKEN = "8736403186:AAGgWCc9VpFNwkPbj-usX7QaIhK4wmthXGg"
GROUP_ID = -1004481566972
DATA_FILE = "links.json"

# إنشاء البوت
bot = telebot.TeleBot(TOKEN)

# إنشاء تطبيق Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 بوت الروابط يعمل!", 200

@app.route('/health')
def health():
    return "OK", 200

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

# --------------------- أوامر البوت ---------------------

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "👋 *مرحباً! أنا بوت روابط استقبال الراتب*\n\n"
        "📌 *الأوامر المتاحة:*\n\n"
        "👑 *للمشرفين:*\n"
        "`/setlink @موظف الرابط` - تعيين رابط استقبال لموظف\n"
        "`/dellink @موظف` - حذف رابط استقبال موظف\n"
        "`/listlinks` - عرض جميع الروابط المسجلة\n\n"
        "👤 *للجميع:*\n"
        "`/link @موظف` - عرض رابط استقبال موظف\n"
        "`/mylink` - عرض رابط استقبالك أنت",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['setlink'])
def set_payment_link(message):
    """تعيين رابط استقبال الراتب لموظف (للمشرفين فقط)"""
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
    
    # استخراج البيانات من الأمر
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ استخدم: `/setlink @موظف الرابط`", parse_mode='Markdown')
        return
    
    target_username = parts[1].replace('@', '')
    payment_link = parts[2].strip()
    
    # التحقق من صحة الرابط
    if not payment_link.startswith('http://') and not payment_link.startswith('https://'):
        bot.reply_to(message, "⚠️ الرابط يجب أن يبدأ بـ http:// أو https://")
        return
    
    data = load_data()
    data[target_username.lower()] = {
        "username": target_username,
        "link": payment_link,
        "set_by": message.from_user.first_name,
        "set_time": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_data(data)
    
    bot.reply_to(message, 
        f"✅ *تم تعيين رابط استقبال الراتب لـ {target_username}*\n\n"
        f"🔗 {payment_link}",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['dellink'])
def delete_payment_link(message):
    """حذف رابط استقبال الراتب لموظف (للمشرفين فقط)"""
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
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استخدم: `/dellink @موظف`", parse_mode='Markdown')
        return
    
    target_username = parts[1].replace('@', '')
    
    data = load_data()
    if target_username.lower() in data:
        del data[target_username.lower()]
        save_data(data)
        bot.reply_to(message, f"🗑️ تم حذف رابط استقبال {target_username}")
    else:
        bot.reply_to(message, f"❌ لا يوجد رابط مسجل لـ {target_username}")

@bot.message_handler(commands=['link'])
def get_payment_link(message):
    """عرض رابط استقبال الراتب لموظف"""
    if message.chat.id != GROUP_ID:
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ استخدم: `/link @موظف`", parse_mode='Markdown')
        return
    
    target_username = parts[1].replace('@', '')
    
    data = load_data()
    if target_username.lower() in data:
        link_info = data[target_username.lower()]
        bot.reply_to(message,
            f"🔗 *رابط استقبال الراتب لـ {target_username}*\n\n"
            f"{link_info['link']}",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, f"📭 لا يوجد رابط استقبال مسجل لـ {target_username}")

@bot.message_handler(commands=['mylink'])
def my_payment_link(message):
    """عرض رابط استقبال الراتب الخاص بي"""
    if message.chat.id != GROUP_ID:
        return
    
    username = message.from_user.username or message.from_user.first_name
    target_username = username.lower()
    
    data = load_data()
    
    # البحث عن المستخدم بأي طريقة (باستخدام اسم المستخدم أو الاسم الأول)
    found = False
    for key, value in data.items():
        if key == target_username or value["username"].lower() == target_username:
            bot.reply_to(message,
                f"🔗 *رابط استقبال الراتب الخاص بك*\n\n"
                f"{value['link']}",
                parse_mode='Markdown'
            )
            found = True
            break
    
    if not found:
        bot.reply_to(message, 
            "📭 لا يوجد رابط استقبال مسجل لك.\n\n"
            "💡 اطلب من المشرف تعيين رابط لك باستخدام:\n"
            "`/setlink @اسمك الرابط`",
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['listlinks'])
def list_all_links(message):
    """عرض جميع الروابط المسجلة (للمشرفين فقط)"""
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
    
    data = load_data()
    
    if not data:
        bot.reply_to(message, "📭 لا توجد روابط مسجلة.")
        return
    
    report = "📋 *قائمة روابط استقبال الراتب*\n"
    report += "═" * 20 + "\n\n"
    
    for username, info in data.items():
        report += f"👤 *{info['username']}*\n"
        report += f"🔗 {info['link']}\n"
        report += f"📝 تم التعيين بواسطة: {info.get('set_by', 'غير معروف')}\n"
        report += f"🕐 التاريخ: {info.get('set_time', 'غير معروف')}\n"
        report += "─" * 15 + "\n"
    
    bot.reply_to(message, report, parse_mode='Markdown')

# --------------------- معالجة الرسائل النصية ---------------------

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """معالجة طلب رابط الموظف عند كتابة 'رابط @موظف'"""
    if message.chat.id != GROUP_ID:
        return
    
    text = message.text.strip()
    
    # التحقق من كتابة "رابط @موظف"
    if text.lower().startswith("رابط"):
        parts = text.split()
        if len(parts) < 2:
            return
        
        # استخراج اسم المستخدم
        target_username = parts[1].replace('@', '')
        
        data = load_data()
        if target_username.lower() in data:
            link_info = data[target_username.lower()]
            bot.reply_to(message,
                f"🔗 *رابط استقبال الراتب لـ {target_username}*\n\n"
                f"{link_info['link']}",
                parse_mode='Markdown'
            )
        else:
            bot.reply_to(message, f"📭 لا يوجد رابط استقبال مسجل لـ {target_username}")
        return
    
    # إذا كانت الرسالة رابط فقط (يبدأ بـ http)
    elif text.startswith('http://') or text.startswith('https://'):
        # لا نفعل شيئاً، نترك البوت يتجاهل الروابط العادية
        pass

# --------------------- تشغيل البوت ---------------------

def run_bot():
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ خطأ في البوت: {e}")

if __name__ == "__main__":
    print("=" * 40)
    print("🤖 بوت روابط استقبال الراتب")
    print("=" * 40)
    print(f"✅ معرف المجموعة: {GROUP_ID}")
    print("🔄 البوت يعمل...")
    print("=" * 40)
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)