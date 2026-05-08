import asyncio
import os
import pandas as pd
from aiogram import Router, types, F
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select

# Loyiha ichki modullari
from config.config import ADMINS
from database.models import async_session, Movie, User, Channel
from database.requests import (
    get_statistics, get_all_users, get_all_channels, 
    add_channel, delete_channel, delete_movie_by_code
)

router = Router()

# --- FSM HOLATLARI ---
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()  # Reklama kutish
    confirm_broadcast = State()      # Tasdiqlash
    waiting_for_movie_manage = State() # Kino boshqaruvi

class ChannelStates(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_title = State()
    waiting_for_channel_link = State()

# --- ADMIN KLAVIATURASI ---
def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📊 Statistika")
    builder.button(text="✉️ Xabar tarqatish")
    builder.button(text="📢 Majburiy obuna")
    builder.button(text="🎬 Kinolarni boshqarish")
    builder.button(text="💾 Bazani yuklash")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

# --- 1. STATISTIKA MODULI ---
@router.message(F.text == "📊 Statistika")
async def show_statistics(message: types.Message):
    if message.from_user.id not in ADMINS: return
    
    wait_msg = await message.answer("⏳ Bazadan ma'lumotlar yig'ilmoqda...")
    total_users, total_movies, top_movies = await get_statistics()
    
    text = (
        f"<b>📊 Loyiha Statistikasi</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 Jami mijozlar: <b>{total_users}</b> ta\n"
        f"🎞 Jami kinolar: <b>{total_movies}</b> ta\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>TOP-3 Kinolar:</b>\n"
    )
    if top_movies:
        for i, movie in enumerate(top_movies, 1):
            text += f" {i}. Kodi: <code>{movie.kino_kodi}</code> | 👍 {movie.likes} ta\n"
    else:
        text += " <i>Hozircha baholangan kinolar yo'q.</i>\n"

    await asyncio.sleep(0.5)
    await wait_msg.edit_text(text, parse_mode="HTML")

# --- 2. XABAR TARQATISH (BROADCAST) MODULI ---
@router.message(F.text == "✉️ Xabar tarqatish")
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS: return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="cancel_broadcast")
    
    await message.answer(
        "📝 Tarqatmoqchi bo'lgan xabaringizni yuboring (Matn, rasm, video yoki forward).\n\n",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_broadcast)

