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
ADMIN_PASSWORD = "1460" #

# --- 2. الاتصال بقاعدة البيانات ---
client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
sections_col = db.sections

# --- 3. حالات المحادثة (Conversation States) ---
(MAIN_MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, SELECT_REV, 
 NAMING, LINKING, SELECT_SET_SEC, INPUT_ID, INPUT_SECRET, SELECT_DEL_VID) = range(11)

def get_all_keys():
    """جلب كافة الأقسام المخزنة في MongoDB"""
    sections = {}
    for s in sections_col.find().sort("section_id", 1):
        sections[str(s["section_id"])] = {"id": s["id"], "secret": s["secret"]}
    return sections

# --- 4. واجهات البوت الرئيسية ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الواجهة الرئيسية للبوت"""
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيلم جديد", callback_data="go_upload"), 
         InlineKeyboardButton("🎬 مراجعة الأقسام", callback_data="go_review")],
        [InlineKeyboardButton("📊 فحص سعة الأقسام", callback_data="go_stats")],
        [InlineKeyboardButton("⚙️ لوحة الإدارة (1460)", callback_data="go_admin")]
    ]
    text = "🎬 <b>لوحة تحكم سينما بلاس الاحترافية</b>\nتم إصلاح كافة الأقسام والربط بالسحابة بنجاح ✅"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MAIN_MENU

