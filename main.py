
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

# الإعدادات الأساسية
BOT_TOKEN = os.getenv("BOT_TOKEN")

# الأقسام العشرة مع مفاتيح Mux الخاصة بكل منها
MUX_SECTIONS = {
    "1": {"id": "2ab8ed37-b8af-4ffa-ab78-bc0910fcac6e", "secret": "zkX7I4isPxeMz6tFh20vFt37sNOWPpPgaMpH0u7i2dvavEMea84Wob8UfFvIVouNcfzjpIgt7jl"},
    "2": {"id": "3522203d-1925-4ec3-a5f7-9ca9efd1771a", "secret": "p7fHTPl4hFvLh1koWPHlJ7cif9GcOCFxDAYHIAraC4mcGABRrJWp2jNJ4B4cVgIcE2YOY+AT1wb"},
    "3": {"id": "85501be0-bc4f-415c-afde-b8ac1b996974", "secret": "QXzmzVANcX9VrS2vBCTa0h91+QAlr7iM5izLDrzKUDdhSx2sJx2CuNFT6CJHpqOsftsW2MICpci"},
    "4": {"id": "7894140e-03a9-4946-9698-1b58f1e3ea38", "secret": "HwgZg1a7h05ul/AYpeICooOp0fOt4o7W9Fxf0am2z4Qb1QyHfIL3BRMjxh1e6b1Dn+WXehKdjaN"},
    "5": {"id": "147d1438-4269-4739-ae68-7dcbdf9f1d84", "secret": "6cqf9LKM38Q7gbkrrYmWGNwH0v27UjY8DzQWRDZ1Md137UE7+n52NlBGIVc/4qaShADTH5D+LsU"},
    "6": {"id": "60d38bcd-bb17-4db0-9599-129c232cdabf", "secret": "E9j1AbbGropItPcS4K+Gl1csebAiLMJJuglGn9NxIasbJAmM/CsVXTL9BCyw+jBwsR7Zq51RJy2"},
    "7": {"id": "31517bbe-2628-438e-b7ac-261708d6f26e", "secret": "pnHQhp05xWhu6tSc8u98c3x47ycmT7zhW3V6mzxlSmqz30vac71VmsHYgRUBI5aDuBFYBIlkcF4"},
    "8": {"id": "4c53f771-ab87-4dab-9484-2f7f94799f6e", "secret": "rWXTB3ktFkyvcKQkJwD6tcOT+6sV1dM3ndU/H4oZu5qnG6/+2WIw4keq2DPFU+F0foJ57eI0BPz"},
    "9": {"id": "0f39d0e7-33d9-4983-a20d-c20a54a39d19", "secret": "GG2UNHGjJysTBxe32+VOGEOpLGSEUGINWVvEFyhz+inbm+G41LNi/Hua8Kd9pqeRO+FOLyLgk5/"},
    "10": {"id": "fcbfcdcb-fbd3-41ae-ab10-5451502ac8d3", "secret": "NtwphUQyZZsrhOXgadrZN3QoJXxMVW2za+q0xFe/1vLl4PfRjrGCOn18BOqpGFMCFZAc/g2rR0R"}
}

# حالات المحادثة
CHOOSING, NAMING, LINKING = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(f"القسم {i}", callback_data=str(i)) for i in range(1, 6)],
                [InlineKeyboardButton(f"القسم {i}", callback_data=str(i)) for i in range(6, 11)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مرحباً بك في سيرفر سينما بلاس 🎬\nالرجاء اختيار القسم المراد الرفع إليه:", reply_markup=reply_markup)
    return CHOOSING

async def section_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['section'] = query.data
    await query.edit_message_text(f"لقد اخترت القسم: {query.data}\nالآن أرسل 'اسم الفيلم':")
    return NAMING

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['video_name'] = update.message.text
    await update.message.reply_text(f"تم تسجيل الاسم: {update.message.text}\nالآن أرسل 'رابط الفيديو المباشر':")
    return LINKING

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_url = update.message.text
    section_id = context.user_data['section']
    creds = MUX_SECTIONS[section_id]
    
    await update.message.reply_text("جاري بدء عملية الرفع إلى Mux... انتظر قليلاً ⏳")
    
    # طلب الرفع إلى Mux API
    mux_url = "https://api.mux.com/video/v1/assets"
    payload = {
        "input": video_url,
        "playback_policy": ["public"],
        "passthrough": context.user_data['video_name']
    }
    
    try:
        response = requests.post(mux_url, json=payload, auth=(creds["id"], creds["secret"]))
        if response.status_code == 201:
            data = response.json()
            asset_id = data["data"]["id"]
            await update.message.reply_text(f"✅ تم الرفع بنجاح للقسم {section_id}!\n🆔 Asset ID: {asset_id}\nاسم الفيلم: {context.user_data['video_name']}")
        else:
            await update.message.reply_text(f"❌ فشل الرفع. السبب: {response.status_code}\n{response.text}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ تقني: {str(e)}")
    
    return ConversationHandler.END

if __name__ == '__main__':
    print("Bot is running on Koyeb...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [CallbackQueryHandler(section_choice)],
            NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    
    app.add_handler(conv_handler)
    app.run_polling()
