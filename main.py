import os
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ================== الإعدادات والجلب من البيئة ==================
MONGO_URL = os.getenv("MONGO_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = "1460" 

# ================== الاتصال بقاعدة البيانات ==================
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
dyn_col = db.dynamic_sections

def get_all_mux():
    """دمج الأقسام الثابتة مع الأقسام المضافة في MongoDB"""
    # الأقسام الثابتة الأساسية
    mux_sections = {
        "1": {"id": "2ab8ed37-b8af-4ffa-ab78-bc0910fcac6e", "secret": "zkX7I4isPxeMz6tFh20vFt37sNOWPpPgaMpH0u7i2dvavEMea84Wob8UfFvIVouNcfzjpIgt7jl"},
        "2": {"id": "3522203d-1925-4ec3-a5f7-9ca9efd1771a", "secret": "p7fHTPl4hFvLh1koWPHlJ7cif9GcOCFxDAYHIAraC4mcGABRrJWp2jNJ4B4cVgIcE2YOY+AT1wb"},
        # يمكنك إضافة بقية الـ 10 أقسام هنا بنفس النمط
    }
    # جلب الأقسام الإضافية من قاعدة البيانات
    for s in dyn_col.find().sort("section_id", 1):
        mux_sections[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return mux_sections

# ================== حالات المحادثة ==================
(MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, NAMING, LINKING, 
 SELECT_REV, SELECT_DEL, DEL_ID, ADD_SEC_ID, ADD_SEC_SECRET) = range(11)

# ================== الدوال الأساسية ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📤 رفع فيلم", callback_data="nav_up"),
         InlineKeyboardButton("🎬 مراجعة", callback_data="nav_rev")],
        [InlineKeyboardButton("📊 فحص السعة", callback_data="nav_stats")],
        [InlineKeyboardButton("⚙️ الإدارة", callback_data="nav_adm")]
    ]
    text = "🎬 <b>لوحة تحكم سينما بلاس</b>\n\nأهلاً بك! اختر المهمة المطلوبة:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return MENU

async def navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    sections = get_all_mux()

    if q.data == "nav_up":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in sections]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
        await q.edit_message_text("📤 اختر القسم للرفع:", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_UP

    if q.data == "nav_rev":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"rev_{i}") for i in sections]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
        kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
        await q.edit_message_text("🎬 اختر القسم للمراجعة:", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_REV

    if q.data == "nav_stats":
        await q.edit_message_text("⏳ جاري جلب تقارير السعة...")
        report = "📊 <b>تقرير الأقسام:</b>\n\n"
        for i, creds in sections.items():
            try:
                r = requests.get("https://api.mux.com/video/v1/assets?limit=1", auth=(creds["id"], creds["secret"]), timeout=5)
                count = r.json().get("total_row_count", 0)
                status = "🔴 ممتلئ" if count >= 98 else "🟢 متاح"
                report += f"📍 القسم {i}: <b>{count}/100</b> فيلم | {status}\n"
            except: report += f"📍 القسم {i}: ⚠️ خطأ اتصال\n"
        kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_home")]]
        await q.edit_message_text(report, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        return MENU

    if q.data == "nav_adm":
        if context.user_data.get("is_admin"): return await admin_home(update, context)
        await q.edit_message_text("🔐 أرسل كلمة المرور:")
        return AUTH_ADMIN

# ================== منطق الرفع والمراجعة ==================

async def start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sec"] = update.callback_query.data.split("_")[1]
    await update.callback_query.edit_message_text("✏️ أرسل <b>اسم الفيلم</b>:")
    return NAMING

async def upload_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🔗 أرسل <b>رابط الفيديو المباشر</b>:")
    return LINKING

async def upload_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sec = context.user_data["sec"]
    creds = get_all_mux().get(sec)
    msg = await update.message.reply_text("⏳ جاري الرفع...")
    
    r = requests.post(
        "https://api.mux.com/video/v1/assets",
        json={"input": update.message.text, "playback_policy": ["public"], "passthrough": context.user_data["name"]},
        auth=(creds["id"], creds["secret"])
    )
    if r.status_code == 201:
        pid = r.json()["data"]["playback_ids"][0]["id"]
        await msg.edit_text(f"✅ تم الرفع!\nالـ ID: <code>{pid}</code>", parse_mode=ParseMode.HTML)
    else: await msg.edit_text("❌ فشل الرفع.")
    return await start(update, context)

async def review_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    sec = q.data.split("_")[1]
    creds = get_all_mux().get(sec)
    r = requests.get("https://api.mux.com/video/v1/assets?limit=10", auth=(creds["id"], creds["secret"]))
    assets = r.json().get("data", [])
    text = f"🎬 <b>أفلام القسم {sec}:</b>\n\n"
    for a in assets:
        text += f"• {a.get('passthrough','بدون اسم')}\nAsset ID: <code>{a['id']}</code>\n\n"
    kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="nav_rev")]]
    await q.edit_message_text(text or "القسم فارغ", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return MENU

# ================== قسم الإدارة (إضافة وحذف) ==================

async def admin_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete() # حذف الباسورد فوراً للخصوصية
    if update.message.text == ADMIN_PASSWORD:
        context.user_data["is_admin"] = True
        return await admin_home(update, context)
    await update.message.reply_text("❌ كلمة مرور خاطئة")
    return MENU

async def admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("➕ إضافة قسم", callback_data="adm_add")],
          [InlineKeyboardButton("🗑 حذف فيلم", callback_data="adm_del")],
          [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_home")]]
    text = "⚙️ <b>إعدادات الإدارة</b>"
    if update.callback_query: await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return ADMIN_HOME

async def add_sec_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("🆕 أرسل Mux Access Token ID:")
    return ADD_SEC_ID

async def add_sec_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_id"] = update.message.text
    await update.message.reply_text("🔑 أرسل Mux Secret Key:")
    return ADD_SEC_SECRET

async def add_sec_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_num = len(get_all_mux()) + 1
    dyn_col.insert_one({"section_id": new_num, "id": context.user_data["new_id"], "secret": update.message.text})
    await update.message.reply_text(f"✅ تم تفعيل القسم {new_num}")
    return await admin_home(update, context)

async def delete_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"del_{i}") for i in get_all_mux()]
    kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
    await update.callback_query.edit_message_text("🗑 اختر القسم للحذف منه:", reply_markup=InlineKeyboardMarkup(kb))
    return SELECT_DEL

async def delete_ask_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["del_sec"] = update.callback_query.data.split("_")[1]
    await update.callback_query.edit_message_text("🆔 أرسل Asset ID الخاص بالفيلم:")
    return DEL_ID

async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    creds = get_all_mux().get(context.user_data["del_sec"])
    r = requests.delete(f"https://api.mux.com/video/v1/assets/{update.message.text}", auth=(creds["id"], creds["secret"]))
    await update.message.reply_text("✅ تم الحذف" if r.status_code == 204 else "❌ فشل الحذف")
    return await start(update, context)

# ================== تشغيل المحرك ==================
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
        ADMIN_HOME: [CallbackQueryHandler(delete_select, pattern="adm_del"), CallbackQueryHandler(add_sec_start, pattern="adm_add")],
        SELECT_DEL: [CallbackQueryHandler(delete_ask_id, pattern="del_")],
        DEL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_confirm)],
        ADD_SEC_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sec_id)],
        ADD_SEC_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sec_final)],
    },
    fallbacks=[CommandHandler("start", start)],
    allow_reentry=True
)
app.add_handler(conv_handler)
app.run_polling()
