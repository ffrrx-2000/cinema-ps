import os
import requests
import asyncio
import time
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# --- 1. الإعدادات والربط ---
MONGO_URL = os.getenv("MONGO_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")

client = MongoClient(MONGO_URL)
db = client.cinema_plus_db
auth_col = db.user_sessions # لتخزين الجلسات (48 ساعة)
dyn_col = db.dynamic_sections

# --- 2. بيانات الأقسام ---
CINEMA_SECTIONS = {
    str(i): {"id": id_v, "secret": sec_v} for i, (id_v, sec_v) in enumerate([
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

SHOOF_SECTIONS = {
    str(i): {"id": id_v, "secret": sec_v} for i, (id_v, sec_v) in enumerate([
        ("b6a28905-15dd-4c4e-8455-116d1934820f", "Z8P9cIYFf49ElRMqGECViG/O5N/qRz8U5ux2r7uhIX2Yp950dgI0DTvWCvUoaeL6rXIaZQ6q+VY"),
        ("a058bf43-4c80-49d6-b902-b0fd00cfff18", "+q5bNYmCQyhii+HdXN8RB4jadh704TVtZVp2qqtlwAmNhX5mhibj/0Yg/UALbysMjVfUxO6qTBA"),
        ("664f5ab9-4b93-4a85-9cdc-39bed76857dd", "RZG8KZLJkd/+30Idcq26otBmje36qrQTWx3QWdqUErAjhonVPsCIYVZnFq5gLo/nGzAk5GWz5gl"),
        ("6984f132-ca88-4c86-aac4-d10e44594548", "C9rWwb3cVH2WUXD7no5co4g/bSIFPox12pmB2xggsCQuBa1/RVDq/5aigHW9Drr5aLTi60SLK5Y"),
        ("3888e6fc-1e13-4f91-8e03-5d73aab3375c", "DcedrXuHMmxvbiJby+A8nt0U5LhFOPDvNpFAMuREwRZ/boh1yfG09Gw35e46krTWXvyCZ0ToRQ0"),
        ("06b5abfd-de0f-4acb-87a0-7716d8951115", "QZCYyNNCHcAuTk3Y+XvpP/uWIThW57mVWMyBagiNiFeMVBVZaB0e1deXazxLfBef/H77XVkIWkG"),
        ("2d3edb5b-dc6e-4af3-917f-726434532b3c", "SP5m9+Vc4eGwITG/nUbYNfbdnkYcR6hDIkZz6FZ8ni9ocsTeva6dKbmP/SfoOcwaEaZ4dMkO95d"),
        ("4a32292d-e7ee-492d-b43c-57ce8b8a2095", "3tklq+6lYCEUedNEyliywgieRM3jDW6XTWiB+CDI1Zs0TEUC4GweXsAIq08LQbK9ebReIaiOTK4"),
        ("0d8b2a67-2c1c-474e-a1a3-cbdfb3e56cb1", "K6jv2a+cNTVndUuM94VvLnu54be2wBFg9a8q0TdqoRv98qu+UHJ9+vIc0u1Ax59eBtoVgyWlA4G"),
        ("d732c626-11ec-43bd-90f0-50b9c96489ef", "tGVwrWhcwU9DzhBrgnyvWbVkt1i7nmw8e6B5D0PozwhJ14NHmg+u4nMQrknZOu0NssnNmANGDW9"),
        ("1bb7a1e8-ba83-419e-9796-d8f95fd6767f", "dD+2uEj5mR2g/6N5RmsDZhLQ0hk7EVhvTBgS43UQqYNtpBUQxdz9dxMDeoVpXT3VLStO/x3HHql"),
        ("44acb746-ade9-4b1a-9202-99f319e22647", "oLeB+xQt1EFGMVkwonV1O2iRKxGbBUdHuo1oF+vEUbU4r3NoucOgcaUXH5vgefM02DNF2aCI90P"),
        ("cfefbf91-c4b8-4b49-9c85-5f4e3fb2fbd3", "H6pC+M1B96SQBrOBe6twQ1+glm3Stu8eroGMcs7Y5dtNy9Dkj7YacQBzXdONGM+p9l1R8r8LzPA"),
        ("cc28a604-d2df-4d8f-a7a9-55a6e5722bf6", "VeYbzua6o/e0IpCclkImkrOriueb2RbqvpXo///A/V4T89kLFFr8PE2/ZqZiJPlg74IU6c8IGZs"),
        ("e85fa620-de3d-4366-962f-d57faa83838e", "dj5ujB9t4a7sQNzT7k4otAotEVBK01RasBhaI3c6M6nveOdmCUtr9kSjuVzROOezPy9iAj+ksxY"),
        ("16c71792-9fa2-4381-9793-12256695a0bd", "F496wajL4fRk7QWj9tnBCbTwuGC4Ybjn8Me6L+fZJxtFenI/WtcD8yeFnPCKZiiGxQBCCTZcQIy"),
        ("3bd99e7d-5805-45e7-90ba-cf7395bea2ec", "2cTSi3G5LkqJ9/TLMXezMZ6Q+AZNBCpgKRTe/PLH3lyFtijhpGJJ34sEenktHll7anjDCszqopT"),
        ("2f230bba-92a3-425a-a235-ba792a6cda4e", "LyoGF6sbby1ajGKvCQKak11/7T9jPNKWt8sF4uTCMppjisoq8lIAHwQalyaNcnaAepcLNgwPoQ1"),
        ("ba238656-8a32-40ea-b8ea-edaabd17ea4e", "hjJh8oSOZ0nznssaR9iioEAQ3gHiq9aQEUUbw8+PrqSRkr9VE69fhC6wlqa0gYU1asz7JNo/c32"),
        ("5414c527-5e37-4229-b761-0a7f4343b6d8", "zOWmBPj7pM3vj4lTy9NzFj//qFhbRaJFqqarfDsSJ55hTo+mP0XeR07mAS8uC3OcDbGzdcRFE3S")
    ], 1)
}

# --- 3. حالات المحادثة ---
(CHOOSE_SYSTEM, AUTH_WAIT, MENU, SELECT_UP, NAMING, LINKING, SELECT_REV, ADMIN_HOME, SELECT_DEL_VID) = range(9)

# --- 4. الوظائف المساعدة ---

def get_user_sections(user_type):
    return CINEMA_SECTIONS if user_type == "cinema" else SHOOF_SECTIONS

async def is_authenticated(user_id, user_type):
    session = auth_col.find_one({"user_id": user_id, "type": user_type})
    if session and (time.time() - session['timestamp'] < 172800): # 48 ساعة
        return True
    return False

# --- 5. منطق البوت الرئيسي ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🎬 Cinema Plus", callback_data="sys_cinema"), 
           InlineKeyboardButton("🎥 Shoof Plus", callback_data="sys_shoof")]]
    await update.message.reply_text("🎬 <b>أهلاً بك في نظام الإدارة الموحد</b>\nاختر النظام الذي تريد الدخول إليه:", 
                                    reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return CHOOSE_SYSTEM

async def handle_system_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    sys_type = query.data.split("_")[1]
    context.user_data['sys_type'] = sys_type
    
    if await is_authenticated(update.effective_user.id, sys_type):
        return await show_menu(update, context)
    
    await query.edit_message_text(f"🔐 يرجى إدخال كلمة السر الخاصة بنظام {'Cinema Plus' if sys_type == 'cinema' else 'Shoof Plus'}:")
    return AUTH_WAIT

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pwd = update.message.text
    sys_type = context.user_data['sys_type']
    target_pwd = "67146" if sys_type == "cinema" else "1460"
    
    await update.message.delete()
    if pwd == target_pwd:
        auth_col.update_one({"user_id": update.effective_user.id, "type": sys_type}, 
                            {"$set": {"timestamp": time.time()}}, upsert=True)
        return await show_menu(update, context)
    
    await update.message.reply_text("❌ كلمة سر خاطئة!")
    return CHOOSE_SYSTEM

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sys_name = "Cinema Plus" if context.user_data['sys_type'] == "cinema" else "Shoof Plus"
    kb = [[InlineKeyboardButton("📤 رفع فيلم", callback_data="nav_up"), InlineKeyboardButton("🎬 مراجعة", callback_data="nav_rev")],
          [InlineKeyboardButton("📊 فحص السعة", callback_data="nav_stats"), InlineKeyboardButton("⚙️ الإدارة", callback_data="nav_adm")],
          [InlineKeyboardButton("🔄 تبديل النظام", callback_data="back_home")]]
    
    text = f"⚙️ لوحة تحكم: <b>{sys_name}</b>\nالجلسة نشطة لمدة 48 ساعة ✅"
    if update.callback_query: await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    return MENU

# --- 6. نظام الرفع المصلح (مع فحص السعة) ---

async def handle_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    sections = get_user_sections(context.user_data['sys_type'])
    
    if q.data == "nav_up":
        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in sections]
        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
        await q.edit_message_text("📤 اختر القسم للرفع:", reply_markup=InlineKeyboardMarkup(kb))
        return SELECT_UP
    
    elif q.data == "nav_stats":
        await q.edit_message_text("⏳ جاري فحص السعة الحية...")
        report = "📊 <b>تقرير السعة:</b>\n\n"
        for i, creds in sections.items():
            try:
                r = requests.get("https://api.mux.com/video/v1/assets", params={"limit": 1}, auth=(creds["id"], creds["secret"]), timeout=5)
                count = r.json().get("total_row_count", 0)
                status = "🔴 ممتلئ" if count >= 95 else "🟢 متاح"
                report += f"📍 القسم {i}: <b>{count}/100</b> | {status}\n"
            except: report += f"📍 القسم {i}: ⚠️ خطأ\n"
        await q.edit_message_text(report + "\n/start للعودة.", parse_mode=ParseMode.HTML); return MENU

    elif q.data == "nav_adm":
        kb = [[InlineKeyboardButton("🗑 حذف فيلم", callback_data="adm_del")], [InlineKeyboardButton("🏠 القائمة", callback_data="back_menu")]]
        await q.edit_message_text("⚙️ <b>قسم الإدارة</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        return ADMIN_HOME

async def start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sec_id = update.callback_query.data.split("_")[1]
    creds = get_user_sections(context.user_data['sys_type'])[sec_id]
    
    # فحص السعة قبل الرفع
    r = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]))
    if len(r.json().get("data", [])) >= 99:
        await update.callback_query.answer("⚠️ هذا القسم ممتلئ تماماً! اختر قسماً آخر.", show_alert=True)
        return SELECT_UP
    
    context.user_data["active_sec"] = sec_id
    await update.callback_query.edit_message_text("✏️ أرسل <b>اسم الفيلم</b>:")
    return NAMING

