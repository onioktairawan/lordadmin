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

# Fungsi untuk mendapatkan ID dan username pengguna
async def get_user_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Jika ada balasan pesan
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user

    # Jika ada username yang diberikan dalam perintah
    if len(update.message.text.split()) > 1:
        target = update.message.text.split()[1]
        
        if target.startswith('@'):
            # Mengambil username tanpa '@'
            username = target.lstrip('@')
            try:
                # Coba ambil user berdasarkan username
                user = await context.bot.get_chat_member(update.message.chat_id, username)
                return user.user
            except:
                await update.message.reply_text(f"Pengguna dengan username @{username} tidak ditemukan.")
                return None
        else:
            try:
                # Jika itu ID numerik, coba cari berdasarkan ID
                user = await context.bot.get_chat_member(update.message.chat_id, int(target))
                return user.user
            except:
                await update.message.reply_text(f"Pengguna dengan ID {target} tidak ditemukan.")
                return None

    return None  # Jika tidak ada username atau ID yang diberikan

# Fungsi untuk menyambut anggota baru
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        name = member.first_name
        username = member.username if member.username else "Tidak ada username"
        user_id = member.id
        await update.message.reply_text(f"Selamat datang {name} (@{username}) dengan ID {user_id}!")

# Fungsi untuk memberikan peringatan
@admin_required
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user = await get_user_from_message(update, context)
    if not target_user:
        return

    warned_user = target_user
    await update.message.reply_text(f"{warned_user.first_name} telah diberi peringatan.")
    await notify_admins(update, context, "Memberi peringatan", warned_user.first_name)

# Fungsi untuk membisukan anggota
@admin_required
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user = await get_user_from_message(update, context)
    if not target_user:
        return

    muted_user = target_user
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
    target_user = await get_user_from_message(update, context)
    if not target_user:
        return

    kicked_user = target_user
    await context.bot.ban_chat_member(update.message.chat_id, kicked_user.id)
    await update.message.reply_text(f"{kicked_user.first_name} telah dikeluarkan dari grup.")
    await notify_admins(update, context, "Mengeluarkan", kicked_user.first_name)

# Fungsi untuk unmute anggota
@admin_required
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user = await get_user_from_message(update, context)
    if not target_user:
        return

    unmuted_user = target_user
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
    # Cek apakah perintah dimulai dengan nama bot ini
    if not update.message.text.startswith('/' + context.bot.username):
        return  # Abaikan perintah yang ditujukan ke bot lain

    # Jika perintah tidak dikenali, balas dengan pesan ini
    await update.message.reply_text("Perintah yang Anda masukkan tidak dikenal. Ketik /help untuk daftar perintah yang tersedia.")

# Fungsi untuk menangani perintah /info
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global status_bot
    await update.message.reply_text(f"Bot Status: {status_bot}")

# Fungsi untuk menangani event bot disconnect
async def handle_disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global status_bot
    status_bot = "Disconnected"
    logger.error("Bot status updated to Disconnected.")

# Fungsi utama untuk menjalankan bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("kick", kick))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("info", info))  # Menambahkan perintah /info
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Misalnya, memanggil handle_disconnect ketika bot terputus (untuk simulasi)
    # Anda dapat menyesuaikan logika ini tergantung bagaimana Anda mendeteksi disconnect
    application.add_error_handler(handle_disconnect)

    application.run_polling()

if __name__ == "__main__":
    main()
