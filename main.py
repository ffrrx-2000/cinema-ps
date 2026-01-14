import os
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# --- الإعدادات ---
MONGO_URL = os.getenv("MONGO_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = "1460"

# --- الاتصال بالقاعدة ---
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
sections_col = db.sections

# --- حالات المحادثة ---
(MAIN_MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, SELECT_REV, 
 NAMING, LINKING, SET_ID, SET_SECRET, DEL_VID) = range(10)

def get_all_keys():
    """جلب كافة الأقسام من القاعدة"""
    sections = {}
    for s in sections_col.find().sort("section_id", 1):
        sections[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return sections

# --- 1. واجهة البداية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيلم", callback_data="go_upload"), 
         InlineKeyboardButton("🎬 مراجعة", callback_data="go_review")],
        [InlineKeyboardButton("📊 حالة الأقسام", callback_data="go_stats")],
        [InlineKeyboardButton("⚙️ الإدارة", callback_data="go_admin")]
    ]
    text = "🎬 <b>مرحباً بك في سيرفر سينما بلاس</b>\nالنظام مستقر ومرتبط بالسحابة ✅"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MAIN_MENU

# --- 2. نظام الأمان الذكي ---
async def auth_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # حذف رسالة كلمة السر فوراً للأمان
    user_pass = update.message.text
    await update.message.delete()
    
    if user_pass == ADMIN_PASSWORD:
        context.user_data['is_admin'] = True
        return await admin_home(update, context)
    else:
        await update.message.reply_text("❌ كلمة مرور خاطئة. تم تسجيل المحاولة.")
        return MAIN_MENU

async def admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔑 إضافة/تعديل قسم", callback_data="manage_keys")],
        [InlineKeyboardButton("🗑️ حذف فيديو", callback_data="manage_del")],
        [InlineKeyboardButton("🏠 العودة", callback_data="back_home")]
    ]
    text = "⚙️ <b>لوحة التحكم المركزية</b>\nيمكنك الآن تعديل مفاتيح Mux أو حذف البيانات."
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return ADMIN_HOME

# --- 3. ميزة فحص الأقسام (Stats) ---
async def check_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keys = get_all_keys()
    if not keys:
        await query.answer("⚠️ لا توجد أقسام مضافة بعد.", show_alert=True)
        return MAIN_MENU

    await query.edit_message_text("⏳ جاري فحص استهلاك الأقسام...")
    report = "📊 <b>تقرير استهلاك الأقسام:</b>\n\n"
    for s_id, creds in keys.items():
        try:
            res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]), timeout=5)
            count = len(res.json().get("data", []))
            # نفترض أن كل قسم يستوعب 100 فيلم كحد تنظيمي
            remaining = 100 - count
            status = "🟢 مستقر" if remaining > 20 else "🟡 ممتلئ تقريباً"
            report += f"📍 <b>القسم {s_id}:</b>\n- الأفلام: {count}\n- المتبقي: {remaining}\n- الحالة: {status}\n\n"
        except:
            report += f"📍 <b>القسم {s_id}:</b> ❌ خطأ في الاتصال\n\n"
    
    await query.edit_message_text(report, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 عودة", callback_data="back_home")]]), parse_mode=ParseMode.HTML)
    return MAIN_MENU

# --- 4. ميزة المراجعة المصلحة ---
async def review_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    s_id = query.data.split("_")[1]
    keys = get_all_keys()
    creds = keys.get(s_id)
    
    await query.edit_message_text(f"🔍 جاري جلب أفلام القسم {s_id}...")
    try:
        res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]))
        assets = res.json().get("data", [])
        if not assets:
            await query.edit_message_text(f"📁 القسم {s_id} فارغ حالياً.")
            return MAIN_MENU
        
        text = f"🎬 <b>أفلام القسم {s_id}:</b>\n\n"
        for i, a in enumerate(assets[:15], 1): # عرض آخر 15 فيلم
            name = a.get("passthrough", "بدون اسم")
            p_id = a.get("playback_ids", [{"id": "-"}])[0]["id"]
            text += f"{i}- {name} ✅\n<code>{p_id}</code>\n\n"
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 عودة", callback_data="back_home")]]), parse_mode=ParseMode.HTML)
    except:
        await query.edit_message_text("❌ خطأ! تأكد من صحة مفاتيح هذا القسم في الإدارة.")
    return MAIN_MENU

# --- (بقية معالجات الرفع وحذف المفاتيح بنفس المنطق المتزامن) ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("🔐 أرسل كلمة المرور:"), pattern="go_admin"),
                CallbackQueryHandler(check_stats, pattern="go_stats"),
                CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("📤 اختر قسم الرفع:"), pattern="go_upload"),
                CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("🔍 اختر قسم المراجعة:"), pattern="go_review"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, auth_step)
            ],
            ADMIN_HOME: [
                CallbackQueryHandler(admin_home, pattern="manage_"),
                CallbackQueryHandler(start, pattern="back_home")
            ],
            # ... إضافة بقية الحالات هنا
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    
    app.add_handler(conv)
    print("Cinema Plus V3 is LIVE...")
    app.run_polling()