async def execute_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    v_url = update.message.text
    sec_id = context.user_data["active_sec"]
    movie_name = context.user_data["active_name"]
    creds = get_user_sections(context.user_data['sys_type'])[sec_id]
    
    msg = await update.message.reply_text("⏳ جاري الرفع...")
    try:
        r = requests.post("https://api.mux.com/video/v1/assets", 
                          json={"input": v_url, "playback_policy": ["public"], "passthrough": movie_name}, 
                          auth=(creds["id"], creds["secret"]))
        if r.status_code == 201:
            pid = r.json()["data"]["playback_ids"][0]["id"]
            await msg.edit_text(f"✅ تم الرفع!\nالفيلم: {movie_name}\nالكود: <code>{pid}</code>\n\nأرسل اسم الفيلم التالي الآن:", parse_mode=ParseMode.HTML)
            return NAMING
    except: await msg.edit_text("❌ خطأ في الرفع.")
    return MENU

# --- 7. نظام الحذف المصلح (Async) ---

async def list_vids_for_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sys_type = context.user_data['sys_type']
    sections = get_user_sections(sys_type)
    # هنا تختار القسم للحذف منه
    btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"dsec_{i}") for i in sections]
    kb = [btns[i:i+3] for i in range(0, len(btns), 3)]
    await update.callback_query.edit_message_text("🗑 اختر القسم للحذف منه:", reply_markup=InlineKeyboardMarkup(kb))
    return SELECT_DEL_VID

