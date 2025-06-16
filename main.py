# -*- coding: utf-8 -*-
import logging
import asyncio
import os
import ssl
import random
from datetime import datetime
from typing import Dict, Optional, Any

# OCR Imports
import cv2
import numpy as np
import pytesseract as pty

# Telegram and Web Imports
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.helpers import escape_markdown
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
    
# --- CONFIGURATION ---
# Use environment variables for sensitive data
BOT_TOKEN = os.getenv("BOT_TOKEN", "7626608558:AAG2sSmF3awXpk8dbSKoEAb4QDpObyN-kNA")
BOT_2_TOKEN = os.getenv("BOT_2_TOKEN", "7775302991:AAGhN0WzRQ7FNu4z_TJkOTPU6peAPZuMlnU")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "1732455712")
BOT_2_ADMIN_CHAT_ID = os.getenv("BOT_2_ADMIN_CHAT_ID", "1732455712")

# --- OCR CONFIGURATION ---
# Make tesseract path configurable
TESSERACT_PATH = os.getenv("TESSERACT_PATH", r"C:\Users\panho\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
if os.path.exists(TESSERACT_PATH):
    pty.pytesseract.tesseract_cmd = TESSERACT_PATH
else:
    # Try common paths or system PATH
    try:
        import shutil
        tesseract_cmd = shutil.which('tesseract')
        if tesseract_cmd:
            pty.pytesseract.tesseract_cmd = tesseract_cmd
    except:
        pass

# --- ASSET URLs ---
START_PHOTO_URL = "https://i.pinimg.com/736x/dd/cb/03/ddcb0341971d4836da7d12c399149675.jpg"
PROCESSING_GIF_URL = "https://i.pinimg.com/originals/fd/5b/d2/fd5bd28732e0345037d301274c8df692.gif"
PAYMENT_REJECTED_GIF_URL = "https://i.pinimg.com/originals/a5/75/0b/a5750babcf0f417f30e0b4773b29e376.gif"
THANK_YOU_PHOTO_URL = "https://i.pinimg.com/736x/da/1f/3b/da1f3b1746d1d05cfa59f371d0310f8a.jpg"

PAYMENT_PHOTOS = {
    "4": "https://i.pinimg.com/736x/37/62/f1/3762f112c8f2179a2663e997c1419619.jpg",
    "7": "https://i.pinimg.com/736x/14/70/c4/1470c436182cf4c4142bfa343b45c844.jpg",
    "12": "https://i.pinimg.com/736x/6a/3d/98/6a3d98a08550c0d823623279e458411a.jpg",
    "16": "https://i.pinimg.com/736x/b5/96/76/b5967687b83a2bc141c8735dc232ca5e.jpg"
}

# --- URLs FOR THE DYNAMIC BUTTON ---
CHECK_TIME_URLS = {
    "4": "https://time-3day.vercel.app/",
    "7": "https://www.nhoy.store",
    "12": "https://www.pinterest.com/#shop",
    "16": "https://www.irra.store"
}

# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- IN-MEMORY USER DATA STORAGE ---
user_data: Dict[int, Dict[str, Any]] = {}

# --- HELPER FUNCTIONS ---

def is_valid_udid(udid: str) -> bool:
    """Validate UDID format"""
    if not udid or len(udid) < 20 or ' ' in udid:
        return False
    # Additional UDID validation can be added here
    return True

async def extract_text_from_photo(photo_file) -> str:
    """Extract text from photo using OCR"""
    try:
        file_bytes = await photo_file.download_as_bytearray()
        np_array = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error("Could not decode image")
            return "Error: Could not read image file."
        
        # Preprocess image for better OCR results
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Apply some preprocessing to improve OCR accuracy
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        text = pty.image_to_string(gray, config='--psm 6')
        return text.strip() if text else "No text found in image."
        
    except Exception as e:
        logger.error(f"Error during OCR processing: {e}")
        return f"Error during text extraction: {str(e)}"

async def send_to_bot_2(order_data: dict) -> bool:
    """Send order details to Bot 2"""
    url = f"https://api.telegram.org/bot{BOT_2_TOKEN}/sendMessage"
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    username = order_data.get('username', 'N/A')
    
    message_text = (
        f"🎉 NEW COMPLETED ORDER FROM BOT 1 🎉\n\n"
        f"👤 User: {username}\n"
        f"🆔 User ID: {order_data.get('user_id', 'N/A')}\n"
        f"Esign Amount: ${order_data.get('amount', 'N/A')} USD\n"
        f"📱 UDID: {order_data.get('udid', 'N/A')}\n"
        f"🆔 Payment ID: {order_data.get('payment_id', 'N/A')}\n"
        f"⏰ Order Time: {current_time}\n"
        f"📊 Status: ✅ PAYMENT CONFIRMED"
    )
    
    payload = {
        'chat_id': BOT_2_ADMIN_CHAT_ID,
        'text': message_text
    }
    
    timeout = aiohttp.ClientTimeout(total=15)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, data=payload) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent order details to Bot 2 for user {order_data.get('user_id')}")
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"Failed to send to Bot 2. Status: {response.status}, Response: {response_text}")
                    return False
    except asyncio.TimeoutError:
        logger.error("Timeout while sending to Bot 2")
        return False
    except Exception as e:
        logger.error(f"Exception while sending to Bot 2: {e}")
        return False

