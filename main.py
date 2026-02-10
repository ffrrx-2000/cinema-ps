import os
import json
import asyncio
import base64
import time
import math
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
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "ffrrx-2000/cinema-ps")  # format: "username/repo"
GITHUB_FILE_PATH = "sections.json"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
TMDB_API_KEY = "06f120992cfacd7c118f6e7086d23544"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

CINEMA_PLUS_PASSWORD = "67146"
SHOOF_PLAY_PASSWORD = "1460"

# Path to sections JSON file (local cache)
SECTIONS_FILE = "sections.json"

# Default sections structure
DEFAULT_SECTIONS = {
    "cinema_plus": {},
    "shoof_play": {}
}

# In-memory cache for sections
_sections_cache = None
_github_file_sha = None

def load_sections_from_github() -> tuple[dict, str | None]:
    """Load sections from GitHub repository."""
    global _sections_cache, _github_file_sha
    
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("Warning: GitHub credentials not set, using local file")
        return load_sections_local(), None
    
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        params = {"ref": GITHUB_BRANCH}
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            sha = data["sha"]
            sections = json.loads(content)
            
            # Ensure both systems exist
            if "cinema_plus" not in sections:
                sections["cinema_plus"] = {}
            if "shoof_play" not in sections:
                sections["shoof_play"] = {}
            
            _sections_cache = sections
            _github_file_sha = sha
            return sections, sha
        elif response.status_code == 404:
            # File doesn't exist, create it
            print("sections.json not found on GitHub, creating...")
            save_sections_to_github(DEFAULT_SECTIONS)
            return DEFAULT_SECTIONS.copy(), None
        else:
            print(f"GitHub API error: {response.status_code} - {response.text}")
            return load_sections_local(), None
            
    except Exception as e:
        print(f"Error loading from GitHub: {e}")
        return load_sections_local(), None


def save_sections_to_github(sections: dict) -> bool:
    """Save sections to GitHub repository."""
    global _github_file_sha
    
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("Warning: GitHub credentials not set, saving locally only")
        return save_sections_local(sections)
    
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Encode content to base64
        content = json.dumps(sections, indent=2, ensure_ascii=False)
        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        
        # Prepare the request body
        body = {
            "message": f"Update sections.json - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_b64,
            "branch": GITHUB_BRANCH
        }
        
        # If we have SHA, include it (required for updating existing file)
        if _github_file_sha:
            body["sha"] = _github_file_sha
        else:
            # Get current SHA if we don't have it
            response = requests.get(url, headers=headers, params={"ref": GITHUB_BRANCH}, timeout=10)
            if response.status_code == 200:
                body["sha"] = response.json()["sha"]
        
        # Make the PUT request
        response = requests.put(url, headers=headers, json=body, timeout=30)
        
        if response.status_code in [200, 201]:
            # Update the SHA for future updates
            _github_file_sha = response.json()["content"]["sha"]
            print("Successfully saved to GitHub")
            
            # Also save locally as backup
            save_sections_local(sections)
            return True
        else:
            print(f"GitHub save error: {response.status_code} - {response.text}")
            return save_sections_local(sections)
            
    except Exception as e:
        print(f"Error saving to GitHub: {e}")
        return save_sections_local(sections)


