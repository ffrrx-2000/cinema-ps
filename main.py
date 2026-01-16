import os

import requests

import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import (

    ApplicationBuilder, CommandHandler, MessageHandler,

    CallbackQueryHandler, filters, ContextTypes, ConversationHandler

)

from telegram.constants import ParseMode



# ================== 1. الإعدادات ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_PASSWORD = "1460" 

MAX_CAPACITY = 10  # الحد الحقيقي للأقسام المجانية في Mux



def get_all_mux():

    """قائمة الأقسام الـ 19 الخاصة بـ Shoof Play"""

    return {

        "1": {"id": "A058bf43-4c80-49d6-b902-b0fd00cfff18", "secret": "+q5bNYmCQyhii+HdXN8RB4jadh704TVtZVp2qqtlwAmNhX5mhibj/0Yg/UALbysMjVfUxO6qTBA"},

        "2": {"id": "664f5ab9-4b93-4a85-9cdc-39bed76857dd", "secret": "RZG8KZLJkd/+30Idcq26otBmje36qrQTWx3QWdqUErAjhonVPsCIYVZnFq5gLo/nGzAk5GWz5gl"},

        "3": {"id": "6984f132-ca88-4c86-aac4-d10e44594548", "secret": "C9rWwb3cVH2WUXD7no5co4g/bSIFPox12pmB2xggsCQuBa1/RVDq/5aigHW9Drr5aLTi60SLK5Y"},

        "4": {"id": "3888e6fc-1e13-4f91-8e03-5d73aab3375c", "secret": "DcedrXuHMmxvbiJby+A8nt0U5LhFOPDvNpFAMuREwRZ/boh1yfG09Gw35e46krTWXvyCZ0ToRQ0"},

        "5": {"id": "06b5abfd-de0f-4acb-87a0-7716d8951115", "secret": "QZCYyNNCHcAuTk3Y+XvpP/uWIThW57mVWMyBagiNiFeMVBVZaB0e1deXazxLfBef/H77XVkIWkG"},

        "6": {"id": "2d3edb5b-dc6e-4af3-917f-726434532b3c", "secret": "SP5m9+Vc4eGwITG/nUbYNfbdnkYcR6hDIkZz6FZ8ni9ocsTeva6dKbmP/SfoOcwaEaZ4dMkO95d"},

        "7": {"id": "4a32292d-e7ee-492d-b43c-57ce8b8a2095", "secret": "3tklq+6lYCEUedNEyliywgieRM3jDW6XTWiB+CDI1Zs0TEUC4GweXsAIq08LQbK9ebReIaiOTK4"},

        "8": {"id": "0d8b2a67-2c1c-474e-a1a3-cbdfb3e56cb1", "secret": "K6jv2a+cNTVndUuM94VvLnu54be2wBFg9a8q0TdqoRv98qu+UHJ9+vIc0u1Ax59eBtoVgyWlA4G"},

        "9": {"id": "d732c626-11ec-43bd-90f0-50b9c96489ef", "secret": "tGVwrWhcwU9DzhBrgnyvWbVkt1i7nmw8e6B5D0PozwhJ14NHmg+u4nMQrknZOu0NssnNmANGDW9"},

        "10": {"id": "1bb7a1e8-ba83-419e-9796-d8f95fd6767f", "secret": "dD+2uEj5mR2g/6N5RmsDZhLQ0hk7EVhvTBgS43UQqYNtpBUQxdz9dxMDeoVpXT3VLStO/x3HHql"},

        "11": {"id": "44acb746-ade9-4b1a-9202-99f319e22647", "secret": "oLeB+xQt1EFGMVkwonV1O2iRKxGbBUdHuo1oF+vEUbU4r3NoucOgcaUXH5vgefM02DNF2aCI90P"},

        "12": {"id": "cfefbf91-c4b8-4b49-9c85-5f4e3fb2fbd3", "secret": "H6pC+M1B96SQBrOBe6twQ1+glm3Stu8eroGMcs7Y5dtNy9Dkj7YacQBzXdONGM+p9l1R8r8LzPA"},

        "13": {"id": "cc28a604-d2df-4d8f-a7a9-55a6e5722bf6", "secret": "VeYbzua6o/e0IpCclkImkrOriueb2RbqvpXo///A/V4T89kLFFr8PE2/ZqZiJPlg74IU6c8IGZs"},

        "14": {"id": "e85fa620-de3d-4366-962f-d57faa83838e", "secret": "dj5ujB9t4a7sQNzT7k4otAotEVBK01RasBhaI3c6M6nveOdmCUtr9kSjuVzROOezPy9iAj+ksxY"},

        "15": {"id": "16c71792-9fa2-4381-9793-12256695a0bd", "secret": "F496wajL4fRk7QWj9tnBCbTwuGC4Ybjn8Me6L+fZJxtFenI/WtcD8yeFnPCKZiiGxQBCCTZcQIy"},

        "16": {"id": "3bd99e7d-5805-45e7-90ba-cf7395bea2ec", "secret": "2cTSi3G5LkqJ9/TLMXezMZ6Q+AZNBCpgKRTe/PLH3lyFtijhpGJJ34sEenktHll7anjDCszqopT"},

        "17": {"id": "2f230bba-92a3-425a-a235-ba792a6cda4e", "secret": "LyoGF6sbby1ajGKvCQKak11/7T9jPNKWt8sF4uTCMppjisoq8lIAHwQalyaNcnaAepcLNgwPoQ1"},

        "18": {"id": "ba238656-8a32-40ea-b8ea-edaabd17ea4e", "secret": "hjJh8oSOZ0nznssaR9iioEAQ3gHiq9aQEUUbw8+PrqSRkr9VE69fhC6wlqa0gYU1asz7JNo/c32"},

        "19": {"id": "5414c527-5e37-4229-b761-0a7f4343b6d8", "secret": "zOWmBPj7pM3vj4lTy9NzFj//qFhbRaJFqqarfDsSJ55hTo+mP0XeR07mAS8uC3OcDbGzdcRFE3S"}

    }



