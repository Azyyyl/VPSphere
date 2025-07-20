import os
import asyncio
import subprocess
import tempfile
import time
import threading
import re
from telegram.ext import ApplicationBuilder
from datetime import datetime
import pytz
from dotenv import load_dotenv
from telegram import (
    Update, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)

# -------------------------
# ⚙️ Konfigurasi
# -------------------------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
USER_ID = os.getenv("USER_ID")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN belum diset di file .env!")
if not USER_ID:
    raise ValueError("❌ USER_ID belum diset di file .env!")

ALLOWED_USER_ID = int(USER_ID)
current_dir = "/opt/hostingerbot"  # Lokasi instalasi bot
active_process = {}
BUFFER_LIMIT = 3500

# -------------------------
# 🔒 Escape Markdown
# -------------------------
def escape_markdown(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f"([{re.escape(escape_chars)}])", r'\\\1', text)

# -------------------------
# 🔍 Deteksi Login SSH 
# -------------------------
async def check_logins(bot):
    """
    Pantau login SSH dari systemd journal (Debian 12, Hostinger).
    Kirim notifikasi otomatis ke ALLOWED_USER_ID jika ada login baru.
    """
    known_logins = set()

    print("📂 Memantau log SSH dari systemd journal...")
    try:
        # Jalankan journalctl follow mode
        process = await asyncio.create_subprocess_exec(
            "/usr/bin/journalctl", "-u", "ssh", "-f", "-n", "0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )


        async for line_bytes in process.stdout:
            line = line_bytes.decode(errors="ignore").strip()

            # Cari event login berhasil
            if "Accepted password for" in line:
                match = re.search(r"Accepted password for (\w+) from ([\d\.]+)", line)
                if match:
                    user, ip = match.groups()
                    waktu = datetime.now(pytz.timezone("Asia/Makassar")).strftime("%Y-%m-%d %H:%M:%S")
                    key = f"{user}@{ip}"

                    if key not in known_logins:
                        known_logins.add(key)

                        pesan = (
                            "🚨 <b><u>WARNING: SSH ACCESS</u></b> 🚨\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 <b>User:</b> <code>{user}</code>\n"
                            f"🌐 <b>IP:</b> <code>{ip}</code>\n"
                            f"⏰ <b>Time (WITA):</b> <code>{waktu}</code>\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            "⚠️ <b>Verify if this login is authorized!</b>"
                        )

                        try:
                            await bot.send_message(chat_id=ALLOWED_USER_ID, text=pesan, parse_mode="HTML")
                        except Exception as e:
                            print(f"Gagal kirim notifikasi SSH: {e}")

    except asyncio.CancelledError:
        print("Task check_logins dihentikan.")
        raise


# -------------------------
# 📝 Log aktivitas
# -------------------------
def log_activity(command):
    with open("activity.log", "a") as f:
        f.write(f"[{datetime.now()}] CMD: {command}\n")

# -------------------------
# 👋 Pesan Selamat Datang
# -------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    welcome_msg = (
        "*Selamat Datang di VPSphere v3.3!*\n\n"
        "Bot ini siap membantu kamu mengelola server langsung dari Telegram.\n\n"
        "Ketik `/help` untuk melihat daftar perintah yang tersedia.\n\n"
        "⚠️ *Hanya user terotorisasi yang bisa mengakses bot ini!*"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

# -------------------------
# 📖 Bantuan
# -------------------------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🧹 Bersihkan", callback_data="clear"),
        InlineKeyboardButton("📂 Lihat Folder", callback_data="ls"),
        InlineKeyboardButton("📊 Status Server", callback_data="status")
    ]])
    msg = (
        "*VPSphere v3.3 - Menu Bantuan:*\n"
        "==========================================\n"
        "`cd [folder]` - pindah direktori\n"
        "`[perintah shell]` - jalankan perintah bebas\n"
        "`/upload` - upload file ke server\n"
        "`/download [file]` - ambil file dari server\n"
        "`/clear` - hapus chat terakhir\n"
        "`/help` - tampilkan menu ini\n\n"
        "*Contoh:*\n"
        "`nmap scanme.nmap.org`\n"
        "`apt update && apt upgrade -y`\n"
        "`sqlmap -u \"http://target.com?id=1\"`\n\n"
        "==========================================\n"
        "*Powered by : Azylx001*"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

# -------------------------
# 🧹 Clear Chat
# -------------------------
async def clear_messages(chat_id, message_id, context, count=30):
    for i in range(count):
        try:
            await context.bot.delete_message(chat_id, message_id - i)
        except:
            continue

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    await clear_messages(update.effective_chat.id, update.message.message_id, context, count=30)
    await update.message.reply_text("🧹 *Chat dibersihkan.*", parse_mode="Markdown")

# -------------------------
# 📂 Lihat Folder
# -------------------------
async def ls_folder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = os.listdir(current_dir)
    message = "\n".join(files) or "📂 Tidak ada file."
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        f"📂 *Isi folder:*\n```\n{escape_markdown(message)}\n```",
        parse_mode="MarkdownV2"
    )

# -------------------------
# 📊 Status Server
# -------------------------
async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uptime = subprocess.check_output("uptime -p", shell=True).decode().strip()
        disk = subprocess.check_output("df -h /", shell=True).decode().strip()
        mem = subprocess.check_output("free -h", shell=True).decode().strip()
        msg = (
            f"*Status Server:*\n\n"
            f"🟢 *Uptime:* `{escape_markdown(uptime)}`\n\n"
            f"💾 *Disk:*\n```\n{escape_markdown(disk)}\n```\n\n"
            f"🧠 *Memori:*\n```\n{escape_markdown(mem)}\n```"
        )
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(msg, parse_mode="MarkdownV2")
    except Exception as e:
        await update.callback_query.message.reply_text(
            f"❌ Error status:\n`{escape_markdown(str(e))}`", parse_mode="MarkdownV2"
        )

