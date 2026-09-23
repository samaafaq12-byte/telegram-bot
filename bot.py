import re
from simpleeval import simple_eval
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

def big(text):
    """تكبير الأرقام"""
    for n in "0123456789":
        text = text.replace(n, f"`{n}`")
    return text

def fmt(n):
    """رقم بدون فواصل"""
    if n == int(n):
        return str(int(n))
    return f"{n:.2f}".rstrip("0").rstrip(".")

def get_bal(uid):
    if uid not in balances:
        balances[uid] = {"usd": 0, "try": 0}
    return balances[uid]

def show_balance(uid):
    b = get_bal(uid)
    return (
        f"💵 *دولار:* {big(fmt(b['usd']))}\n"
        f"💷 *ليرة:* {big(fmt(b['try']))}"
    )

# ==================== الأوامر ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *بوت الحسابات والدفعات*\n\n"
        "🧮 *الحساب:*\n"
        "  `6000 / 141`\n\n"
        "💵 *الدولار:*\n"
        "  `+2000$` — إضافة\n"
        "  `-7000$` — خصم\n\n"
        "💷 *الليرة:*\n"
        "  `+2000` — إضافة\n"
        "  `-7000` — خصم\n\n"
        "💰 /balance — الرصيد\n"
        "🔄 /reset — تصفير",
        parse_mode=ParseMode.MARKDOWN
    )

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        f"💰 *الرصيد*\n\n{show_balance(uid)}",
        parse_mode=ParseMode.MARKDOWN
    )

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    balances[uid] = {"usd": 0, "try": 0}
    await update.message.reply_text("🔄 تم تصفير الرصيد.")

# ==================== معالج الرسائل ====================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = normalize(update.message.text.strip())
    uid = update.effective_user.id
    bal = get_bal(uid)
    
    if text.startswith("/"):
        return
    
    # 🧮 عملية حسابية
    if re.match(r"^[\d\.\s\+\-\*/\(\)]+$", text) and any(op in text for op in ["/", "*"]):
        try:
            result = simple_eval(text)
            await update.message.reply_text(
                f"🧮 {big(text)} = {big(fmt(result))}",
                parse_mode=ParseMode.MARKDOWN
            )
        except ZeroDivisionError:
            await update.message.reply_text("❌ لا يمكن القسمة على صفر.")
        except Exception:
            await update.message.reply_text("❌ عملية غير صحيحة.")
        return
    
    # 💵 دولار
    m = re.match(r"^([\+\-])\s*([\d\.]+)\s*\$?$", text)
    if m and "$" in text:
        sign, amount = m.group(1), float(m.group(2))
        if sign == "+":
            bal["usd"] += amount
            await update.message.reply_text(
                f"💵 *تمت الإضافة (دولار)*\n\n"
                f"المبلغ: {big('+' + fmt(amount))}\n\n"
                f"{show_balance(uid)}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            bal["usd"] -= amount
            await update.message.reply_text(
                f"💵 *تم الخصم (دولار)*\n\n"
                f"المبلغ: {big('-' + fmt(amount))}\n\n"
                f"{show_balance(uid)}",
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # 💷 ليرة
    m = re.match(r"^([\+\-])\s*([\d\.]+)$", text)
    if m:
        sign, amount = m.group(1), float(m.group(2))
        if sign == "+":
            bal["try"] += amount
            await update.message.reply_text(
                f"💷 *تمت الإضافة (ليرة)*\n\n"
                f"المبلغ: {big('+' + fmt(amount))}\n\n"
                f"{show_balance(uid)}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            bal["try"] -= amount
            await update.message.reply_text(
                f"💷 *تم الخصم (ليرة)*\n\n"
                f"المبلغ: {big('-' + fmt(amount))}\n\n"
                f"{show_balance(uid)}",
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
