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

# --- 1. الإعدادات وجلب المتغيرات من Koyeb ---
# ملاحظة: تأكد أن MONGO_URL في Koyeb يبدأ بـ mongodb بحرف صغير
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
    """تحميل المفاتيح من MongoDB لضمان عدم ضياعها"""
    sections = {}
    stored_sections = sections_col.find().sort("section_id", 1)
    for section in stored_sections:
        sections[str(section["section_id"])] = {"id": section["id"], "secret": section["secret"]}
    return sections

# تحميل المفاتيح في الذاكرة عند التشغيل
MUX_SECTIONS = load_mux_keys()

# --- 4. الوظائف البرمجية (Async Functions) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيديو جديد", callback_data="nav_upload")],
        [InlineKeyboardButton("🎬 مراجعة أفلامك", callback_data="nav_review")],
        [InlineKeyboardButton("⚙️ قسم الإدارة (1460)", callback_data="nav_admin")]
    ]
    text = "🎬 <b>لوحة تحكم سينما بلاس الاحترافية</b>\nالنظام مرتبط بقاعدة البيانات ومؤمن بالكامل ✅"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MENU

# --- قسم الإدارة والأمان ---
async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        context.user_data['is_auth'] = True
        await update.message.reply_text("✅ تم التحقق بنجاح! أرسل /start لفتح خيارات الإدارة.")
        return ConversationHandler.END
    await update.message.reply_text("❌ كلمة مرور خاطئة. حاول مرة أخرى:")
    return AUTH_ADMIN

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("🗑️ حذف أفلام من Mux", callback_data="admin_del")],
        [InlineKeyboardButton("🔑 إضافة/تعديل مفاتيح", callback_data="admin_keys")],
        [InlineKeyboardButton("🏠 العودة", callback_data="back_home")]
    ]
    await query.edit_message_text("⚙️ <b>إدارة النظام:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MENU

# --- إضافة وتبديل المفاتيح في MongoDB ---
async def manage_keys_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    global MUX_SECTIONS
    MUX_SECTIONS = load_mux_keys()
    buttons = [InlineKeyboardButton(f"تعديل {i}", callback_data=f"set_{i}") for i in MUX_SECTIONS.keys()]
    keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="set_new")])
    keyboard.append([InlineKeyboardButton("🏠 عودة", callback_data="back_home")])
    await query.edit_message_text("🔑 <b>إدارة مفاتيح الأقسام:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return SELECT_SET_SEC

async def input_id_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")[1]
    context.user_data['target_sec'] = str(len(MUX_SECTIONS) + 1) if data == "new" else data
    await query.edit_message_text(f"📍 القسم {context.user_data['target_sec']}: أرسل <b>Access Token ID</b> الجديد:", parse_mode=ParseMode.HTML)
    return INPUT_ID

async def input_secret_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_id'] = update.message.text
    await update.message.reply_text("تم الاستلام. أرسل الآن <b>Secret Key</b> الجديد:", parse_mode=ParseMode.HTML)
    return INPUT_SECRET

async def save_keys_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_secret = update.message.text
    s_id, access_id = context.user_data['target_sec'], context.user_data['new_id']
    sections_col.update_one({"section_id": s_id}, {"$set": {"id": access_id, "secret": new_secret}}, upsert=True)
    await update.message.reply_text(f"✅ تم حفظ وتحديث القسم {s_id} في MongoDB!")
    return await start(update, context)

# --- حذف الفيديوهات ---
async def list_videos_to_kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    s_id = query.data.split("_")[1]
    context.user_data['del_sec'] = s_id
    creds = MUX_SECTIONS[s_id]
    res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]))
    assets = res.json().get("data", [])
    if not assets:
        await query.edit_message_text("📁 هذا القسم فارغ.")
        return MENU
    keyboard = [[InlineKeyboardButton(f"❌ {a.get('passthrough', 'فيلم')}", callback_data=f"kill_{a['id']}")] for a in assets]
    keyboard.append([InlineKeyboardButton("🏠 إلغاء", callback_data="back_home")])
    await query.edit_message_text("⚠️ اختر الفيديو لحذفه نهائياً من Mux:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_DEL_VID

async def kill_execution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    v_id = query.data.split("_")[1]
    s_id = context.user_data['del_sec']
    creds = MUX_SECTIONS[s_id]
    requests.delete(f"https://api.mux.com/video/v1/assets/{v_id}", auth=(creds["id"], creds["secret"]))
    await query.answer("✅ تم الحذف من Mux بنجاح!", show_alert=True)
    return await start(update, context)

# --- معالجة القوائم الرئيسية ---
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "nav_admin":
        if context.user_data.get('is_auth'):
            return await admin_menu(update, context)
        await query.edit_message_text("🔐 أرسل كلمة المرور (1460) للمتابعة:")
        return AUTH_ADMIN
    elif query.data == "admin_keys":
        return await manage_keys_menu(update, context)
    elif query.data == "admin_del":
        buttons = [InlineKeyboardButton(f"القسم {i}", callback_data=f"dsec_{i}") for i in MUX_SECTIONS.keys()]
        keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        await query.edit_message_text("🗑️ اختر القسم للحذف:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_DEL_SEC
    return MENU

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MENU: [CallbackQueryHandler(main_menu_handler)],
            AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler)],
            SELECT_SET_SEC: [CallbackQueryHandler(input_id_step, pattern="^set_")],
            INPUT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_secret_step)],
            INPUT_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_keys_final)],
            SELECT_DEL_SEC: [CallbackQueryHandler(list_videos_to_kill, pattern="^dsec_")],
            SELECT_DEL_VID: [CallbackQueryHandler(kill_execution, pattern="^kill_")],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    app.add_handler(conv)
    app.run_polling()