(MENU, AUTH_ADMIN, ADMIN_HOME, SELECT_UP, NAMING, LINKING, SELECT_REV, SELECT_ADM_DEL) = range(8)



# ================== 2. نظام التنبيهات ==================

async def check_video_status(context: ContextTypes.DEFAULT_TYPE):

    job = context.job

    asset_id, creds, chat_id, movie_name = job.data['asset_id'], job.data['creds'], job.data['chat_id'], job.data['movie_name']

    try:

        r = requests.get(f"https://api.mux.com/video/v1/assets/{asset_id}", auth=(creds["id"], creds["secret"]), timeout=10)

        if r.status_code == 200 and r.json()["data"]["status"] == "ready":

            p_id = r.json()["data"]["playback_ids"][0]["id"]

            stream_url = f"https://stream.mux.com/{p_id}.m3u8"

            text = f"🌟 <b>الفيلم جاهز الآن!</b>\n\n🎬 الاسم: <b>{movie_name}</b>\n🔗 الرابط المباشر:\n<code>{stream_url}</code>"

            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)

            job.schedule_removal()

    except: pass



# ================== 3. الدوال الرئيسية ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    kb = [[InlineKeyboardButton("📤 رفع فيلم", callback_data="nav_up"), InlineKeyboardButton("🎬 مراجعة", callback_data="nav_rev")],

          [InlineKeyboardButton("📊 فحص السعة الحقيقية", callback_data="nav_stats"), InlineKeyboardButton("⚙️ الإدارة", callback_data="nav_adm")]]

    text = "🎬 <b>لوحة تحكم Shoof Play</b>\nأهلاً بك! الرجاء اختيار عملية:"

    if update.callback_query:

        await update.callback_query.answer()

        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    else:

        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    return MENU



