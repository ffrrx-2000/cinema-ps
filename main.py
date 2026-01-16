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
        "id": "2ab8ed37-b8af-4ffa-ab78-bc0910fcac6e",
        "secret": "zkX7I4isPxeMz6tFh20vFt37sNOWPpPgaMpH0u7i2dvavEMea84Wob8UfFvIVouNcfzjpIgt7jl",
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
) = range(10)


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
        return "Cinema Plus"
    elif system == "shoof_play":
        return "Shoof Play"
    return ""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🎬 Cinema Plus", callback_data="system_cinema_plus")],
        [InlineKeyboardButton("📺 Shoof Play", callback_data="system_shoof_play")],
    ]
    await update.message.reply_text(
        "🎬 <b>Welcome to Video Management Bot</b>\n\n"
        "Please select a system to access:",
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
        f"🔐 <b>{system_name} Authentication</b>\n\n"
        "Please enter the password to access this system:",
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
            f"✅ <b>Authentication Successful!</b>\n\n"
            f"Welcome to {system_name}. Your session is valid for 48 hours.",
            parse_mode=ParseMode.HTML,
        )
        return await show_main_menu(update, context, edit=False)
    else:
        await update.message.reply_text(
            "❌ <b>Incorrect Password</b>\n\n"
            "Please try again or use /start to select a different system.",
            parse_mode=ParseMode.HTML,
        )
        return AUTH_PASSWORD


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    system = context.user_data.get("system")
    system_name = get_system_name(system)
    sections = get_sections_for_system(system)
    section_count = len(sections)

    keyboard = [
        [InlineKeyboardButton("📤 Upload Video", callback_data="menu_upload")],
        [InlineKeyboardButton("🔍 Review Section", callback_data="menu_review")],
        [InlineKeyboardButton("🎞️ Show Playback IDs", callback_data="menu_playback")],
        [InlineKeyboardButton("📊 Live Capacity Check", callback_data="menu_capacity")],
        [InlineKeyboardButton("🔙 Switch System", callback_data="menu_switch")],
    ]

    text = (
        f"🎬 <b>{system_name} Management</b>\n\n"
        f"📁 Total Sections: {section_count}\n"
        f"🔐 Session Active: 48 hours\n\n"
        "Select an action:"
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
    elif action == "menu_playback":
        return await show_section_selector(update, context, "playback")
    elif action == "menu_capacity":
        return await show_section_selector(update, context, "capacity")
    elif action == "menu_switch":
        keyboard = [
            [InlineKeyboardButton("🎬 Cinema Plus", callback_data="system_cinema_plus")],
            [InlineKeyboardButton("📺 Shoof Play", callback_data="system_shoof_play")],
        ]
        await query.edit_message_text(
            "🎬 <b>Select a System</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
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
        row.append(InlineKeyboardButton(f"Section {section_id}", callback_data=callback_data))
        if i % 5 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")])

    action_titles = {
        "upload": "📤 Upload Video",
        "review": "🔍 Review Section",
        "playback": "🎞️ Show Playback IDs",
        "capacity": "📊 Capacity Check",
    }

    await query.edit_message_text(
        f"<b>{action_titles[action_type]} - {system_name}</b>\n\n"
        "Select a section:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )

    state_mapping = {
        "upload": SELECT_SECTION_UPLOAD,
        "review": SELECT_SECTION_REVIEW,
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
            f"⚠️ <b>Connection Error</b>\n\nFailed to connect to Mux API: {str(e)}\n\n"
            "Use /start to try again.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    if count >= 10:
        await query.answer("⚠️ Section is full (10/10 videos)", show_alert=True)
        return SELECT_SECTION_UPLOAD

    context.user_data["section_id"] = section_id
    context.user_data["section_creds"] = creds

    await query.edit_message_text(
        f"📤 <b>Upload to Section {section_id}</b>\n\n"
        f"📊 Current Capacity: {count}/10\n"
        f"📁 Available Slots: {10 - count}\n\n"
        "<b>Please enter the video name:</b>",
        parse_mode=ParseMode.HTML,
    )
    return ENTER_VIDEO_NAME


async def handle_video_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_name = update.message.text.strip()
    context.user_data["video_name"] = video_name

    await update.message.reply_text(
        f"📝 <b>Video Name:</b> {video_name}\n\n"
        "<b>Now please send the video URL:</b>",
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
        "⏳ <b>Uploading to Mux...</b>\n\n"
        "Please wait while we process your video.",
        parse_mode=ParseMode.HTML,
    )

    try:
        response = requests.post(
            "https://api.mux.com/video/v1/assets",
            json={
                "input": video_url,
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
            playback_id = playback_ids[0]["id"] if playback_ids else "Pending..."

            keyboard = [
                [InlineKeyboardButton("📤 Upload Another", callback_data=f"section_upload_{section_id}")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")],
            ]

            await status_msg.edit_text(
                f"✅ <b>Upload Successful!</b>\n\n"
                f"🎬 <b>System:</b> {system_name}\n"
                f"📁 <b>Section:</b> {section_id}\n"
                f"🎥 <b>Video Name:</b> {video_name}\n"
                f"🆔 <b>Asset ID:</b>\n<code>{asset_id}</code>\n"
                f"🔑 <b>Playback ID:</b>\n<code>{playback_id}</code>\n\n"
                "<i>Tracking asset status...</i>",
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
            error_msg = response.json().get("error", {}).get("message", "Unknown error")
            await status_msg.edit_text(
                f"❌ <b>Upload Failed</b>\n\n"
                f"Error: {error_msg}\n"
                f"Status Code: {response.status_code}\n\n"
                "Use /start to try again.",
                parse_mode=ParseMode.HTML,
            )
            return ConversationHandler.END
    except Exception as e:
        await status_msg.edit_text(
            f"⚠️ <b>Error</b>\n\n{str(e)}\n\n" "Use /start to try again.",
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
                    await bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"✨ <b>Video Ready!</b>\n\n"
                            f"🎥 <b>Video:</b> {video_name}\n"
                            f"✅ <b>Status:</b> Ready for playback\n"
                            f"🔑 <b>Playback ID:</b>\n<code>{final_playback_id}</code>"
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                    return
                elif status == "errored":
                    await bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"❌ <b>Video Processing Failed</b>\n\n"
                            f"🎥 <b>Video:</b> {video_name}\n"
                            f"Please check the source URL and try again."
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
        f"⏳ <b>Fetching assets from Section {section_id}...</b>",
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
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]]
            await query.edit_message_text(
                f"📁 <b>Section {section_id} is empty</b>\n\n"
                f"System: {system_name}\n"
                "No videos found in this section.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
            return MAIN_MENU

        text = f"📂 <b>{system_name} - Section {section_id}</b>\n"
        text += f"📊 Total Videos: {len(assets)}/10\n\n"

        all_playback_ids = []
        for i, asset in enumerate(assets, 1):
            name = asset.get("passthrough", "Untitled")
            status = asset.get("status", "unknown")
            asset_id = asset.get("id", "N/A")
            playback_ids = asset.get("playback_ids", [])
            p_id = playback_ids[0]["id"] if playback_ids else "N/A"

            status_emoji = "✅" if status == "ready" else "⏳" if status == "preparing" else "❌"

            text += f"<b>{i}. {name}</b>\n"
            text += f"   Status: {status_emoji} {status}\n"
            text += f"   Playback: <code>{p_id}</code>\n\n"

            if p_id != "N/A":
                all_playback_ids.append(p_id)

        context.user_data["all_playback_ids"] = all_playback_ids

        keyboard = [
            [InlineKeyboardButton("📋 Copy All Playback IDs", callback_data="review_copy_all")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")],
        ]

        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
        return REVIEW_ACTIONS

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]]
        await query.edit_message_text(
            f"⚠️ <b>Error fetching data</b>\n\n{str(e)}",
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
                f"📋 <b>All Playback IDs:</b>\n\n<code>{ids_text}</code>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await query.answer("No playback IDs available", show_alert=True)
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
        f"⏳ <b>Fetching playback IDs from Section {section_id}...</b>",
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
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]]
            await query.edit_message_text(
                f"📁 <b>Section {section_id} is empty</b>\n\n" "No playback IDs to display.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
            return MAIN_MENU

        text = f"🎞️ <b>{system_name} - Section {section_id} Playback IDs</b>\n\n"
        all_ids = []

        for i, asset in enumerate(assets, 1):
            name = asset.get("passthrough", "Untitled")
            playback_ids = asset.get("playback_ids", [])
            p_id = playback_ids[0]["id"] if playback_ids else "N/A"

            text += f"<b>{i}. {name}</b>\n<code>{p_id}</code>\n\n"
            if p_id != "N/A":
                all_ids.append(p_id)

        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]]

        if all_ids:
            text += f"\n<b>Quick Copy (All IDs):</b>\n<code>{chr(10).join(all_ids)}</code>"

        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
        return MAIN_MENU

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]]
        await query.edit_message_text(
            f"⚠️ <b>Error</b>\n\n{str(e)}",
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
            f"⏳ <b>Checking all sections capacity...</b>\n\n" "This may take a moment.",
            parse_mode=ParseMode.HTML,
        )

        text = f"📊 <b>{system_name} - Live Capacity Report</b>\n\n"
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
                status = "✅" if count < 10 else "⚠️ FULL"
                bar = "█" * count + "░" * (10 - count)
                text += f"Section {section_id}: [{bar}] {count}/10 {status}\n"
            except:
                text += f"Section {section_id}: ⚠️ Connection Error\n"

        text += f"\n<b>Total Usage:</b> {total_used}/{total_capacity}"
        text += f"\n<b>Available Slots:</b> {total_capacity - total_used}"

        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]]
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
        f"⏳ <b>Checking Section {section_id} capacity...</b>",
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
        status = "✅ Available" if count < 10 else "⚠️ FULL"

        text = f"📊 <b>{system_name} - Section {section_id}</b>\n\n"
        text += f"<b>Capacity:</b> [{bar}] {count}/10\n"
        text += f"<b>Status:</b> {status}\n"
        text += f"<b>Available Slots:</b> {10 - count}\n\n"

        if assets:
            text += "<b>Current Videos:</b>\n"
            for i, asset in enumerate(assets, 1):
                name = asset.get("passthrough", "Untitled")
                asset_status = asset.get("status", "unknown")
                emoji = "✅" if asset_status == "ready" else "⏳"
                text += f"{i}. {emoji} {name}\n"

        keyboard = [
            [InlineKeyboardButton("🔄 Check All Sections", callback_data="capacity_check_all")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")],
        ]

        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
        )
        return MAIN_MENU

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_back")]]
        await query.edit_message_text(
            f"⚠️ <b>Error</b>\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ <b>Operation Cancelled</b>\n\n" "Use /start to begin again.",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


def main():
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN environment variable is not set!")
        return

    print("Starting Video Management Bot...")
    print(f"Cinema Plus: {len(CINEMA_PLUS_SECTIONS)} sections loaded")
    print(f"Shoof Play: {len(SHOOF_PLAY_SECTIONS)} sections loaded")

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
