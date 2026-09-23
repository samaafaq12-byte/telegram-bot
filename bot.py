import os
import re
from simpleeval import simple_eval, InvalidExpression
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

# ⚠️ استبدل هذا بالتوكن الجديد بعد عمل /revoke
TOKEN = "8943186430:AAHuq4AxmEFN3ldt4252p4Ii5f5GNJLYtDY"

# الرصيد في الذاكرة فقط
balances = {}

def normalize(text):
    """تحويل الأرقام العربية والرموز"""
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return text.replace("×", "*").replace("÷", "/").replace("−", "-").replace("–", "-")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *بوت الحسابات والدفعات*\n\n"
        "📌 *الأوامر:*\n"
        "• `2000 / 135` — عملية حسابية\n"
        "• `+2000` — إضافة دفعة\n"
        "• `-7000` — خصم دفعة\n"
        "• `/balance` — عرض رصيدك\n"
        "• `/reset` — تصفير رصيدك\n\n"
        "✅ يعمل في أي مجموعة",
        parse_mode="Markdown"
    )

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    bal = balances.get(uid, 0)
    await update.message.reply_text(f"💰 رصيدك الحالي: `{bal:,.2f}`", parse_mode="Markdown")

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    balances[uid] = 0
    await update.message.reply_text("✅ تم تصفير رصيدك")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # يعمل في أي مجموعة + الخاص
    if not update.message or not update.message.text:
        return
    
    text = normalize(update.message.text.strip())
    uid = update.effective_user.id
    
    # تجاهل الأوامر
    if text.startswith("/"):
        return
    
    # 1) عملية حسابية (تحتوي على / أو *)
    if re.match(r"^[\d\.\s\+\-\*/\(\)]+$", text) and any(op in text for op in ["/", "*"]):
        try:
            result = simple_eval(text)
            await update.message.reply_text(f"🧮 النتيجة: `{result:,.2f}`", parse_mode="Markdown")
        except ZeroDivisionError:
            await update.message.reply_text("❌ لا يمكن القسمة على صفر")
        except (InvalidExpression, Exception):
            await update.message.reply_text("❌ عملية غير صحيحة")
        return
    
    # 2) إضافة دفعة: +2000
    m = re.match(r"^\+\s*([\d\.]+)$", text)
    if m:
        amount = float(m.group(1))
        balances[uid] = balances.get(uid, 0) + amount
        await update.message.reply_text(
            f"➕ تمت إضافة `{amount:,.2f}`\n"
            f"💰 الرصيد الحالي: `{balances[uid]:,.2f}`",
            parse_mode="Markdown"
        )
        return
    
    # 3) خصم دفعة: -7000
    m = re.match(r"^\-\s*([\d\.]+)$", text)
    if m:
        amount = float(m.group(1))
        balances[uid] = balances.get(uid, 0) - amount
        await update.message.reply_text(
            f"➖ تم خصم `{amount:,.2f}`\n"
            f"💰 الرصيد الحالي: `{balances[uid]:,.2f}`",
            parse_mode="Markdown"
        )
        return

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("🤖 البوت يعمل في أي مجموعة...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
