import os
import asyncio
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# --- الإعدادات وجلب المتغيرات من Koyeb ---
MONGO_URL = os.getenv("MONGO_URL") # الرابط الذي حصلت عليه من MongoDB Atlas
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = "1460" 

# --- الاتصال بقاعدة البيانات ---
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
sections_col = db.sections

# --- حالات المحادثة (States) ---
(MENU, SELECT_UP, SELECT_REV, NAMING, LINKING, AUTH_ADMIN, 
 SELECT_DEL_SEC, SELECT_DEL_VID, SELECT_SET_SEC, INPUT_ID, INPUT_SECRET) = range(11)

def load_mux_keys():
    """تحميل المفاتيح من MongoDB لضمان ثباتها حتى بعد إعادة التشغيل"""
    sections = {}
    stored_sections = sections_col.find().sort("section_id", 1)
    for section in stored_sections:
        sections[str(section["section_id"])] = {"id": section["id"], "secret": section["secret"]}
    return sections

# تحميل المفاتيح في الذاكرة عند بدء التشغيل
MUX_SECTIONS = load_mux_keys()

# --- دالة البداية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # تنظيف حالة الأمان للمستخدم
    context.user_data['is_auth'] = context.user_data.get('is_auth', False)
    
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيديو جديد", callback_data="nav_upload")],
        [InlineKeyboardButton("🎬 مراجعة أفلامك", callback_data="nav_review")],
        [InlineKeyboardButton("⚙️ قسم الإدارة (1460)", callback_data="nav_admin")]
    ]
    text = "🎬 <b>لوحة تحكم سينما بلاس الذكية</b>\nالنظام مرتبط بقاعدة البيانات ومؤمن بالكامل ✅"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MENU

