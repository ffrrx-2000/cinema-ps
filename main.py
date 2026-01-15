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

# ================== الإعدادات والجلب من البيئة ==================
MONGO_URL = os.getenv("MONGO_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = "1460" 

# ================== الاتصال بقاعدة البيانات ==================
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
dyn_col = db.dynamic_sections

def get_all_mux():
    """دمج الأقسام الـ 10 الرسمية مع أي أقسام مضافة في MongoDB"""
    mux_sections = {
        "1": {"id": "2ab8ed37-b8af-4ffa-ab78-bc0910fcac6e", "secret": "zkX7I4isPxeMz6tFh20vFt37sNOWPpPgaMpH0u7i2dvavEMea84Wob8UfFvIVouNcfzjpIgt7jl"},
        "2": {"id": "3522203d-1925-4ec3-a5f7-9ca9efd1771a", "secret": "p7fHTPl4hFvLh1koWPHlJ7cif9GcOCFxDAYHIAraC4mcGABRrJWp2jNJ4B4cVgIcE2YOY+AT1wb"},
        "3": {"id": "85501be0-bc4f-415c-afde-b8ac1b996974", "secret": "QXzmzVANcX9VrS2vBCTa0h91+QAlr7iM5izLDrzKUDdhSx2sJx2CuNFT6CJHpqOsftsW2MICpci"},
        "4": {"id": "7894140e-03a9-4946-9698-1b58f1e3ea38", "secret": "HwgZg1a7h05ul/AYpeICooOp0fOt4o7W9Fxf0am2z4Qb1QyHfIL3BRMjxh1e6b1Dn+WXehKdjaN"},
        "5": {"id": "147d1438-4269-4739-ae68-7dcbdf9f1d84", "secret": "6cqf9LKM38Q7gbkrrYmWGNwH0v27UjY8DzQWRDZ1Md137UE7+n52NlBGIVc/4qaShADTH5D+LsU"},
        "6": {"id": "60d38bcd-bb17-4db0-9599-129c232cdabf", "secret": "E9j1AbbGropItPcS4K+Gl1csebAiLMJJuglGn9NxIasbJAmM/CsVXTL9BCyw+jBwsR7Zq51RJy2"},
        "7": {"id": "31517bbe-2628-438e-b7ac-261708d6f26e", "secret": "pnHQhp05xWhu6tSc8u98c3x47ycmT7zhW3V6mzxlSmqz30vac71VmsHYgRUBI5aDuBFYBIlkcF4"},
        "8": {"id": "4c53f771-ab87-4dab-9484-2f7f94799f6e", "secret": "rWXTB3ktFkyvcKQkJwD6tcOT+6sV1dM3ndU/H4oZu5qnG6/+2WIw4keq2DPFU+F0foJ57eI0BPz"},
        "9": {"id": "0f39d0e7-33d9-4983-a20d-c20a54a39d19", "secret": "GG2UNHGjJysTBxe32+VOGEOpLGSEUGINWVvEFyhz+inbm+G41LNi/Hua8Kd9pqeRO+FOLyLgk5/"},
        "10": {"id": "fcbfcdcb-fbd3-41ae-ab10-5451502ac8d3", "secret": "NtwphUQyZZsrhOXgadrZN3QoJXxMVW2za+q0xFe/1vLl4PfRjrGCOn18BOqpGFMCFZAc/g2rR0R"}
    }
    for s in dyn_col.find().sort("section_id", 1):
        mux_sections[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return mux_sections

# ================== حالات المحادثة ==================
(MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, NAMING, LINKING, 
 SELECT_REV, SELECT_ADM_DEL, ADD_SEC_ID, ADD_SEC_SECRET) = range(10)

# ================== نظام التنبيهات (خبر سعيد) ==================
async def check_video_status(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    asset_id, creds, chat_id, movie_name = job.data['asset_id'], job.data['creds'], job.data['chat_id'], job.data['movie_name']
    try:
        r = requests.get(f"https://api.mux.com/video/v1/assets/{asset_id}", auth=(creds["id"], creds["secret"]), timeout=10)
        if r.status_code == 200 and r.json()["data"]["status"] == "ready":
            text = f"🌟 <b>خبر سعيد</b>\n\n🎬 الفيلم: <b>{movie_name}</b>\n✅ الحالة: <b>جاهز للمشاهدة الآن</b>"
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
            job.schedule_removal()
    except: pass

# ================== الدوال الرئيسية ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("📤 رفع فيلم", callback_data="nav_up"), InlineKeyboardButton("🎬 مراجعة", callback_data="nav_rev")],
          [InlineKeyboardButton("📊 فحص السعة", callback_data="nav_stats"), InlineKeyboardButton("⚙️ الإدارة", callback_data="nav_adm")]]
    text = "🎬 <b>لوحة تحكم سينما بلاس</b>\nالرجاء اختيار عملية:"
    if update.callback_query: await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return MENU

async def navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    sections = get_all_mux()
    if q.data == "nav_up":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in sections]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]; kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
        await q.edit_message_text("📤 اختر القسم للرفع:", reply_markup=InlineKeyboardMarkup(kb)); return SELECT_UP
    if q.data == "nav_rev":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"rev_{i}") for i in sections]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]; kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
        await q.edit_message_text("🎬 اختر القسم للمراجعة:", reply_markup=InlineKeyboardMarkup(kb)); return SELECT_REV
    if q.data == "nav_stats":
        await q.edit_message_text("⏳ جاري جلب تقارير دقيقة من سيرفرات Mux...")
        report = "📊 <b>تقرير الأقسام المحدث:</b>\n\n"
        for i, creds in sections.items():
            try:
                # طلب بيانات دقيقة للعدد الإجمالي
                r = requests.get("https://api.mux.com/video/v1/assets", params={"limit": 1}, auth=(creds["id"], creds["secret"]), timeout=7)
                count = r.json().get("total_row_count", 0)
                status = "🔴 ممتلئ" if count >= 98 else "🟢 متاح"
                report += f"📍 القسم {i}: <b>{count}/100</b> فيلم | {status}\n"
            except: report += f"📍 القسم {i}: ⚠️ خطأ اتصال\n"
        kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_home")]]
        await q.edit_message_text(report, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML); return MENU
    if q.data == "nav_adm":
        if context.user_data.get("is_admin"): return await admin_home(update, context)
        await q.edit_message_text("🔐 أرسل كلمة المرور:"); return AUTH_ADMIN

