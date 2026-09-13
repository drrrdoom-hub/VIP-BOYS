import os
import logging
import re

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
GROUP_ID = os.getenv("GROUP_ID")

# Railway Variables me actual Razorpay link rakho
PAYMENT_LINK = os.getenv("PAYMENT_LINK")

# QR image ka filename
PAYMENT_QR = "payment_qr.jpg"

# Preview screenshots ke filenames
PREVIEW_IMAGES = [
    "preview1.jpg",
    "preview2.jpg",
    "preview3.jpg",
]

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
                "👀 Preview",
                callback_data="preview"
            )
        ],
        [
            InlineKeyboardButton(
                "💎 Payment – ₹99/month",
                callback_data="payment"
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

    await update.message.reply_text(
        "🔥 Welcome to VVIP Premium!\n\n"
        "💎 Membership: ₹99/month\n\n"
        "👀 Pehle Preview dekh sakte ho.\n"
        "💳 Payment ke liye Payment button dabao.\n\n"
        "Payment ke baad:\n"
        "1️⃣ Payment screenshot bhejo\n"
        "2️⃣ UTR / Transaction ID bhejo\n"
        "3️⃣ Admin verification karega\n"
        "4️⃣ Approval ke baad private group ka invite milega.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # =========================
    # PREVIEW
    # =========================

    if query.data == "preview":

        await query.message.reply_text(
            "👀 VVIP Premium Preview\n\n"
            "Neeche premium content ka preview hai:"
        )

        for image in PREVIEW_IMAGES:

            if os.path.exists(image):
                try:
                    with open(image, "rb") as photo:
                        await query.message.reply_photo(photo=photo)
                except Exception as e:
                    logging.error(f"Preview error: {e}")

        await query.message.reply_text(
            "💎 Full Premium access ke liye ₹99/month membership available hai.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "💳 Pay ₹99",
                        callback_data="payment"
                    )
                ]
            ])
        )

    # =========================
    # PAYMENT
    # =========================

    elif query.data == "payment":

        if not PAYMENT_LINK:
            await query.message.reply_text(
                "⚠️ Payment system temporarily unavailable."
            )
            return

        keyboard = [
            [
                InlineKeyboardButton(
                    "💳 Pay ₹99 Now",
                    url=PAYMENT_LINK
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ I Have Paid",
                    callback_data="paid"
                )
            ]
        ]

        # QR
        if os.path.exists(PAYMENT_QR):

            with open(PAYMENT_QR, "rb") as qr:
                await query.message.reply_photo(
                    photo=qr,
                    caption=(
                        "💎 VVIP Premium Membership\n\n"
                        "💰 Price: ₹99/month\n\n"
                        "📱 QR scan karke payment karo\n"
                        "ya neeche Payment Link use karo."
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        else:

            await query.message.reply_text(
                "💎 VVIP Premium Membership\n\n"
                "💰 Price: ₹99/month\n\n"
                "Payment ke liye neeche button dabao.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # =========================
    # I HAVE PAID
    # =========================

    elif query.data == "paid":

        pending_users[user_id] = {
            "username": query.from_user.username,
            "name": query.from_user.full_name,
            "screenshot": None,
            "utr": None,
            "step": "screenshot",
        }

        await query.message.reply_text(
            "📸 Payment screenshot bhejo.\n\n"
            "⚠️ Screenshot mein payment amount aur transaction details clearly visible honi chahiye.\n\n"
            "Screenshot receive hone ke baad main UTR maangunga."
        )

    # =========================
    # HELP
    # =========================

    elif query.data == "help":

        await query.message.reply_text(
            "ℹ️ Help\n\n"
            "💎 Membership: ₹99/month\n\n"
            "1️⃣ Preview dekho\n"
            "2️⃣ ₹99 payment karo\n"
            "3️⃣ Payment screenshot bhejo\n"
            "4️⃣ UTR / Transaction ID bhejo\n"
            "5️⃣ Admin verification karega\n"
            "6️⃣ Approval ke baad private invite milega."
        )


# =========================
# PAYMENT SCREENSHOT
# =========================

async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.id not in pending_users:
        await update.message.reply_text(
            "Pehle /start karo aur payment process follow karo."
        )
        return

    data = pending_users[user.id]

    if data.get("step") != "screenshot":
        return

    if not update.message.photo:

        await update.message.reply_text(
            "❌ Please payment ka screenshot/photo bhejo.\n\n"
            "Screenshot ke bina verification nahi ho sakta."
        )
        return

    # Highest quality photo
    photo = update.message.photo[-1]

    data["screenshot"] = photo.file_id
    data["step"] = "utr"

    await update.message.reply_text(
        "✅ Payment screenshot received.\n\n"
        "🔢 Ab apna UTR / Transaction ID bhejo.\n\n"
        "⚠️ Sirf DIGITS bhejo.\n"
        "Example:\n"
        "123456789012"
    )


# =========================
# UTR
# =========================

async def receive_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    text = update.message.text.strip()

    if user.id not in pending_users:

        await update.message.reply_text(
            "Pehle /start karo aur payment process follow karo."
        )
        return

    data = pending_users[user.id]

    if data.get("step") != "utr":

        await update.message.reply_text(
            "Pehle payment screenshot bhejo."
        )
        return

    # =========================
    # ONLY DIGITS
    # =========================

    if not re.fullmatch(r"\d+", text):

        await update.message.reply_text(
            "❌ Invalid UTR.\n\n"
            "UTR / Transaction ID mein sirf DIGITS hone chahiye.\n\n"
            "Example:\n"
            "123456789012\n\n"
            "📸 Payment screenshot + 🔢 UTR dobara bhejo."
        )

        data["step"] = "screenshot"
        data["screenshot"] = None
        return

    # UTR save
    data["utr"] = text

    username = (
        f"@{user.username}"
        if user.username
        else "No username"
    )

    admin_message = (
        "🔔 NEW PAYMENT VERIFICATION\n\n"
        f"👤 Name: {user.full_name}\n"
        f"🆔 User ID: {user.id}\n"
        f"📱 Username: {username}\n\n"
        f"💳 UTR / Transaction ID:\n{text}\n\n"
        "📸 Payment screenshot upar attached hai.\n\n"
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

    # Send screenshot to admin
    if data.get("screenshot"):

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=data["screenshot"],
            caption=admin_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    await update.message.reply_text(
        "✅ Payment screenshot + UTR received!\n\n"
        "⏳ Your payment is being verified.\n"
        "Approval ke baad yahin private group invite milega."
    )

    data["step"] = "verification"


# =========================
# ADMIN APPROVAL
# =========================

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:

        await query.answer(
            "❌ Unauthorized.",
            show_alert=True
        )
        return

    action, user_id = query.data.split(":")
    user_id = int(user_id)

    # =========================
    # REJECT
    # =========================

    if action == "reject":

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ Payment verification failed.\n\n"
                "Please contact admin if you believe this is an error."
            )
        )

        await query.edit_message_caption(
            caption=query.message.caption + "\n\n❌ REJECTED"
        )

        pending_users.pop(user_id, None)

        return

    # =========================
    # APPROVE
    # =========================

    if action == "approve":

        try:

            # Single-use invite
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
                    "⚠️ This invite is for one use only.\n"
                    "Please don't share it."
                )
            )

            await query.edit_message_caption(
                caption=query.message.caption + "\n\n✅ APPROVED"
            )

            pending_users.pop(user_id, None)

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

    if not PAYMENT_LINK:
        logging.warning("PAYMENT_LINK is missing.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(
            button_handler,
            pattern="^(preview|payment|paid|help)$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_action,
            pattern="^(approve|reject):"
        )
    )

    # Screenshot/photo handler
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_screenshot
        )
    )

    # UTR/text handler
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_utr
        )
    )

    print("VVIP Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