async def delete_video_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    asset_id = q.data.split("_")[1]
    sec_id = context.user_data['active_del_sec']
    creds = get_user_sections(context.user_data['sys_type'])[sec_id]
    
    # استخدام asyncio.to_thread لمنع التجمد أثناء الحذف
    await q.answer("⏳ جاري الحذف...")
    res = await asyncio.to_thread(requests.delete, f"https://api.mux.com/video/v1/assets/{asset_id}", auth=(creds["id"], creds["secret"]))
    
    if res.status_code == 204: await q.answer("✅ تم الحذف بنجاح!", show_alert=True)
    else: await q.answer("❌ فشل الحذف.", show_alert=True)
    return await show_menu(update, context)

# --- 8. تشغيل البوت ---

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_SYSTEM: [CallbackQueryHandler(handle_system_choice, pattern="^sys_")],
            AUTH_WAIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            MENU: [CallbackQueryHandler(handle_nav, pattern="^nav_"), CallbackQueryHandler(start, pattern="back_home")],
            SELECT_UP: [CallbackQueryHandler(start_upload, pattern="^up_")],
            NAMING: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: (c.user_data.update({"active_name": u.message.text}), u.message.reply_text("🔗 أرسل الرابط:"))[1])],
            LINKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_upload)],
            ADMIN_HOME: [CallbackQueryHandler(list_vids_for_del, pattern="adm_del"), CallbackQueryHandler(show_menu, pattern="back_menu")],
            SELECT_DEL_VID: [CallbackQueryHandler(delete_video_action, pattern="^kill_")],
        },
        fallbacks=[CommandHandler("start", start)], allow_reentry=True
    )
    
    app.add_handler(conv)
    print("Bot is LIVE with Dual-System Mode...")
    app.run_polling()
