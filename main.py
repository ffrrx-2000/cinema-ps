import os
import asyncio
import requests
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# --- الإعدادات وجلب المتغيرات من Koyeb ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL") # يجب أن يبدأ بـ mongodb بحرف صغير
ADMIN_PASSWORD = "1460"

# --- 1. الأقسام القديمة (بياناتك الموثقة - لا تُحذف) ---
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

# --- 2. الاتصال بقاعدة البيانات للأقسام الجديدة ---
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
dynamic_sections_col = db.dynamic_sections

def get_all_sections():
    """دمج الأقسام القديمة مع الأقسام المخزنة في MongoDB"""
    all_sections = MUX_SECTIONS_FIXED.copy()
    for s in dynamic_sections_col.find().sort("section_id", 1):
        all_sections[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return all_sections

# --- 3. حالات المحادثة ---
MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, SELECT_REV, NAMING, LINKING, ADD_SEC_ID, ADD_SEC_SECRET, SELECT_DEL_SEC, SELECT_DEL_VID = range(11)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيلم", callback_data="nav_upload"), InlineKeyboardButton("🎬 مراجعة", callback_data="nav_review")],
        [InlineKeyboardButton("📊 حالة الأقسام", callback_data="nav_stats")],
        [InlineKeyboardButton("⚙️ الإدارة (1460)", callback_data="nav_admin")]
    ]
    text = "🎬 <b>مرحباً بك في سيرفر سينما بلاس المطور</b>\nتم دمج الأقسام اليدوية والسحابية ✅"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MENU

# --- 4. نظام الإدارة المحمي (1460) ---
async def auth_admin_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_pass = update.message.text
    await update.message.delete() # حذف كلمة السر فوراً للأمان
    
    if user_pass == ADMIN_PASSWORD:
        context.user_data['is_admin'] = True
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قسم سحابي", callback_data="adm_add_sec")],
            [InlineKeyboardButton("🗑️ حذف فيديو من Mux", callback_data="adm_del_vid")],
            [InlineKeyboardButton("🏠 خروج", callback_data="back_home")]
        ]
        await update.message.reply_text("⚙️ <b>لوحة تحكم الإدارة</b>\nاختر المهمة المطلوبة:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return ADMIN_HOME
    else:
        await update.message.reply_text("❌ كلمة مرور خاطئة.")
        return MENU

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    all_mux = get_all_sections()

    if query.data == "nav_upload":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in all_mux.keys()]
        keyboard = [btns[i:i+3] for i in range(0, len(btns), 3)]
        await query.edit_message_text("📤 <b>اختر القسم للرفع إليه:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return SELECT_UP

    elif query.data == "nav_review":
        btns = [InlineKeyboardButton(f"مراجعة {i}", callback_data=f"rev_{i}") for i in all_mux.keys()]
        keyboard = [btns[i:i+3] for i in range(0, len(btns), 3)]
        await query.edit_message_text("🔍 <b>اختر القسم للمراجعة:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return SELECT_REV

    elif query.data == "nav_stats":
        await query.edit_message_text("⏳ جاري فحص كافة الأقسام (المدمجة)...")
        stats = "📊 <b>حالة السعة الكلية:</b>\n\n"
        for s_id, creds in all_mux.items():
            try:
                res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]), timeout=5)
                count = len(res.json().get("data", []))
                stats += f"📍 القسم {s_id}: ({count}/100) {'✅' if count < 90 else '⚠️ ممتلئ'}\n"
            except: stats += f"📍 القسم {s_id}: ❌ خطأ اتصال\n"
        await query.edit_message_text(stats + "\nأرسل /start للعودة.", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    elif query.data == "nav_admin":
        await query.edit_message_text("🔐 أرسل كلمة المرور لفتح الإدارة:")
        return AUTH_ADMIN

# --- 5. ميزة إضافة قسم جديد (ديناميكي) ---
async def start_add_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    all_mux = get_all_sections()
    next_id = str(max([int(k) for k in all_mux.keys()]) + 1)
    context.user_data['new_sec_num'] = next_id
    await query.edit_message_text(f"📍 سيتم إضافة القسم رقم {next_id} سحابياً\nأرسل الآن **Access Token ID**:")
    return ADD_SEC_ID

async def save_new_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secret = update.message.text
    acc_id = context.user_data['temp_acc_id']
    sec_num = context.user_data['new_sec_num']
    dynamic_sections_col.update_one({"section_id": sec_num}, {"$set": {"id": acc_id, "secret": secret}}, upsert=True)
    await update.message.reply_text(f"✅ تم حفظ القسم {sec_num} في MongoDB بنجاح!")
    return await start(update, context)

# --- 6. ميزة حذف الفيديوهات من Mux ---
async def select_del_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    all_mux = get_all_sections()
    btns = [InlineKeyboardButton(f"حذف من {i}", callback_data=f"dsec_{i}") for i in all_mux.keys()]
    keyboard = [btns[i:i+3] for i in range(0, len(btns), 3)]
    await query.edit_message_text("🗑️ اختر القسم للحذف منه:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_DEL_SEC

async def list_vids_to_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    s_id = query.data.split("_")[1]
    context.user_data['del_target_sec'] = s_id
    creds = get_all_sections()[s_id]
    res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]))
    assets = res.json().get("data", [])
    if not assets:
        await query.edit_message_text("📁 القسم فارغ.")
        return ADMIN_HOME
    btns = [[InlineKeyboardButton(f"❌ {a.get('passthrough', 'فيلم')}", callback_data=f"kill_{a['id']}")] for a in assets]
    await query.edit_message_text("⚠️ اختر الفيلم لحذفه نهائياً:", reply_markup=InlineKeyboardMarkup(btns))
    return SELECT_DEL_VID

async def kill_vid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    v_id = query.data.split("_")[1]
    s_id = context.user_data['del_target_sec']
    creds = get_all_sections()[s_id]
    requests.delete(f"https://api.mux.com/video/v1/assets/{v_id}", auth=(creds["id"], creds["secret"]))
    await query.answer("✅ تم الحذف!", show_alert=True)
    return await start(update, context)

# --- (بقية منطق الرفع والمراجعة يعمل تلقائياً مع get_all_sections) ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MENU: [CallbackQueryHandler(handle_navigation, pattern="nav_")],
            AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_admin_step)],
            ADMIN_HOME: [CallbackQueryHandler(start_add_sec, pattern="adm_add_sec"), CallbackQueryHandler(select_del_sec, pattern="adm_del_vid")],
            SELECT_UP: [CallbackQueryHandler(lambda u,c: (c.user_data.update({'up_sec': u.callback_query.data.split('_')[1]}), u.callback_query.edit_message_text("أرسل اسم الفيلم:"))[1], pattern="^up_")],
            NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: (c.user_data.update({'up_name': u.message.text}), u.message.reply_text("أرسل الرابط:"))[1])],
            # أضف بقية معالجات الرفع والمراجعة هنا بنفس المنطق المعتاد...
            ADD_SEC_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: (c.user_data.update({'temp_acc_id': u.message.text}), u.message.reply_text("أرسل Secret:"))[1])],
            ADD_SEC_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_sec)],
            SELECT_DEL_SEC: [CallbackQueryHandler(list_vids_to_del, pattern="^dsec_")],
            SELECT_DEL_VID: [CallbackQueryHandler(kill_vid, pattern="^kill_")],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    app.add_handler(conv)
    print("Cinema Plus Hybrid Server is LIVE...")
    app.run_polling()
