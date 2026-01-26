import os
import json
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

# Path to sections JSON file
SECTIONS_FILE = "sections.json"

# Default sections structure
DEFAULT_SECTIONS = {
    "cinema_plus": {},
    "shoof_play": {}
}

def load_sections() -> dict:
    """Load sections from JSON file. Creates file with defaults if it doesn't exist."""
    if os.path.exists(SECTIONS_FILE):
        try:
            with open(SECTIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure both systems exist
                if "cinema_plus" not in data:
                    data["cinema_plus"] = {}
                if "shoof_play" not in data:
                    data["shoof_play"] = {}
                return data
        except (json.JSONDecodeError, IOError):
            return DEFAULT_SECTIONS.copy()
    else:
        # Create default file
        save_sections(DEFAULT_SECTIONS)
        return DEFAULT_SECTIONS.copy()


def save_sections(sections: dict) -> bool:
    """Save sections to JSON file."""
    try:
        with open(SECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sections, f, indent=2, ensure_ascii=False)
        return True
    except IOError:
        return False


def get_next_section_number(system: str) -> str:
    """Get the next available section number for a system."""
    sections = load_sections()
    system_sections = sections.get(system, {})
    if not system_sections:
        return "1"
    # Get all numeric keys and find the max
    numeric_keys = [int(k) for k in system_sections.keys() if k.isdigit()]
    if not numeric_keys:
        return "1"
    return str(max(numeric_keys) + 1)


def add_section(system: str, mux_id: str, mux_secret: str) -> str:
    """Add a new section to a system. Returns the new section number."""
    sections = load_sections()
    new_number = get_next_section_number(system)
    sections[system][new_number] = {
        "id": mux_id,
        "secret": mux_secret
    }
    save_sections(sections)
    return new_number


# In-memory cache for sections (reloaded on each access for real-time updates)
def get_sections_for_system(system: str) -> dict:
    """Get sections for a specific system from JSON file."""
    sections = load_sections()
    return sections.get(system, {})


user_auth_cache = {}

# Conversation states
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
    ADD_SECTION_MUX_ID,
    ADD_SECTION_MUX_SECRET,
) = range(15)


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
        [InlineKeyboardButton("➕ إضافة قسم", callback_data="menu_add_section")],
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
    elif action == "menu_add_section":
        return await start_add_section(update, context)
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


async def start_add_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the process of adding a new section to the CURRENT system."""
    query = update.callback_query
    system = context.user_data.get("system")
    system_name = get_system_name(system)
    
    # Get the next section number for this system
    next_number = get_next_section_number(system)
    context.user_data["adding_section_number"] = next_number
    
    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="menu_back")]]
    
    await query.edit_message_text(
        f"➕ <b>إضافة قسم جديد - {system_name}</b>\n\n"
        f"📁 رقم القسم الجديد: <b>{next_number}</b>\n\n"
        f"<b>الخطوة 1 من 2:</b>\n"
        f"الرجاء إرسال <b>Mux ID</b>:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return ADD_SECTION_MUX_ID


async def handle_add_section_mux_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle receiving the Mux ID for the new section."""
    mux_id = update.message.text.strip()
    context.user_data["new_section_mux_id"] = mux_id
    
    system = context.user_data.get("system")
    system_name = get_system_name(system)
    next_number = context.user_data.get("adding_section_number")
    
    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="menu_back")]]
    
    await update.message.reply_text(
        f"➕ <b>إضافة قسم جديد - {system_name}</b>\n\n"
        f"📁 رقم القسم الجديد: <b>{next_number}</b>\n"
        f"🔑 Mux ID: <code>{mux_id}</code>\n\n"
        f"<b>الخطوة 2 من 2:</b>\n"
        f"الرجاء إرسال <b>Mux Secret</b>:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return ADD_SECTION_MUX_SECRET


async def handle_add_section_mux_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle receiving the Mux Secret and save the new section."""
    mux_secret = update.message.text.strip()
    mux_id = context.user_data.get("new_section_mux_id")
    system = context.user_data.get("system")
    system_name = get_system_name(system)
    
    # Try to delete the secret message for security
    try:
        await update.message.delete()
    except:
        pass
    
    # Add the section to the JSON file
    new_section_number = add_section(system, mux_id, mux_secret)
    
    # Clear temporary data
    context.user_data.pop("new_section_mux_id", None)
    context.user_data.pop("adding_section_number", None)
    
    keyboard = [
        [InlineKeyboardButton("➕ إضافة قسم آخر", callback_data="menu_add_section")],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
    ]
    
    await update.message.reply_text(
        f"✅ <b>تم إضافة القسم بنجاح!</b>\n\n"
        f"🎬 <b>النظام:</b> {system_name}\n"
        f"📁 <b>رقم القسم:</b> {new_section_number}\n"
        f"🔑 <b>Mux ID:</b> <code>{mux_id}</code>\n\n"
        f"<i>القسم متاح الآن للاستخدام مباشرة!</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return MAIN_MENU


async def show_section_selector(update: Update, context: ContextTypes.DEFAULT_TYPE, action_type: str):
    query = update.callback_query
    system = context.user_data.get("system")
    sections = get_sections_for_system(system)
    system_name = get_system_name(system)

    context.user_data["action_type"] = action_type

    if not sections:
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قسم", callback_data="menu_add_section")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
        ]
        await query.edit_message_text(
            f"⚠️ <b>لا توجد أقسام في {system_name}</b>\n\n"
            "الرجاء إضافة قسم أولاً باستخدام زر 'إضافة قسم'.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return MAIN_MENU

    keyboard = []
    row = []
    # Sort sections by numeric value
    sorted_sections = sorted(sections.keys(), key=lambda x: int(x) if x.isdigit() else 0)
    for i, section_id in enumerate(sorted_sections, 1):
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

        sorted_sections = sorted(sections.keys(), key=lambda x: int(x) if x.isdigit() else 0)
        for section_id in sorted_sections:
            creds = sections[section_id]
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
                    if response.text:
                        error_msg = response.text[:200]
                
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

    # Load sections from JSON file
    sections = load_sections()
    
    print("جاري تشغيل بوت إدارة الفيديوهات...")
    print(f"سينما بلس: تم تحميل {len(sections.get('cinema_plus', {}))} أقسام")
    print(f"شوف بلاي: تم تحميل {len(sections.get('shoof_play', {}))} أقسام")

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
            ADD_SECTION_MUX_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_section_mux_id),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
            ],
            ADD_SECTION_MUX_SECRET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_section_mux_secret),
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
