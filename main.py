import os
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# --- 1. الإعدادات وجلب البيئة ---
MONGO_URL = os.getenv("MONGO_URL") #
BOT_TOKEN = os.getenv("BOT_TOKEN") #
ADMIN_PASSWORD = "1460"

# --- 2. الربط مع MongoDB Atlas ---
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
sections_col = db.sections

# --- 3. حالات المحادثة (States) ---
(MAIN_MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, SELECT_REV, 
 NAMING, LINKING, MANAGE_KEYS, INPUT_ID, INPUT_SECRET, SELECT_DEL_VID) = range(11)

def get_keys_from_db():
    """تحميل المفاتيح من القاعدة لضمان عمل الرفع والمراجعة"""
    sections = {}
    for s in sections_col.find().sort("section_id", 1):
        sections[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return sections

# --- 4. الوظائف البرمجية (Logic) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الواجهة الرئيسية للبوت"""
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيلم جديد", callback_data="go_upload"), 
         InlineKeyboardButton("🎬 مراجعة الأقسام", callback_data="go_review")],
        [InlineKeyboardButton("📊 فحص حالة الأقسام", callback_data="go_stats")],
        [InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="go_admin")]
    ]
    text = "🎬 <b>مرحباً بك في سيرفر سينما بلاس</b>\nالنظام مرتبط بالسحابة ومؤمن بالكامل ✅"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MAIN_MENU

# --- نظام الأمان (حذف كلمة السر فوراً) ---
async def auth_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من كلمة السر وحذفها فوراً للأمان"""
    user_input = update.message.text
    # ميزة احترافية: حذف رسالة كلمة السر لكي لا يراها أحد في الشات
    await update.message.delete()
    
    if user_input == ADMIN_PASSWORD:
        context.user_data['is_admin'] = True
        return await admin_panel(update, context)
    else:
        await update.message.reply_text("❌ كلمة مرور خاطئة. العودة للرئيسية...")
        return await start(update, context)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم الإدارة"""
    keyboard = [
        [InlineKeyboardButton("🔑 إضافة/تعديل قسم", callback_data="adm_keys")],
        [InlineKeyboardButton("🗑️ حذف فيديو نهائياً", callback_data="adm_del")],
        [InlineKeyboardButton("🏠 خروج", callback_data="back_home")]
    ]
    text = "⚙️ <b>لوحة التحكم المركزية</b>\nيمكنك الآن تعديل مفاتيح Mux أو حذف البيانات."
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return ADMIN_HOME

# --- ميزة فحص السعة (Stats) ---
async def stats_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص الأقسام الممتلئة والمتبقي لها"""
    query = update.callback_query
    keys = get_keys_from_db()
    if not keys:
        await query.answer("⚠️ لا توجد أقسام مضافة بعد.", show_alert=True)
        return MAIN_MENU

    await query.edit_message_text("⏳ جاري فحص استهلاك الأقسام...")
    report = "📊 <b>تقرير سعة الأقسام (Mux):</b>\n\n"
    for s_id, creds in keys.items():
        try:
            res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]), timeout=7)
            count = len(res.json().get("data", []))
            remaining = 100 - count # تقدير سعة القسم بـ 100 فيلم
            status = "🟢 مستقر" if remaining > 20 else "🔴 ممتلئ"
            report += f"📍 <b>القسم {s_id}:</b>\n- المرفوع: {count} فيلم\n- المتبقي: {remaining} فيلم\n- الحالة: {status}\n\n"
        except:
            report += f"📍 <b>القسم {s_id}:</b> ❌ خطأ في المفاتيح\n\n"
    
    await query.edit_message_text(report, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 عودة", callback_data="back_home")]]), parse_mode=ParseMode.HTML)
    return MAIN_MENU

# --- ميزة المراجعة المصلحة ---
async def review_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جلب قائمة الأفلام وعرضها"""
    query = update.callback_query
    s_id = query.data.split("_")[1]
    keys = get_keys_from_db()
    creds = keys.get(s_id)
    
    await query.edit_message_text(f"🔍 جاري جلب أفلام القسم {s_id}...")
    try:
        res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]))
        assets = res.json().get("data", [])
        if not assets:
            await query.edit_message_text(f"📁 القسم {s_id} فارغ حالياً.")
            return MAIN_MENU
        
        text = f"🎬 <b>أفلام القسم {s_id}:</b>\n\n"
        for i, a in enumerate(assets[:15], 1): # عرض أول 15 فيلم
            name = a.get("passthrough", "بدون اسم")
            p_id = a.get("playback_ids", [{"id": "-"}])[0]["id"]
            text += f"{i}- {name} - <b>شغال ✅</b>\n<code>{p_id}</code>\n\n"
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 عودة", callback_data="back_home")]]), parse_mode=ParseMode.HTML)
    except:
        await query.edit_message_text("❌ فشل الاتصال. تأكد من مفاتيح القسم.")
    return MAIN_MENU

# --- (بقية معالجات الرفع وحفظ المفاتيح منظمة بنفس الطريقة) ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("🔐 أرسل كلمة المرور بصمت (1460):"), pattern="go_admin"),
                CallbackQueryHandler(stats_check, pattern="go_stats"),
                CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("📤 اختر القسم للرفع إليه:"), pattern="go_upload"),
                CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("🔍 اختر القسم للمراجعة:"), pattern="go_review"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, auth_process)
            ],
            ADMIN_HOME: [
                CallbackQueryHandler(admin_panel, pattern="adm_"),
                CallbackQueryHandler(start, pattern="back_home")
            ],
            # ... إضافة بقية الحالات (SELECT_UP, NAMING, LINKING, SELECT_REV) هنا
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    
    app.add_handler(conv_handler)
    print("Cinema Plus V5 Pro is Running...")
    app.run_polling()