# --- نظام الأمان الذكي ---
async def auth_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من كلمة السر وحذفها فوراً للأمان"""
    user_pass = update.message.text
    # ميزة احترافية: حذف كلمة السر لكي لا يراها أحد
    await update.message.delete()
    
    if user_pass == ADMIN_PASSWORD:
        context.user_data['is_admin'] = True
        return await admin_home_view(update, context)
    else:
        await update.message.reply_text("❌ كلمة مرور خاطئة. العودة للقائمة الرئيسية...")
        return await start(update, context)

async def admin_home_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم الإدارة"""
    keyboard = [
        [InlineKeyboardButton("🔑 إضافة/تعديل قسم", callback_data="manage_keys")],
        [InlineKeyboardButton("🗑️ حذف فيلم نهائياً", callback_data="manage_del")],
        [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_home")]
    ]
    text = "⚙️ <b>لوحة التحكم المركزية</b>\nيمكنك الآن التحكم في مفاتيح Mux وحذف البيانات."
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return ADMIN_HOME

# --- ميزة فحص السعة المتبقية (Stats) ---
async def check_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص الأقسام الممتلئة والمتبقي لها"""
    query = update.callback_query
    keys = get_all_keys()
    if not keys:
        await query.answer("⚠️ لا توجد أقسام مضافة بعد.", show_alert=True)
        return MAIN_MENU

    await query.edit_message_text("⏳ جاري فحص حالة الأقسام وسعة Mux...")
    report = "📊 <b>تقرير استهلاك الأقسام:</b>\n\n"
    for s_id, creds in keys.items():
        try:
            res = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]), timeout=7)
            count = len(res.json().get("data", []))
            # تقدير سعة القسم بـ 100 فيلم لغرض التنظيم
            remaining = 100 - count
            status = "🟢 مستقر" if remaining > 20 else "🔴 ممتلئ"
            report += f"📍 <b>القسم {s_id}:</b>\n- المرفوع: {count} فيلم\n- المتبقي: {remaining} فيلم\n- الحالة: {status}\n\n"
        except:
            report += f"📍 <b>القسم {s_id}:</b> ❌ خطأ في المفاتيح\n\n"
    
    await query.edit_message_text(report, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 عودة", callback_data="back_home")]]), parse_mode=ParseMode.HTML)
    return MAIN_MENU

# --- ميزات المراجعة والرفع (Review & Upload) ---
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
        for i, a in enumerate(assets[:10], 1): # عرض أول 10 أفلام
            name = a.get("passthrough", "بدون اسم")
            p_id = a.get("playback_ids", [{"id": "-"}])[0]["id"]
            text += f"{i}- {name} ✅\n<code>{p_id}</code>\n\n"
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 عودة", callback_data="back_home")]]), parse_mode=ParseMode.HTML)
    except:
        await query.edit_message_text("❌ فشل الجلب. تأكد من صحة المفاتيح.")
    return MAIN_MENU

async def start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['up_sec'] = query.data.split("_")[1]
    await query.edit_message_text("📝 أرسل اسم الفيلم الآن:")
    return NAMING

async def upload_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_url = update.message.text
    s_id, v_name = context.user_data['up_sec'], context.user_data['up_name']
    keys = get_all_keys()
    creds = keys[s_id]
    
    msg = await update.message.reply_text("⏳ جاري الرفع إلى Mux...")
    payload = {"input": video_url, "playback_policy": ["public"], "passthrough": v_name}
    res = requests.post("https://api.mux.com/video/v1/assets", json=payload, auth=(creds["id"], creds["secret"]))
    
    if res.status_code == 201:
        p_id = res.json()["data"]["playback_ids"][0]["id"]
        await msg.edit_text(f"✅ تم الرفع بنجاح!\nالكود: <code>{p_id}</code>", parse_mode=ParseMode.HTML)
    else:
        await msg.edit_text(f"❌ فشل الرفع. تأكد من الرابط والمفاتيح.")
    return await start(update, context)

# --- إدارة المفاتيح والحذف ---
async def manage_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keys = get_all_keys()
    buttons = [InlineKeyboardButton(f"تعديل {i}", callback_data=f"set_{i}") for i in keys.keys()]
    keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    keyboard.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="set_new")])
    keyboard.append([InlineKeyboardButton("🏠 عودة", callback_data="manage_home")])
    await query.edit_message_text("🔑 اختر القسم لتعديله أو أضف قسماً جديداً:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECT_SET_SEC

async def save_key_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    secret = update.message.text
    s_id, acc_id = context.user_data['target_sec'], context.user_data['temp_id']
    sections_col.update_one({"section_id": s_id}, {"$set": {"id": acc_id, "secret": secret}}, upsert=True)
    await update.message.reply_text(f"✅ تم حفظ وتأمين القسم {s_id} في MongoDB!")
    return await start(update, context)

# --- تشغيل البوت ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # تحسين: استخدام ConversationHandler واحد لكل الوظائف لضمان عدم الضياع
    main_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="back_home")],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("🔐 أرسل كلمة المرور بصمت:"), pattern="go_admin"),
                CallbackQueryHandler(check_stats, pattern="go_stats"),
                CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("📤 اختر القسم للرفع:"), pattern="go_upload"),
                CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("🔍 اختر القسم للمراجعة:"), pattern="go_review"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, auth_step)
            ],
            ADMIN_HOME: [
                CallbackQueryHandler(manage_keys, pattern="manage_keys"),
                CallbackQueryHandler(lambda u,c: u.callback_query.edit_message_text("🗑️ اختر القسم للحذف:"), pattern="manage_del"),
                CallbackQueryHandler(start, pattern="back_home")
            ],
            SELECT_UP: [CallbackQueryHandler(start_upload, pattern="^up_")],
            NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: (c.user_data.update({'up_name': u.message.text}), u.message.reply_text("🔗 أرسل الرابط المباشر:"))[1])],
            LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, upload_video)],
            SELECT_REV: [CallbackQueryHandler(review_flow, pattern="^rev_")],
            SELECT_SET_SEC: [CallbackQueryHandler(lambda u,c: (c.user_data.update({'target_sec': str(len(get_all_keys())+1) if u.callback_query.data=='set_new' else u.callback_query.data.split('_')[1]}), u.callback_query.edit_message_text("أرسل Access Token ID:"))[1], pattern="^set_")],
            INPUT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: (c.user_data.update({'temp_id': u.message.text}), u.message.reply_text("أرسل Secret Key:"))[1])],
            INPUT_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_key_final)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    
    app.add_handler(main_conv)
    print("Cinema Plus System V4 is Running...")
    app.run_polling()
