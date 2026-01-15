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

# ================== الأقسام الثابتة (كما هي) ==================
MUX_SECTIONS_FIXED = {
    str(i): {"id": id_val, "secret": secret_val}
    for i, (id_val, secret_val) in enumerate([
        ("2ab8ed37-b8af-4ffa-ab78-bc0910fcac6e", "zkX7I4isPxeMz6tFh20vFt37sNOWPpPgaMpH0u7i2dvavEMea84Wob8UfFvIVouNcfzjpIgt7jl"),
        ("3522203d-1925-4ec3-a5f7-9ca9efd1771a", "p7fHTPl4hFvLh1koWPHlJ7cif9GcOCFxDAYHIAraC4mcGABRrJWp2jNJ4B4cVgIcE2YOY+AT1wb"),
        ("85501be0-bc4f-415c-afde-b8ac1b996974", "QXzmzVANcX9VrS2vBCTa0h91+QAlr7iM5izLDrzKUDdhSx2sJx2CuNFT6CJHpqOsftsW2MICpci"),
        ("7894140e-03a9-4946-9698-1b58f1e3ea38", "HwgZg1a7h05ul/AYpeICooOp0fOt4o7W9Fxf0am2z4Qb1QyHfIL3BRMjxh1e6b1Dn+WXehKdjaN"),
        ("147d1438-4269-4739-ae68-7dcbdf9f1d84", "6cqf9LKM38Q7gbkrrYmWGNwH0v27UjY8DzQWRDZ1Md137UE7+n52NlBGIVc/4qaShADTH5D+LsU"),
        ("60d38bcd-bb17-4db0-9599-129c232cdabf", "E9j1AbbGropItPcS4K+Gl1csebAiLMJJuglGn9NxIasbJAmM/CsVXTL9BCyw+jBwsR7Zq51RJy2"),
        ("31517bbe-2628-438e-b7ac-261708d6f26e", "pnHQhp05xWhu6tSc8u98c3x47ycmT7zhW3V6mzxlSmqz30vac71VmsHYgRUBI5aDuBFYBIlkcF4"),
        ("4c53f771-ab87-4dab-9484-2f7f94799f6e", "rWXTB3ktFkyvcKQkJwD6tcOT+6sV1dM3ndU/H4oZu5qnG6/+2WIw4keq2DPFU+F0foJ57eI0BPz"),
        ("0f39d0e7-33d9-4983-a20d-c20a54a39d19", "GG2UNHGjJysTBxe32+VOGEOpLGSEUGINWVvEFyhz+inbm+G41LNi/Hua8Kd9pqeRO+FOLyLgk5/"),
        ("fcbfcdcb-fbd3-41ae-ab10-5451502ac8d3", "NtwphUQyZZsrhOXgadrZN3QoJXxMVW2za+q0xFe/1vLl4PfRjrGCOn18BOqpGFMCFZAc/g2rR0R")
    ], 1)
}

# ================== MongoDB ==================
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
dyn_col = db.dynamic_sections

def get_all_mux():
    all_mux = MUX_SECTIONS_FIXED.copy()
    for s in dyn_col.find().sort("section_id", 1):
        all_mux[str(s["section_id"])] = {
            "id": s["id"],
            "secret": s["secret"]
        }
    return all_mux

# ================== الحالات ==================
(
    MENU, AUTH_ADMIN, ADMIN_HOME,
    SELECT_UP, NAMING, LINKING,
    SELECT_REV, SELECT_DEL, DEL_PID,
    ADD_SEC_ID, ADD_SEC_SECRET
) = range(11)

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📤 رفع فيلم", callback_data="nav_up"),
         InlineKeyboardButton("🎬 مراجعة", callback_data="nav_rev")],
        [InlineKeyboardButton("📊 فحص السعة", callback_data="nav_stats")],
        [InlineKeyboardButton("⚙️ الإدارة", callback_data="nav_adm")]
    ]
    text = "🎬 <b>لوحة تحكم سينما بلاس</b>"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return MENU

