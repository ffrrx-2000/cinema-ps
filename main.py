import os
import asyncio
import time
from datetime import datetime, timedelta
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")

CINEMA_PLUS_PASSWORD = "67146"
SHOOF_PLAY_PASSWORD = "1460"

CINEMA_PLUS_SECTIONS = {
    "1": {
        "id": "dd686bd9-2119-44b5-a8cf-37d1cd95a1a5",
        "secret": "D4nzOMDyTJUWrztXyAQsjGnWcS5sqgCZTchPB8HLIXkRY3fXK9Y5aXgMFnYhjUQKzpQ8iBNwkMO",
    },
    "2": {
        "id": "3522203d-1925-4ec3-a5f7-9ca9efd1771a",
        "secret": "p7fHTPl4hFvLh1koWPHlJ7cif9GcOCFxDAYHIAraC4mcGABRrJWp2jNJ4B4cVgIcE2YOY+AT1wb",
    },
    "3": {
        "id": "85501be0-bc4f-415c-afde-b8ac1b996974",
        "secret": "QXzmzVANcX9VrS2vBCTa0h91+QAlr7iM5izLDrzKUDdhSx2sJx2CuNFT6CJHpqOsftsW2MICpci",
    },
    "4": {
        "id": "7894140e-03a9-4946-9698-1b58f1e3ea38",
        "secret": "HwgZg1a7h05ul/AYpeICooOp0fOt4o7W9Fxf0am2z4Qb1QyHfIL3BRMjxh1e6b1Dn+WXehKdjaN",
    },
    "5": {
        "id": "147d1438-4269-4739-ae68-7dcbdf9f1d84",
        "secret": "6cqf9LKM38Q7gbkrrYmWGNwH0v27UjY8DzQWRDZ1Md137UE7+n52NlBGIVc/4qaShADTH5D+LsU",
    },
    "6": {
        "id": "60d38bcd-bb17-4db0-9599-129c232cdabf",
        "secret": "E9j1AbbGropItPcS4K+Gl1csebAiLMJJuglGn9NxIasbJAmM/CsVXTL9BCyw+jBwsR7Zq51RJy2",
    },
    "7": {
        "id": "31517bbe-2628-438e-b7ac-261708d6f26e",
        "secret": "pnHQhp05xWhu6tSc8u98c3x47ycmT7zhW3V6mzxlSmqz30vac71VmsHYgRUBI5aDuBFYBIlkcF4",
    },
    "8": {
        "id": "4c53f771-ab87-4dab-9484-2f7f94799f6e",
        "secret": "rWXTB3ktFkyvcKQkJwD6tcOT+6sV1dM3ndU/H4oZu5qnG6/+2WIw4keq2DPFU+F0foJ57eI0BPz",
    },
    "9": {
        "id": "0f39d0e7-33d9-4983-a20d-c20a54a39d19",
        "secret": "GG2UNHGjJysTBxe32+VOGEOpLGSEUGINWVvEFyhz+inbm+G41LNi/Hua8Kd9pqeRO+FOLyLgk5/",
    },
    "10": {
        "id": "fcbfcdcb-fbd3-41ae-ab10-5451502ac8d3",
        "secret": "NtwphUQyZZsrhOXgadrZN3QoJXxMVW2za+q0xFe/1vLl4PfRjrGCOn18BOqpGFMCFZAc/g2rR0R",
    },
}

