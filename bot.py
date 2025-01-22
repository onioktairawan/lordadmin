from dotenv import load_dotenv
import os
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters
from functools import wraps
import logging

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Variabel global untuk menyimpan status bot dan pengguna yang diban
status_bot = "Running"  # Status awal adalah Running
banned_users = {}  # Menyimpan user_id dan username dari pengguna yang diban

# Fungsi untuk memeriksa apakah pengguna adalah admin
async def is_admin(update: Update) -> bool:
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    admins = await update.message.chat.get_administrators()
    return any(admin.user.id == user_id for admin in admins)

# Dekorator untuk memeriksa apakah pengguna adalah admin
def admin_required(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not await is_admin(update):
            await update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Fungsi untuk menyambut anggota baru
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_image_url = "https://i.pinimg.com/236x/1f/c8/24/1fc8244a27f7665e2d694a44665a4d83.jpg"
    welcome_text = "Selamat datang di grup, {}! 😊 Jangan lupa baca aturan grup dan jadikan tempat ini menyenangkan untuk semua!"
    
    for member in update.message.new_chat_members:
        await update.message.reply_photo(welcome_image_url, caption=welcome_text.format(member.first_name))

# Fungsi untuk menangani perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Saya adalah bot pengelola grup Anda. Ketik /help untuk melihat daftar perintah.")

# Fungsi untuk memberikan peringatan
@admin_required
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Harap balas pesan anggota yang ingin diberi peringatan.")
        return

    warned_user = update.message.reply_to_message.from_user
    await update.message.reply_text(f"{warned_user.first_name} telah diberi peringatan.")
    await notify_admins(update, context, "Memberi peringatan", warned_user.first_name)

# Fungsi untuk membisukan anggota
@admin_required
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Harap balas pesan anggota yang ingin dibisukan.")
        return

    muted_user = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        update.message.chat_id,
        muted_user.id,
        permissions=ChatPermissions(can_send_messages=False)
    )
    await update.message.reply_text(f"{muted_user.first_name} telah dibisukan.")
    await notify_admins(update, context, "Membisukan", muted_user.first_name)

# Fungsi untuk mengeluarkan anggota
@admin_required
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Harap balas pesan anggota yang ingin dikeluarkan.")
        return

    kicked_user = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.message.chat_id, kicked_user.id)
    await update.message.reply_text(f"{kicked_user.first_name} telah dikeluarkan dari grup.")
    await notify_admins(update, context, "Mengeluarkan", kicked_user.first_name)

# Fungsi untuk ban anggota
@admin_required
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Harap balas pesan anggota yang ingin diban.")
        return

    banned_user = update.message.reply_to_message.from_user
    username = f"@{banned_user.username}" if banned_user.username else banned_user.first_name

    # Simpan User ID ke dalam dictionary banned_users
    banned_users[banned_user.id] = username

    await context.bot.ban_chat_member(update.message.chat_id, banned_user.id)
    await update.message.reply_text(f"{username} telah diban dari grup secara permanen.")
    await notify_admins(update, context, "Banned", username)

# Fungsi untuk unban anggota
@admin_required
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Harap masukkan username atau User ID anggota yang ingin di-unban.")
        return

    input_value = context.args[0]
    user_id = next((uid for uid, uname in banned_users.items() if uname.strip("@") == input_value.strip("@")), None)

    if user_id:
        await context.bot.unban_chat_member(update.message.chat_id, user_id)
        await update.message.reply_text(f"{input_value} telah di-unban.")
        # Hapus dari daftar banned_users
        banned_users.pop(user_id, None)
        await notify_admins(update, context, "Unbanned", input_value)
    else:
        await update.message.reply_text("Tidak dapat menemukan anggota dengan username atau User ID tersebut.")

# Fungsi untuk memberi pemberitahuan kepada admin saat peringatan/mute/kick/ban
async def notify_admins(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, target_user: str):
    admins = await update.message.chat.get_administrators()
    action_message = f"Admin {update.message.from_user.first_name} telah melakukan aksi: {action} pada {target_user}."
    for admin in admins:
        await context.bot.send_message(admin.user.id, action_message)

# Fungsi utama untuk menjalankan bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("kick", kick))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))

    application.run_polling()

if __name__ == "__main__":
    main()

from dotenv import load_dotenv
import os
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters
from functools import wraps
import logging

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Variabel global untuk menyimpan status bot, banned users, dan data anggota
status_bot = "Running"
banned_users = {}
members_data = {}  # {user_id: {"current_name": str, "current_username": str, "history": list}}

# Fungsi untuk memperbarui data anggota
def update_member_data(member):
    user_id = member.id
    name = member.full_name
    username = f"@{member.username}" if member.username else None

    if user_id not in members_data:
        members_data[user_id] = {"current_name": name, "current_username": username, "history": []}
    else:
        current_data = members_data[user_id]
        # Jika nama atau username berubah, tambahkan ke riwayat
        if current_data["current_name"] != name:
            current_data["history"].append(f"Name: {current_data['current_name']}")
            current_data["current_name"] = name
        if current_data["current_username"] != username:
            current_data["history"].append(f"Username: {current_data['current_username']}")
            current_data["current_username"] = username

# Fungsi untuk memeriksa apakah pengguna adalah admin
async def is_admin(update: Update) -> bool:
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    admins = await update.message.chat.get_administrators()
    return any(admin.user.id == user_id for admin in admins)

# Dekorator untuk memeriksa apakah pengguna adalah admin
def admin_required(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not await is_admin(update):
            await update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Fungsi untuk menyambut anggota baru
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_image_url = "https://i.pinimg.com/236x/1f/c8/24/1fc8244a27f7665e2d694a44665a4d83.jpg"
    welcome_text = "Selamat datang di grup, {}! 😊 Jangan lupa baca aturan grup dan jadikan tempat ini menyenangkan untuk semua!"

    for member in update.message.new_chat_members:
        update_member_data(member)  # Perbarui data anggota
        await update.message.reply_photo(welcome_image_url, caption=welcome_text.format(member.first_name))

# Fungsi untuk menampilkan data semua anggota dengan perintah /sg
@admin_required
async def show_all_member_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(members_data) == 0:
        await update.message.reply_text("Tidak ada data anggota.")
        return

    all_members_info = "Data Semua Anggota:\n\n"
    for user_id, data in members_data.items():
        history = "\n".join(data["history"]) if data["history"] else "Tidak ada riwayat."
        all_members_info += (
            f"User ID: {user_id}\n"
            f"- Nama: {data['current_name']}\n"
            f"- Username: {data['current_username']}\n"
            f"Riwayat:\n{history}\n\n"
        )
    
    await update.message.reply_text(all_members_info)

# Fungsi untuk menangani perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Saya adalah bot pengelola grup Anda. Ketik /help untuk melihat daftar perintah.")

# Fungsi utama untuk menjalankan bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sg", show_all_member_data))  # Handler untuk perintah /sg

    application.run_polling()

if __name__ == "__main__":
    main()
