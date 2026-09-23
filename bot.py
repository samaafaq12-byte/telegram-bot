import re
from simpleeval import simple_eval, InvalidExpression
from telegram import Update, BotCommand
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

TOKEN = "8943186430:AAHuq4AxmEFN3ldt4252p4Ii5f5GNJLYtDY"

balances = {}

def normalize(text):
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return text.replace("×", "*").replace("÷", "/").replace("−", "-")

def fmt(n):
    return f"{n:,.2f}"

# ==================== الأوامر ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *بوت الحسابات والدفعات*\n\n"
        "🧮 `2000 / 135` — عملية حسابية\n"
        "➕ `+2000` — إضافة دفعة\n"
        "➖ `-7000` — خصم دفعة\n\n"
        "💰 /balance — عرض الرصيد\n"
        "🔄 /reset — تصفير الرصيد",
        parse_mode=ParseMode.MARKDOWN
    )

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = balances.get(update.effective_user.id, 0)
    await update.message.reply_text(
        f"💰 *الرصيد*\n\n`{fmt(bal)}`",
        parse_mode=ParseMode.MARKDOWN
    )

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balances[update.effective_user.id] = 0
    await update.message.reply_text("🔄 تم تصفير الرصيد.")

# ==================== معالج الرسائل ====================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = normalize(update.message.text.strip())
    uid = update.effective_user.id
    
    if text.startswith("/"):
        return
    
    # 🧮 عملية حسابية
    if re.match(r"^[\d\.\s\+\-\*/\(\)]+$", text) and any(op in text for op in ["/", "*"]):
        try:
            result = simple_eval(text)
            await update.message.reply_text(
                f"🧮 *النتيجة*\n\n`{fmt(result)}`",
                parse_mode=ParseMode.MARKDOWN
            )
        except ZeroDivisionError:
            await update.message.reply_text("❌ لا يمكن القسمة على صفر.")
        except Exception:
            await update.message.reply_text("❌ عملية غير صحيحة.")
        return
    
    # ➕ إضافة دفعة
    m = re.match(r"^\+\s*([\d\.]+)$", text)
    if m:
        amount = float(m.group(1))
        balances[uid] = balances.get(uid, 0) + amount
        await update.message.reply_text(
            f"➕ *تمت الإضافة*\n\n"
            f"المبلغ: `+{fmt(amount)}`\n"
            f"الرصيد: `{fmt(balances[uid])}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # ➖ خصم دفعة
    m = re.match(r"^\-\s*([\d\.]+)$", text)
    if m:
        amount = float(m.group(1))
        balances[uid] = balances.get(uid, 0) - amount
        await update.message.reply_text(
            f"➖ *تم الخصم*\n\n"
            f"المبلغ: `-{fmt(amount)}`\n"
            f"الرصيد: `{fmt(balances[uid])}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

# ==================== الإقلاع ====================
async def post_init(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start",   "🏠 البداية"),
        BotCommand("balance", "💰 الرصيد"),
        BotCommand("reset",   "🔄 تصفير"),
    ])

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("🤖 البوت يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
