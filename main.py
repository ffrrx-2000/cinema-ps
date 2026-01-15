import os
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ================== الإعدادات الأساسية ==================
MONGO_URL = os.getenv("MONGO_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = "1460" 

# ================== الاتصال بقاعدة البيانات ==================
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
dyn_col = db.dynamic_sections

def get_all_mux():
    """جلب كل الأقسام الثابتة والديناميكية"""
    mux_sections = {
        "1": {"id": "2ab8ed37-b8af-4ffa-ab78-bc0910fcac6e", "secret": "zkX7I4isPxeMz6tFh20vFt37sNOWPpPgaMpH0u7i2dvavEMea84Wob8UfFvIVouNcfzjpIgt7jl"},
        "2": {"id": "3522203d-1925-4ec3-a5f7-9ca9efd1771a", "secret": "p7fHTPl4hFvLh1koWPHlJ7cif9GcOCFxDAYHIAraC4mcGABRrJWp2jNJ4B4cVgIcE2YOY+AT1wb"},
        # يمكنك إضافة بقية الأقسام الثابتة هنا...
    }
    # جلب الأقسام الإضافية من MongoDB
    for s in dyn_col.find().sort("section_id", 1):
        mux_sections[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return mux_sections

# ================== تعريف حالات المحادثة ==================
(MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, NAMING, LINKING, 
 SELECT_REV, SELECT_DEL, DEL_ID, ADD_SEC_ID, ADD_SEC_SECRET) = range(11)

# ================== الدالة الرئيسية (البداية) ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📤 رفع فيلم جديد", callback_data="nav_up"),
         InlineKeyboardButton("🎬 مراجعة الأفلام", callback_data="nav_rev")],
        [InlineKeyboardButton("📊 فحص سعة الأقسام", callback_data="nav_stats")],
        [InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="nav_adm")]
    ]
    text = "🎬 <b>لوحة تحكم سينما بلاس (الإصدار الاحترافي)</b>\n\nيرجى اختيار القسم المطلوب من الأزرار أدناه:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return MENU

# ================== نظام التنقل ==================
async def navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    sections = get_all_mux()

    if q.data == "nav_up":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in sections]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
        await q.edit_message_text("📤 اختر القسم المراد الرفع إليه:", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_UP

    if q.data == "nav_rev":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"rev_{i}") for i in sections]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
        await q.edit_message_text("🎬 اختر القسم لمراجعة المحتوى:", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_REV

    if q.data == "nav_stats":
        await q.edit_message_text("⏳ جاري جلب البيانات من السيرفر...")
        report = "📊 <b>تقرير السعة والاستهلاك:</b>\n\n"
        for i, creds in sections.items():
            try:
                r = requests.get("https://api.mux.com/video/v1/assets?limit=1", auth=(creds["id"], creds["secret"]), timeout=5)
                count = r.json().get("total_row_count", 0)
                status = "🔴 ممتلئ" if count >= 95 else "🟢 متاح"
                report += f"📍 القسم {i}: <b>{count}</b> فيلم | {status}\n"
            except:
                report += f"📍 القسم {i}: ⚠️ خطأ في الاتصال\n"
        
        kb = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_home")]]
        await q.edit_message_text(report, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        return MENU

    if q.data == "nav_adm":
        if context.user_data.get("is_admin"):
            return await admin_home(update, context)
        await q.edit_message_text("🔐 أرسل كلمة المرور للدخول لقسم الإدارة:")
        return AUTH_ADMIN

# ================== رفع الأفلام ==================
async def start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sec"] = update.callback_query.data.split("_")[1]
    await update.callback_query.edit_message_text("✏️ حسناً، أرسل الآن <b>اسم الفيلم</b>:")
    return NAMING

async def upload_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🔗 ممتاز، الآن أرسل <b>رابط الفيديو (Direct Link)</b>:")
    return LINKING

async def upload_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sec = context.user_data["sec"]
    creds = get_all_mux().get(sec)
    
    msg = await update.message.reply_text("⏳ جاري الرفع إلى Mux...")
    
    r = requests.post(
        "https://api.mux.com/video/v1/assets",
        json={"input": update.message.text, "playback_policy": ["public"], "passthrough": context.user_data["name"]},
        auth=(creds["id"], creds["secret"])
    )

    if r.status_code == 201:
        pid = r.json()["data"]["playback_ids"][0]["id"]
        await msg.edit_text(f"✅ تم الرفع بنجاح!\nمعرف التشغيل: <code>{pid}</code>", parse_mode=ParseMode.HTML)
    else:
        await msg.edit_text("❌ فشل الرفع. تأكد من صحة الرابط أو مفاتيح القسم.")
    
    return await start(update, context)

# ================== مراجعة وحذف الفيديوهات ==================
async def review_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    sec = q.data.split("_")[1]
    creds = get_all_mux().get(sec)
    
    r = requests.get("https://api.mux.com/video/v1/assets?limit=8", auth=(creds["id"], creds["secret"]))
    assets = r.json().get("data", [])
    
    text = f"🎬 <b>أفلام القسم {sec}:</b>\n\n"
    if not assets:
        text += "هذا القسم فارغ حالياً."
    else:
        for a in assets:
            text += f"• {a.get('passthrough', 'بدون اسم')}\nID: <code>{a['id']}</code>\n\n"

    kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="nav_rev")]]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return MENU

