import os
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ================== الإعدادات ==================
MONGO_URL = os.getenv("MONGO_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = "1460" 

# ================== MongoDB ==================
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
dyn_col = db.dynamic_sections

# دالة لجلب كل الأقسام (الثابتة + الديناميكية)
def get_all_mux():
    # الأقسام الأساسية (يمكنك نقلها لـ MongoDB لاحقاً لزيادة الأمان)
    mux_sections = {
        "1": {"id": "2ab8ed37-b8af-4ffa-ab78-bc0910fcac6e", "secret": "zkX7I4isPxeMz6tFh20vFt37sNOWPpPgaMpH0u7i2dvavEMea84Wob8UfFvIVouNcfzjpIgt7jl"},
        # ... بقية الأقسام الثابتة تضاف هنا بنفس النمط
    }
    for s in dyn_col.find().sort("section_id", 1):
        mux_sections[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return mux_sections

# ================== الحالات ==================
(MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, NAMING, LINKING, 
 SELECT_REV, SELECT_DEL, DEL_ID, ADD_SEC_ID, ADD_SEC_SECRET) = range(11)

# ================== الوظائف الأساسية ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📤 رفع فيلم", callback_data="nav_up"),
         InlineKeyboardButton("🎬 مراجعة", callback_data="nav_rev")],
        [InlineKeyboardButton("📊 فحص السعة", callback_data="nav_stats")],
        [InlineKeyboardButton("⚙️ الإدارة", callback_data="nav_adm")]
    ]
    text = "🎬 <b>أهلاً بك في لوحة تحكم سينما بلاس</b>\n\nاختر من القائمة أدناه لإدارة المحتوى:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return MENU

async def navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "nav_up":
        sections = get_all_mux()
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in sections]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
        await q.edit_message_text("📤 اختر القسم المراد الرفع إليه:", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_UP

    if q.data == "nav_rev":
        sections = get_all_mux()
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"rev_{i}") for i in sections]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
        await q.edit_message_text("🎬 اختر القسم لمراجعة آخر الأفلام:", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_REV

    if q.data == "nav_stats":
        await q.edit_message_text("⏳ جاري فحص السعة، يرجى الانتظار...")
        sections = get_all_mux()
        report = "📊 <b>تقرير حالة الأقسام:</b>\n\n"
        for i, creds in sections.items():
            r = requests.get("https://api.mux.com/video/v1/assets?limit=1", auth=(creds["id"], creds["secret"]))
            count = r.json().get("total_row_count", 0) if r.status_code == 200 else "⚠️ خطأ"
            status = "🔴 ممتلئ" if isinstance(count, int) and count >= 95 else "🟢 متاح"
            report += f"📍 القسم {i}: ({count}/100) فيلم | {status}\n"
        
        kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_home")]]
        await q.edit_message_text(report, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        return MENU

    if q.data == "nav_adm":
        if context.user_data.get("is_admin"):
            return await admin_home(update, context)
        await q.edit_message_text("🔐 أرسل كلمة المرور الخاصة بالإدارة:")
        return AUTH_ADMIN

# ================== نظام المراجعة المطور ==================
async def review_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    sec = q.data.split("_")[1]
    creds = get_all_mux().get(sec)
    
    r = requests.get("https://api.mux.com/video/v1/assets?limit=10", auth=(creds["id"], creds["secret"]))
    
    if r.status_code != 200:
        await q.edit_message_text("❌ فشل الاتصال بـ Mux")
        return MENU

    assets = r.json().get("data", [])
    text = f"🎬 <b>آخر 10 أفلام في القسم {sec}:</b>\n\n"
    
    if not assets:
        text += "لا توجد أفلام في هذا القسم حالياً."
    else:
        for a in assets:
            name = a.get('passthrough', 'غير مسمى')
            status = "✅ جاهز" if a.get('status') == 'ready' else "⏳ معالجة"
            text += f"• <b>{name}</b> | {status}\n<code>{a['id']}</code>\n\n"

    kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="nav_rev")]]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return MENU

# ================== إدارة الأقسام والإدارة ==================
async def admin_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    # 🌟 ميزة احترافية: حذف رسالة كلمة السر فوراً
    await update.message.delete()
    
    if password == ADMIN_PASSWORD:
        context.user_data["is_admin"] = True
        return await admin_home(update, context)
    
    await update.message.reply_text("❌ كلمة مرور خاطئة. تم رفض الدخول.")
    return MENU

async def admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="adm_add")],
        [InlineKeyboardButton("🗑 حذف فيديو (Asset ID)", callback_data="adm_del")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_home")]
    ]
    text = "⚙️ <b>لوحة تحكم المدير</b>\n\nتنبيه: حذف الفيديو نهائي ولا يمكن التراجع عنه."
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return ADMIN_HOME

# إضافة قسم جديد (حل مشكلة النقص)
async def add_sec_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("🆕 أرسل Mux Access Token ID:")
    return ADD_SEC_ID

async def add_sec_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_id"] = update.message.text
    await update.message.reply_text("🔑 الآن أرسل Mux Secret Key:")
    return ADD_SEC_SECRET

async def add_sec_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secret = update.message.text
    token_id = context.user_data["new_id"]
    
    # حساب رقم القسم الجديد تلقائياً
    current_count = len(get_all_mux())
    dyn_col.insert_one({
        "section_id": current_count + 1,
        "id": token_id,
        "secret": secret
    })
    
    await update.message.reply_text(f"✅ تم إضافة القسم رقم {current_count + 1} بنجاح!")
    return await admin_home(update, context)

# ================== تشغيل المحرك ==================
app = ApplicationBuilder().token(BOT_TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start), CallbackQueryHandler(start, pattern="back_home")],
    states={
        MENU: [CallbackQueryHandler(navigate, pattern="nav_")],
        SELECT_UP: [CallbackQueryHandler(start_upload, pattern="up_")], # نفس وظيفتك السابقة
        NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_name)],
        LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_video)],
        SELECT_REV: [CallbackQueryHandler(review_assets, pattern="rev_")],
        AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_auth)],
        ADMIN_HOME: [
            CallbackQueryHandler(delete_select, pattern="adm_del"),
            CallbackQueryHandler(add_sec_start, pattern="adm_add")
        ],
        SELECT_DEL: [CallbackQueryHandler(delete_ask_pid, pattern="del_")],
        DEL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_confirm)],
        ADD_SEC_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sec_id)],
        ADD_SEC_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sec_final)],
    },
    fallbacks=[CommandHandler("start", start)],
    allow_reentry=True
)

app.add_handler(conv)
app.run_polling()
