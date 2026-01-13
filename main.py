import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# استدعاء التوكن من إعدادات Koyeb (Environment Variables)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

SECTIONS = [
    {"name": "القسم الأول", "key": "poksl8tkgo7g6rv9j25uudbum"},
    {"name": "القسم الثاني", "key": "3cd45va0dsnbunj97ulbelcs7"},
    {"name": "القسم الثالث", "key": "acfk4gc9j6etapub26pl78f7k"},
    {"name": "القسم الرابع", "key": "n3u8minhnb5mrh3h5m40l34jj"},
    {"name": "القسم الخامس", "key": "q3ok4daqp4f9c4j5sqqgkob3h"},
    {"name": "القسم السادس", "key": "bnurmk0jeffjiem7gn0bfjtse"},
    {"name": "القسم السابع", "key": "8hi3vchpsvglhbo9mekkqcuto"},
    {"name": "القسم الثامن", "key": "q8l8uqiv6d2h8nk3cerf4jjed"},
    {"name": "القسم التاسع", "key": "anb5let9klmq1r8vcd3u4ivqu"},
    {"name": "القسم العاشر", "key": "46sq58mnmdes5feehokf0ubi8"},
]

USERS = {}

async def start(update, context):
    keyboard = [[InlineKeyboardButton(s["name"], callback_data=str(i))] for i, s in enumerate(SECTIONS)]
    await update.message.reply_text("مرحباً بك في سيرفر سينما بلاس. اختر القسم للرفع:", reply_markup=InlineKeyboardMarkup(keyboard))

async def section_callback(update, context):
    query = update.callback_query
    await query.answer()
    USERS[query.from_user.id] = int(query.data)
    await query.edit_message_text(f"لقد اخترت: {SECTIONS[int(query.data)]['name']}\nأرسل الآن اسم الفيديو.")

async def handle_message(update, context):
    user_id = update.message.from_user.id
    if user_id not in USERS:
        await update.message.reply_text("يرجى الضغط على /start أولاً.")
        return

    text = update.message.text.strip()
    if "awaiting_name" not in context.user_data:
        context.user_data["awaiting_name"] = text
        await update.message.reply_text(f"تم تسجيل الاسم: {text}\nالآن أرسل رابط الفيديو المباشر.")
        return

    video_name = context.user_data.pop("awaiting_name")
    section = SECTIONS[USERS[user_id]]
    msg = await update.message.reply_text(f"جاري رفع '{video_name}'...")

    try:
        response = requests.post(
            "https://api.mux.com/video/v1/uploads",
            auth=(section["key"], ""),
            json={"new_asset_settings": {"playback_policy": "public"}, "input": text}
        )
        if response.status_code == 201:
            playback_id = response.json().get("data", {}).get("id", "N/A")
            await msg.edit_text(f"✅ تم الرفع بنجاح!\nالاسم: {video_name}\nID: {playback_id}")
        else:
            await msg.edit_text(f"❌ فشل الرفع. السبب: {response.status_code}")
    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ: {str(e)}")

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("خطأ: لم يتم ضبط BOT_TOKEN!")
    else:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(section_callback))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        print("Bot is running on Koyeb...")
        app.run_polling()