# ================== المراجعة (Playback فقط) ==================

async def review_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    sec = q.data.split("_")[1]
    creds = get_all_mux().get(sec)
    r = requests.get(f"https://api.mux.com/video/v1/assets?limit=15", auth=(creds["id"], creds["secret"]))
    assets = r.json().get("data", [])
    text = f"🎬 <b>أفلام القسم {sec}:</b>\n\n"
    if not assets: text += "القسم فارغ."
    else:
        for a in assets:
            p_id = a.get('playback_ids', [{}])[0].get('id', 'N/A')
            text += f"• <b>{a.get('passthrough','بدون اسم')}</b>\n└ Playback: <code>{p_id}</code>\n\n"
    kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="nav_rev")]]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML); return MENU

# ================== الإدارة (الحذف وإضافة قسم) ==================

async def admin_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()
    if update.message.text == ADMIN_PASSWORD:
        context.user_data["is_admin"] = True
        return await admin_home(update, context)
    await update.message.reply_text("❌ خطأ!"); return MENU

async def admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🗑 حذف فيلم (مع إظهار الأيدي)", callback_data="adm_del_sec")], 
          [InlineKeyboardButton("➕ إضافة قسم", callback_data="adm_add_sec")], [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")]]
    if update.callback_query: await update.callback_query.edit_message_text("⚙️ <b>إدارة النظام</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else: await update.message.reply_text("⚙️ <b>إدارة النظام</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return ADMIN_HOME

async def admin_del_select_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"adel_{i}") for i in get_all_mux()]
    kb = [btns[i:i+3] for i in range(0, len(btns), 3)]; kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="nav_adm")])
    await update.callback_query.edit_message_text("🗑 اختر القسم لإدارة الحذف:", reply_markup=InlineKeyboardMarkup(kb)); return SELECT_ADM_DEL