# -------------------------
# 📤 Upload Handler (Info)
# -------------------------
async def upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    await update.message.reply_text("📤 Kirim file (maks 2GB). Akan disimpan di folder `Upload/`.")

# -------------------------
# 📥 Download Handler
# -------------------------
async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    parts = update.message.text.strip().split()
    if len(parts) != 2:
        await update.message.reply_text("❗ Format: `/download nama_file.ext`", parse_mode="Markdown")
        return
    filepath = os.path.join(current_dir, parts[1])
    if not os.path.isfile(filepath):
        await update.message.reply_text("❌ File tidak ditemukan.")
        return
    try:
        with open(filepath, "rb") as f:
            await update.message.reply_document(InputFile(f, filename=parts[1]))
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal mengirim file:\n`{escape_markdown(str(e))}`", parse_mode="MarkdownV2")

# -------------------------
# 🧠 Jalankan Perintah Shell
# -------------------------
async def run_shell(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    global active_process
    await update.message.reply_text(
        f"⏳ Menjalankan perintah:\n`{escape_markdown(command)}`", parse_mode="MarkdownV2"
    )
    log_activity(command)
    proc = await asyncio.create_subprocess_shell(
        command, cwd=current_dir,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ, "TERM": "xterm"}
    )
    active_process[update.effective_chat.id] = proc
    buffer = []
    async for line in proc.stdout:
        text = line.decode(errors="ignore")
        buffer.append(text)
        if sum(len(x) for x in buffer) > BUFFER_LIMIT:
            await update.message.reply_text(
                f"```\n{escape_markdown(''.join(buffer))}\n```", parse_mode="MarkdownV2"
            )
            buffer.clear()
    if buffer:
        output = "".join(buffer).strip()
        if len(output) > 3500:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w") as tmpf:
                tmpf.write(output)
                tmp_path = tmpf.name
            await update.message.reply_document(open(tmp_path, "rb"), filename="output.txt")
            os.remove(tmp_path)
        else:
            await update.message.reply_text(
                f"```\n{escape_markdown(output)}\n```", parse_mode="MarkdownV2"
            )
    await proc.wait()
    active_process.pop(update.effective_chat.id, None)

# -------------------------
# 🖊 Input Manual
# -------------------------
async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    proc = active_process.get(update.effective_chat.id)
    if proc:
        user_input = update.message.text + "\n"
        proc.stdin.write(user_input.encode())
        await proc.stdin.drain()
    else:
        await handle_command(update, context)

# -------------------------
# Perintah Teks Utama
# -------------------------
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    global current_dir
    text = update.message.text.strip()
    if text.lower().startswith("cd "):
        new_path = os.path.abspath(os.path.join(current_dir, text[3:].strip()))
        if os.path.isdir(new_path):
            current_dir = new_path
            await update.message.reply_text(
                f"📁 Berpindah ke:\n`{escape_markdown(current_dir)}`", parse_mode="MarkdownV2"
            )
        else:
            await update.message.reply_text("❌ Folder tidak ditemukan.")
    else:
        await run_shell(update, context, text)

# -------------------------
# Upload File Handler
# -------------------------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    try:
        doc = update.message.document
        if not doc:
            await update.message.reply_text("❌ Tidak ada file yang diupload.", parse_mode="HTML")
            return
        target_dir = os.path.join(current_dir, "Upload")
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, doc.file_name)
        telegram_file = await context.bot.get_file(doc.file_id)
        await telegram_file.download_to_drive(filepath)
        await update.message.reply_text(
            f"✅ <b>Upload berhasil!</b>\n"
            f"Nama file: <code>{doc.file_name}</code>\n"
            f"Lokasi: <code>{filepath}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal upload:\n<code>{e}</code>", parse_mode="HTML")

# -------------------------
# Handle Media (Foto/Video/Audio)
# -------------------------
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    try:
        target_dir = os.path.join(current_dir, "Upload")
        os.makedirs(target_dir, exist_ok=True)

        if update.message.photo:
            file_obj = update.message.photo[-1]
            ext = ".jpg"
            fname = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        elif update.message.video:
            file_obj = update.message.video
            ext = ".mp4"
            fname = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        elif update.message.audio:
            file_obj = update.message.audio
            ext = ".mp3"
            fname = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        else:
            await update.message.reply_text("❌ Tidak ada media yang bisa diupload.", parse_mode="HTML")
            return

        filepath = os.path.join(target_dir, fname)
        telegram_file = await context.bot.get_file(file_obj.file_id)
        await telegram_file.download_to_drive(filepath)

        await update.message.reply_text(
            f"✅ <b>Media berhasil diupload!</b>\n"
            f"Nama file: <code>{fname}</code>\n"
            f"Lokasi: <code>{filepath}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal upload media:\n<code>{e}</code>", parse_mode="HTML")

# -------------------------
# Callback Handler
# -------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "clear":
        await clear_messages(update.effective_chat.id, update.callback_query.message.message_id, context, count=30)
    elif data == "ls":
        await ls_folder(update, context)
    elif data == "status":
        await system_status(update, context)

# -------------------------
# 🚀 Main
# -------------------------
last_logged_in = set()

async def on_startup(app):
    print("Bot siap!")
    asyncio.create_task(check_logins(app.bot))


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("upload", upload_handler))
    app.add_handler(CommandHandler("download", download_handler))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    app.run_polling()
