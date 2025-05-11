import random
import time
import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

DATA_FILE = "user_data.json"
BONUS_COOLDOWN = 2 * 60 * 60  # 2 hours

def load_user_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ JSON decode error. Starting with empty data.")
            return {}
    print("[!] No existing data found.")
    return {}

def save_user_data():
    with open(DATA_FILE, "w") as f:
        json.dump(user_data, f, indent=4)

# Adding transaction history
def add_transaction(user_id, amount, transaction_type, recipient_id=None):
    if user_id not in user_data:
        user_data[user_id] = {
            'balance': 100,
            'invites': 0,
            'bonus': 10,
            'last_bonus_time': 0,
            'transactions': []  # Initialize transactions list if not present
        }
    
    transaction = {
        "amount": amount,
        "type": transaction_type,  # 'send', 'receive', 'withdraw', etc.
        "recipient_id": recipient_id,
        "time": time.time()
    }
    user_data[user_id]['transactions'].append(transaction)
    save_user_data()

user_data = load_user_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.full_name
    ref_id = None

    if update.message and update.message.text.startswith("/start"):
        parts = update.message.text.split()
        if len(parts) > 1:
            ref_id = parts[1]

    if user_id not in user_data:
        user_data[user_id] = {
            'balance': 100,
            'invites': 0,
            'bonus': 10,
            'last_bonus_time': 0,
            'transactions': []  # Initialize transaction history list
        }
        save_user_data()

        if ref_id and ref_id != user_id and ref_id in user_data:
            user_data[ref_id]['invites'] += 1
            user_data[ref_id]['balance'] += 2
            save_user_data()

    keyboard = [
        [InlineKeyboardButton("📄 Account", callback_data='account'),
         InlineKeyboardButton("💰 Balance", callback_data='balance')],
        [InlineKeyboardButton("📨 Invite", callback_data='invite'),
         InlineKeyboardButton("🎁 Bonus", callback_data='bonus')], 
        [InlineKeyboardButton("💸 Withdraw", callback_data='withdraw'),
         InlineKeyboardButton("❓ FAQ", callback_data='faq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = f"Hello, *{user_name}*! Welcome to the Neuro bot."

    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if user_id not in user_data:
        await query.edit_message_text("User not found. Please /start first.")
        return

    data = user_data[user_id]

    if query.data == 'account':
        text = (
            f"👤 *Account Info:*\n"
            f"User ID: `{user_id}`\n"
            f"Username: @{query.from_user.username or 'N/A'}\n"
            f"Balance: {data['balance']} NRO\n"
            f"Invites: {data['invites']}\n"
            f"Bonus: {data['bonus']} NRO"
        )
        keyboard = [
            [InlineKeyboardButton("💸 Send", callback_data='send')],
            [InlineKeyboardButton("📅 Receive", callback_data='receive')],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif query.data == 'send':
        # Asking the user to input the recipient's User ID
        context.user_data['awaiting_user_id'] = True
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='account')]]
        await query.edit_message_text(
            f"💳 আপনার ব্যালেন্স: {data['balance']} NRO\n\nযাকে সেন্ড করতে চান তার User ID দিন:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    elif query.data == 'receive':
        text = "📅 আপনি আপনার User ID অন্যদের শেয়ার করলে তারা আপনাকে NRO সেন্ড করতে পারবে।"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='account')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif query.data == 'balance':
        text = f"💰 আপনার বর্তমান ব্যালেন্স: {data['balance']} NRO"
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data='back')],
            [InlineKeyboardButton("📝 Transaction History", callback_data='transaction_history')]  # Added button here
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif query.data == 'invite':
        try:
            bot_username = (await context.bot.get_me()).username
            invite_link = f"https://t.me/{bot_username}?start={user_id}"
            text = f"📨 *Invite your friends using the link below:*\n`{invite_link}`"
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            print(f"Error in invite handler: {e}")
            await query.edit_message_text("❌ Failed to generate invite link.")

    elif query.data == 'bonus':
        now = time.time()
        last_time = data.get('last_bonus_time', 0)

        if now - last_time >= BONUS_COOLDOWN:
            bonus_amount = random.randint(1, 20)
            data['balance'] += bonus_amount
            data['last_bonus_time'] = now
            save_user_data()
            text = f"🎁 আপনি {bonus_amount} NRO বোনাস পেয়েছেন!\nনতুন ব্যালেন্স: {data['balance']} NRO"
        else:
            remaining = int(BONUS_COOLDOWN - (now - last_time))
            minutes = remaining // 60
            seconds = remaining % 60
            text = f"⏳ পরবর্তী বোনাসের জন্য অপেক্ষা করুন {minutes} মিনিট {seconds} সেকেন্ড।"

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif query.data == 'withdraw':
        if data['invites'] >= 10:
            withdraw_amount = data['balance']
            data['balance'] = 0
            save_user_data()
            text = f"💸 আপনি {withdraw_amount} NRO উইথড্র করেছেন! ব্যালেন্স এখন 0।"
        else:
            text = "❌ উইথড্র করার জন্য আপনার কমপক্ষে 10 ইনভাইট দরকার।"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif query.data == 'faq':
        text = (
            "*FAQ‼*\n\n"
            "1. *কিভাবে বোনাস পাওয়া যায়?*\n→ 🎁 Bonus বাটনে প্রতি 2 ঘণ্টা পর ক্লিক করুন।\n\n"
            "2. *কিভাবে টাকা তুলবো?*\n→ 10 জনকে ইনভাইট করলে Withdraw করতে পারবেন।\n\n"
            "3. *ইনভাইট লিংক কোথায়?*\n→ 📨 Invite বাটনে ক্লিক করুন।"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif query.data == 'back':
        await start(update, context)

    elif query.data == 'transaction_history':
        if data['transactions']:
            transaction_text = "*Transaction History:*\n\n"
            for tx in data['transactions'][-5:]:  # Show only the last 5 transactions
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(tx['time']))
                transaction_text += f"Type: {tx['type']} | Amount: {tx['amount']} NRO | Time: {time_str}\n"
        else:
            transaction_text = "No transactions yet."

        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back')]]
        await query.edit_message_text(transaction_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Handling the 'awaiting_user_id' state
    if 'awaiting_user_id' in context.user_data:
        recipient_user_id = update.message.text.strip()

        # Validate if the recipient is a valid user
        if recipient_user_id in user_data and recipient_user_id != user_id:
            amount = 50  # The amount to send
            add_transaction(user_id, amount, 'send', recipient_user_id)
            user_data[user_id]['balance'] -= amount
            user_data[recipient_user_id]['balance'] += amount
            save_user_data()
            await update.message.reply_text(f"Successfully sent {amount} NRO to user {recipient_user_id}.")
        else:
            await update.message.reply_text("Invalid User ID. Please provide a valid User ID.")
        
        del context.user_data['awaiting_user_id']  # Reset the awaiting state
    
    else:
        await update.message.reply_text("Type /start to interact with the bot.")

def main():
    app = ApplicationBuilder().token("7999031552:AAHYe41SOElYKX19mZiU3Mpi4e_jWy-Kn4U").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