# --- معالج القوائم الرئيسي ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    global MUX_SECTIONS
    MUX_SECTIONS = load_mux_keys() # تحديث المفاتيح من القاعدة

    if query.data == "nav_upload":
        buttons = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in MUX_SECTIONS.keys()]
        keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        keyboard.append([InlineKeyboardButton("🏠 عودة", callback_data="back_home")])
        await query.edit_message_text("📤 <b>اختر القسم للرفع إليه:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return SELECT_UP

    elif query.data == "nav_review":
        buttons = [InlineKeyboardButton(f"مراجعة {i}", callback_data=f"rev_{i}") for i in MUX_SECTIONS.keys()]
        keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        keyboard.append([InlineKeyboardButton("🏠 عودة", callback_data="back_home")])
        await query.edit_message_text("🔍 <b>اختر القسم لمشاهدة الأفلام المرفوعة:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return SELECT_REV

    elif query.data == "nav_admin":
        if context.user_data.get('is_auth'):
            keyboard = [
                [InlineKeyboardButton("🗑️ حذف فيديوهات من Mux", callback_data="admin_del")],
                [InlineKeyboardButton("🔑 إضافة/تعديل مفاتيح الأقسام", callback_data="admin_keys")],
                [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]
            ]
            await query.edit_message_text("⚙️ <b>إدارة الأقسام والبيانات:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
            return MENU
        else:
            await query.edit_message_text("🔐 الميزة محمية. أرسل كلمة المرور لفتح الإدارة:")
            return AUTH_ADMIN
            
    elif query.data == "back_home":
        return await start(update, context)

# --- نظام الأمان بكلمة السر ---
async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        context.user_data['is_auth'] = True
        await update.message.reply_text("✅ تم التحقق بنجاح. أرسل /start لفتح خيارات الإدارة.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ كلمة مرور خاطئة. حاول مرة أخرى:")
        return AUTH_ADMIN

# --- ميزة إضافة/تعديل الأقسام في MongoDB ---
async def manage_keys_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    buttons = [InlineKeyboardButton(f"تعديل {i}", callback_data=f"set_{i}") for i in MUX_SECTIONS.keys()]
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="set_new")])
    keyboard.append([InlineKeyboardButton("🏠 عودة", callback_data="back_home")])
    await query.edit_message_text("🔑 اختر القسم لتعديله أو أضف بيئة جديدة:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_SET_SEC

async def input_id_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")[1]
    context.user_data['target_sec'] = str(len(MUX_SECTIONS) + 1) if data == "new" else data
    await query.edit_message_text(f"📍 تحديث القسم: {context.user_data['target_sec']}\nأرسل الآن **Access Token ID** الجديد:")
    return INPUT_ID

async def finalize_keys_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_secret = update.message.text
    s_id, access_id = context.user_data['target_sec'], context.user_data['new_access_id']
    sections_col.update_one({"section_id": s_id}, {"$set": {"id": access_id, "secret": new_secret}}, upsert=True)
    await update.message.reply_text(f"✅ تم حفظ وتحديث القسم {s_id} في القاعدة بنجاح!")
    return await start(update, context)

# --- ميزة حذف الفيديوهات نهائياً ---
async def delete_vid_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    s_id = query.data.split("_")[1]
    creds = MUX_SECTIONS[s_id]
    context.user_data['del_sec'] = s_id
    res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]))
    assets = res.json().get("data", [])
    if not assets:
        await query.edit_message_text("📁 هذا القسم فارغ.")
        return MENU
    keyboard = [[InlineKeyboardButton(f"❌ {a.get('passthrough', 'فيلم')}", callback_data=f"kill_{a['id']}")] for a in assets]
    keyboard.append([InlineKeyboardButton("🏠 إلغاء", callback_data="back_home")])
    await query.edit_message_text("⚠️ اختر الفيديو لحذفه نهائياً من Mux:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_DEL_VID

# --- معالجات الرفع والمراجعة الحية ---
async def upload_init(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['up_section'] = update.callback_query.data.split("_")[1]
    await update.callback_query.edit_message_text("📝 أرسل اسم الفيلم (سيظهر في Mux):")
    return NAMING

async def upload_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_url, s_id, v_name = update.message.text, context.user_data['up_section'], context.user_data['up_name']
    creds = MUX_SECTIONS[s_id]
    payload = {"input": video_url, "playback_policy": ["public"], "passthrough": v_name, "metadata": {"video_title": v_name}}
    res = requests.post("https://api.mux.com/video/v1/assets", json=payload, auth=(creds["id"], creds["secret"]))
    if res.status_code == 201:
        await update.message.reply_text(f"✅ تم الرفع! الكود: <code>{res.json()['data']['playback_ids'][0]['id']}</code>", parse_mode=ParseMode.HTML)
    return await start(update, context)

# --- تشغيل البوت ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MENU: [CallbackQueryHandler(menu_handler, pattern="nav_"), CallbackQueryHandler(manage_keys_select, pattern="admin_keys"), CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("🗑️ اختر القسم للحذف:"), pattern="admin_del")],
            SELECT_UP: [CallbackQueryHandler(upload_init, pattern="^up_")],
            NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: (c.user_data.update({'up_name': u.message.text}), u.message.reply_text("أرسل الرابط المباشر:"))[1])],
            LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_final)],
            AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler)],
            SELECT_SET_SEC: [CallbackQueryHandler(input_id_step, pattern="^set_")],
            INPUT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: (c.user_data.update({'new_access_id': u.message.text}), u.message.reply_text("أرسل Secret Key:"))[1])],
            INPUT_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalize_keys_save)],
            SELECT_DEL_VID: [CallbackQueryHandler(lambda u,c: requests.delete(f"https://api.mux.com/video/v1/assets/{u.callback_query.data.split('_')[1]}", auth=(MUX_SECTIONS[c.user_data['del_sec']]['id'], MUX_SECTIONS[c.user_data['del_sec']]['secret'])).status_code and u.callback_query.answer("✅ تم الحذف!", show_alert=True), pattern="^kill_")],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    app.add_handler(conv)
    app.run_polling()