async def admin_del_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    sec = q.data.split("_")[1]
    creds = get_all_mux().get(sec)
    r = requests.get(f"https://api.mux.com/video/v1/assets?limit=15", auth=(creds["id"], creds["secret"]))
    assets = r.json().get("data", [])
    text = f"⚙️ <b>حذف من القسم {sec}:</b>\nهنا يظهر Asset ID للحذف الدقيق.\n\n"
    kb = []
    for a in assets:
        name = a.get('passthrough','...')
        kb.append([InlineKeyboardButton(f"🎬 {name} (AID: {a['id'][:8]}...)", callback_data="none"), InlineKeyboardButton("🗑", callback_data=f"drop_{sec}_{a['id']}")])
    kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_del_sec")])
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML); return ADMIN_HOME

# ================== الرفع (احترافي) ==================

async def start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sec"] = update.callback_query.data.split("_")[1]
    await update.callback_query.edit_message_text("✏️ أرسل <b>اسم الفيلم</b>:"); return NAMING

async def upload_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🔗 أرسل <b>رابط الفيديو المباشر</b>:"); return LINKING

async def upload_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sec, movie_name = context.user_data["sec"], context.user_data["name"]
    creds = get_all_mux().get(sec)
    r = requests.post("https://api.mux.com/video/v1/assets", json={"input": update.message.text, "playback_policy": ["public"], "passthrough": movie_name}, auth=(creds["id"], creds["secret"]))
    if r.status_code == 201:
        data = r.json()["data"]
        p_id = data["playback_ids"][0]["id"]
        text = f"✅ <b>تم الرفع بنجاح</b>\n\nالفيلم: <b>{movie_name}</b>\n📥 Playback ID:\n<code>{p_id}</code>\n\n✨ أرسل اسم الفيلم التالي الآن."
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        context.job_queue.run_repeating(check_video_status, interval=60, first=30, data={'asset_id': data["id"], 'creds': creds, 'chat_id': update.message.chat_id, 'movie_name': movie_name})
    else: await update.message.reply_text("❌ فشل!"); return NAMING

# (بقية دوال الحذف وإضافة القسم مدمجة منطقياً)
async def delete_asset_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; _, sec, asset_id = q.data.split("_")
    creds = get_all_mux().get(sec)
    r = requests.delete(f"https://api.mux.com/video/v1/assets/{asset_id}", auth=(creds["id"], creds["secret"]))
    await q.answer("✅ تم الحذف" if r.status_code == 204 else "❌ خطأ"); return await admin_del_list(update, context)

async def add_sec_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("🆕 أرسل Mux Access Token ID:"); return ADD_SEC_ID

async def add_sec_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_id"] = update.message.text
    await update.message.reply_text("🔑 أرسل Mux Secret Key:"); return ADD_SEC_SECRET

async def add_sec_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dyn_col.insert_one({"section_id": len(get_all_mux()) + 1, "id": context.user_data["new_id"], "secret": update.message.text})
    await update.message.reply_text("✅ تم!"); return await admin_home(update, context)

# ================== تشغيل البوت ==================
app = ApplicationBuilder().token(BOT_TOKEN).build()
conv = ConversationHandler(
    entry_points=[CommandHandler("start", start), CallbackQueryHandler(start, pattern="back_home")],
    states={
        MENU: [CallbackQueryHandler(navigate, pattern="nav_"), CallbackQueryHandler(delete_asset_action, pattern="drop_")],
        SELECT_UP: [CallbackQueryHandler(start_upload, pattern="up_")],
        NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_name)],
        LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_video)],
        SELECT_REV: [CallbackQueryHandler(review_assets, pattern="rev_")],
        AUTH_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_auth)],
        ADMIN_HOME: [CallbackQueryHandler(admin_del_select_sec, pattern="adm_del_sec"), CallbackQueryHandler(add_sec_start, pattern="adm_add_sec")],
        SELECT_ADM_DEL: [CallbackQueryHandler(admin_del_list, pattern="adel_")],
        ADD_SEC_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sec_id)],
        ADD_SEC_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sec_final)],
    },
    fallbacks=[CommandHandler("start", start)], allow_reentry=True
)
app.add_handler(conv); app.run_polling()
