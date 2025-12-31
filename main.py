#import asyncio
import re
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession

# --- SOZLAMALAR ---
API_TOKEN = 'SIZNING_BOT_TOKENING'
CHANNEL_ID = -1003530569786
ADMIN_ID = 8512002202

# PythonAnywhere Free tier proxy (misol)
PROXY = "http://proxy.server:3128"

logging.basicConfig(level=logging.INFO)

# Botni proxy bilan yaratish
session = AiohttpSession(proxy=PROXY)
bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

posts_db = {}
user_data_saved = set()

VILOYATLAR = [
    "toshkent", "andijon", "farg'ona", "namangan", "sirdaryo", "jizzax",
    "samarqand", "buxoro", "navoiy", "qashqadaryo", "surxondaryo",
    "xorazm", "qoraqalpog'iston"
]

class OrderState(StatesGroup):
    waiting_for_check = State()
    waiting_for_address = State()

# --- Kanal postlarini avtomatik saqlash ---
@dp.channel_post()
async def auto_save_post(message: types.Message):
    text = message.text or message.caption
    if text and "#ID" in text.upper():
        try:
            tovar_id = re.search(r'#ID(\d+)', text.upper()).group(1)
            posts_db[tovar_id] = message.message_id
            print(f"✅ Tovar saqlandi: ID {tovar_id}")
        except Exception as e:
            print(f"❌ Xatolik: {e}")

# --- /start komandasi ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "Xush kelibsiz! Turkiya kiyimlari botiga xush kelibsiz.\n\n"
        "Tovar haqida ma'lumot olish uchun uning ID raqamini kiriting (Masalan: 1)"
    )

# --- Tovar ID bo‘yicha qidirish ---
@dp.message(F.text.isdigit())
async def search_tovar(message: types.Message):
    t_id = message.text
    if t_id in posts_db:
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="🛒 Sotib olish", callback_data=f"buy_{t_id}"))

        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=CHANNEL_ID,
            message_id=posts_db[t_id],
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer(
            f"Kechirasiz, {t_id} raqamli tovar topilmadi. Kanalga yangi post (#ID{t_id}) qo'shib ko'ring."
        )

# --- Sotib olish tugmasi ---
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Men to'lov qildim", callback_data="paid"))

    text = (
        "💳 **To'lov ma'lumotlari:**\n\n"
        "Karta raqami: `XXXXXXXXXXXX` (Xavfsiz tarzda yozildi)\n"
        "To'lov qilganingizdan so'ng 'Men to'lov qildim' tugmasini bosing."
    )
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb.as_markup())
    await callback.answer()

# --- To'lov qilindi tugmasi ---
@dp.callback_query(F.data == "paid")
async def ask_check(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Iltimos, to'lov cheki rasmini yoki faylini yuboring.")
    await state.set_state(OrderState.waiting_for_check)
    await callback.answer()

# --- Chek / fayl qabul qilish ---
@dp.message(OrderState.waiting_for_check, F.photo | F.document)
async def get_check(message: types.Message, state: FSMContext):
    await message.answer(
        "Siz ro'yxatga olindingiz! ✅\n\n"
        "Endi yashash manzilingizni (Viloyat nomi bilan) va telefon raqamingizni yuboring."
    )
    await state.set_state(OrderState.waiting_for_address)

# --- Manzil va telefon qabul qilish ---
@dp.message(OrderState.waiting_for_address)
async def get_address(message: types.Message, state: FSMContext):
    msg_text = message.text.lower()
    # Oddiy matn ko'rinishida xavfsiz qabul
    has_phone = re.search(r"\+?998\d{9}", msg_text)
    has_region = any(v in msg_text for v in VILOYATLAR)

    if message.from_user.id in user_data_saved:
        await message.answer("Iltimos kuting, biz siz bilan bog'lanamiz.")
        return

    if has_phone or has_region:
        user_data_saved.add(message.from_user.id)
        await message.answer(
            "Sizning ma'lumotlaringiz saqlandi. Biz siz bilan tez orada bog'lanamiz!"
        )
        # Adminga yuborish
        await bot.send_message(
            ADMIN_ID,
            f"🔔 Yangi buyurtma!\n"
            f"Kimdan: @{message.from_user.username}\n"
            f"ID: {message.from_user.id}\n"
            f"Ma'lumotlar: {message.text}"
        )
        await state.clear()
    else:
        await message.answer(
            "Iltimos, viloyat nomini yoki telefon raqamingizni (+998...) kiriting."
        )

# --- Noma'lum buyruqlar ---
@dp.message()
async def echo_handler(message: types.Message):
    await message.answer(
        "Tushunarsiz buyruq. Tovar ID raqamini faqat raqam ko'rinishida kiriting."
    )

# --- Main ---
async def main():
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
