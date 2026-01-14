import os
import asyncio
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# --- الإعدادات وجلب المتغيرات من Koyeb ---
MONGO_URL = os.getenv("MONGO_URL") #
BOT_TOKEN = os.getenv("BOT_TOKEN") #
ADMIN_PASSWORD = "1460" 

# --- الاتصال بقاعدة البيانات ---
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
sections_col = db.sections

# --- حالات المحادثة (States) ---
(MENU, SELECT_UP, SELECT_REV, NAMING, LINKING, AUTH_ADMIN, 
 SELECT_DEL_SEC, SELECT_DEL_VID, SELECT_SET_SEC, INPUT_ID, INPUT_SECRET) = range(11)

def load_mux_keys():
    """تحميل مفاتيح الأقسام من MongoDB لضمان عدم ضياعها"""
    sections = {}
    stored = sections_col.find().sort("section_id", 1)
    for s in stored:
        sections[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return sections

MUX_SECTIONS = load_mux_keys()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيلم جديد", callback_data="nav_upload")],
        [InlineKeyboardButton("🎬 مراجعة الأفلام", callback_data="nav_review")],
        [InlineKeyboardButton("⚙️ قسم الإدارة (1460)", callback_data="nav_admin")]
    ]
    text = "🎬 <b>لوحة تحكم سيرفر سينما بلاس</b>\nالبيانات مؤمنة عبر MongoDB وMux ✅"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MENU

# --- قسم الإدارة (الحماية والتحكم) ---
async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        context.user_data['is_auth'] = True
        keyboard = [
            [InlineKeyboardButton("🗑️ حذف فيديوهات من Mux", callback_data="admin_del")],
            [InlineKeyboardButton("🔑 إضافة/تعديل مفاتيح الأقسام", callback_data="admin_keys")],
            [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]
        ]
        await update.message.reply_text("✅ <b>تم التحقق بنجاح!</b>\nاختر الإجراء المطلوب:", 
                                       reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return MENU
    else:
        await update.message.reply_text("❌ كلمة مرور خاطئة. حاول مرة أخرى:")
        return AUTH_ADMIN

# --- ميزة إضافة أو تبديل معلومات القسم ---
async def manage_keys_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    buttons = [InlineKeyboardButton(f"تعديل {i}", callback_data=f"set_{i}") for i in MUX_SECTIONS.keys()]
    keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    keyboard.append([InlineKeyboardButton("➕ إضافة قسم (بيئة جديدة)", callback_data="set_new")])
    keyboard.append([InlineKeyboardButton("🏠 عودة", callback_data="back_home")])
    await query.edit_message_text("🔑 <b>إدارة مفاتيح Mux:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return SELECT_SET_SEC

async def finalize_keys_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_secret = update.message.text
    s_id, access_id = context.user_data['target_sec'], context.user_data['new_access_id']
    # الحفظ في MongoDB لضمان عدم الضياع
    sections_col.update_one({"section_id": s_id}, {"$set": {"id": access_id, "secret": new_secret}}, upsert=True)
    global MUX_SECTIONS
    MUX_SECTIONS = load_mux_keys() # تحديث فوري
    await update.message.reply_text(f"✅ تم تحديث القسم {s_id} وحفظه في القاعدة!")
    return await start(update, context)

# --- ميزة حذف الفيديوهات نهائياً ---
async def delete_vid_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    s_id = query.data.split("_")[1]
    creds = MUX_SECTIONS.get(s_id)
    context.user_data['del_sec'] = s_id
    res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]))
    assets = res.json().get("data", [])
    if not assets:
        await query.edit_message_text("📁 هذا القسم فارغ.")
        return MENU
    keyboard = [[InlineKeyboardButton(f"❌ {a.get('passthrough', 'فيلم')}", callback_data=f"kill_{a['id']}")] for a in assets]
    keyboard.append([InlineKeyboardButton("🏠 إلغاء", callback_data="back_home")])
    await query.edit_message_text("⚠️ اختر الفيلم لحذفه نهائياً من Mux:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_DEL_VID

# --- معالج القوائم والرفع ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "nav_admin":
        if context.user_data.get('is_auth'):
            return await manage_keys_select(update, context)
        else:
            await query.edit_message_text("🔐 أرسل كلمة المرور (1460) للمتابعة:")
            return AUTH_ADMIN
    elif query.data == "back_home":
        return await start(update, context)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MENU: [CallbackQueryHandler(menu_handler)],
            AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler)],
            SELECT_SET_SEC: [CallbackQueryHandler(lambda u,c: (c.user_data.update({'target_sec': str(len(MUX_SECTIONS)+1) if u.callback_query.data=='set_new' else u.callback_query.data.split('_')[1]}), u.callback_query.edit_message_text("أرسل Access Token ID:"))[1], pattern="^set_")],
            INPUT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: (c.user_data.update({'new_access_id': u.message.text}), u.message.reply_text("أرسل Secret Key:"))[1])],
            INPUT_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalize_keys_save)],
            SELECT_DEL_VID: [CallbackQueryHandler(lambda u,c: requests.delete(f"https://api.mux.com/video/v1/assets/{u.callback_query.data.split('_')[1]}", auth=(MUX_SECTIONS[c.user_data['del_sec']]['id'], MUX_SECTIONS[c.user_data['del_sec']]['secret'])).status_code and u.callback_query.answer("✅ تم الحذف!", show_alert=True), pattern="^kill_")],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    app.add_handler(conv)
    app.run_polling()
