"""
Admin paneli handlerlari.

Tuzatilgan muammolar:
  - Har handlerda if-check o'rniga IsAdmin filtri ishlatiladi
  - add_channel_step2: int() xato bersa catch qilinadi
  - Excel eksport: tempfile bilan xavfsiz fayl nomi
  - broadcast: asyncio.sleep o'rniga proper delay
  - cancel_broadcast FSM holati waiting_for_broadcast da ham ishlaydi
  - Barcha xatolar loglanadi
"""
from __future__ import annotations

import asyncio
import os
import tempfile

import pandas as pd
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from sqlalchemy import select

from config.config import ADMINS, BROADCAST_DELAY
from database.models import async_session, User
from database.requests import (
    get_statistics,
    get_all_users,
    get_all_channels,
    add_channel,
    delete_channel,
    delete_movie_by_code,
    get_new_users_count,
    get_top_missed_searches,
)
from filters.is_admin import IsAdmin
from utils.logger import get_logger

logger = get_logger(__name__)
router = Router()

# ── Admin filtrini routerga ulash (bir marta) ─────────────────────────────────
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ── FSM holatlari ─────────────────────────────────────────────────────────────
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    confirm_broadcast = State()
    waiting_for_movie_manage = State()


class ChannelStates(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_title = State()
    waiting_for_channel_link = State()


# ── Klaviatura ────────────────────────────────────────────────────────────────
def get_admin_keyboard() -> types.ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📊 Statistika")
    builder.button(text="✉️ Xabar tarqatish")
    builder.button(text="📢 Majburiy obuna")
    builder.button(text="🎬 Kinolarni boshqarish")
    builder.button(text="💾 Bazani yuklash")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


# ── 1. STATISTIKA ─────────────────────────────────────────────────────────────
@router.message(F.text == "📊 Statistika")
async def show_statistics(message: types.Message, state: FSMContext) -> None:
    await state.clear()  # eski FSM oqimi (masalan, broadcast) bekor qilinadi
    wait_msg = await message.answer("⏳ Bazadan ma'lumotlar yig'ilmoqda...")
    total_users, total_movies, top_movies = await get_statistics()
    new_today = await get_new_users_count(days=1)
    new_week = await get_new_users_count(days=7)
    missed = await get_top_missed_searches(limit=5)

    lines = [
        "<b>📊 Loyiha Statistikasi</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b> ta",
        f"🎞 Jami kinolar: <b>{total_movies}</b> ta",
        f"🆕 Bugun qo'shilgan: <b>{new_today}</b> ta | Haftada: <b>{new_week}</b> ta",
        "━━━━━━━━━━━━━━━━━━",
        "🏆 <b>TOP-3 Kinolar:</b>",
    ]
    if top_movies:
        for i, movie in enumerate(top_movies, 1):
            lines.append(
                f"  {i}. Kodi: <code>{movie.kino_kodi}</code> | 👍 {movie.likes} ta"
            )
    else:
        lines.append("  <i>Hozircha baholangan kinolar yo'q.</i>")

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("🔍 <b>Eng ko'p so'ralgan, lekin topilmagan kodlar:</b>")
    if missed:
        for i, m in enumerate(missed, 1):
            lines.append(f"  {i}. Kodi: <code>{m.kino_kodi}</code> | {m.count} marta so'ralgan")
    else:
        lines.append("  <i>Hozircha bunday so'rovlar yo'q.</i>")

    await wait_msg.edit_text("\n".join(lines), parse_mode="HTML")


# ── 2. XABAR TARQATISH ────────────────────────────────────────────────────────
@router.message(F.text == "✉️ Xabar tarqatish")
async def start_broadcast(message: types.Message, state: FSMContext) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="cancel_broadcast")

    await message.answer(
        "📝 Tarqatmoqchi bo'lgan xabaringizni yuboring (matn, rasm, video yoki forward).",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(AdminStates.waiting_for_broadcast)


@router.message(AdminStates.waiting_for_broadcast)
async def preview_broadcast(message: types.Message, state: FSMContext) -> None:
    await state.update_data(msg_id=message.message_id, from_chat=message.chat.id)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tarqatishni boshlash", callback_data="start_sending")
    builder.button(text="❌ Bekor qilish", callback_data="cancel_broadcast")
    builder.adjust(1)

    await message.send_copy(chat_id=message.chat.id)
    await message.answer(
        "Xabar barchaga yuborilsinmi?", reply_markup=builder.as_markup()
    )
    await state.set_state(AdminStates.confirm_broadcast)


@router.callback_query(AdminStates.confirm_broadcast, F.data == "start_sending")
async def send_to_all(call: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    msg_id: int = data["msg_id"]
    from_chat: int = data["from_chat"]

    await call.message.edit_text("🚀 Tarqatish boshlandi...")
    users = await get_all_users()
    success = fail = 0

    for user in users:
        try:
            await call.bot.copy_message(
                chat_id=user.telegram_id,
                from_chat_id=from_chat,
                message_id=msg_id,
            )
            success += 1
        except Exception as exc:
            logger.debug(
                "Broadcast yuborilmadi: user_id=%s, xato=%s", user.telegram_id, exc
            )
            fail += 1
        await asyncio.sleep(BROADCAST_DELAY)

    await call.message.edit_text(
        f"✅ <b>Tarqatish yakunlandi!</b>\n\n"
        f"🟢 Muvaffaqiyatli: <b>{success}</b> ta\n"
        f"🔴 Bloklaganlar / xato: <b>{fail}</b> ta",
        parse_mode="HTML",
    )
    await state.clear()
    logger.info("Broadcast yakunlandi: muvaffaqiyatli=%s, xato=%s", success, fail)


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(call: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.delete()
    await call.answer("Bekor qilindi.")


# ── 3. MAJBURIY OBUNA ─────────────────────────────────────────────────────────
@router.message(F.text == "📢 Majburiy obuna")
async def manage_channels(message: types.Message, state: FSMContext) -> None:
    await state.clear()  # eski FSM oqimi (masalan, broadcast) bekor qilinadi
    channels = await get_all_channels()
    text = "<b>📢 Majburiy obuna kanallari:</b>\n\n"
    builder = InlineKeyboardBuilder()

    if channels:
        for i, ch in enumerate(channels, 1):
            text += f"{i}. <b>{ch.title}</b> (ID: <code>{ch.channel_id}</code>)\n"
            builder.button(
                text=f"❌ {ch.title} ni o'chirish",
                callback_data=f"del_channel_{ch.channel_id}",
            )
    else:
        text += "<i>Hozircha kanallar yo'q.</i>\n\n"

    builder.button(text="➕ Yangi kanal qo'shish", callback_data="add_new_channel")
    builder.adjust(1)
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "add_new_channel")
async def add_channel_step1(call: types.CallbackQuery, state: FSMContext) -> None:
    await call.message.edit_text(
        "📝 Kanalning <b>ID raqamini</b> yuboring (masalan: -1001234567890):",
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.waiting_for_channel_id)


@router.message(ChannelStates.waiting_for_channel_id)
async def add_channel_step2(message: types.Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        channel_id = int(raw)
    except ValueError:
        await message.answer(
            "⚠️ Noto'g'ri format. Iltimos, faqat <b>raqam</b> yuboring "
            "(masalan: <code>-1001234567890</code>).",
            parse_mode="HTML",
        )
        return

    await state.update_data(channel_id=channel_id)
    await message.answer("Endi kanalning <b>nomini</b> yuboring:", parse_mode="HTML")
    await state.set_state(ChannelStates.waiting_for_channel_title)


@router.message(ChannelStates.waiting_for_channel_title)
async def add_channel_step3(message: types.Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await message.answer(
        "Kanalga kirish <b>havolasini (URL)</b> yuboring "
        "(masalan: <code>https://t.me/kanalnom</code>):",
        parse_mode="HTML",
    )
    await state.set_state(ChannelStates.waiting_for_channel_link)


@router.message(ChannelStates.waiting_for_channel_link)
async def add_channel_step4(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    link = (message.text or "").strip()

    if not link.startswith("https://"):
        await message.answer("⚠️ Havola https:// bilan boshlanishi kerak.")
        return

    success = await add_channel(data["channel_id"], data["title"], link)
    if success:
        await message.answer(
            f"✅ <b>{data['title']}</b> kanali qo'shildi!", parse_mode="HTML"
        )
    else:
        await message.answer("⚠️ Bu kanal avval qo'shilgan.")
    await state.clear()


@router.callback_query(F.data.startswith("del_channel_"))
async def del_channel_handler(call: types.CallbackQuery) -> None:
    raw = call.data.removeprefix("del_channel_")
    try:
        ch_id = int(raw)
    except ValueError:
        await call.answer("⚠️ Noto'g'ri format!", show_alert=True)
        return

    success = await delete_channel(ch_id)
    if success:
        await call.answer("🗑 Kanal o'chirildi!", show_alert=True)
        await call.message.delete()
    else:
        await call.answer("⚠️ Kanal topilmadi.", show_alert=True)


# ── 4. KINOLARNI BOSHQARISH ───────────────────────────────────────────────────
@router.message(F.text == "🎬 Kinolarni boshqarish")
async def manage_movies_start(message: types.Message, state: FSMContext) -> None:
    await message.answer(
        "🔎 Ma'lumot olmoqchi bo'lgan <b>kino kodini</b> yuboring:",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_movie_manage)


@router.message(AdminStates.waiting_for_movie_manage)
async def movie_info_handler(message: types.Message, state: FSMContext) -> None:
    kino_kodi = (message.text or "").strip()
    await state.clear()

    async with async_session() as session:
        from database.models import Movie
        movie = await session.scalar(
            select(Movie).where(Movie.kino_kodi == kino_kodi)
        )

    if not movie:
        await message.answer("😔 Bunday kodli kino topilmadi.")
        return

    text = (
        f"🎬 <b>Kino ma'lumotlari:</b>\n"
        f"🆔 Kodi: <code>{movie.kino_kodi}</code>\n"
        f"📟 Message ID: <code>{movie.message_id}</code>\n"
        f"👍 Likes: <b>{movie.likes}</b> | 👎 Dislikes: <b>{movie.dislikes}</b>"
    )
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🗑 Kinoni o'chirish", callback_data=f"delmovie_{movie.kino_kodi}"
    )
    builder.button(text="❌ Yopish", callback_data="cancel_manage")
    builder.adjust(1)
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("delmovie_"))
async def delete_movie_callback(call: types.CallbackQuery) -> None:
    kino_kodi = call.data.removeprefix("delmovie_")
    success = await delete_movie_by_code(kino_kodi)
    await call.answer(
        "✅ Kino o'chirildi!" if success else "❌ Kino topilmadi.", show_alert=True
    )
    await call.message.delete()


@router.callback_query(F.data == "cancel_manage")
async def cancel_manage_handler(call: types.CallbackQuery) -> None:
    await call.message.delete()


# ── 5. EXCEL EKSPORT ─────────────────────────────────────────────────────────
@router.message(F.text == "💾 Bazani yuklash")
async def export_users_to_excel(message: types.Message, state: FSMContext) -> None:
    await state.clear()  # eski FSM oqimi (masalan, broadcast) bekor qilinadi
    wait_msg = await message.answer("📊 Excel fayl tayyorlanmoqda...")

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        await wait_msg.edit_text("❌ Bazada foydalanuvchilar yo'q.")
        return

    data = [
        {
            "ID": u.id,
            "Telegram ID": u.telegram_id,
            "Ismi": u.full_name,
            "Username": f"@{u.username}" if u.username else "—",
            "Ro'yxatdan vaqti": (
                u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "—"
            ),
        }
        for u in users
    ]

    df = pd.DataFrame(data)

    # Tempfile — parallel so'rovlarda fayl nomi to'qnashmaydi
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        file_path = tmp.name

    try:
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Foydalanuvchilar")
            ws = writer.sheets["Foydalanuvchilar"]
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 3
                ws.column_dimensions[chr(65 + i)].width = min(max_len, 50)

        await message.answer_document(
            FSInputFile(file_path, filename="users_database.xlsx"),
            caption=f"✅ Baza tayyor! Jami: <b>{len(users)}</b> ta foydalanuvchi.",
            parse_mode="HTML",
        )
        await wait_msg.delete()
        logger.info("Excel eksport muvaffaqiyatli: %s ta user", len(users))
    except Exception as exc:
        logger.error("Excel eksportda xato: %s", exc)
        await wait_msg.edit_text("❌ Excel tayyorlashda xatolik yuz berdi.")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
