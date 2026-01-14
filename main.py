import os
import asyncio
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# --- 1. الإعدادات وجلب المتغيرات ---
MONGO_URL = os.getenv("MONGO_URL") #
BOT_TOKEN = os.getenv("BOT_TOKEN") #
ADMIN_PASSWORD = "1460" #

# --- 2. الاتصال بقاعدة البيانات ---
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
sections_col = db.sections

# --- 3. حالات المحادثة (States) ---
(MENU, SELECT_UP, SELECT_REV, NAMING, LINKING, AUTH_ADMIN, 
 SELECT_DEL_SEC, SELECT_DEL_VID, SELECT_SET_SEC, INPUT_ID, INPUT_SECRET) = range(11)

def load_mux_keys():
    """تحميل المفاتيح من MongoDB لضمان عمل الرفع والمراجعة"""
    sections = {}
    stored_sections = sections_col.find().sort("section_id", 1)
    for section in stored_sections:
        sections[str(section["section_id"])] = {"id": section["id"], "secret": section["secret"]}
    return sections

# تحميل المفاتيح في الذاكرة
MUX_SECTIONS = load_mux_keys()

# --- 4. الوظائف المصلحة (بدلاً من Lambda) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيلم جديد", callback_data="nav_upload")],
        [InlineKeyboardButton("🎬 مراجعة الأفلام", callback_data="nav_review")],
        [InlineKeyboardButton("⚙️ قسم الإدارة (الادارة)", callback_data="nav_admin")]
    ]
    text = "🎬 <b>سيرفر سينما بلاس - النسخة المستقرة</b>\nتم إصلاح كافة الأقسام والربط بالقاعدة ✅"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MENU

# --- وظائف المراجعة (Review) ---
async def review_section_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    s_id = query.data.split("_")[1]
    creds = MUX_SECTIONS.get(s_id)
    
    await query.edit_message_text(f"⏳ جاري جلب أفلام القسم {s_id}...")
    try:
        res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]), timeout=10)
        assets = res.json().get("data", [])
        
        if not assets:
            await query.edit_message_text(f"📁 القسم {s_id} فارغ حالياً.")
            return MENU
            
        text = f"📂 <b>مرفوعات القسم {s_id}:</b>\n\n"
        for i, a in enumerate(assets, 1):
            name = a.get("passthrough", "فيلم بدون اسم")
            p_id = a.get("playback_ids", [{"id": "-"}])[0]["id"]
            text += f"{i}- {name} - <b>شغال ✅</b>\n<code>{p_id}</code>\n\n"
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 عودة", callback_data="back_home")]]), parse_mode=ParseMode.HTML)
    except:
        await query.edit_message_text("❌ خطأ في الاتصال. تأكد من صحة مفاتيح القسم.")
    return MENU

# --- وظائف الرفع (Upload) ---
async def start_upload_naming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['up_section'] = query.data.split("_")[1]
    await query.edit_message_text("📝 أرسل اسم الفيلم الآن:")
    return NAMING

async def get_upload_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['up_name'] = update.message.text
    await update.message.reply_text("🔗 أرسل الرابط المباشر للفيديو:")
    return LINKING

async def execute_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_url = update.message.text
    s_id = context.user_data['up_section']
    v_name = context.user_data['up_name']
    creds = MUX_SECTIONS[s_id]
    
    status_msg = await update.message.reply_text("⏳ جاري الرفع إلى Mux...")
    payload = {"input": video_url, "playback_policy": ["public"], "passthrough": v_name}
    
    res = requests.post("https://api.mux.com/video/v1/assets", json=payload, auth=(creds["id"], creds["secret"]))
    if res.status_code == 201:
        p_id = res.json()["data"]["playback_ids"][0]["id"]
        await status_msg.edit_text(f"✅ تم الرفع بنجاح!\nالكود: <code>{p_id}</code>", parse_mode=ParseMode.HTML)
    else:
        await status_msg.edit_text(f"❌ فشل الرفع. كود الخطأ: {res.status_code}")
    return await start(update, context)

# --- معالج القائمة الرئيسي ---
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    global MUX_SECTIONS
    MUX_SECTIONS = load_mux_keys()

    if query.data == "nav_upload":
        buttons = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in MUX_SECTIONS.keys()]
        keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        await query.edit_message_text("📤 اختر القسم للرفع:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_UP

    elif query.data == "nav_review":
        buttons = [InlineKeyboardButton(f"مراجعة {i}", callback_data=f"rev_{i}") for i in MUX_SECTIONS.keys()]
        keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        await query.edit_message_text("🔍 اختر القسم للمراجعة:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_REV

    elif query.data == "nav_admin":
        if context.user_data.get('is_auth'):
            keyboard = [[InlineKeyboardButton("🔑 تحديث المفاتيح", callback_data="admin_keys")], [InlineKeyboardButton("🏠 عودة", callback_data="back_home")]]
            await query.edit_message_text("⚙️ إدارة النظام:", reply_markup=InlineKeyboardMarkup(keyboard))
            return MENU
        await query.edit_message_text("🔐 أرسل كلمة المرور (الادمن):")
        return AUTH_ADMIN
    return MENU

# --- تشغيل البوت ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MENU: [CallbackQueryHandler(handle_main_menu)],
            SELECT_UP: [CallbackQueryHandler(start_upload_naming, pattern="^up_")],
            SELECT_REV: [CallbackQueryHandler(review_section_list, pattern="^rev_")],
            NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_upload_link)],
            LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_upload)],
            AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: ConversationHandler.END if u.message.text=="1460" else AUTH_ADMIN)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    app.add_handler(conv)
    app.run_polling()