async def navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query; await q.answer()

    sections = get_all_mux()

    if q.data == "nav_up":

        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"up_{i}") for i in sections]

        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]; kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])

        await q.edit_message_text("📤 اختر القسم للرفع إليه:", reply_markup=InlineKeyboardMarkup(kb)); return SELECT_UP

    elif q.data == "nav_rev":

        btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"rev_{i}") for i in sections]

        kb = [btns[i:i+3] for i in range(0, len(btns), 3)]; kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])

        await q.edit_message_text("🎬 اختر القسم للمراجعة واستخراج الروابط:", reply_markup=InlineKeyboardMarkup(kb)); return SELECT_REV

    elif q.data == "nav_stats":

        await q.edit_message_text("⏳ جاري الاتصال بـ Mux وفحص السعة الحقيقية لكل قسم...")

        report = "📊 <b>تقرير السعة الحقيقية (الحد 10 أفلام):</b>\n\n"

        for i, creds in sections.items():

            try:

                # طلب قائمة الأصول لمعرفة العدد الحقيقي الحالي

                r = requests.get("https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]), timeout=10)

                if r.status_code == 200:

                    assets_list = r.json().get("data", [])

                    count = len(assets_list)

                    status = "🔴 ممتلئ" if count >= MAX_CAPACITY else "🟢 متاح"

                    report += f"📍 القسم {i}: <b>{count}/{MAX_CAPACITY}</b> فيلم | {status}\n"

                else: report += f"📍 القسم {i}: ⚠️ خطأ في المصادقة\n"

            except: report += f"📍 القسم {i}: ⚠️ خطأ اتصال\n"

        kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_home")]]

        await q.edit_message_text(report, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML); return MENU

    elif q.data == "nav_adm":

        if context.user_data.get("is_admin"): return await admin_home(update, context)

        await q.edit_message_text("🔐 أرسل كلمة المرور للدخول للإدارة:"); return AUTH_ADMIN



# ================== 4. الرفع والمراجعة ==================

async def start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query; await q.answer()

    context.user_data["sec"] = q.data.split("_")[1]

    await q.edit_message_text("✏️ أرسل <b>اسم الفيلم</b>:"); return NAMING



async def upload_name(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["name"] = update.message.text

    await update.message.reply_text("🔗 أرسل <b>رابط الفيديو المباشر</b>:"); return LINKING



async def upload_video(update: Update, context: ContextTypes.DEFAULT_TYPE):

    sec, movie_name = context.user_data["sec"], context.user_data["name"]

    creds = get_all_mux().get(sec)

    r = requests.post("https://api.mux.com/video/v1/assets", 

                      json={"input": update.message.text, "playback_policy": ["public"], "passthrough": movie_name}, 

                      auth=(creds["id"], creds["secret"]))

    if r.status_code == 201:

        data = r.json()["data"]

        p_id = data["playback_ids"][0]["id"]

        stream_url = f"https://stream.mux.com/{p_id}.m3u8"

        text = f"✅ <b>بدأ الرفع بنجاح</b>\n🎬 الفيلم: <b>{movie_name}</b>\n🔗 الرابط المباشر (انسخه):\n<code>{stream_url}</code>\n\n⏳ سيصلك إشعار فور اكتمال معالجة الفيديو."

        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

        context.job_queue.run_repeating(check_video_status, interval=60, first=30, 

                                        data={'asset_id': data["id"], 'creds': creds, 'chat_id': update.message.chat_id, 'movie_name': movie_name})

    else: await update.message.reply_text("❌ فشل الرفع. تأكد من صحة الرابط أو سعة الحساب."); return NAMING



async def review_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query; await q.answer(); sec = q.data.split("_")[1]

    creds = get_all_mux().get(sec)

    r = requests.get(f"https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]))

    assets = r.json().get("data", [])

    text = f"🎬 <b>أفلام القسم {sec} وروابط البث:</b>\n\n"

    if not assets: text += "القسم فارغ."

    for a in assets:

        p_id = a.get('playback_ids', [{}])[0].get('id', 'N/A')

        stream_url = f"https://stream.mux.com/{p_id}.m3u8"

        text += f"• <b>{a.get('passthrough','بدون اسم')}</b>\n└ 🔗 <code>{stream_url}</code>\n\n"

    kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="nav_rev")]]

    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML); return MENU



# ================== 5. الإدارة ==================

async def admin_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.delete()

    if update.message.text == ADMIN_PASSWORD:

        context.user_data["is_admin"] = True; return await admin_home(update, context)

    await update.message.reply_text("❌ كلمة مرور خاطئة!"); return MENU



async def admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE):

    kb = [[InlineKeyboardButton("🗑 حذف فيلم", callback_data="adm_del_sec")], [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_home")]]

    text = "⚙️ <b>لوحة إدارة Shoof Play</b>"

    if update.callback_query:

        await update.callback_query.answer()

        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    else:

        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    return ADMIN_HOME



async def admin_del_select_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query; await q.answer()

    btns = [InlineKeyboardButton(f"القسم {i}", callback_data=f"adel_{i}") for i in get_all_mux()]

    kb = [btns[i:i+3] for i in range(0, len(btns), 3)]; kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="nav_adm")])

    await q.edit_message_text("🗑 اختر القسم للحذف منه:", reply_markup=InlineKeyboardMarkup(kb)); return SELECT_ADM_DEL



async def admin_del_list(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query; await q.answer(); sec = q.data.split("_")[1]

    creds = get_all_mux().get(sec)

    r = requests.get(f"https://api.mux.com/video/v1/assets", auth=(creds["id"], creds["secret"]))

    assets = r.json().get("data", [])

    kb = [[InlineKeyboardButton(f"🎬 {a.get('passthrough','...')}", callback_data="none"), InlineKeyboardButton("🗑", callback_data=f"drop_{sec}_{a['id']}")] for a in assets]

    kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_del_sec")])

    await q.edit_message_text(f"🗑 إدارة الحذف للقسم {sec}:", reply_markup=InlineKeyboardMarkup(kb)); return ADMIN_HOME



async def delete_asset_action(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query; await q.answer(); _, sec, asset_id = q.data.split("_")

    creds = get_all_mux().get(sec)

    r = requests.delete(f"https://api.mux.com/video/v1/assets/{asset_id}", auth=(creds["id"], creds["secret"]))

    await q.answer("✅ تم الحذف" if r.status_code == 204 else "❌ خطأ"); return await admin_del_list(update, context)



# ================== 6. التشغيل ==================

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

        ADMIN_HOME: [CallbackQueryHandler(admin_del_select_sec, pattern="adm_del_sec")],

        SELECT_ADM_DEL: [CallbackQueryHandler(admin_del_list, pattern="adel_")],

    },

    fallbacks=[CommandHandler("start", start)], allow_reentry=True

)

app.add_handler(conv); app.run_polling()

    