def load_sections_local() -> dict:
    """Load sections from local JSON file (fallback)."""
    if os.path.exists(SECTIONS_FILE):
        try:
            with open(SECTIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "cinema_plus" not in data:
                    data["cinema_plus"] = {}
                if "shoof_play" not in data:
                    data["shoof_play"] = {}
                return data
        except (json.JSONDecodeError, IOError):
            return DEFAULT_SECTIONS.copy()
    return DEFAULT_SECTIONS.copy()


def save_sections_local(sections: dict) -> bool:
    """Save sections to local JSON file (fallback/backup)."""
    try:
        with open(SECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sections, f, indent=2, ensure_ascii=False)
        return True
    except IOError:
        return False


def load_sections() -> dict:
    """Load sections - tries GitHub first, falls back to local."""
    global _sections_cache
    sections, _ = load_sections_from_github()
    _sections_cache = sections
    return sections


def save_sections(sections: dict) -> bool:
    """Save sections - saves to GitHub and local."""
    global _sections_cache
    _sections_cache = sections
    return save_sections_to_github(sections)


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


# ─── TMDB Helper Functions ───────────────────────────────────────────────────

def tmdb_get_series(tmdb_id: int) -> dict | None:
    """Fetch TV series details from TMDB."""
    try:
        url = f"{TMDB_BASE_URL}/tv/{tmdb_id}"
        params = {"api_key": TMDB_API_KEY, "language": "ar-SA"}
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json()
        # Fallback to English if Arabic not available
        params["language"] = "en-US"
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json()
        return None
    except Exception:
        return None


def tmdb_get_season(tmdb_id: int, season_number: int) -> dict | None:
    """Fetch season details from TMDB."""
    try:
        url = f"{TMDB_BASE_URL}/tv/{tmdb_id}/season/{season_number}"
        params = {"api_key": TMDB_API_KEY, "language": "ar-SA"}
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json()
        params["language"] = "en-US"
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json()
        return None
    except Exception:
        return None


def calculate_sections_needed(total_episodes: int) -> int:
    """Calculate how many Mux sections are needed for episodes (max 10 per section)."""
    return math.ceil(total_episodes / 10)


def get_available_sections_with_space(system: str) -> list[dict]:
    """Get sections that have available space, with their current count."""
    sections = get_sections_for_system(system)
    available = []
    sorted_keys = sorted(sections.keys(), key=lambda x: int(x) if x.isdigit() else 0)
    for section_id in sorted_keys:
        creds = sections[section_id]
        try:
            res = requests.get(
                "https://api.mux.com/video/v1/assets",
                auth=(creds["id"], creds["secret"]),
                timeout=10,
            )
            count = len(res.json().get("data", []))
            if count < 10:
                available.append({
                    "section_id": section_id,
                    "creds": creds,
                    "used": count,
                    "free": 10 - count,
                })
        except Exception:
            pass
    return available


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
    # Series states
    SERIES_ENTER_TMDB_ID,
    SERIES_SELECT_SEASON,
    SERIES_CONFIRM_PLAN,
    SERIES_ENTER_EPISODE_LINK,
    SERIES_SEASON_DONE,
    SERIES_SHOW_PLAYBACK_IDS,
) = range(21)


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
        [InlineKeyboardButton("📺 إضافة مسلسل كامل", callback_data="menu_series")],
    ]

    # Add "continue series" button if there's an active series session
    if context.user_data.get("series_tmdb_id"):
        series_name = context.user_data.get("series_name", "")
        keyboard.append([InlineKeyboardButton(f"▶️ استكمال: {series_name}", callback_data="menu_series_continue")])

    keyboard.extend([
        [InlineKeyboardButton("🔍 مراجعة القسم", callback_data="menu_review")],
        [InlineKeyboardButton("🗑️ حذف فيديو", callback_data="menu_delete")],
        [InlineKeyboardButton("🎞️ عرض معرفات التشغيل", callback_data="menu_playback")],
        [InlineKeyboardButton("📊 فحص السعة المباشر", callback_data="menu_capacity")],
        [InlineKeyboardButton("➕ إضافة قسم", callback_data="menu_add_section")],
        [InlineKeyboardButton("🔙 تبديل النظام", callback_data="menu_switch")],
    ])

    text = (
        f"🎬 <b>إدارة {system_name}</b>\n\n"
        f"📁 إجمالي الأقسام: {section_count}\n"
        f"🔐 الجلسة نشطة: 48 ساعة\n\n"
        "اختر إجراء:"
    )

    if edit:
        query = update.callback_query
        try:
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
            )
        except Exception:
            # If edit fails (e.g. photo message was deleted), send new message
            await query.message.chat.send_message(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
            )
    else:
        if update.message:
            await update.message.reply_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
            )
        elif update.callback_query:
            await update.callback_query.message.chat.send_message(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML
            )
    return MAIN_MENU


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "menu_upload":
        return await show_section_selector(update, context, "upload")
    elif action == "menu_series":
        return await series_start(update, context)
    elif action == "menu_series_continue":
        return await series_continue(update, context)
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
                            f"⚠️ <b>الرابط المصدر ��ير شغال!</b>\n"
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


# ─── Series (TV Show) Handlers ───────────────────────────────────────────────