# ================== التنقل ==================
async def navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "nav_up":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in get_all_mux()]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
        await q.edit_message_text("📤 اختر القسم:", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_UP

    if q.data == "nav_rev":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"rev_{i}") for i in get_all_mux()]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
        await q.edit_message_text("🎬 اختر القسم للمراجعة:", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_REV

    if q.data == "nav_stats":
        total = 0
        for creds in get_all_mux().values():
            r = requests.get(
                "https://api.mux.com/video/v1/assets?limit=1",
                auth=(creds["id"], creds["secret"])
            )
            if r.status_code == 200:
                total += r.json()["total_row_count"]

        await q.edit_message_text(
            f"📊 فحص السعة\n\n"
            f"عدد الأقسام: <b>{len(get_all_mux())}</b>\n"
            f"عدد الفيديوهات: <b>{total}</b>",
            parse_mode=ParseMode.HTML
        )
        return MENU

    if q.data == "nav_adm":
        if context.user_data.get("is_admin"):
            return await admin_home(update, context)
        await q.edit_message_text("🔐 أرسل كلمة المرور:")
        return AUTH_ADMIN

# ================== رفع ==================
async def start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sec"] = update.callback_query.data.split("_")[1]
    await update.callback_query.edit_message_text("✏️ أرسل اسم الفيلم:")
    return NAMING

async def upload_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🔗 أرسل رابط الفيديو:")
    return LINKING

async def upload_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sec = context.user_data["sec"]
    creds = get_all_mux()[sec]

    r = requests.post(
        "https://api.mux.com/video/v1/assets",
        json={
            "input": update.message.text,
            "playback_policy": ["public"],
            "passthrough": context.user_data["name"]
        },
        auth=(creds["id"], creds["secret"])
    )

    if r.status_code == 201:
        pid = r.json()["data"]["playback_ids"][0]["id"]
        await update.message.reply_text(f"✅ تم الرفع\n<code>{pid}</code>", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ فشل الرفع")

    return await start(update, context)

# ================== مراجعة ==================
async def review_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    sec = q.data.split("_")[1]
    creds = get_all_mux()[sec]

    r = requests.get(
        "https://api.mux.com/video/v1/assets?limit=5",
        auth=(creds["id"], creds["secret"])
    )

    text = f"🎬 آخر فيديوهات القسم {sec}\n\n"
    for a in r.json()["data"]:
        text += f"• {a.get('passthrough','بدون اسم')}\n<code>{a['playback_ids'][0]['id']}</code>\n\n"

    await q.edit_message_text(text, parse_mode=ParseMode.HTML)
    return MENU

# ================== إدارة ==================
async def admin_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == ADMIN_PASSWORD:
        context.user_data["is_admin"] = True
        return await admin_home(update, context)
    await update.message.reply_text("❌ كلمة مرور خاطئة")
    return MENU

async def admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("➕ إضافة قسم", callback_data="adm_add")],
        [InlineKeyboardButton("🗑 حذف فيديو", callback_data="adm_del")],
        [InlineKeyboardButton("🏠 رجوع", callback_data="back_home")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text("⚙️ لوحة الإدارة", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("⚙️ لوحة الإدارة", reply_markup=InlineKeyboardMarkup(kb))
    return ADMIN_HOME

# ================== حذف فيديو ==================
async def delete_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"del_{i}") for i in get_all_mux()]
    kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
    await q.edit_message_text("🗑 اختر القسم:", reply_markup=InlineKeyboardMarkup(kb))
    return SELECT_DEL

async def delete_ask_pid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["del_sec"] = update.callback_query.data.split("_")[1]
    await update.callback_query.edit_message_text("🆔 أرسل Playback ID:")
    return DEL_PID

async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = update.message.text
    creds = get_all_mux()[context.user_data["del_sec"]]

    r = requests.delete(
        f"https://api.mux.com/video/v1/assets/{pid}",
        auth=(creds["id"], creds["secret"])
    )

    await update.message.reply_text("✅ تم الحذف" if r.status_code == 204 else "❌ فشل الحذف")
    return await start(update, context)

# ================== تشغيل ==================
app = ApplicationBuilder().token(BOT_TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        MENU: [CallbackQueryHandler(navigate, pattern="nav_")],
        SELECT_UP: [CallbackQueryHandler(start_upload, pattern="up_")],
        NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_name)],
        LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_video)],
        SELECT_REV: [CallbackQueryHandler(review_assets, pattern="rev_")],
        AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_auth)],
        ADMIN_HOME: [CallbackQueryHandler(delete_select, pattern="adm_del")],
        SELECT_DEL: [CallbackQueryHandler(delete_ask_pid, pattern="del_")],
        DEL_PID: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_confirm)],
    },
    fallbacks=[CommandHandler("start", start)],
    allow_reentry=True
)

app.add_handler(conv)
app.run_polling()
