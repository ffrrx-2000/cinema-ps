import os
import asyncio
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# --- الإعدادات وجلب المتغيرات من Koyeb ---
MONGO_URL = os.getenv("MONGO_URL")
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
    """تحميل المفاتيح من MongoDB لضمان ثباتها"""
    sections = {}
    stored_sections = sections_col.find().sort("section_id", 1)
    for section in stored_sections:
        sections[str(section["section_id"])] = {"id": section["id"], "secret": section["secret"]}
    return sections

# تحميل المفاتيح في الذاكرة عند بدء التشغيل
MUX_SECTIONS = load_mux_keys()

# --- واجهة البداية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# --- قسم الإدارة (محمي بكلمة السر) ---
async def auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        context.user_data['is_auth'] = True
        keyboard = [
            [InlineKeyboardButton("🗑️ حذف فيديوهات من Mux", callback_data="admin_del")],
            [InlineKeyboardButton("🔑 إضافة/تعديل مفاتيح الأقسام", callback_data="admin_keys")],
            [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]
        ]
        await update.message.reply_text("✅ <b>تم التحقق!</b>\nأهلاً بك في قسم الإدارة، اختر الإجراء المطلوب:", 
                                       reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return MENU
    else:
        await update.message.reply_text("❌ كلمة مرور خاطئة. حاول مرة أخرى:")
        return AUTH_ADMIN

# --- ميزة إضافة أو تبديل معلومات القسم ---
async def manage_keys_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # عرض الأقسام الحالية من القاعدة
    buttons = [InlineKeyboardButton(f"تعديل {i}", callback_data=f"set_{i}") for i in MUX_SECTIONS.keys()]
    keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد (بيئة جديدة)", callback_data="set_new")])
    keyboard.append([InlineKeyboardButton("🏠 عودة", callback_data="back_home")])
    
    await query.edit_message_text("🔑 <b>إدارة مفاتيح الأقسام:</b>\nيمكنك تبديل بيانات قسم قديم أو إضافة بيئة جديدة.", 
                                  reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return SELECT_SET_SEC

async def input_id_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")[1]
    
    if data == "new":
        context.user_data['target_sec'] = str(len(MUX_SECTIONS) + 1)
    else:
        context.user_data['target_sec'] = data
        
    await query.edit_message_text(f"📍 تحديث بيانات القسم: {context.user_data['target_sec']}\nأرسل الآن **Access Token ID** الجديد:")
    return INPUT_ID

async def finalize_keys_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # حفظ البيانات في MongoDB
    new_secret = update.message.text
    s_id = context.user_data['target_sec']
    access_id = context.user_data['new_access_id']
    
    sections_col.update_one(
        {"section_id": s_id},
        {"$set": {"id": access_id, "secret": new_secret}},
        upsert=True
    )
    
    # تحديث الذاكرة الفورية
    global MUX_SECTIONS
    MUX_SECTIONS = load_mux_keys()
    
    await update.message.reply_text(f"✅ تم حفظ وتحديث بيانات القسم {s_id} في القاعدة بنجاح!")
    return await start(update, context)

# --- ميزة حذف الفيديوهات نهائياً ---
async def delete_vid_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    s_id = query.data.split("_")[1]
    creds = MUX_SECTIONS.get(s_id)
    context.user_data['del_sec'] = s_id
    
    await query.edit_message_text("⏳ جاري جلب قائمة الأفلام القابلة للحذف...")
    res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]))
    assets = res.json().get("data", [])
    
    if not assets:
        await query.edit_message_text("📁 هذا القسم فارغ حالياً.")
        return MENU
        
    keyboard = []
    for a in assets:
        title = a.get("passthrough", "فيلم بدون اسم")
        keyboard.append([InlineKeyboardButton(f"❌ حذف: {title}", callback_data=f"kill_{a['id']}")])
    keyboard.append([InlineKeyboardButton("🏠 إلغاء", callback_data="back_home")])
    
    await query.edit_message_text("⚠️ اختر الفيديو الذي تريد حذفه نهائياً من Mux:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_DEL_VID

# --- معالج الأزرار والرفع والمراجعة ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "nav_admin":
        if context.user_data.get('is_auth'):
            return await manage_keys_select(update, context)
        else:
            await query.edit_message_text("🔐 قسم الإدارة محمي. أرسل كلمة المرور (1460) للمتابعة:")
            return AUTH_ADMIN
            
    elif query.data == "admin_keys":
        return await manage_keys_select(update, context)
        
    elif query.data == "admin_del":
        buttons = [InlineKeyboardButton(f"القسم {i}", callback_data=f"dsec_{i}") for i in MUX_SECTIONS.keys()]
        keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        await query.edit_message_text("🗑️ اختر القسم الذي تريد حذف فيديوهات منه:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_DEL_SEC
        
    elif query.data == "back_home":
        return await start(update, context)

# --- تشغيل البوت ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MENU: [CallbackQueryHandler(menu_handler)],
            AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_handler)],
            SELECT_SET_SEC: [CallbackQueryHandler(input_id_step, pattern="^set_")],
            INPUT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: (c.user_data.update({'new_access_id': u.message.text}), u.message.reply_text("تم الاستلام. أرسل الآن Secret Key الجديد:"))[1])],
            INPUT_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalize_keys_save)],
            SELECT_DEL_SEC: [CallbackQueryHandler(delete_vid_list, pattern="^dsec_")],
            SELECT_DEL_VID: [CallbackQueryHandler(lambda u,c: requests.delete(f"https://api.mux.com/video/v1/assets/{u.callback_query.data.split('_')[1]}", auth=(MUX_SECTIONS[c.user_data['del_sec']]['id'], MUX_SECTIONS[c.user_data['del_sec']]['secret'])).status_code and u.callback_query.answer("✅ تم الحذف!", show_alert=True), pattern="^kill_")],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    app.add_handler(conv)
    print("Bot cinema-ps is ready on Koyeb...")
    app.run_polling()
