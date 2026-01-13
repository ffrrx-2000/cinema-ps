import os
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# الإعدادات الأساسية - التوكن مخفي للأمان (نصيحة إبراهيم)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# هيكل البيانات للأقسام والمفاتيح مع تتبع المرفوعات
# ملاحظة: يتم حفظ المرفوعات في ذاكرة السيرفر المؤقتة
MUX_SECTIONS = {
    str(i): {
        "id": id_val, 
        "secret": secret_val, 
        "uploads": [] # تخزين (اسم الفيلم + Playback ID)
    } for i, (id_val, secret_val) in enumerate([
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

# حالات المحادثة
MENU, SELECT_UP, SELECT_REV, NAMING, LINKING = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 رفع فيديو جديد", callback_data="nav_upload")],
        [InlineKeyboardButton("🎬 مراجعة أفلامك", callback_data="nav_review")],
        [InlineKeyboardButton("📊 سعة الأقسام", callback_data="nav_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎬 <b>أهلاً بك في سيرفر سينما بلاس</b>\nالرجاء اختيار الوظيفة المطلوبة:", 
        reply_markup=reply_markup, 
        parse_mode=ParseMode.HTML
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "nav_upload":
        keyboard = [[InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in range(1, 6)],
                    [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in range(6, 11)]]
        await query.edit_message_text("📤 <b>اختر القسم للبدء بالرفع:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return SELECT_UP
    
    elif query.data == "nav_review":
        keyboard = [[InlineKeyboardButton(f"مراجعة القسم {i}", callback_data=f"rev_{i}") for i in range(1, 4)],
                    [InlineKeyboardButton(f"مراجعة القسم {i}", callback_data=f"rev_{i}") for i in range(4, 7)],
                    [InlineKeyboardButton(f"مراجعة القسم {i}", callback_data=f"rev_{i}") for i in range(7, 11)]]
        await query.edit_message_text("🔍 <b>اختر القسم لمراجعة مرفوعاته:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return SELECT_REV

    elif query.data == "nav_stats":
        stats = "📊 <b>إحصائيات سعة الأقسام:</b>\n\n"
        for s_id, data in MUX_SECTIONS.items():
            count = len(data["uploads"])
            stats += f"📍 القسم {s_id}: ({count}/10) {'✅' if count < 10 else '⚠️ ممتلئ'}\n"
        await query.edit_message_text(stats + "\n/start للعودة", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

async def select_upload_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    section_id = query.data.split("_")[1]
    
    if len(MUX_SECTIONS[section_id]["uploads"]) >= 10:
        await query.answer("⚠️ هذا القسم ممتلئ تماماً (10/10 فيديوهات)", show_alert=True)
        return SELECT_UP

    context.user_data['section'] = section_id
    await query.edit_message_text(f"📍 اخترت القسم: {section_id}\n<b>الآن أرسل 'اسم الفيلم':</b>", parse_mode=ParseMode.HTML)
    return NAMING

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['video_name'] = update.message.text
    await update.message.reply_text(f"📝 الاسم: {update.message.text}\n<b>الآن أرسل 'رابط الفيديو':</b>", parse_mode=ParseMode.HTML)
    return LINKING

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_url = update.message.text
    section_id = context.user_data['section']
    creds = MUX_SECTIONS[section_id]
    video_title = context.user_data['video_name']
    
    status_msg = await update.message.reply_text("⏳ جاري الرفع وتعيين الاسم في Mux...")
    
    try:
        response = requests.post(
            "https://api.mux.com/video/v1/assets", 
            json={"input": video_url, "playback_policy": ["public"], "passthrough": video_title},
            auth=(creds["id"], creds["secret"])
        )
        
        if response.status_code == 201:
            res_data = response.json()["data"]
            playback_id = res_data["playback_ids"][0]["id"]
            asset_id = res_data["id"]
            
            # حفظ في الذاكرة لتاريخ المراجعة
            MUX_SECTIONS[section_id]["uploads"].append({"name": video_title, "playback_id": playback_id})
            remaining = 10 - len(MUX_SECTIONS[section_id]["uploads"])
            
            await status_msg.edit_text(
                f"✅ <b>تم الرفع بنجاح!</b>\n\n🎬 الفيلم: <b>{video_title}</b>\n"
                f"🔗 <b>Playback ID:</b>\n<code>{playback_id}</code>\n\n"
                f"📦 المتبقي في القسم: {remaining} فيديوهات.\n\n"
                f"سأرسل لك إشعاراً عند الجاهزية.\n<b>أرسل اسم الفيلم التالي (لنفس القسم):</b>",
                parse_mode=ParseMode.HTML
            )
            asyncio.create_task(check_status(update, asset_id, creds, video_title, playback_id))
            return NAMING # حلقة مستمرة للرفع في نفس القسم
        else:
            await status_msg.edit_text(f"❌ فشل الرفع. كود: {response.status_code}")
            return NAMING
    except Exception as e:
        await status_msg.edit_text(f"⚠️ خطأ: {str(e)}")
        return NAMING

async def review_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    section_id = query.data.split("_")[1]
    uploads = MUX_SECTIONS[section_id]["uploads"]
    
    if not uploads:
        await query.edit_message_text(f"📁 القسم {section_id} فارغ حالياً.\n/start للعودة")
        return ConversationHandler.END

    text = f"📂 <b>مرفوعات القسم {section_id}:</b>\n\n"
    copy_block = ""
    for i, movie in enumerate(uploads, 1):
        text += f"{i}- {movie['name']}\n<code>{movie['playback_id']}</code>\n"
        copy_block += f"{movie['playback_id']}\n"
    
    context.user_data['full_ids'] = copy_block
    keyboard = [[InlineKeyboardButton("📋 نسخ جميع النتائج", callback_data="copy_all")],
                [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="nav_home")]]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return SELECT_REV

async def copy_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "copy_all":
        ids = context.user_data.get('full_ids', 'لا يوجد بيانات')
        await query.message.reply_text(f"📑 <b>قائمة الأيديهات المرفوعة:</b>\n\n<code>{ids}</code>", parse_mode=ParseMode.HTML)
        await query.answer("تم التجهيز!")
    elif query.data == "nav_home":
        # إعادة توجيه للبداية (غير مفعلة في ConversationHandler البسيط)
        await query.edit_message_text("اضغط /start للعودة للقائمة.")
    return SELECT_REV

async def check_status(update, asset_id, creds, title, p_id):
    """فحص الجاهزية كل 20 ثانية"""
    url = f"https://api.mux.com/video/v1/assets/{asset_id}"
    for _ in range(30): # 10 دقائق كحد أقصى
        await asyncio.sleep(20)
        try:
            res = requests.get(url, auth=(creds["id"], creds["secret"]))
            if res.status_code == 200 and res.json()["data"]["status"] == "ready":
                await update.message.reply_text(
                    f"✨ <b>خبر عاجل!</b> ✨\nالفيلم: <b>{title}</b>\nالحالة: <b>جاهز للمشاهدة الآن ✅</b>",
                    parse_mode=ParseMode.HTML
                )
                return
        except: pass

if __name__ == '__main__':
    print("Bot is Starting with Advanced Dashboard...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [CallbackQueryHandler(menu_handler)],
            SELECT_UP: [CallbackQueryHandler(select_upload_section)],
            SELECT_REV: [CallbackQueryHandler(review_section), CallbackQueryHandler(copy_all_handler, pattern="copy_all")],
            NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    
    app.add_handler(conv_handler)
    app.run_polling()