@router.message(AdminStates.waiting_for_broadcast)
async def preview_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS: return
    
    await state.update_data(msg_id=message.message_id, from_chat=message.chat.id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tarqatishni boshlash", callback_data="start_sending")
    builder.button(text="❌ Bekor qilish", callback_data="cancel_broadcast")
    builder.adjust(1)
    
    await message.send_copy(chat_id=message.chat.id)
    await message.answer("Xabar barchaga yuborilsinmi?", reply_markup=builder.as_markup())
    await state.set_state(AdminStates.confirm_broadcast)

@router.callback_query(AdminStates.confirm_broadcast, F.data == "start_sending")
async def send_to_all(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    msg_id, from_chat = data.get('msg_id'), data.get('from_chat')
    
    await call.message.edit_text("🚀 Tarqatish boshlandi...")
    
    users = await get_all_users()
    success, fail = 0, 0
    
    for user in users:
        try:
            await call.bot.copy_message(chat_id=user.telegram_id, from_chat_id=from_chat, message_id=msg_id)
            success += 1
            await asyncio.sleep(0.05) 
        except Exception:
            fail += 1
            
    await call.message.edit_text(
        f"✅ <b>Tarqatish yakunlandi!</b>\n\n"
        f"🟢 Muvaffaqiyatli: <b>{success} ta</b>\n"
        f"🔴 Bloklaganlar: <b>{fail} ta</b>", parse_mode="HTML"
    )
    await state.clear()

# --- 3. MAJBURIY OBUNA MODULI ---
@router.message(F.text == "📢 Majburiy obuna")
async def manage_channels(message: types.Message):
    if message.from_user.id not in ADMINS: return
    
    channels = await get_all_channels()
    text = "<b>📢 Majburiy obuna kanallari tizimi:</b>\n\n"
    builder = InlineKeyboardBuilder()
    
    if channels:
        for i, ch in enumerate(channels, 1):
            text += f"{i}. <b>{ch.title}</b> (ID: <code>{ch.channel_id}</code>)\n"
            builder.button(text=f"❌ {ch.title} ni o'chirish", callback_data=f"del_channel_{ch.channel_id}")
    else:
        text += "<i>Hozircha kanallar yo'q.</i>\n\n"
        
    builder.button(text="➕ Yangi kanal qo'shish", callback_data="add_new_channel")
    builder.adjust(1)
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "add_new_channel")
async def add_channel_step1(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("📝 Yangi kanalning <b>ID raqamini</b> yuboring:", parse_mode="HTML")
    await state.set_state(ChannelStates.waiting_for_channel_id)

@router.message(ChannelStates.waiting_for_channel_id)
async def add_channel_step2(message: types.Message, state: FSMContext):
    await state.update_data(channel_id=int(message.text.strip()))
    await message.answer("Endi kanalning <b>Nomini</b> yuboring:", parse_mode="HTML")
    await state.set_state(ChannelStates.waiting_for_channel_title)

@router.message(ChannelStates.waiting_for_channel_title)
async def add_channel_step3(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Kanalga kirish <b>ssilkasini (URL)</b> yuboring:", parse_mode="HTML")
    await state.set_state(ChannelStates.waiting_for_channel_link)

@router.message(ChannelStates.waiting_for_channel_link)
async def add_channel_step4(message: types.Message, state: FSMContext):
    data = await state.get_data()
    success = await add_channel(data['channel_id'], data['title'], message.text)
    await message.answer("✅ Kanal qo'shildi!" if success else "⚠️ Avval qo'shilgan.")
    await state.clear()

@router.callback_query(F.data.startswith("del_channel_"))
async def del_channel_handler(call: types.CallbackQuery):
    ch_id = int(call.data.replace("del_channel_", ""))
    await delete_channel(ch_id)
    await call.answer("🗑 Kanal o'chirildi!", show_alert=True)
    await call.message.delete()

# --- 4. KINOLARNI BOSHQARISH MODULI ---
@router.message(F.text == "🎬 Kinolarni boshqarish")
async def manage_movies_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS: return
    await message.answer("🔎 Ma'lumot olmoqchi bo'lgan <b>kino kodini</b> yuboring:", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_movie_manage)

@router.message(AdminStates.waiting_for_movie_manage)
async def movie_info_handler(message: types.Message, state: FSMContext):
    kino_kodi = message.text.strip()
    async with async_session() as session:
        movie = await session.scalar(select(Movie).where(Movie.kino_kodi == kino_kodi))
        if movie:
            text = (
                f"🎬 <b>Kino ma'lumotlari:</b>\n"
                f"🆔 Kodi: <code>{movie.kino_kodi}</code>\n"
                f"📟 Message ID: <code>{movie.message_id}</code>\n"
                f"👍 Likes: <b>{movie.likes}</b> | 👎 Dislikes: <b>{movie.dislikes}</b>"
            )
            builder = InlineKeyboardBuilder()
            builder.button(text="🗑 Kinoni o'chirish", callback_data=f"delmovie_{movie.kino_kodi}")
            builder.button(text="❌ Yopish", callback_data="cancel_manage")
            builder.adjust(1)
            await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        else:
            await message.answer("😔 Kino topilmadi.")
    await state.clear()

@router.callback_query(F.data.startswith("delmovie_"))
async def delete_movie_callback(call: types.CallbackQuery):
    kino_kodi = call.data.split("_")[1]
    success = await delete_movie_by_code(kino_kodi)
    await call.answer("✅ O'chirildi!" if success else "❌ Xato!", show_alert=True)
    await call.message.delete()

# --- 5. BAZANI EXCELGA YUKLASH ---
@router.message(F.text == "💾 Bazani yuklash")
async def export_users_to_excel(message: types.Message):
    if message.from_user.id not in ADMINS: return
    wait_msg = await message.answer("📊 Excel tayyorlanmoqda...")
    
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        if not users:
            await wait_msg.edit_text("❌ Bazada userlar yo'q.")
            return

        data = [{"ID": u.id, "Telegram ID": u.telegram_id, "Ismi": u.full_name, "Vaqt": u.created_at.strftime("%Y-%m-%d %H:%M")} for u in users]
        df = pd.DataFrame(data)
        file_path = "users_database.xlsx"
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Foydalanuvchilar')
            ws = writer.sheets['Foydalanuvchilar']
            for i, col in enumerate(df.columns):
                ws.column_dimensions[chr(65 + i)].width = max(df[col].astype(str).map(len).max(), len(col)) + 2

        await message.answer_document(FSInputFile(file_path), caption=f"✅ Baza tayyor! Jami: {len(users)} ta")
        if os.path.exists(file_path): os.remove(file_path)
        await wait_msg.delete()

# --- CALLBACK BEKOR QILISHLAR ---
@router.callback_query(F.data == "cancel_broadcast")
async def cancel_b(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()

@router.callback_query(F.data == "cancel_manage")
async def cancel_manage_handler(call: types.CallbackQuery):
    await call.message.delete()