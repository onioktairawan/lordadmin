from dotenv import load_dotenv
import os
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters
from telegram import Bot
import logging
from functools import wraps

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Variabel global untuk menyimpan status bot
status_bot = "Running"  # Status awal adalah Running

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

# Fungsi untuk mencari user berdasarkan username
async def get_user_by_username(update: Update, username: str):
    chat_id = update.message.chat_id
    members = await update.message.chat.get_members()
    for member in members:
        if member.user.username == username:
            return member.user
    return None

# Fungsi untuk menyambut anggota baru
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_image_url = "https://i.pinimg.com/236x/1f/c8/24/1fc8244a27f7665e2d694a44665a4d83.jpg"
    welcome_text = "Selamat datang di grup, {}! 😊 Jangan lupa baca aturan grup dan jadikan tempat ini menyenangkan untuk semua!"
    
    for member in update.message.new_chat_members:
        await update.message.reply_photo(welcome_image_url, caption=welcome_text.format(member.first_name))

# Fungsi untuk menangani perintah /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Saya adalah bot pengelola grup Anda. Ketik /help untuk melihat daftar perintah.")

# Fungsi untuk menangani perintah /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Daftar Perintah:\n/start - Memulai bot\n/help - Melihat bantuan\n/rules - Menampilkan aturan grup\n/report - Melaporkan masalah ke admin\n/warn - Memberikan peringatan ke anggota\n/mute - Membisukan anggota\n/kick - Mengeluarkan anggota")

# Fungsi untuk menampilkan aturan grup
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Aturan Grup:\n1. Hormati sesama anggota.\n2. Jangan spam.\n3. Ikuti arahan admin.")

# Fungsi untuk memberi peringatan
@admin_required
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Harap balas pesan anggota yang ingin diberi peringatan.")
        return

    warned_user = update.message.reply_to_message.from_user
    await update.message.reply_text(f"{warned_user.first_name} telah diberi peringatan.")
    await notify_admins(update, context, "Memberi peringatan", warned_user.first_name)

# Fungsi untuk membisukan anggota berdasarkan username atau reply
@admin_required
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if len(text.split()) > 1:
        # Menggunakan username
        username = text.split()[1].lstrip('@')
        user_to_mute = await get_user_by_username(update, username)
        if user_to_mute:
            await context.bot.restrict_chat_member(
                update.message.chat_id,
                user_to_mute.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await update.message.reply_text(f"{user_to_mute.first_name} telah dibisukan.")
            await notify_admins(update, context, "Membisukan", user_to_mute.first_name)
        else:
            await update.message.reply_text(f"Pengguna dengan username @{username} tidak ditemukan.")
    elif update.message.reply_to_message:
        # Menggunakan reply
        muted_user = update.message.reply_to_message.from_user
        await context.bot.restrict_chat_member(
            update.message.chat_id,
            muted_user.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await update.message.reply_text(f"{muted_user.first_name} telah dibisukan.")
        await notify_admins(update, context, "Membisukan", muted_user.first_name)
    else:
        await update.message.reply_text("Harap balas pesan anggota yang ingin dibisukan atau masukkan username dengan format @username.")

# Fungsi untuk kick anggota berdasarkan username atau reply
@admin_required
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if len(text.split()) > 1:
        # Menggunakan username
        username = text.split()[1].lstrip('@')
        user_to_kick = await get_user_by_username(update, username)
        if user_to_kick:
            await context.bot.ban_chat_member(update.message.chat_id, user_to_kick.id)
            await update.message.reply_text(f"{user_to_kick.first_name} telah dikeluarkan dari grup.")
            await notify_admins(update, context, "Mengeluarkan", user_to_kick.first_name)
        else:
            await update.message.reply_text(f"Pengguna dengan username @{username} tidak ditemukan.")
    elif update.message.reply_to_message:
        # Menggunakan reply
        kicked_user = update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(update.message.chat_id, kicked_user.id)
        await update.message.reply_text(f"{kicked_user.first_name} telah dikeluarkan dari grup.")
        await notify_admins(update, context, "Mengeluarkan", kicked_user.first_name)
    else:
        await update.message.reply_text("Harap balas pesan anggota yang ingin dikeluarkan atau masukkan username dengan format @username.")

# Fungsi untuk unmute anggota
@admin_required
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Harap balas pesan anggota yang ingin diunmute.")
        return

    unmuted_user = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        update.message.chat_id,
        unmuted_user.id,
        permissions=ChatPermissions(can_send_messages=True)
    )
    await update.message.reply_text(f"{unmuted_user.first_name} telah diunmute.")
    await notify_admins(update, context, "Unmute", unmuted_user.first_name)

# Fungsi untuk memberi pemberitahuan kepada admin saat peringatan/mute/kick
async def notify_admins(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, target_user: str):
    admins = await update.message.chat.get_administrators()
    action_message = f"Admin {update.message.from_user.first_name} telah melakukan aksi: {action} pada {target_user}."
    for admin in admins:
        await context.bot.send_message(admin.user.id, action_message)

# Fungsi untuk menangani laporan
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report_message = "Seorang anggota melaporkan masalah di grup."
    admins = await update.message.chat.get_administrators()
    for admin in admins:
        await context.bot.send_message(admin.user.id, f"Laporan Baru:\n{report_message}\nDari: {update.message.from_user.first_name}")
    await update.message.reply_text("Laporan Anda telah dikirim ke admin.")

# Fungsi untuk menangani perintah yang tidak dikenal
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.startswith('/' + context.bot.username):
        return  # Abaikan perintah yang ditujukan ke bot lain

    await update.message.reply_text("Perintah yang Anda masukkan tidak dikenal. Ketik /help untuk daftar perintah yang tersedia.")

# Fungsi untuk menangani perintah /info
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global status_bot
    await update.message.reply_text(f"Bot Status: {status_bot}")

# Fungsi utama untuk menjalankan bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("kick", kick))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("info", info))  # Menambahkan perintah /info
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    application.run_polling()

if __name__ == "__main__":
    main()
