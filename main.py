import os
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# --- 1. الإعدادات وجلب المتغيرات من Koyeb ---
MONGO_URL = os.getenv("MONGO_URL") #
BOT_TOKEN = os.getenv("BOT_TOKEN") #
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1460")

# --- 2. الأقسام الثابتة (لا تقم بحذفها) ---
FIXED_SECTIONS = {
    "1": {"id": "YOUR_FIXED_ID_1", "secret": "YOUR_FIXED_SECRET_1"},
    "2": {"id": "YOUR_FIXED_ID_2", "secret": "YOUR_FIXED_SECRET_2"},
    # أضف بقية أقسامك القديمة هنا بنفس التنسيق
}

# --- 3. الاتصال بقاعدة البيانات للأقسام الديناميكية ---
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
dynamic_sections_col = db.dynamic_sections

# --- 4. دالة الدمج الموحدة (أهم جزء) ---
def get_all_active_sections():
    """تدمج الأقسام الثابتة مع الديناميكية من MongoDB في مصدر واحد"""
    all_sections = FIXED_SECTIONS.copy()
    # جلب الأقسام المضافة عبر البوت من القاعدة
    db_sections = dynamic_sections_col.find().sort("section_id", 1)
    for s in db_sections:
        all_sections[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return all_sections

# --- 5. حالات المحادثة ---
(MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, SELECT_REV, 
 NAMING, LINKING, ADD_SEC_ID, ADD_SEC_SECRET) = range(9)

# --- 6. الوظائف البرمجية ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيلم", callback_data="nav_upload"), 
         InlineKeyboardButton("🎬 مراجعة", callback_data="nav_review")],
        [InlineKeyboardButton("⚙️ الإدارة", callback_data="nav_admin")]
    ]
    text = "🎬 <b>سيرفر سينما بلاس - النظام الموحد</b>\nتم دمج الأقسام الثابتة والديناميكية ✅"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MENU

async def admin_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تأمين الإدارة وحذف كلمة السر فوراً"""
    user_pass = update.message.text
    await update.message.delete() # حذف كلمة السر للأمان
    
    if user_pass == ADMIN_PASSWORD:
        context.user_data['is_admin'] = True
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قسم ديناميكي", callback_data="add_dyn_sec")],
            [InlineKeyboardButton("🏠 العودة", callback_data="back_home")]
        ]
        await update.message.reply_text("⚙️ <b>لوحة التحكم بالبيانات</b>\nيمكنك الآن إضافة أقسام جديدة للقاعدة.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return ADMIN_HOME
    else:
        await update.message.reply_text("❌ كلمة مرور خاطئة.")
        return MENU

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    all_mux = get_all_active_sections() # جلب المصدر الموحد

    if query.data == "nav_upload":
        buttons = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in all_mux.keys()]
        keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        await query.edit_message_text("📤 اختر القسم (ثابت أو ديناميكي):", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_UP

    elif query.data == "nav_review":
        buttons = [InlineKeyboardButton(f"مراجعة {i}", callback_data=f"rev_{i}") for i in all_mux.keys()]
        keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        await query.edit_message_text("🔍 مراجعة أفلام الأقسام الموحدة:", reply_markup=InlineKeyboardMarkup(keyboard))
        return SELECT_REV

    elif query.data == "nav_admin":
        await query.edit_message_text("🔐 أرسل كلمة المرور لفتح الإدارة:")
        return AUTH_ADMIN

# --- إضافة قسم جديد لقاعدة البيانات ---
async def start_add_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    all_mux = get_all_active_sections()
    # تحديد الرقم التالي تلقائياً
    next_id = str(max([int(k) for k in all_mux.keys()]) + 1)
    context.user_data['new_sec_num'] = next_id
    await query.edit_message_text(f"📍 سيتم إضافة القسم رقم {next_id}\nأرسل الآن **Access Token ID**:")
    return ADD_SEC_ID

async def save_new_sec_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secret = update.message.text
    new_id = context.user_data['temp_acc_id']
    sec_num = context.user_data['new_sec_num']
    
    # حفظ في MongoDB لضمان الاستمرارية
    dynamic_sections_col.update_one(
        {"section_id": sec_num},
        {"$set": {"id": new_id, "secret": secret}},
        upsert=True
    )
    await update.message.reply_text(f"✅ تم حفظ القسم {sec_num} في السحابة بنجاح!")
    return await start(update, context)

# --- (بقية منطق الرفع والمراجعة يعمل تلقائياً مع all_mux) ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MENU: [CallbackQueryHandler(handle_navigation, pattern="nav_")],
            AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_auth)],
            ADMIN_HOME: [CallbackQueryHandler(start_add_sec, pattern="add_dyn_sec")],
            ADD_SEC_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: (c.user_data.update({'temp_acc_id': u.message.text}), u.message.reply_text("أرسل Secret Key:"))[1])],
            ADD_SEC_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_key_final)],
            # أضف هنا حالات الرفع والمراجعة القديمة الخاصة بك
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    
    app.add_handler(conv_handler)
    print("Cinema Plus Unified System is Running...")
    app.run_polling()