SHOOF_PLAY_SECTIONS = {
    "1": {
        "id": "b6a28905-15dd-4c4e-8455-116d1934820f",
        "secret": "Z8P9cIYFf49ElRMqGECViG/O5N/qRz8U5ux2r7uhIX2Yp950dgI0DTvWCvUoaeL6rXIaZQ6q+VY",
    },
    "2": {
        "id": "a058bf43-4c80-49d6-b902-b0fd00cfff18",
        "secret": "+q5bNYmCQyhii+HdXN8RB4jadh704TVtZVp2qqtlwAmNhX5mhibj/0Yg/UALbysMjVfUxO6qTBA",
    },
    "3": {
        "id": "664f5ab9-4b93-4a85-9cdc-39bed76857dd",
        "secret": "RZG8KZLJkd/+30Idcq26otBmje36qrQTWx3QWdqUErAjhonVPsCIYVZnFq5gLo/nGzAk5GWz5gl",
    },
    "4": {
        "id": "6984f132-ca88-4c86-aac4-d10e44594548",
        "secret": "C9rWwb3cVH2WUXD7no5co4g/bSIFPox12pmB2xggsCQuBa1/RVDq/5aigHW9Drr5aLTi60SLK5Y",
    },
    "5": {
        "id": "3888e6fc-1e13-4f91-8e03-5d73aab3375c",
        "secret": "DcedrXuHMmxvbiJby+A8nt0U5LhFOPDvNpFAMuREwRZ/boh1yfG09Gw35e46krTWXvyCZ0ToRQ0",
    },
    "6": {
        "id": "06b5abfd-de0f-4acb-87a0-7716d8951115",
        "secret": "QZCYyNNCHcAuTk3Y+XvpP/uWIThW57mVWMyBagiNiFeMVBVZaB0e1deXazxLfBef/H77XVkIWkG",
    },
    "7": {
        "id": "2d3edb5b-dc6e-4af3-917f-726434532b3c",
        "secret": "SP5m9+Vc4eGwITG/nUbYNfbdnkYcR6hDIkZz6FZ8ni9ocsTeva6dKbmP/SfoOcwaEaZ4dMkO95d",
    },
    "8": {
        "id": "4a32292d-e7ee-492d-b43c-57ce8b8a2095",
        "secret": "3tklq+6lYCEUedNEyliywgieRM3jDW6XTWiB+CDI1Zs0TEUC4GweXsAIq08LQbK9ebReIaiOTK4",
    },
    "9": {
        "id": "0d8b2a67-2c1c-474e-a1a3-cbdfb3e56cb1",
        "secret": "K6jv2a+cNTVndUuM94VvLnu54be2wBFg9a8q0TdqoRv98qu+UHJ9+vIc0u1Ax59eBtoVgyWlA4G",
    },
    "10": {
        "id": "d732c626-11ec-43bd-90f0-50b9c96489ef",
        "secret": "tGVwrWhcwU9DzhBrgnyvWbVkt1i7nmw8e6B5D0PozwhJ14NHmg+u4nMQrknZOu0NssnNmANGDW9",
    },
    "11": {
        "id": "1bb7a1e8-ba83-419e-9796-d8f95fd6767f",
        "secret": "dD+2uEj5mR2g/6N5RmsDZhLQ0hk7EVhvTBgS43UQqYNtpBUQxdz9dxMDeoVpXT3VLStO/x3HHql",
    },
    "12": {
        "id": "44acb746-ade9-4b1a-9202-99f319e22647",
        "secret": "oLeB+xQt1EFGMVkwonV1O2iRKxGbBUdHuo1oF+vEUbU4r3NoucOgcaUXH5vgefM02DNF2aCI90P",
    },
    "13": {
        "id": "cfefbf91-c4b8-4b49-9c85-5f4e3fb2fbd3",
        "secret": "H6pC+M1B96SQBrOBe6twQ1+glm3Stu8eroGMcs7Y5dtNy9Dkj7YacQBzXdONGM+p9l1R8r8LzPA",
    },
    "14": {
        "id": "cc28a604-d2df-4d8f-a7a9-55a6e5722bf6",
        "secret": "VeYbzua6o/e0IpCclkImkrOriueb2RbqvpXo///A/V4T89kLFFr8PE2/ZqZiJPlg74IU6c8IGZs",
    },
    "15": {
        "id": "e85fa620-de3d-4366-962f-d57faa83838e",
        "secret": "dj5ujB9t4a7sQNzT7k4otAotEVBK01RasBhaI3c6M6nveOdmCUtr9kSjuVzROOezPy9iAj+ksxY",
    },
    "16": {
        "id": "16c71792-9fa2-4381-9793-12256695a0bd",
        "secret": "F496wajL4fRk7QWj9tnBCbTwuGC4Ybjn8Me6L+fZJxtFenI/WtcD8yeFnPCKZiiGxQBCCTZcQIy",
    },
    "17": {
        "id": "3bd99e7d-5805-45e7-90ba-cf7395bea2ec",
        "secret": "2cTSi3G5LkqJ9/TLMXezMZ6Q+AZNBCpgKRTe/PLH3lyFtijhpGJJ34sEenktHll7anjDCszqopT",
    },
    "18": {
        "id": "2f230bba-92a3-425a-a235-ba792a6cda4e",
        "secret": "LyoGF6sbby1ajGKvCQKak11/7T9jPNKWt8sF4uTCMppjisoq8lIAHwQalyaNcnaAepcLNgwPoQ1",
    },
    "19": {
        "id": "ba238656-8a32-40ea-b8ea-edaabd17ea4e",
        "secret": "hjJh8oSOZ0nznssaR9iioEAQ3gHiq9aQEUUbw8+PrqSRkr9VE69fhC6wlqa0gYU1asz7JNo/c32",
    },
    "20": {
        "id": "5414c527-5e37-4229-b761-0a7f4343b6d8",
        "secret": "zOWmBPj7pM3vj4lTy9NzFj//qFhbRaJFqqarfDsSJ55hTo+mP0XeR07mAS8uC3OcDbGzdcRFE3S",
    },
}

user_auth_cache = {}