# ================== قسم الإدارة ==================
async def admin_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # إخفاء كلمة السر فور إرسالها
    await update.message.delete()
    if update.message.text == ADMIN_PASSWORD:
        context.user_data["is_admin"] = True
        return await admin_home(update, context)
    await update.message.reply_text("❌ كلمة مرور خاطئة!")
    return MENU

async def admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="adm_add")],
        [InlineKeyboardButton("🗑 حذف فيديو نهائياً", callback_data="adm_del")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_home")]
    ]
    text = "⚙️ <b>لوحة تحكم المدير</b>\n\nيمكنك إضافة أقسام جديدة أو حذف ملفات من سيرفر Mux."
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return ADMIN_HOME

# إضافة قسم جديد
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
    new_num = len(get_all_mux()) + 1
    dyn_col.insert_one({"section_id": new_num, "id": token_id, "secret": secret})
    await update.message.reply_text(f"✅ تم تفعيل القسم رقم {new_num} بنجاح!")
    return await admin_home(update, context)

# حذف فيديو
async def delete_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sections = get_all_mux()
    btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"del_{i}") for i in sections]
    kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
    await update.callback_query.edit_message_text("🗑 اختر القسم الذي تريد حذف فيلم منه:", reply_markup=InlineKeyboardMarkup(kb))
    return SELECT_DEL

async def delete_ask_pid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["del_sec"] = update.callback_query.data.split("_")[1]
    await update.callback_query.edit_message_text("🆔 أرسل Asset ID الخاص بالفيلم لحذفه:")
    return DEL_ID

async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    asset_id = update.message.text
    creds = get_all_mux().get(context.user_data["del_sec"])
    r = requests.delete(f"https://api.mux.com/video/v1/assets/{asset_id}", auth=(creds["id"], creds["secret"]))
    
    if r.status_code == 204:
        await update.message.reply_text("✅ تم حذف الفيديو بنجاح من سيرفر Mux.")
    else:
        await update.message.reply_text("❌ لم يتم العثور على الفيديو أو حدث خطأ.")
    return await start(update, context)

# ================== تشغيل البوت ==================
app = ApplicationBuilder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start), CallbackQueryHandler(start, pattern="back_home")],
    states={
        MENU: [CallbackQueryHandler(navigate, pattern="nav_")],
        SELECT_UP: [CallbackQueryHandler(start_upload, pattern="up_")],
        NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_name)],
        LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_video)],
        SELECT_REV: [CallbackQueryHandler(review_assets, pattern="rev_")],
        AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_auth)],
        ADMIN_HOME: [
            CallbackQueryHandler(delete_select, pattern="adm_del"),
            CallbackQueryHandler(add_sec_start, pattern="adm_add"),
            CallbackQueryHandler(start, pattern="back_home")
        ],
        SELECT_DEL: [CallbackQueryHandler(delete_ask_pid, pattern="del_")],
        DEL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_confirm)],
        ADD_SEC_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sec_id)],
        ADD_SEC_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sec_final)],
    },
    fallbacks=[CommandHandler("start", start)],
    allow_reentry=True
)

app.add_handler(conv_handler)
print("🚀 البوت يعمل الآن بنجاح...")
app.run_polling()
