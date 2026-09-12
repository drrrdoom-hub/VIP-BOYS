import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Apna Razorpay Payment Link yahan baad mein daalenge
PAYMENT_LINK = "https://rzp.io/rzp/4QxW1xOq"

# Apne private Telegram group ka username/ID baad mein set karenge
GROUP_ID = os.getenv("GROUP_ID")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Temporary storage
pending_users = {}


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton(
                "💎 Join Premium – ₹99/month",
                url=PAYMENT_LINK
            )
        ],
        [
            InlineKeyboardButton(
                "💳 I Have Paid",
                callback_data="paid"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Help",
                callback_data="help"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔥 Welcome to VVIP Premium!\n\n"
        "💎 Membership: ₹99/month\n\n"
        "1️⃣ Click 'Join Premium'\n"
        "2️⃣ Complete the payment\n"
        "3️⃣ Click 'I Have Paid'\n"
        "4️⃣ Send your UTR / Transaction ID\n"
        "5️⃣ After verification, you will receive the private group invite.\n\n"
        "⚡ Fast verification after payment.",
        reply_markup=reply_markup
    )


# =========================
# BUTTONS
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "paid":

        pending_users[query.from_user.id] = {
            "username": query.from_user.username,
            "name": query.from_user.full_name,
        }

        await query.message.reply_text(
            "💳 Payment complete?\n\n"
            "Ab apna **UTR / Transaction ID** bhejo.\n\n"
            "Example:\n"
            "UTR: 123456789012\n\n"
            "⚠️ Sirf payment ka UTR/Transaction ID bhejna."
        )

    elif query.data == "help":

        await query.message.reply_text(
            "ℹ️ Help\n\n"
            "₹99/month Premium membership ke liye:\n\n"
            "1. Payment button dabao\n"
            "2. Payment complete karo\n"
            "3. 'I Have Paid' dabao\n"
            "4. UTR / Transaction ID bhejo\n"
            "5. Verification ke baad invite milega."
        )


# =========================
# UTR MESSAGE
# =========================

async def receive_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    text = update.message.text.strip()

    if user.id not in pending_users:
        await update.message.reply_text(
            "Pehle /start karo aur payment process follow karo."
        )
        return

    username = f"@{user.username}" if user.username else "No username"

    admin_message = (
        "🔔 NEW PAYMENT VERIFICATION\n\n"
        f"👤 Name: {user.full_name}\n"
        f"🆔 User ID: {user.id}\n"
        f"📱 Username: {username}\n\n"
        f"💳 UTR / Transaction ID:\n{text}\n\n"
        "Verify payment and choose an action:"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ APPROVE",
                callback_data=f"approve:{user.id}"
            ),
            InlineKeyboardButton(
                "❌ REJECT",
                callback_data=f"reject:{user.id}"
            )
        ]
    ]

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text(
        "✅ UTR received!\n\n"
        "Your payment is being verified.\n"
        "Verification ke baad yahin invite link milega."
    )


# =========================
# ADMIN APPROVAL
# =========================

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("❌ Unauthorized.")
        return

    action, user_id = query.data.split(":")
    user_id = int(user_id)

    if action == "reject":

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ Payment verification failed.\n\n"
                "Please contact admin if you believe this is an error."
            )
        )

        await query.edit_message_text(
            query.message.text + "\n\n❌ REJECTED"
        )

        return

    if action == "approve":

        try:

            invite = await context.bot.create_chat_invite_link(
                chat_id=GROUP_ID,
                member_limit=1
            )

            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 PAYMENT VERIFIED!\n\n"
                    "✅ Your Premium membership is approved.\n\n"
                    "🔐 Private Group Invite:\n"
                    f"{invite.invite_link}\n\n"
                    "⚠️ This invite is for your account only."
                )
            )

            await query.edit_message_text(
                query.message.text + "\n\n✅ APPROVED"
            )

        except Exception as e:

            await query.message.reply_text(
                f"⚠️ Invite link create nahi hua.\n\nError: {e}"
            )


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing.")

    if not ADMIN_ID:
        raise ValueError("ADMIN_ID is missing.")

    if not GROUP_ID:
        raise ValueError("GROUP_ID is missing.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(
        button_handler,
        pattern="^(paid|help)$"
    ))
    app.add_handler(CallbackQueryHandler(
        admin_action,
        pattern="^(approve|reject):"
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        receive_utr
    ))

    print("VVIP Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()