(
    SELECT_SYSTEM,
    AUTH_PASSWORD,
    MAIN_MENU,
    SELECT_SECTION_UPLOAD,
    ENTER_VIDEO_NAME,
    ENTER_VIDEO_LINK,
    SELECT_SECTION_REVIEW,
    REVIEW_ACTIONS,
    SELECT_SECTION_PLAYBACK,
    SELECT_SECTION_CAPACITY,
    SELECT_SECTION_DELETE,
    SELECT_VIDEO_DELETE,
    CONFIRM_DELETE,
) = range(13)


def is_user_authenticated(user_id: int, system: str) -> bool:
    key = f"{user_id}_{system}"
    if key in user_auth_cache:
        auth_time = user_auth_cache[key]
        if datetime.now() - auth_time < timedelta(hours=48):
            return True
        else:
            del user_auth_cache[key]
    return False


def authenticate_user(user_id: int, system: str):
    key = f"{user_id}_{system}"
    user_auth_cache[key] = datetime.now()


def get_sections_for_system(system: str) -> dict:
    if system == "cinema_plus":
        return CINEMA_PLUS_SECTIONS
    elif system == "shoof_play":
        return SHOOF_PLAY_SECTIONS
    return {}


def get_password_for_system(system: str) -> str:
    if system == "cinema_plus":
        return CINEMA_PLUS_PASSWORD
    elif system == "shoof_play":
        return SHOOF_PLAY_PASSWORD
    return ""