async def safe_delete_message(message) -> None:
    """Safely delete a message with error handling"""
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Could not delete message: {e}")

# --- BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    if not update.effective_user or not update.message:
        return
        
    user = update.effective_user
    user_id = user.id
    
    # Clear any existing user data
    if user_id in user_data:
        del user_data[user_id]
    
    keyboard = [[
        InlineKeyboardButton("📱 Download UDID Profile", url="https://udid.tech/download-profile")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = (
        f"🎉 *Welcome, {escape_markdown(user.first_name, version=2)}\\!* 🎉\n\n"
        "1️⃣ First, download the UDID profile using the button below\\.\n"
        "2️⃣ Install it on your device\\.\n"
        "3️⃣ Copy your unique UDID and send it to me to begin\\."
    )
    
    try:
        await update.message.reply_photo(
            photo=START_PHOTO_URL,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Error sending start message: {e}")
        await update.message.reply_text("Welcome! Please send your UDID to begin.")

async def handle_udid_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle UDID input from user"""
    if not update.effective_user or not update.message or not update.message.text:
        return
        
    user_id = update.effective_user.id
    udid = update.message.text.strip()
    
    if not is_valid_udid(udid):
        await update.message.reply_text(
            "❌ *Invalid UDID Format*\n\n"
            "Please make sure you copied the entire UDID string\\. "
            "It should be a long string of letters and numbers with no spaces\\.\n\n"
            "Use /start to get the download link again if you need help\\.",
            parse_mode='MarkdownV2'
        )
        return
    
    # Store user data
    user_data[user_id] = {'udid': udid}
    
    keyboard = [
        [
            InlineKeyboardButton("Esign $4", callback_data="payment_4"),
            InlineKeyboardButton("Esign $7", callback_data="payment_7")
        ],
        [
            InlineKeyboardButton("Esign $12", callback_data="payment_12"),
            InlineKeyboardButton("Esign $16", callback_data="payment_16")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await update.message.reply_text(
            f"✅ *UDID Received\\!*\n\n"
            f"📱 *Your UDID:* `{escape_markdown(udid, version=2)}`\n\n"
            f"👇 *Please select your payment plan:*",
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Error sending UDID confirmation: {e}")
        await update.message.reply_text("UDID received! Please select your payment plan.")

async def handle_payment_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment button clicks"""
    if not update.callback_query or not update.callback_query.from_user or not update.callback_query.data:
        return
        
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user has valid session
    if user_id not in user_data or 'udid' not in user_data[user_id]:
        await query.edit_message_text(
            "❌ Error: Your session has expired. Please send your UDID again using /start."
        )
        return
    
    try:
        parts = query.data.split('_')
        if len(parts) != 2:
            raise ValueError("Invalid callback data format")
        
        action, amount = parts[0], parts[1]
        
        if amount not in PAYMENT_PHOTOS:
            raise ValueError(f"Invalid payment amount: {amount}")
        
        udid = user_data[user_id]['udid']
        user_data[user_id]['pending_amount'] = amount
        user_data[user_id]['payment_id'] = f"PAY-{amount}-{udid[:8]}"
        
        payment_photo_url = PAYMENT_PHOTOS[amount]
        
        caption = (
            f"💳 *Payment for ${amount} USD*\n\n"
            f"📱 *UDID:* `{escape_markdown(udid, version=2)}`\n"
            f"🆔 *Payment ID:* `{user_data[user_id]['payment_id']}`\n\n"
            f"1️⃣ Make the payment using the QR code in the image\\.\n"
            f"2️⃣ Take a screenshot of the payment confirmation\\.\n"
            f"3️⃣ Send the screenshot back to this chat\\."
        )
        
        if query.message:
            await query.message.reply_photo(
                photo=payment_photo_url,
                caption=caption,
                parse_mode='MarkdownV2'
            )
            await query.edit_message_text(
                text=f"Instructions sent for ${amount} payment. Please check the new message.",
                reply_markup=None
            )
            
    except Exception as e:
        logger.error(f"Error handling payment button: {e}")
        await query.edit_message_text("❌ An error occurred. Please try again or use /start.")

async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment screenshot validation"""
    if not update.effective_user or not update.message:
        return
        
    user = update.effective_user
    user_id = user.id
    message = update.message
    
    # Check if user has pending payment
    if user_id not in user_data or 'pending_amount' not in user_data[user_id]:
        await message.reply_text(
            "❌ I wasn't expecting a photo from you. Please start the payment process first using /start."
        )
        return

    if not message.photo:
        await message.reply_text("📸 Please send a photo of your payment confirmation.")
        return

    # Show processing animation
    processing_caption_text = escape_markdown("... please wait.", version=2)
    processing_message = None
    
    try:
        processing_message = await message.reply_animation(
            animation=PROCESSING_GIF_URL,
            caption=f"🔄 *Validating your payment{processing_caption_text}*",
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Error sending processing animation: {e}")
        processing_message = await message.reply_text("🔄 Validating your payment... please wait.")
    
    try:
        # Get the highest resolution photo
        photo_file = await message.photo[-1].get_file()
        extracted_text = await extract_text_from_photo(photo_file)
        
        # Check for required name in payment
        required_name = "Roeurn Bora"
        
        if required_name.lower() in extracted_text.lower():
            logger.info(f"Payment validated for user {user_id}. Preparing notifications.")
            
            user_info = user_data[user_id]
            username_raw = f"@{user.username}" if user.username else user.first_name
            
            order_data = {
                'username': username_raw,
                'user_id': user_id,
                'amount': user_info.get('pending_amount'),
                'udid': user_info.get('udid'),
                'payment_id': user_info.get('payment_id')
            }

            # Send to Bot 2
            await send_to_bot_2(order_data)
            
            # Delete processing message
            if processing_message:
                await safe_delete_message(processing_message)
            
            amount = order_data['amount']
            amount_float = float(amount)
            
            # Create dynamic button
            check_time_url = CHECK_TIME_URLS.get(amount, "https://t.me")
            keyboard = [[
                InlineKeyboardButton("⏳ Check Time", url=check_time_url)
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Create success message
            thank_you_caption_text = (
                f"🎉 *Thank You, {escape_markdown(user.first_name, version=2)}* 🎉\n\n"
                f"Order has been completed\\.\n\n"
                f"UDID: `{escape_markdown(order_data['udid'], version=2)}`\n"
                f"Price: `${amount_float:.2f}`\n"
                f"Added on: `Cambodia`\n\n"
                f"To start a new order, use /start"
            )

            await message.reply_photo(
                photo=THANK_YOU_PHOTO_URL,
                caption=thank_you_caption_text,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )

            # Clean up user data
            if user_id in user_data:
                del user_data[user_id]

        else:
            logger.warning(f"Payment REJECTED for user {user_id}. Name '{required_name}' was NOT found.")
            
            if processing_message:
                await safe_delete_message(processing_message)
            
            rejection_text = (
                "Sorry, I could not find the name `Roeurn Bora` in the payment screenshot. "
                "Please make sure you have sent the correct and complete payment confirmation and try again."
            )
            rejection_caption = f"⚠️ *Payment Not Confirmed*\n\n{escape_markdown(rejection_text, version=2)}"
            
            await message.reply_animation(
                animation=PAYMENT_REJECTED_GIF_URL,
                caption=rejection_caption,
                parse_mode='MarkdownV2'
            )
            
    except Exception as e:
        logger.error(f"Error in handle_payment_screenshot for user {user_id}: {e}")
        
        if processing_message:
            await safe_delete_message(processing_message)
        
        await message.reply_text(
            "❌ An unexpected error occurred while processing your photo. Please try again."
        )

async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle other text messages (assumed to be UDID)"""
    await handle_udid_input(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")

async def main() -> None:
    """Main function to run the bot"""
    print("🤖 Starting Telegram UDID Payment & OCR Bot...")
    
    # Validate configuration
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN not configured properly")
        return
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(handle_payment_button, pattern='^payment_'))
        application.add_handler(MessageHandler(filters.PHOTO, handle_payment_screenshot))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))
        
        # Add error handler
        application.add_error_handler(error_handler)

        print("✅ Bot is now running!")
        logger.info("Bot started successfully")
        
        # Start the bot
        async with application:
            await application.start()
            if application.updater:
                await application.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True
                )
                
                # Keep the bot running
                try:
                    while True:
                        await asyncio.sleep(3600)
                except KeyboardInterrupt:
                    logger.info("Bot stopped by user")
                finally:
                    await application.updater.stop()
                    await application.stop()
    
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ Failed to start bot: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logger.error(f"Fatal error: {e}")