
import os
import requests
import asyncio
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# --- 1. الإعدادات ---
MONGO_URL = os.getenv("MONGO_URL") # تأكد أنه يبدأ بـ mongodb صغير في Koyeb
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = "1460"

# --- الأقسام الثابتة (بياناتك الأصلية) ---
MUX_SECTIONS_FIXED = {
    str(i): {"id": id_val, "secret": secret_val} for i, (id_val, secret_val) in enumerate([
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

# --- 2. الربط مع MongoDB ---
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
dyn_col = db.dynamic_sections

def get_all_mux():
    """دمج الأقسام القديمة والجديدة"""
    all_mux = MUX_SECTIONS_FIXED.copy()
    for s in dyn_col.find().sort("section_id", 1):
        all_mux[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return all_mux

# --- 3. حالات المحادثة ---
(MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, SELECT_REV, 
 NAMING, LINKING, ADD_SEC_ID, ADD_SEC_SECRET, SELECT_DEL_VID) = range(10)

# --- 4. وظائف البوت المصلحة ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيلم", callback_data="nav_up"), InlineKeyboardButton("🎬 مراجعة", callback_data="nav_rev")],
        [InlineKeyboardButton("📊 فحص السعة", callback_data="nav_stats")],
        [InlineKeyboardButton("⚙️ الإدارة (1460)", callback_data="nav_adm")]
    ]
    text = "🎬 <b>لوحة تحكم سينما بلاس الموحدة</b>\nتم إصلاح مسارات الرفع وإضافة الأقسام بنجاح ✅"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MENU

# --- إصلاح نظام الرفع (Upload Flow) ---
async def start_upload_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['up_sec'] = query.data.split("_")[1]
    await query.edit_message_text(f"📍 القسم {context.user_data['up_sec']}: <b>أرسل الآن اسم الفيلم:</b>", parse_mode=ParseMode.HTML)
    return NAMING

async def process_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['up_name'] = update.message.text
    await update.message.reply_text(f"📝 الاسم: {update.message.text}\n<b>أرسل الآن رابط الفيديو المباشر:</b>", parse_mode=ParseMode.HTML)
    return LINKING

async def process_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    v_url = update.message.text
    s_id, v_name = context.user_data['up_sec'], context.user_data['up_name']
    creds = get_all_mux()[s_id]
    
    msg = await update.message.reply_text("⏳ جاري الإرسال لـ Mux...")
    res = requests.post("https://api.mux.com/video/v1/assets", 
                        json={"input": v_url, "playback_policy": ["public"], "passthrough": v_name},
                        auth=(creds["id"], creds["secret"]))
    
    if res.status_code == 201:
        pid = res.json()["data"]["playback_ids"][0]["id"]
        await msg.edit_text(f"✅ تم الرفع بنجاح!\nالفيلم: {v_name}\nالكود: <code>{pid}</code>", parse_mode=ParseMode.HTML)
    else:
        await msg.edit_text("❌ فشل الرفع. تأكد من الرابط أو مفاتيح القسم.")
    return await start(update, context)

# --- إصلاح نظام إضافة الأقسام (Add Section Flow) ---
async def start_add_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_m = get_all_mux()
    next_id = str(max([int(k) for k in all_m.keys()]) + 1)
    context.user_data['new_id'] = next_id
    await update.callback_query.edit_message_text(f"➕ إضافة القسم رقم {next_id}\nأرسل الآن **Access Token ID**:")
    return ADD_SEC_ID

async def process_sec_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['temp_id'] = update.message.text
    await update.message.reply_text("تم الاستلام. أرسل الآن **Secret Key**:")
    return ADD_SEC_SECRET

async def process_sec_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secret = update.message.text
    s_id, acc_id = context.user_data['new_id'], context.user_data['temp_id']
    dyn_col.update_one({"section_id": s_id}, {"$set": {"id": acc_id, "secret": secret}}, upsert=True)
    await update.message.reply_text(f"✅ تم حفظ وتفعيل القسم {s_id} في MongoDB!")
    return await start(update, context)

# --- نظام الحماية المطور ---
async def admin_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_pass = update.message.text
    await update.message.delete() # حذف كلمة السر للأمان
    if u_pass == ADMIN_PASSWORD:
        keyboard = [[InlineKeyboardButton("➕ إضافة قسم سحابي", callback_data="adm_add")],
                    [InlineKeyboardButton("🏠 خروج", callback_data="back_home")]]
        await update.message.reply_text("⚙️ <b>لوحة الإدارة</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return ADMIN_HOME
    return MENU

# --- معالج الملاحة الرئيسي ---
async def navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    all_m = get_all_mux()
    if q.data == "nav_up":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in all_m.keys()]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
        await q.edit_message_text("📤 اختر القسم للرفع:", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_UP
    elif q.data == "nav_adm":
        await q.edit_message_text("🔐 أرسل كلمة المرور (الادارة):")
        return AUTH_ADMIN
    return MENU

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MENU: [CallbackQueryHandler(navigate, pattern="nav_")],
            AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_auth)],
            ADMIN_HOME: [CallbackQueryHandler(start_add_sec, pattern="adm_add")],
            SELECT_UP: [CallbackQueryHandler(start_upload_process, pattern="^up_")],
            NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_name)],
            LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_upload)],
            ADD_SEC_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_sec_id)],
            ADD_SEC_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_sec_save)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    app.add_handler(conv)
    app.run_polling()