async def series_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the series addition flow - ask for TMDB ID."""
    query = update.callback_query
    system = context.user_data.get("system")
    system_name = get_system_name(system)

    keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]

    await query.edit_message_text(
        f"📺 <b>إضافة مسلسل كامل - {system_name}</b>\n\n"
        "الرجاء إرسال <b>TMDB ID</b> الخاص بالمسلسل.\n\n"
        "<i>يمكنك العثور على الـ ID من موقع themoviedb.org\n"
        "مثال: 1396 (Breaking Bad)</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return SERIES_ENTER_TMDB_ID


async def series_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Continue a previously started series - show seasons or resume episode upload."""
    query = update.callback_query
    series_name = context.user_data.get("series_name")
    tmdb_id = context.user_data.get("series_tmdb_id")
    seasons = context.user_data.get("series_seasons", [])
    all_pids = context.user_data.get("series_all_playback_ids", {})

    # Check if there's an active episode upload in progress
    ep_index = context.user_data.get("series_current_ep_index")
    total_episodes = context.user_data.get("series_total_episodes", 0)
    upload_plan = context.user_data.get("series_upload_plan")

    if ep_index is not None and upload_plan and ep_index < total_episodes:
        # There's an active upload session - offer to resume
        season_num = context.user_data.get("series_current_season")
        keyboard = [
            [InlineKeyboardButton(f"▶️ استكمال الموسم {season_num} (الحلقة {ep_index + 1})", callback_data="series_resume_from_menu")],
            [InlineKeyboardButton("📺 اختيار موسم آخر", callback_data="series_back_to_seasons")],
            [InlineKeyboardButton("📋 عرض جميع المعرفات", callback_data="series_show_all_ids")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
        ]

        text = (
            f"📺 <b>استكمال: {series_name}</b>\n"
            f"🆔 TMDB ID: <code>{tmdb_id}</code>\n\n"
            f"▶️ <b>يوجد رفع متوقف:</b>\n"
            f"  الموسم {season_num} - الحلقة {ep_index + 1} من {total_episodes}\n\n"
            "<b>ماذا تريد أن تفعل؟</b>"
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return SERIES_SEASON_DONE
    else:
        # No active upload - show seasons list
        return await series_back_to_seasons(update, context)


async def series_handle_tmdb_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the TMDB ID input and show series info with seasons."""
    tmdb_id_text = update.message.text.strip()

    if not tmdb_id_text.isdigit():
        await update.message.reply_text(
            "❌ <b>الرجاء إرسال رقم صحيح فقط (TMDB ID)</b>",
            parse_mode=ParseMode.HTML,
        )
        return SERIES_ENTER_TMDB_ID

    tmdb_id = int(tmdb_id_text)
    series_data = tmdb_get_series(tmdb_id)

    if not series_data:
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]]
        await update.message.reply_text(
            "❌ <b>لم يتم العثور على المسلسل</b>\n\n"
            "تأكد من صحة الـ TMDB ID وحاول مرة أخرى.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return SERIES_ENTER_TMDB_ID

    # Store series data
    series_name = series_data.get("name", "غير معروف")
    seasons = series_data.get("seasons", [])
    # Filter out season 0 (specials)
    regular_seasons = [s for s in seasons if s.get("season_number", 0) > 0]
    total_seasons = len(regular_seasons)
    poster_path = series_data.get("poster_path", "")
    overview = series_data.get("overview", "لا يوجد وصف")

    context.user_data["series_tmdb_id"] = tmdb_id
    context.user_data["series_name"] = series_name
    context.user_data["series_seasons"] = regular_seasons
    context.user_data["series_all_playback_ids"] = {}  # {season_num: {ep_num: playback_id}}

    # Build season buttons
    keyboard = []
    row = []
    for i, season in enumerate(regular_seasons, 1):
        s_num = season.get("season_number", i)
        ep_count = season.get("episode_count", 0)
        btn_text = f"الموسم {s_num} ({ep_count} حلقة)"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"series_season_{s_num}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")])

    poster_url = f"https://image.tmdb.org/t/p/w300{poster_path}" if poster_path else ""

    text = (
        f"📺 <b>{series_name}</b>\n\n"
        f"🆔 TMDB ID: <code>{tmdb_id}</code>\n"
        f"📅 عدد المواسم: <b>{total_seasons}</b>\n\n"
    )

    # Add season details
    for season in regular_seasons:
        s_num = season.get("season_number", 0)
        ep_count = season.get("episode_count", 0)
        text += f"  الموسم {s_num}: {ep_count} حلقة\n"

    text += "\n<b>اختر الموسم الذي تريد إضافته:</b>"

    if poster_url:
        try:
            await update.message.reply_photo(
                photo=poster_url,
                caption=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
            return SERIES_SELECT_SEASON
        except Exception:
            pass

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return SERIES_SELECT_SEASON


async def _safe_send_or_edit(query, text, keyboard, parse_mode=ParseMode.HTML):
    """Helper: try edit_message_text, fallback to delete + send new message for photo messages."""
    try:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=parse_mode,
        )
    except Exception:
        # The message is likely a photo - delete it and send a new text message
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=parse_mode,
        )


async def series_select_season(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle season selection - check sections and show plan."""
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        # Delete the photo message and send a fresh text menu
        try:
            await query.message.delete()
        except Exception:
            pass
        return await show_main_menu(update, context, edit=False)

    season_num = int(query.data.replace("series_season_", ""))
    tmdb_id = context.user_data.get("series_tmdb_id")
    series_name = context.user_data.get("series_name")
    system = context.user_data.get("system")
    system_name = get_system_name(system)

    # Delete the photo/current message first, then work with fresh text messages
    try:
        await query.message.delete()
    except Exception:
        pass

    chat = query.message.chat

    # Fetch season details from TMDB
    season_data = tmdb_get_season(tmdb_id, season_num)
    if not season_data:
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="series_back_to_seasons")]]
        await chat.send_message(
            "❌ <b>فشل في جلب بيانات الموسم</b>\n\nحاول مرة أخرى.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return SERIES_SELECT_SEASON

    episodes = season_data.get("episodes", [])
    total_episodes = len(episodes)

    context.user_data["series_current_season"] = season_num
    context.user_data["series_episodes"] = episodes
    context.user_data["series_total_episodes"] = total_episodes

    # Calculate sections needed
    sections_needed = calculate_sections_needed(total_episodes)

    # Show loading message
    loading_msg = await chat.send_message(
        "⏳ <b>جاري فحص الأقسام المتاحة...</b>",
        parse_mode=ParseMode.HTML,
    )

    available = get_available_sections_with_space(system)
    total_free_slots = sum(s["free"] for s in available)

    # Build the upload plan: assign episodes to sections
    upload_plan = []  # list of {"section_id", "creds", "episodes": [ep_numbers]}
    remaining_eps = list(range(1, total_episodes + 1))

    for sec in available:
        if not remaining_eps:
            break
        take = min(sec["free"], len(remaining_eps))
        eps_for_section = remaining_eps[:take]
        remaining_eps = remaining_eps[take:]
        upload_plan.append({
            "section_id": sec["section_id"],
            "creds": sec["creds"],
            "episodes": eps_for_section,
        })

    context.user_data["series_upload_plan"] = upload_plan
    context.user_data["series_remaining_eps"] = remaining_eps

    # Show the plan
    text = (
        f"📺 <b>{series_name} - الموسم {season_num}</b>\n"
        f"🎬 <b>النظام:</b> {system_name}\n\n"
        f"📊 <b>عدد الحلقات:</b> {total_episodes}\n"
        f"📁 <b>الأقسام المطلوبة:</b> {sections_needed}\n"
        f"✅ <b>الأماكن المتاحة:</b> {total_free_slots}\n\n"
    )

    if remaining_eps:
        # Not enough space
        missing_slots = len(remaining_eps)
        extra_sections = calculate_sections_needed(missing_slots)
        text += (
            f"⚠️ <b>تحتاج إلى {extra_sections} قسم/أقسام إضافية!</b>\n"
            f"📌 ينقصك <b>{missing_slots}</b> مكان لاستيعاب جميع الحلقات.\n\n"
            "<b>الرجاء إضافة أقسام جديدة أولاً ثم العودة.</b>"
        )
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="menu_add_section")],
            [InlineKeyboardButton("🔙 رجوع للمواسم", callback_data="series_back_to_seasons")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
        ]
        await loading_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return SERIES_SELECT_SEASON
    else:
        # Enough space - show the plan
        text += "<b>خطة التوزيع:</b>\n"
        for plan in upload_plan:
            ep_range = plan["episodes"]
            if ep_range:
                text += f"  القسم {plan['section_id']}: الحلقات {ep_range[0]} - {ep_range[-1]} ({len(ep_range)} حلقة)\n"

        text += "\n<b>هل تريد البدء بالرفع؟</b>"

        keyboard = [
            [InlineKeyboardButton("✅ ابدأ الرفع", callback_data="series_confirm_start")],
            [InlineKeyboardButton("🔙 رجوع للمواسم", callback_data="series_back_to_seasons")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
        ]

        await loading_msg.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return SERIES_CONFIRM_PLAN


async def series_confirm_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plan confirmation - start asking for episode links."""
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        return await show_main_menu(update, context, edit=True)

    if query.data == "series_back_to_seasons":
        return await series_back_to_seasons(update, context)

    if query.data == "series_confirm_start":
        # Initialize episode tracking
        context.user_data["series_current_ep_index"] = 0
        context.user_data["series_current_plan_index"] = 0
        context.user_data["series_uploaded_playback_ids"] = []  # list of (ep_num, playback_id)

        return await series_ask_next_episode(update, context, edit=True)


async def series_ask_next_episode(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = True):
    """Ask the user for the next episode link."""
    upload_plan = context.user_data.get("series_upload_plan", [])
    plan_index = context.user_data.get("series_current_plan_index", 0)
    ep_index = context.user_data.get("series_current_ep_index", 0)
    series_name = context.user_data.get("series_name")
    season_num = context.user_data.get("series_current_season")
    total_episodes = context.user_data.get("series_total_episodes", 0)
    episodes = context.user_data.get("series_episodes", [])

    # Calculate overall episode number
    overall_ep = ep_index + 1

    if overall_ep > total_episodes:
        # All episodes done
        return await series_season_complete(update, context, edit=edit)

    # Find current section from plan
    current_plan = None
    ep_count_so_far = 0
    for i, plan in enumerate(upload_plan):
        if ep_count_so_far + len(plan["episodes"]) >= overall_ep:
            current_plan = plan
            context.user_data["series_current_plan_index"] = i
            break
        ep_count_so_far += len(plan["episodes"])

    if not current_plan:
        return await series_season_complete(update, context, edit=edit)

    section_id = current_plan["section_id"]

    # Get episode name from TMDB data
    ep_data = episodes[ep_index] if ep_index < len(episodes) else {}
    ep_name = ep_data.get("name", f"الحلقة {overall_ep}")
    ep_overview = ep_data.get("overview", "")

    keyboard = [
        [InlineKeyboardButton("⏸️ إيقاف مؤقت والإكمال لاحقاً", callback_data="series_pause")],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
    ]

    text = (
        f"📺 <b>{series_name} - الموسم {season_num}</b>\n"
        f"📁 <b>القسم الحالي:</b> {section_id}\n\n"
        f"🎬 <b>الحلقة {overall_ep} من {total_episodes}</b>\n"
        f"📝 <b>عنوان الحلقة:</b> {ep_name}\n\n"
        f"<b>أرسل رابط الحلقة {overall_ep}:</b>"
    )

    if edit:
        query = update.callback_query
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )

    return SERIES_ENTER_EPISODE_LINK


async def series_handle_episode_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle receiving an episode link - upload to Mux."""
    video_url = update.message.text.strip()
    upload_plan = context.user_data.get("series_upload_plan", [])
    plan_index = context.user_data.get("series_current_plan_index", 0)
    ep_index = context.user_data.get("series_current_ep_index", 0)
    series_name = context.user_data.get("series_name")
    season_num = context.user_data.get("series_current_season")
    total_episodes = context.user_data.get("series_total_episodes", 0)
    episodes = context.user_data.get("series_episodes", [])

    overall_ep = ep_index + 1
    current_plan = upload_plan[plan_index]
    creds = current_plan["creds"]
    section_id = current_plan["section_id"]

    # Get episode name
    ep_data = episodes[ep_index] if ep_index < len(episodes) else {}
    ep_name = ep_data.get("name", f"الحلقة {overall_ep}")

    # Build passthrough name: "SeriesName - S01E01 - EpisodeName"
    passthrough_name = f"{series_name} - S{season_num:02d}E{overall_ep:02d} - {ep_name}"

    try:
        await update.message.delete()
    except Exception:
        pass

    status_msg = await update.message.reply_text(
        f"⏳ <b>جاري رفع الحلقة {overall_ep} من {total_episodes}...</b>\n\n"
        f"📝 {passthrough_name}",
        parse_mode=ParseMode.HTML,
    )

    try:
        response = requests.post(
            "https://api.mux.com/video/v1/assets",
            json={
                "input": [{"url": video_url}],
                "playback_policy": ["public"],
                "passthrough": passthrough_name,
            },
            auth=(creds["id"], creds["secret"]),
            timeout=30,
        )

        if response.status_code == 201:
            res_data = response.json()["data"]
            asset_id = res_data["id"]
            playback_ids = res_data.get("playback_ids", [])
            playback_id = playback_ids[0]["id"] if playback_ids else "قيد الانتظار..."

            # Store playback ID
            uploaded = context.user_data.get("series_uploaded_playback_ids", [])
            uploaded.append((overall_ep, playback_id, passthrough_name))
            context.user_data["series_uploaded_playback_ids"] = uploaded

            # Also store in the season playback IDs
            all_pids = context.user_data.get("series_all_playback_ids", {})
            season_key = str(season_num)
            if season_key not in all_pids:
                all_pids[season_key] = {}
            all_pids[season_key][str(overall_ep)] = playback_id
            context.user_data["series_all_playback_ids"] = all_pids

            # Track asset status in background
            asyncio.create_task(
                track_asset_status(
                    update.effective_chat.id,
                    context.bot,
                    asset_id,
                    creds,
                    passthrough_name,
                    playback_id,
                )
            )

            await status_msg.edit_text(
                f"✅ <b>تم رفع الحلقة {overall_ep} بنجاح!</b>\n\n"
                f"📝 {passthrough_name}\n"
                f"📁 القسم: {section_id}\n"
                f"🆔 Playback ID: <code>{playback_id}</code>\n\n"
                f"📊 التقدم: {overall_ep}/{total_episodes}",
                parse_mode=ParseMode.HTML,
            )

            # Move to next episode
            context.user_data["series_current_ep_index"] = ep_index + 1

            # Ask for next episode
            return await series_ask_next_episode(update, context, edit=False)

        else:
            error_msg = response.json().get("error", {}).get("message", "خطأ غير معروف")
            keyboard = [
                [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="series_retry_ep")],
                [InlineKeyboardButton("⏭️ تخطي هذه الحلقة", callback_data="series_skip_ep")],
                [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
            ]
            await status_msg.edit_text(
                f"❌ <b>فشل رفع الحلقة {overall_ep}</b>\n\n"
                f"الخطأ: {error_msg}\n\n"
                "اختر إجراء:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
            return SERIES_ENTER_EPISODE_LINK

    except Exception as e:
        keyboard = [
            [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="series_retry_ep")],
            [InlineKeyboardButton("⏭️ تخطي هذه الحلقة", callback_data="series_skip_ep")],
            [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
        ]
        await status_msg.edit_text(
            f"⚠️ <b>خطأ في رفع الحلقة {overall_ep}</b>\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return SERIES_ENTER_EPISODE_LINK


async def series_episode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks during episode upload (retry, skip, pause)."""
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        return await show_main_menu(update, context, edit=True)

    if query.data == "series_retry_ep":
        # Ask for the same episode again
        return await series_ask_next_episode(update, context, edit=True)

    if query.data == "series_skip_ep":
        # Skip current episode
        ep_index = context.user_data.get("series_current_ep_index", 0)
        overall_ep = ep_index + 1
        # Store a placeholder
        uploaded = context.user_data.get("series_uploaded_playback_ids", [])
        uploaded.append((overall_ep, "تم_التخطي", "تم التخطي"))
        context.user_data["series_uploaded_playback_ids"] = uploaded
        context.user_data["series_current_ep_index"] = ep_index + 1
        return await series_ask_next_episode(update, context, edit=True)

    if query.data == "series_pause":
        return await series_pause(update, context)


async def series_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause the upload and show summary so far."""
    query = update.callback_query
    series_name = context.user_data.get("series_name")
    season_num = context.user_data.get("series_current_season")
    ep_index = context.user_data.get("series_current_ep_index", 0)
    total_episodes = context.user_data.get("series_total_episodes", 0)
    uploaded = context.user_data.get("series_uploaded_playback_ids", [])

    text = (
        f"⏸️ <b>تم إيقاف الرفع مؤقتاً</b>\n\n"
        f"📺 <b>{series_name} - الموسم {season_num}</b>\n"
        f"📊 <b>تم رفع:</b> {ep_index} من {total_episodes} حلقة\n\n"
    )

    if uploaded:
        text += "<b>الحلقات المرفوعة:</b>\n"
        for ep_num, pid, name in uploaded:
            if pid == "تم_التخطي":
                text += f"  الحلقة {ep_num}: ⏭️ تم التخطي\n"
            else:
                text += f"  الحلقة {ep_num}: <code>{pid}</code>\n"

    text += "\n<i>يمكنك الاستكمال لاحقاً من القائمة الرئيسية.</i>"

    keyboard = [
        [InlineKeyboardButton("▶️ استكمال الرفع", callback_data="series_resume")],
        [InlineKeyboardButton("📋 عرض معرفات التشغيل", callback_data="series_show_ids")],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return SERIES_SEASON_DONE


async def series_season_complete(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = True):
    """Show completion message for the season."""
    series_name = context.user_data.get("series_name")
    season_num = context.user_data.get("series_current_season")
    total_episodes = context.user_data.get("series_total_episodes", 0)
    uploaded = context.user_data.get("series_uploaded_playback_ids", [])
    seasons = context.user_data.get("series_seasons", [])

    successful = [u for u in uploaded if u[1] != "تم_التخطي"]
    skipped = [u for u in uploaded if u[1] == "تم_التخطي"]

    text = (
        f"✅ <b>اكتمل رفع الموسم {season_num}!</b>\n\n"
        f"📺 <b>{series_name}</b>\n"
        f"📊 <b>إجمالي الحلقات:</b> {total_episodes}\n"
        f"✅ <b>تم رفعها:</b> {len(successful)}\n"
    )

    if skipped:
        text += f"⏭️ <b>تم تخطيها:</b> {len(skipped)}\n"

    text += "\n<b>معرفات التشغيل (بالترتيب):</b>\n"
    # Sort by episode number
    sorted_uploaded = sorted(uploaded, key=lambda x: x[0])
    for ep_num, pid, name in sorted_uploaded:
        if pid == "تم_التخطي":
            text += f"  الحلقة {ep_num}: ⏭️ تم التخطي\n"
        else:
            text += f"  الحلقة {ep_num}: <code>{pid}</code>\n"

    # Check if there are more seasons
    keyboard = []
    other_seasons = [s for s in seasons if s.get("season_number") != season_num]
    if other_seasons:
        keyboard.append([InlineKeyboardButton("📺 إضافة موسم آخر", callback_data="series_back_to_seasons")])
    keyboard.append([InlineKeyboardButton("📋 نسخ جميع المعرفات", callback_data="series_copy_all_ids")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")])

    if edit:
        query = update.callback_query
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML,
            )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )

    return SERIES_SEASON_DONE


async def series_season_done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle actions after season is complete or paused."""
    query = update.callback_query
    await query.answer()

    if query.data == "menu_back":
        return await show_main_menu(update, context, edit=True)

    if query.data == "series_back_to_seasons":
        return await series_back_to_seasons(update, context)

    if query.data in ("series_resume", "series_resume_from_menu"):
        # Resume uploading from where we left off
        return await series_ask_next_episode(update, context, edit=True)

    if query.data == "series_show_ids":
        return await series_show_all_playback_ids(update, context)

    if query.data == "series_copy_all_ids":
        return await series_copy_all_ids(update, context)

    if query.data == "series_back_to_done":
        return await series_season_complete(update, context, edit=True)


async def series_back_to_seasons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to season selection screen."""
    query = update.callback_query
    series_name = context.user_data.get("series_name")
    tmdb_id = context.user_data.get("series_tmdb_id")
    seasons = context.user_data.get("series_seasons", [])

    # Reset episode tracking for new season
    context.user_data.pop("series_current_ep_index", None)
    context.user_data.pop("series_current_plan_index", None)
    context.user_data.pop("series_uploaded_playback_ids", None)
    context.user_data.pop("series_upload_plan", None)

    keyboard = []
    row = []
    for i, season in enumerate(seasons, 1):
        s_num = season.get("season_number", i)
        ep_count = season.get("episode_count", 0)
        btn_text = f"الموسم {s_num} ({ep_count} حلقة)"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"series_season_{s_num}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Add option to view all accumulated playback IDs
    all_pids = context.user_data.get("series_all_playback_ids", {})
    if all_pids:
        keyboard.append([InlineKeyboardButton("📋 عرض جميع معرفات التشغيل", callback_data="series_show_all_ids")])

    keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")])

    text = (
        f"📺 <b>{series_name}</b>\n"
        f"🆔 TMDB ID: <code>{tmdb_id}</code>\n\n"
    )

    for season in seasons:
        s_num = season.get("season_number", 0)
        ep_count = season.get("episode_count", 0)
        # Check if this season has been uploaded
        season_key = str(s_num)
        if season_key in all_pids and all_pids[season_key]:
            uploaded_count = len(all_pids[season_key])
            text += f"  الموسم {s_num}: {ep_count} حلقة (✅ تم رفع {uploaded_count})\n"
        else:
            text += f"  الموسم {s_num}: {ep_count} حلقة\n"

    text += "\n<b>اختر الموسم:</b>"

    await _safe_send_or_edit(query, text, keyboard)
    return SERIES_SELECT_SEASON


async def series_show_all_playback_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all playback IDs for the current season - ordered from episode 1 downward."""
    query = update.callback_query
    series_name = context.user_data.get("series_name")
    season_num = context.user_data.get("series_current_season")
    uploaded = context.user_data.get("series_uploaded_playback_ids", [])

    text = f"📋 <b>{series_name} - الموسم {season_num} - معرفات التشغيل</b>\n\n"

    # Sort by episode number (from 1 downward)
    sorted_uploaded = sorted(uploaded, key=lambda x: x[0])

    all_ids = []
    for ep_num, pid, name in sorted_uploaded:
        if pid == "تم_التخطي":
            text += f"الحلقة {ep_num}: ⏭️ تم التخطي\n"
        else:
            text += f"الحلقة {ep_num}: <code>{pid}</code>\n"
            all_ids.append(pid)

    if all_ids:
        text += f"\n<b>نسخ سريع (جميع المعرفات بالترتيب):</b>\n<code>{chr(10).join(all_ids)}</code>"

    keyboard = [
        [InlineKeyboardButton("🔙 رجوع", callback_data="series_back_to_done")],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )
    return SERIES_SEASON_DONE


async def series_copy_all_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Copy all playback IDs for the current season."""
    query = update.callback_query
    uploaded = context.user_data.get("series_uploaded_playback_ids", [])

    sorted_uploaded = sorted(uploaded, key=lambda x: x[0])
    all_ids = [pid for ep_num, pid, name in sorted_uploaded if pid != "تم_التخطي"]

    if all_ids:
        ids_text = "\n".join(all_ids)
        await query.message.reply_text(
            f"📋 <b>جميع معرفات التشغيل (بالترتيب):</b>\n\n<code>{ids_text}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await query.answer("لا توجد معرفات تشغيل متاحة", show_alert=True)

    return SERIES_SEASON_DONE


async def series_show_all_seasons_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all playback IDs across all uploaded seasons."""
    query = update.callback_query
    await query.answer()

    series_name = context.user_data.get("series_name")
    all_pids = context.user_data.get("series_all_playback_ids", {})

    text = f"📋 <b>{series_name} - جميع معرفات التشغيل</b>\n\n"

    all_ids_flat = []
    for season_key in sorted(all_pids.keys(), key=lambda x: int(x)):
        season_eps = all_pids[season_key]
        text += f"<b>الموسم {season_key}:</b>\n"
        for ep_key in sorted(season_eps.keys(), key=lambda x: int(x)):
            pid = season_eps[ep_key]
            text += f"  الحلقة {ep_key}: <code>{pid}</code>\n"
            if pid != "تم_التخطي":
                all_ids_flat.append(pid)
        text += "\n"

    if all_ids_flat:
        text += f"<b>نسخ سريع:</b>\n<code>{chr(10).join(all_ids_flat)}</code>"

    keyboard = [
        [InlineKeyboardButton("🔙 رجوع للمواسم", callback_data="series_back_to_seasons")],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")],
    ]

    await _safe_send_or_edit(query, text, keyboard)
    return SERIES_SELECT_SEASON


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ <b>تم إلغاء العملية</b>\n\n" "استخدم /start للبدء من جديد.",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable is not set!")
        return
    
    if not GITHUB_TOKEN:
        print("Warning: GITHUB_TOKEN not set - sections will only be saved locally!")
    else:
        print(f"GitHub integration enabled for repo: {GITHUB_REPO}")

    # Load sections from GitHub (or local file as fallback)
    print("Loading sections from GitHub...")
    sections = load_sections()
    
    print("Bot starting...")
    print(f"Cinema Plus: {len(sections.get('cinema_plus', {}))} sections loaded")
    print(f"Shoof Play: {len(sections.get('shoof_play', {}))} sections loaded")

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
            # Series states
            SERIES_ENTER_TMDB_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, series_handle_tmdb_id),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
            ],
            SERIES_SELECT_SEASON: [
                CallbackQueryHandler(series_select_season, pattern="^series_season_"),
                CallbackQueryHandler(series_show_all_seasons_ids, pattern="^series_show_all_ids$"),
                CallbackQueryHandler(series_back_to_seasons, pattern="^series_back_to_seasons$"),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_add_section$"),
            ],
            SERIES_CONFIRM_PLAN: [
                CallbackQueryHandler(series_confirm_plan, pattern="^series_confirm_start$"),
                CallbackQueryHandler(series_back_to_seasons, pattern="^series_back_to_seasons$"),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
            ],
            SERIES_ENTER_EPISODE_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, series_handle_episode_link),
                CallbackQueryHandler(series_episode_callback, pattern="^series_"),
                CallbackQueryHandler(main_menu_handler, pattern="^menu_back$"),
            ],
            SERIES_SEASON_DONE: [
                CallbackQueryHandler(series_season_done_handler, pattern="^series_|^menu_back$"),
                CallbackQueryHandler(series_back_to_seasons, pattern="^series_back_to_seasons$"),
            ],
            SERIES_SHOW_PLAYBACK_IDS: [
                CallbackQueryHandler(series_season_done_handler, pattern="^series_|^menu_back$"),
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