def get_system_name(system: str) -> str:
    if system == "cinema_plus":
        return "سينما بلس"
    elif system == "shoof_play":
        return "شوف بلاي"
    return ""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🎬 سينما بلس", callback_data="system_cinema_plus")],
        [InlineKeyboardButton("📺 شوف بلاي", callback_data="system_shoof_play")],
    ]
    await update.message.reply_text(
        "🎬 <b>مرحباً بك في بوت إدارة الفيديوهات</b>\n\n"
        "الرجاء اختيار النظام للدخول:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return SELECT_SYSTEM


async def select_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    system = query.data.replace("system_", "")
    context.user_data["system"] = system
    user_id = update.effective_user.id

    if is_user_authenticated(user_id, system):
        return await show_main_menu(update, context, edit=True)

    system_name = get_system_name(system)
    await query.edit_message_text(
        f"🔐 <b>تسجيل الدخول - {system_name}</b>\n\n"
        "الرجاء إدخال كلمة المرور للدخول إلى هذا النظام:",
        parse_mode=ParseMode.HTML,
    )
    return AUTH_PASSWORD


async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    system = context.user_data.get("system")
    user_id = update.effective_user.id
    correct_password = get_password_for_system(system)

    try:
        await update.message.delete()
    except:
        pass

    if password == correct_password:
        authenticate_user(user_id, system)
        system_name = get_system_name(system)
        await update.message.reply_text(
            f"✅ <b>تم تسجيل الدخول بنجاح!</b>\n\n"
            f"مرحباً بك في {system_name}. جلستك صالحة لمدة 48 ساعة.",
            parse_mode=ParseMode.HTML,
        )
        return await show_main_menu(update, context, edit=False)
    else:
        await update.message.reply_text(
            "❌ <b>كلمة المرور غير صحيحة</b>\n\n"
            "الرجاء المحاولة مرة أخرى أو استخدام /start لاختيار نظام آخر.",
            parse_mode=ParseMode.HTML,
        )
        return AUTH_PASSWORD


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    system = context.user_data.get("system")
    system_name = get_system_name(system)
    sections = get_sections_for_system(system)
    section_count = len(sections)

    keyboard = [
        [InlineKeyboardButton("📤 رفع فيديو", callback_data="menu_upload")],
        [InlineKeyboardButton("🔍 مراجعة القسم", callback_data="menu_review")],
        [InlineKeyboardButton("🗑️ حذف فيديو", callback_data="menu_delete")],
        [InlineKeyboardButton("🎞️ عرض معرفات التشغيل", callback_data="menu_playback")],
        [InlineKeyboardButton("📊 فحص السعة المباشر", callback_data="menu_capacity")],
        [InlineKeyboardButton("🔙 تبديل النظام", callback_data="menu_switch")],
    ]

    text = (
        f"🎬 <b>إدارة {system_name}</b>\n\n"
        f"📁 إجمالي الأقسام: {section_count}\n"
        f"🔐 الجلسة نشطة: 48 ساعة\n\n"
        "اختر إجراء:"
    )

    if edit:
        query = update.callback_query
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
    return MAIN_MENU


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "menu_upload":
        return await show_section_selector(update, context, "upload")
    elif action == "menu_review":
        return await show_section_selector(update, context, "review")
    elif action == "menu_delete":
        return await show_section_selector(update, context, "delete")
    elif action == "menu_playback":
        return await show_section_selector(update, context, "playback")
    elif action == "menu_capacity":
        return await show_section_selector(update, context, "capacity")
    elif action == "menu_switch":
        keyboard = [
            [InlineKeyboardButton("🎬 سينما بلس", callback_data="system_cinema_plus")],
            [InlineKeyboardButton("📺 شوف بلاي", callback_data="system_shoof_play")],
        ]
        await query.edit_message_text(
            "🎬 <b>اختر النظام</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return SELECT_SYSTEM
    elif action == "menu_back":
        return await show_main_menu(update, context, edit=True)


async def show_section_selector(update: Update, context: ContextTypes.DEFAULT_TYPE, action_type: str):
    query = update.callback_query
    system = context.user_data.get("system")
    sections = get_sections_for_system(system)
    system_name = get_system_name(system)

    context.user_data["action_type"] = action_type

    keyboard = []
    row = []
    for i, section_id in enumerate(sections.keys(), 1):
        callback_data = f"section_{action_type}_{section_id}"
        row.append(InlineKeyboardButton(f"قسم {section_id}", callback_data=callback_data))
        if i % 5 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")])

    action_titles = {
        "upload": "📤 رفع فيديو",
        "review": "🔍 مراجعة القسم",
        "delete": "🗑️ حذف فيديو",
        "playback": "🎞️ عرض معرفات التشغيل",
        "capacity": "📊 فحص السعة",
    }

    await query.edit_message_text(
        f"<b>{action_titles[action_type]} - {system_name}</b>\n\n"
        "اختر القسم:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

    state_mapping = {
        "upload": SELECT_SECTION_UPLOAD,
        "review": SELECT_SECTION_REVIEW,
        "delete": SELECT_SECTION_DELETE,
        "playback": SELECT_SECTION_PLAYBACK,
        "capacity": SELECT_SECTION_CAPACITY,
    }
    return state_mapping[action_type]


async def handle_upload_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        return await show_main_menu(update, context, edit=True)

    section_id = query.data.split("_")[2]
    system = context.user_data.get("system")
    sections = get_sections_for_system(system)
    creds = sections[section_id]

    try:
        res = requests.get(
            "https://api.mux.com/video/v1/assets",
            auth=(creds["id"], creds["secret"]),
            timeout=10,
        )
        assets = res.json().get("data", [])
        count = len(assets)
    except Exception as e:
        await query.edit_message_text(
            f"⚠️ <b>خطأ في الاتصال</b>\n\nفشل الاتصال بـ Mux API: {str(e)}\n\n"
            "استخدم /start للمحاولة مرة أخرى.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    if count >= 10:
        await query.answer("⚠️ القسم ممتلئ (10/10 فيديو)", show_alert=True)
        return SELECT_SECTION_UPLOAD

    context.user_data["section_id"] = section_id
    context.user_data["section_creds"] = creds

    await query.edit_message_text(
        f"📤 <b>الرفع إلى القسم {section_id}</b>\n\n"
        f"📊 السعة الحالية: {count}/10\n"
        f"📁 الأماكن المتاحة: {10 - count}\n\n"
        "<b>الرجاء إدخال اسم الفيديو:</b>",
        parse_mode=ParseMode.HTML,
    )
    return ENTER_VIDEO_NAME


async def handle_video_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_name = update.message.text.strip()
    context.user_data["video_name"] = video_name

    await update.message.reply_text(
        f"📝 <b>اسم الفيديو:</b> {video_name}\n\n"
        "<b>الآن أرسل رابط الفيديو:</b>",
        parse_mode=ParseMode.HTML,
    )
    return ENTER_VIDEO_LINK


async def handle_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_url = update.message.text.strip()
    section_id = context.user_data.get("section_id")
    creds = context.user_data.get("section_creds")
    video_name = context.user_data.get("video_name")
    system = context.user_data.get("system")
    system_name = get_system_name(system)

    try:
        await update.message.delete()
    except:
        pass

    status_msg = await update.message.reply_text(
        "⏳ <b>جاري الرفع إلى Mux...</b>\n\n"
        "الرجاء الانتظار بينما نعالج الفيديو الخاص بك.",
        parse_mode=ParseMode.HTML,
    )

    try:
        response = requests.post(
            "https://api.mux.com/video/v1/assets",
            json={
                "input": [{"url": video_url}],
                "playback_policy": ["public"],
                "passthrough": video_name,
            },
            auth=(creds["id"], creds["secret"]),
            timeout=30,
        )

        if response.status_code == 201:
            res_data = response.json()["data"]
            asset_id = res_data["id"]
            playback_ids = res_data.get("playback_ids", [])
            playback_id = playback_ids[0]["id"] if playback_ids else "قيد الانتظار..."

            stream_url = f"https://stream.mux.com/{playback_id}.m3u8" if playback_id != "قيد الانتظار..." else "قيد الانتظار..."

            keyboard = [
                [InlineKeyboardButton("📤 رفع فيديو آخر", callback_data=f"section_upload_{section_id}")],
                [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
            ]

            await status_msg.edit_text(
                f"✅ <b>تم الرفع بنجاح!</b>\n\n"
                f"🎬 <b>النظام:</b> {system_name}\n"
                f"📁 <b>القسم:</b> {section_id}\n"
                f"🎥 <b>اسم الفيديو:</b> {video_name}\n"
                f"🔗 <b>رابط التشغيل:</b>\n<code>{stream_url}</code>\n"
                f"🆔 <b>Playback ID:</b>\n<code>{playback_id}</code>\n\n"
                "<i>جاري تتبع حالة الأصل...</i>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )

            asyncio.create_task(
                track_asset_status(
                    update.effective_chat.id,
                    context.bot,
                    asset_id,
                    creds,
                    video_name,
                    playback_id,
                )
            )

            return MAIN_MENU
        else:
            error_msg = response.json().get("error", {}).get("message", "خطأ غير معروف")
            await status_msg.edit_text(
                f"❌ <b>فشل الرفع</b>\n\n"
                f"الخطأ: {error_msg}\n"
                f"رمز الحالة: {response.status_code}\n\n"
                "استخدم /start للمحاولة مرة أخرى.",
                parse_mode=ParseMode.HTML,
            )
            return ConversationHandler.END
    except Exception as e:
        await status_msg.edit_text(
            f"⚠️ <b>خطأ</b>\n\n{str(e)}\n\n" "استخدم /start للمحاولة مرة أخرى.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END


async def track_asset_status(chat_id, bot, asset_id, creds, video_name, playback_id):
    url = f"https://api.mux.com/video/v1/assets/{asset_id}"
    for attempt in range(45):
        await asyncio.sleep(20)
        try:
            res = requests.get(url, auth=(creds["id"], creds["secret"]), timeout=10)
            if res.status_code == 200:
                data = res.json()["data"]
                status = data.get("status")
                if status == "ready":
                    final_playback_id = playback_id
                    if data.get("playback_ids"):
                        final_playback_id = data["playback_ids"][0]["id"]
                    stream_url = f"https://stream.mux.com/{final_playback_id}.m3u8" if final_playback_id != "قيد الانتظار..." else "قيد الانتظار..."

                    await bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"✨ <b>الفيديو جاهز!</b>\n\n"
                            f"🎥 <b>الفيديو:</b> {video_name}\n"
                            f"✅ <b>الحالة:</b> جاهز للتشغيل\n"
                            f"🔗 <b>رابط التشغيل:</b>\n<code>{stream_url}</code>\n"
                            f"🆔 <b>Playback ID:</b>\n<code>{final_playback_id}</code>"
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                    return
                elif status == "errored":
                    await bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"🚨 <b>تنبيه: فشل معالجة الفيديو!</b>\n\n"
                            f"🎥 <b>الفيديو:</b> {video_name}\n"
                            f"❌ <b>الحالة:</b> خطأ في المعالجة\n\n"
                            f"⚠️ <b>الرابط المصدر غير شغال!</b>\n"
                            f"📌 <b>تأكد من أن الرابط يعمل بشكل صحيح</b>\n\n"
                            f"<i>يرجى التحقق من الرابط والمحاولة مرة أخرى.</i>"
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                    return
        except:
            pass


async def handle_review_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        return await show_main_menu(update, context, edit=True)

    section_id = query.data.split("_")[2]
    system = context.user_data.get("system")
    sections = get_sections_for_system(system)
    creds = sections[section_id]
    system_name = get_system_name(system)

    context.user_data["review_section_id"] = section_id
    context.user_data["review_creds"] = creds

    await query.edit_message_text(
        f"⏳ <b>جاري جلب الأصول من القسم {section_id}...</b>",
        parse_mode=ParseMode.HTML,
    )

    try:
        res = requests.get(
            "https://api.mux.com/video/v1/assets",
            auth=(creds["id"], creds["secret"]),
            timeout=15,
        )
        assets = res.json().get("data", [])

        if not assets:
            keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
            await query.edit_message_text(
                f"📁 <b>القسم {section_id} فارغ</b>\n\n"
                f"النظام: {system_name}\n"
                "لا توجد فيديوهات في هذا القسم.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
            return MAIN_MENU

        text = f"📂 <b>{system_name} - القسم {section_id}</b>\n"
        text += f"📊 إجمالي الفيديوهات: {len(assets)}/10\n\n"

        all_playback_ids = []
        for i, asset in enumerate(assets, 1):
            name = asset.get("passthrough", "بدون عنوان")
            status = asset.get("status", "غير معروف")
            asset_id = asset.get("id", "غير متوفر")
            playback_ids = asset.get("playback_ids", [])
            p_id = playback_ids[0]["id"] if playback_ids else "غير متوفر"

            status_emoji = "✅" if status == "ready" else "⏳" if status == "preparing" else "❌"
            status_ar = "جاهز" if status == "ready" else "قيد التحضير" if status == "preparing" else "خطأ"

            text += f"<b>{i}. {name}</b>\n"
            text += f"   الحالة: {status_emoji} {status_ar}\n"
            text += f"   معرف التشغيل: <code>{p_id}</code>\n\n"

            if p_id != "غير متوفر":
                all_playback_ids.append(p_id)

        context.user_data["all_playback_ids"] = all_playback_ids

        keyboard = [
            [InlineKeyboardButton("📋 نسخ جميع معرفات التشغيل", callback_data="review_copy_all")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
        ]

        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
        return REVIEW_ACTIONS

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
        await query.edit_message_text(
            f"⚠️ <b>خطأ في جلب البيانات</b>\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return MAIN_MENU


async def handle_review_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        return await show_main_menu(update, context, edit=True)

    if query.data == "review_copy_all":
        all_ids = context.user_data.get("all_playback_ids", [])
        if all_ids:
            ids_text = "\n".join(all_ids)
            await query.message.reply_text(
                f"📋 <b>جميع معرفات التشغيل:</b>\n\n<code>{ids_text}</code>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await query.answer("لا توجد معرفات تشغيل متاحة", show_alert=True)
        return REVIEW_ACTIONS


async def handle_playback_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        return await show_main_menu(update, context, edit=True)

    section_id = query.data.split("_")[2]
    system = context.user_data.get("system")
    sections = get_sections_for_system(system)
    creds = sections[section_id]
    system_name = get_system_name(system)

    await query.edit_message_text(
        f"⏳ <b>جاري جلب معرفات التشغيل من القسم {section_id}...</b>",
        parse_mode=ParseMode.HTML,
    )

    try:
        res = requests.get(
            "https://api.mux.com/video/v1/assets",
            auth=(creds["id"], creds["secret"]),
            timeout=15,
        )
        assets = res.json().get("data", [])

        if not assets:
            keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
            await query.edit_message_text(
                f"📁 <b>القسم {section_id} فارغ</b>\n\n" "لا توجد معرفات تشغيل لعرضها.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
            return MAIN_MENU

        text = f"🎞️ <b>{system_name} - معرفات التشغيل للقسم {section_id}</b>\n\n"
        all_ids = []

        for i, asset in enumerate(assets, 1):
            name = asset.get("passthrough", "بدون عنوان")
            playback_ids = asset.get("playback_ids", [])
            p_id = playback_ids[0]["id"] if playback_ids else "غير متوفر"

            text += f"<b>{i}. {name}</b>\n<code>{p_id}</code>\n\n"
            if p_id != "غير متوفر":
                all_ids.append(p_id)

        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]

        if all_ids:
            text += f"\n<b>نسخ سريع (جميع المعرفات):</b>\n<code>{chr(10).join(all_ids)}</code>"

        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
        return MAIN_MENU

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
        await query.edit_message_text(
            f"⚠️ <b>خطأ</b>\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return MAIN_MENU


async def handle_capacity_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        return await show_main_menu(update, context, edit=True)

    if query.data == "capacity_check_all":
        system = context.user_data.get("system")
        sections = get_sections_for_system(system)
        system_name = get_system_name(system)

        await query.edit_message_text(
            f"⏳ <b>جاري فحص سعة جميع الأقسام...</b>\n\n" "قد يستغرق هذا لحظة.",
            parse_mode=ParseMode.HTML,
        )

        text = f"📊 <b>{system_name} - تقرير السعة المباشر</b>\n\n"
        total_used = 0
        total_capacity = len(sections) * 10

        for section_id, creds in sections.items():
            try:
                res = requests.get(
                    "https://api.mux.com/video/v1/assets",
                    auth=(creds["id"], creds["secret"]),
                    timeout=10,
                )
                count = len(res.json().get("data", []))
                total_used += count
                status = "✅" if count < 10 else "⚠️ ممتلئ"
                bar = "█" * count + "░" * (10 - count)
                text += f"القسم {section_id}: [{bar}] {count}/10 {status}\n"
            except:
                text += f"القسم {section_id}: ⚠️ خطأ في الاتصال\n"

        text += f"\n<b>إجمالي الاستخدام:</b> {total_used}/{total_capacity}"
        text += f"\n<b>الأماكن المتاحة:</b> {total_capacity - total_used}"

        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
        return MAIN_MENU

    section_id = query.data.split("_")[2]
    system = context.user_data.get("system")
    sections = get_sections_for_system(system)
    creds = sections[section_id]
    system_name = get_system_name(system)

    await query.edit_message_text(
        f"⏳ <b>جاري فحص سعة القسم {section_id}...</b>",
        parse_mode=ParseMode.HTML,
    )

    try:
        res = requests.get(
            "https://api.mux.com/video/v1/assets",
            auth=(creds["id"], creds["secret"]),
            timeout=10,
        )
        assets = res.json().get("data", [])
        count = len(assets)

        bar = "█" * count + "░" * (10 - count)
        status = "✅ متاح" if count < 10 else "⚠️ ممتلئ"

        text = f"📊 <b>{system_name} - القسم {section_id}</b>\n\n"
        text += f"<b>السعة:</b> [{bar}] {count}/10\n"
        text += f"<b>الحالة:</b> {status}\n"
        text += f"<b>الأماكن المتاحة:</b> {10 - count}\n\n"

        if assets:
            text += "<b>الفيديوهات الحالية:</b>\n"
            for i, asset in enumerate(assets, 1):
                name = asset.get("passthrough", "بدون عنوان")
                asset_status = asset.get("status", "غير معروف")
                emoji = "✅" if asset_status == "ready" else "⏳"
                text += f"{i}. {emoji} {name}\n"

        keyboard = [
            [InlineKeyboardButton("🔄 فحص جميع الأقسام", callback_data="capacity_check_all")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
        ]

        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
        return MAIN_MENU

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
        await query.edit_message_text(
            f"⚠️ <b>خطأ</b>\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return MAIN_MENU


async def handle_delete_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        return await show_main_menu(update, context, edit=True)

    section_id = query.data.split("_")[2]
    system = context.user_data.get("system")
    sections = get_sections_for_system(system)
    creds = sections[section_id]
    system_name = get_system_name(system)

    context.user_data["delete_section_id"] = section_id
    context.user_data["delete_creds"] = creds

    await query.edit_message_text(
        f"⏳ <b>جاري جلب الفيديوهات من القسم {section_id}...</b>",
        parse_mode=ParseMode.HTML,
    )

    try:
        res = requests.get(
            "https://api.mux.com/video/v1/assets",
            auth=(creds["id"], creds["secret"]),
            timeout=15,
        )
        assets = res.json().get("data", [])

        if not assets:
            keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
            await query.edit_message_text(
                f"📁 <b>القسم {section_id} فارغ</b>\n\n"
                f"النظام: {system_name}\n"
                "لا توجد فيديوهات للحذف في هذا القسم.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
            return MAIN_MENU

        context.user_data["delete_assets"] = assets

        text = f"🗑️ <b>{system_name} - حذف من القسم {section_id}</b>\n"
        text += f"📊 إجمالي الفيديوهات: {len(assets)}/10\n\n"
        text += "<b>اختر الفيديو للحذف:</b>\n\n"

        keyboard = []
        for i, asset in enumerate(assets, 1):
            name = asset.get("passthrough") or asset.get("meta", {}).get("name", "بدون عنوان")
            if not name:
                name = "بدون عنوان"
            status = asset.get("status", "غير معروف")
            asset_id = asset.get("id")
            status_emoji = "✅" if status == "ready" else "⏳" if status == "preparing" else "❌"

            text += f"{i}. {status_emoji} {name}\n"
            keyboard.append([InlineKeyboardButton(f"🗑️ {i}. {name[:30]}", callback_data=f"delete_video_{asset_id}")])

        keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")])

        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
        return SELECT_VIDEO_DELETE

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
        await query.edit_message_text(
            f"⚠️ <b>خطأ في جلب البيانات</b>\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return MAIN_MENU


async def handle_video_delete_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        return await show_main_menu(update, context, edit=True)

    asset_id = query.data.replace("delete_video_", "")
    assets = context.user_data.get("delete_assets", [])
    
    selected_asset = None
    for asset in assets:
        if asset.get("id") == asset_id:
            selected_asset = asset
            break

    if not selected_asset:
        await query.answer("⚠️ لم يتم العثور على الفيديو", show_alert=True)
        return SELECT_VIDEO_DELETE

    context.user_data["delete_asset_id"] = asset_id
    video_name = selected_asset.get("passthrough") or selected_asset.get("meta", {}).get("name", "بدون عنوان")
    if not video_name:
        video_name = "بدون عنوان"
    context.user_data["delete_video_name"] = video_name

    section_id = context.user_data.get("delete_section_id")
    system = context.user_data.get("system")
    system_name = get_system_name(system)

    keyboard = [
        [InlineKeyboardButton("✅ نعم، احذف", callback_data="confirm_delete_yes")],
        [InlineKeyboardButton("❌ لا، إلغاء", callback_data="confirm_delete_no")],
    ]

    await query.edit_message_text(
        f"⚠️ <b>تأكيد الحذف</b>\n\n"
        f"🎬 <b>النظام:</b> {system_name}\n"
        f"📁 <b>القسم:</b> {section_id}\n"
        f"🎥 <b>اسم الفيديو:</b> {video_name}\n\n"
        f"<b>هل أنت متأكد من حذف هذا الفيديو؟</b>\n"
        f"<i>⚠️ لا يمكن التراجع عن هذا الإجراء!</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return CONFIRM_DELETE


async def handle_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_delete_no":
        return await show_main_menu(update, context, edit=True)

    if query.data == "confirm_delete_yes":
        asset_id = context.user_data.get("delete_asset_id")
        creds = context.user_data.get("delete_creds")
        video_name = context.user_data.get("delete_video_name")
        section_id = context.user_data.get("delete_section_id")
        system = context.user_data.get("system")
        system_name = get_system_name(system)

        if not creds or not asset_id:
            keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
            await query.edit_message_text(
                "❌ <b>خطأ في البيانات</b>\n\n"
                "انتهت صلاحية الجلسة أو فقدت البيانات.\n"
                "الرجاء إعادة المحاولة من القائمة الرئيسية.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
            return MAIN_MENU

        await query.edit_message_text(
            f"⏳ <b>جاري حذف الفيديو...</b>\n\n{video_name}",
            parse_mode=ParseMode.HTML,
        )

        try:
            response = requests.delete(
                f"https://api.mux.com/video/v1/assets/{asset_id}",
                auth=(creds["id"], creds["secret"]),
                timeout=30,
            )

            if response.status_code == 204:
                keyboard = [
                    [InlineKeyboardButton("🗑️ حذف فيديو آخر", callback_data=f"section_delete_{section_id}")],
                    [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
                ]

                await query.edit_message_text(
                    f"✅ <b>تم الحذف بنجاح!</b>\n\n"
                    f"🎬 <b>النظام:</b> {system_name}\n"
                    f"📁 <b>القسم:</b> {section_id}\n"
                    f"🎥 <b>الفيديو المحذوف:</b> {video_name}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.HTML,
                )
                return MAIN_MENU
            else:
                error_msg = "خطأ غير معروف"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except (ValueError, KeyError):
                    # Response is not JSON or malformed
                    if response.text:
                        error_msg = response.text[:200]  # Limit error message length
                
                keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
                await query.edit_message_text(
                    f"❌ <b>فشل الحذف</b>\n\n"
                    f"الخطأ: {error_msg}\n"
                    f"رمز الحالة: {response.status_code}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.HTML,
                )
                return MAIN_MENU

        except Exception as e:
            keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
            await query.edit_message_text(
                f"⚠️ <b>خطأ</b>\n\n{str(e)}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
            return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ <b>تم إلغاء العملية</b>\n\n" "استخدم /start للبدء من جديد.",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


def main():
    if not BOT_TOKEN:
        print("خطأ: متغير البيئة BOT_TOKEN غير مُعيّن!")
        return

    print("جاري تشغيل بوت إدارة الفيديوهات...")
    print(f"سينما بلس: تم تحميل {len(CINEMA_PLUS_SECTIONS)} أقسام")
    print(f"شوف بلاي: تم تحميل {len(SHOOF_PLAY_SECTIONS)} أقسام")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_SYSTEM: [
                CallbackQueryHandler(select_system, pattern="^system_"),
            ],
            AUTH_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password),
            ],
            MAIN_MENU: [
                CallbackQueryHandler(main_menu_handler, pattern="^menu_"),
                CallbackQueryHandler(handle_upload_section, pattern="^section_upload_"),
                CallbackQueryHandler(handle_review_section, pattern="^section_review_"),
                CallbackQueryHandler(handle_delete_section, pattern="^section_delete_"),
                CallbackQueryHandler(handle_playback_section, pattern="^section_playback_"),
                CallbackQueryHandler(handle_capacity_section, pattern="^section_capacity_|^capacity_"),
            ],
            SELECT_SECTION_UPLOAD: [
                CallbackQueryHandler(handle_upload_section, pattern="^section_upload_"),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
            ],
            ENTER_VIDEO_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_name),
            ],
            ENTER_VIDEO_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_link),
            ],
            SELECT_SECTION_REVIEW: [
                CallbackQueryHandler(handle_review_section, pattern="^section_review_"),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
            ],
            REVIEW_ACTIONS: [
                CallbackQueryHandler(handle_review_actions, pattern="^review_|^menu_back$"),
            ],
            SELECT_SECTION_PLAYBACK: [
                CallbackQueryHandler(handle_playback_section, pattern="^section_playback_"),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
            ],
            SELECT_SECTION_CAPACITY: [
                CallbackQueryHandler(handle_capacity_section, pattern="^section_capacity_|^capacity_"),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
            ],
            SELECT_SECTION_DELETE: [
                CallbackQueryHandler(handle_delete_section, pattern="^section_delete_"),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
            ],
            SELECT_VIDEO_DELETE: [
                CallbackQueryHandler(handle_video_delete_selection, pattern="^delete_video_"),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
            ],
            CONFIRM_DELETE: [
                CallbackQueryHandler(handle_delete_confirmation, pattern="^confirm_delete_"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

