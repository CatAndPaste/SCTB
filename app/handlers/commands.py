# app/handlers/commands.py

from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import User, Order, UserParameters, Balance
from app.utils.locale import load_locale
from app.utils.db import get_session
from datetime import datetime, timedelta
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

router = Router()

class BuyStates(StatesGroup):
    waiting_for_amount = State()

class SellStates(StatesGroup):
    waiting_for_sell_amount = State()
    waiting_for_sell_price = State()

@router.message(Command('buy'))
async def cmd_buy(message: types.Message, state: FSMContext):
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.balance))
            .where(User.id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("User not found. Please use /start to register.")
            return
        locale = load_locale(user.language)
        balance = user.balance
        if not balance:
            # Initialize user's balance if it doesn't exist
            balance = Balance(user_id=user.id)
            session.add(balance)
            await session.commit()
        # Display instruction and current balance
        balance_text = f"Available USDT: {balance.usdt_available}\nCurrent Price: 50000 USDT/BTC"  # Using a fictitious price
        await message.answer(f"{locale.get('buy_instruction', 'Please enter the amount to buy in USDT.')}\n\n{balance_text}")
        await state.set_state(BuyStates.waiting_for_amount)

@router.message(BuyStates.waiting_for_amount)
async def process_buy_amount(message: types.Message, state: FSMContext):
    amount_text = message.text.strip()
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
        async with get_session() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.balance))
                .where(User.id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            balance = user.balance
            if balance.usdt_available < amount:
                await message.answer("Insufficient funds.")
                await state.clear()
                return
            # Emulate purchase
            current_price = 50000  # Fictitious BTC price
            bought_btc = amount / current_price
            # Create a buy order in the database
            new_order = Order(
                user_id=user.id,
                order_type='buy',
                amount=bought_btc,
                price=current_price,
                status='Completed',
                date_created=datetime.utcnow()
            )
            session.add(new_order)
            # Update user's balance
            balance.usdt_available -= amount
            balance.btc_available += bought_btc
            await session.commit()
        text = f"Purchase successful.\nBought: {bought_btc} BTC\nPrice: {amount} USDT\nDate and time: {datetime.utcnow()}"
        await message.answer(text)
        # Offer to create a sell order
        await message.answer(f"Do you want to create a sell order for {bought_btc} BTC?", reply_markup=create_sell_order_keyboard())
    except ValueError:
        await message.answer("Invalid amount. Please enter a valid number.")
    finally:
        await state.clear()

def create_sell_order_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="Create Sell Order", callback_data="create_sell_order")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(lambda c: c.data == 'create_sell_order')
async def process_create_sell_order(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Enter the amount to sell (in BTC):")
    await state.set_state(SellStates.waiting_for_sell_amount)
    await callback_query.answer()

@router.message(SellStates.waiting_for_sell_amount)
async def process_sell_amount(message: types.Message, state: FSMContext):
    amount_text = message.text.strip()
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
        async with get_session() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.balance))
                .where(User.id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            balance = user.balance
            if balance.btc_available < amount:
                await message.answer("Insufficient BTC balance.")
                await state.clear()
                return
            await state.update_data(sell_amount=amount)
            await message.answer("Enter the desired sell price per 1 BTC (in USDT):")
            await state.set_state(SellStates.waiting_for_sell_price)
    except ValueError:
        await message.answer("Invalid amount. Please enter a valid number.")

@router.message(SellStates.waiting_for_sell_price)
async def process_sell_price(message: types.Message, state: FSMContext):
    price_text = message.text.strip()
    try:
        price = float(price_text)
        if price <= 0:
            raise ValueError
        data = await state.get_data()
        amount = data.get('sell_amount')
        total = amount * price
        async with get_session() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.balance))
                .where(User.id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            # Create a sell order in the database
            new_order = Order(
                user_id=user.id,
                order_type='sell',
                amount=amount,
                price=price,
                status='Open',
                date_created=datetime.utcnow()
            )
            session.add(new_order)
            # Update user's balance
            balance = user.balance
            balance.btc_available -= amount
            balance.btc_frozen += amount
            await session.commit()
        text = f"Limit sell order successfully placed.\nSell: {amount} BTC\nSell price per 1 BTC: {price} USDT\nTotal: {total} USDT\nDate and time: {datetime.utcnow()}"
        await message.answer(text)
    except ValueError:
        await message.answer("Invalid price. Please enter a valid number.")
    finally:
        await state.clear()

@router.message(Command('orders'))
async def cmd_orders(message: types.Message):
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.orders))
            .where(User.id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("User not found. Please use /start to register.")
            return
        locale = load_locale(user.language)
        # Get the list of orders from the database
        orders = user.orders
        if not orders:
            await message.answer("You have no active orders.")
            return
        orders_text = "Order status:\n"
        for order in orders:
            order_text = f"Order №{order.id}\nType: {order.order_type}\nStatus: {order.status}\nAmount: {order.amount} BTC\nPrice: {order.price} USDT\nDate: {order.date_created}"
            orders_text += order_text + "\n\n"
        await message.answer(orders_text)
        # Add buttons to cancel orders
        await message.answer("Do you want to cancel any order?", reply_markup=cancel_order_keyboard(orders))

def cancel_order_keyboard(orders):
    buttons = []
    for order in orders:
        if order.status == 'Open':
            buttons.append([types.InlineKeyboardButton(text=f"Cancel Order №{order.id}", callback_data=f"cancel_order_{order.id}")])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(lambda c: c.data.startswith('cancel_order_'))
async def process_cancel_order(callback_query: types.CallbackQuery):
    order_id = int(callback_query.data.split('_')[2])
    async with get_session() as session:
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.user).selectinload(User.balance))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if order and order.status == 'Open':
            # Update user's balance
            balance = order.user.balance
            if order.order_type == 'sell':
                balance.btc_frozen -= order.amount
                balance.btc_available += order.amount
            elif order.order_type == 'buy':
                total_amount = order.amount * order.price
                balance.usdt_frozen -= total_amount
                balance.usdt_available += total_amount
            order.status = 'Cancelled'
            await session.commit()
            await callback_query.message.answer(f"Order №{order.id} has been cancelled.")
        else:
            await callback_query.message.answer("Order not found or already completed.")
    await callback_query.answer()

class ParamsStates(StatesGroup):
    waiting_for_param_choice = State()
    waiting_for_new_value = State()

@router.message(Command('autobuy'))
async def cmd_autobuy(message: types.Message):
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.parameters))
            .where(User.id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("User not found. Please use /start to register.")
            return
        # Get autotrading parameters
        if not user.parameters:
            params = UserParameters(user_id=user.id)
            session.add(params)
            await session.commit()
        else:
            params = user.parameters
        locale = load_locale(user.language)
        # Display autotrading status and current parameters
        autobuy_status = 'Running' if params.autobuy_on_growth or params.autobuy_on_fall else 'Stopped'
        message_text = f"Autotrading cycle is currently: {autobuy_status}\n\nCurrent parameters:\nPurchase amount: {params.purchase_amount} USDT\nProfit percentage: {params.profit_percentage}%\nPurchase delay: {params.purchase_delay} seconds\nGrowth percentage: {params.growth_percentage}%\nFall percentage: {params.fall_percentage}%"
        await message.answer(message_text, reply_markup=autobuy_keyboard(params))

def autobuy_keyboard(params):
    buttons = []
    if params.autobuy_on_growth or params.autobuy_on_fall:
        buttons.append([types.InlineKeyboardButton(text="Stop", callback_data="autobuy_stop")])
    else:
        buttons.append([types.InlineKeyboardButton(text="Start", callback_data="autobuy_start")])
    buttons.append([types.InlineKeyboardButton(text="Change parameters", callback_data="change_params")])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(lambda c: c.data == 'autobuy_start')
async def process_autobuy_start(callback_query: types.CallbackQuery):
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.parameters))
            .where(User.id == callback_query.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback_query.message.answer("User not found. Please use /start to register.")
            return
        params = user.parameters
        # Start autotrading
        params.autobuy_on_growth = True
        params.autobuy_on_fall = True
        await session.commit()
        await callback_query.message.answer("Autotrading cycle started.")
    await callback_query.answer()

@router.callback_query(lambda c: c.data == 'autobuy_stop')
async def process_autobuy_stop(callback_query: types.CallbackQuery):
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.parameters))
            .where(User.id == callback_query.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback_query.message.answer("User not found. Please use /start to register.")
            return
        params = user.parameters
        if params.autobuy_on_growth or params.autobuy_on_fall:
            params.autobuy_on_growth = False
            params.autobuy_on_fall = False
            await session.commit()
            await callback_query.message.answer("Autotrading cycle stopped.")
        else:
            await callback_query.message.answer("Autotrading cycle is not running.")
    await callback_query.answer()

@router.callback_query(lambda c: c.data == 'change_params')
async def process_change_params(callback_query: types.CallbackQuery, state: FSMContext):
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.parameters))
            .where(User.id == callback_query.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback_query.message.message.answer("User not found. Please use /start to register.")
            return
        # Get parameters
        if not user.parameters:
            params = UserParameters(user_id=user.id)
            session.add(params)
            await session.commit()
        else:
            params = user.parameters
        # Display current parameters
        params_text = f"Parameters:\n1. Purchase amount (USDT): {params.purchase_amount}\n2. Profit percentage: {params.profit_percentage}%\n3. Purchase delay: {params.purchase_delay} seconds\n4. Growth percentage: {params.growth_percentage}%\n5. Fall percentage: {params.fall_percentage}%\n6. Autobuy on growth: {'Enabled' if params.autobuy_on_growth else 'Disabled'}\n7. Autobuy on fall: {'Enabled' if params.autobuy_on_fall else 'Disabled'}\n\nEnter the number of the parameter you want to change, or type 'reset' to reset to default."
        await callback_query.message.answer(params_text)
        await state.set_state(ParamsStates.waiting_for_param_choice)
    await callback_query.answer()

@router.message(Command('params'))
async def cmd_params(message: types.Message, state: FSMContext):
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.parameters))
            .where(User.id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("User not found. Please use /start to register.")
            return
        # Get parameters
        if not user.parameters:
            params = UserParameters(user_id=user.id)
            session.add(params)
            await session.commit()
        else:
            params = user.parameters
        # Display current parameters
        params_text = f"Parameters:\n1. Purchase amount (USDT): {params.purchase_amount}\n2. Profit percentage: {params.profit_percentage}%\n3. Purchase delay: {params.purchase_delay} seconds\n4. Growth percentage: {params.growth_percentage}%\n5. Fall percentage: {params.fall_percentage}%\n6. Autobuy on growth: {'Enabled' if params.autobuy_on_growth else 'Disabled'}\n7. Autobuy on fall: {'Enabled' if params.autobuy_on_fall else 'Disabled'}\n\nEnter the number of the parameter you want to change, or type 'reset' to reset to default."
        await message.answer(params_text)
        await state.set_state(ParamsStates.waiting_for_param_choice)

@router.message(ParamsStates.waiting_for_param_choice)
async def process_param_choice(message: types.Message, state: FSMContext):
    choice = message.text.strip().lower()
    if choice == 'reset':
        async with get_session() as session:
            result = await session.execute(
                select(User)
                .options(selectinload(User.parameters))
                .where(User.id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            # Reset parameters
            if user.parameters:
                await session.delete(user.parameters)
                await session.commit()
            await message.answer("Parameters have been reset to default.")
        await state.clear()
    elif choice in ['1', '2', '3', '4', '5', '6', '7']:
        await state.update_data(param_choice=int(choice))
        await message.answer("Enter the new value:")
        await state.set_state(ParamsStates.waiting_for_new_value)
    else:
        await message.answer("Invalid choice. Please enter a number from 1 to 7, or 'reset'.")

@router.message(ParamsStates.waiting_for_new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    param_choice = data.get('param_choice')
    new_value = message.text.strip()
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.parameters))
            .where(User.id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user.parameters:
            params = UserParameters(user_id=user.id)
            session.add(params)
        else:
            params = user.parameters
        try:
            if param_choice in [1, 2, 3, 4, 5]:
                value = float(new_value)
                if value <= 0:
                    raise ValueError
            elif param_choice in [6, 7]:
                value = new_value.lower() in ['true', 'yes', '1', 'enable', 'on']
            if param_choice == 1:
                params.purchase_amount = value
            elif param_choice == 2:
                params.profit_percentage = value
            elif param_choice == 3:
                params.purchase_delay = int(value)
            elif param_choice == 4:
                params.growth_percentage = value
            elif param_choice == 5:
                params.fall_percentage = value
            elif param_choice == 6:
                params.autobuy_on_growth = value
            elif param_choice == 7:
                params.autobuy_on_fall = value
            await session.commit()
            await message.answer("Parameter updated successfully.")
        except ValueError:
            await message.answer("Invalid value. Please enter a valid number.")
    await state.clear()

@router.message(Command('stop'))
async def cmd_stop(message: types.Message):
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.parameters))
            .where(User.id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("User not found. Please use /start to register.")
            return
        params = user.parameters
        if params.autobuy_on_growth or params.autobuy_on_fall:
            params.autobuy_on_growth = False
            params.autobuy_on_fall = False
            await session.commit()
            await message.answer("Autotrading cycle stopped.")
        else:
            await message.answer("Autotrading cycle is not running.")

@router.message(Command('stats'))
async def cmd_stats(message: types.Message):
    await message.answer("Select the time period:", reply_markup=stats_period_keyboard())

def stats_period_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="Daily", callback_data="stats_daily")],
        [types.InlineKeyboardButton(text="Monthly", callback_data="stats_monthly")],
        [types.InlineKeyboardButton(text="Full", callback_data="stats_full")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(lambda c: c.data.startswith('stats_'))
async def process_stats_period(callback_query: types.CallbackQuery):
    period = callback_query.data.split('_')[1]
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .where(User.id == callback_query.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await callback_query.message.answer("User not found. Please use /start to register.")
            return
        now = datetime.utcnow()
        if period == 'daily':
            start_time = now - timedelta(days=1)
            period_text = "Daily"
        elif period == 'monthly':
            start_time = now - timedelta(days=30)
            period_text = "Monthly"
        else:
            start_time = datetime.min
            period_text = "Full"
        # Get the number of trades and profit
        trades_result = await session.execute(
            select(Order).where(Order.user_id == user.id, Order.date_created >= start_time)
        )
        trades = trades_result.scalars().all()
        num_trades = len(trades)
        total_profit = 0.0  # You can implement profit calculation based on your data
        stats_text = f"Time period: {period_text}\nNumber of trades: {num_trades}\nProfit: {total_profit} USDT"
        await callback_query.message.answer(stats_text)
    await callback_query.answer()

@router.message(Command('balance'))
async def cmd_balance(message: types.Message):
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.balance))
            .where(User.id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("User not found. Please use /start to register.")
            return
        balance = user.balance
        if not balance:
            # Initialize user's balance if it doesn't exist
            balance = Balance(user_id=user.id)
            session.add(balance)
            await session.commit()
        # Calculate total amounts
        orders_pending_execution = balance.usdt_frozen
        available_balance = balance.usdt_available
        total_balance = orders_pending_execution + available_balance

        balance_text = "Balance:\n\nCryptocurrencies:\n"
        balance_text += f"- Bitcoin: Available: {balance.btc_available} BTC, Frozen: {balance.btc_frozen} BTC\n"
        balance_text += f"- USDT: Available: {balance.usdt_available} USDT, Frozen: {balance.usdt_frozen} USDT\n\n"
        balance_text += "Sum of funds:\n"
        balance_text += f"- Orders pending execution: {orders_pending_execution} USDT\n"
        balance_text += f"- Available balance: {available_balance} USDT\n"
        balance_text += f"- Total amount: {total_balance} USDT"
        await message.answer(balance_text)

@router.message(Command('price'))
async def cmd_price(message: types.Message):
    # Emulate current price
    current_price = 50000  # Fictitious price for testing
    await message.answer(f"Current asset price:\n- BTC/USDT: {current_price} USDT")

class HelpStates(StatesGroup):
    viewing_help = State()

help_pages = {
    'en': [
        "Help Page 1: Overview\n\nThis bot allows you to trade BTC/USDT automatically, create orders, view balance, statistics, and more.",
        "Help Page 2: Commands\n\n/autobuy - Start or stop autotrading\n/buy - Purchase cryptocurrency\n/orders - View open orders\n/params - Set autotrading parameters\n/stop - Stop autotrading\n/stats - View statistics\n/balance - View balance\n/price - View current price\n/subscription - Manage your subscription\n/help - View help pages",
        "Help Page 3: FAQ\n\nQ: How do I start trading?\nA: First, purchase a subscription via /subscription, then set your parameters via /params, and start autotrading with /autobuy."
    ],
    'ru': [
        "Страница помощи 1: Обзор\n\nЭтот бот позволяет автоматически торговать парой BTC/USDT, создавать ордера, просматривать баланс, статистику и многое другое.",
        "Страница помощи 2: Команды\n\n/autobuy - Запустить или остановить автоторговлю\n/buy - Купить криптовалюту\n/orders - Просмотреть открытые ордера\n/params - Настроить параметры автоторговли\n/stop - Остановить автоторговлю\n/stats - Просмотреть статистику\n/balance - Просмотреть баланс\n/price - Просмотреть текущую цену\n/subscription - Управлять подпиской\n/help - Просмотреть страницы помощи",
        "Страница помощи 3: Часто задаваемые вопросы\n\nВ: Как начать торговлю?\nО: Сначала приобретите подписку через /subscription, затем настройте параметры через /params и запустите автоторговлю с помощью /autobuy."
    ]
}

@router.message(Command('help'))
async def cmd_help(message: types.Message, state: FSMContext):
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("User not found. Please use /start to register.")
            return
        language = user.language or 'en'
        page = 0
        await state.update_data(help_page=page)
        await message.answer(help_pages[language][page], reply_markup=help_keyboard(page, language))
        await state.set_state(HelpStates.viewing_help)

def help_keyboard(page, language):
    buttons = []
    if page > 0:
        buttons.append(types.InlineKeyboardButton(text="Previous", callback_data=f"help_prev_{page}"))
    if page < len(help_pages[language]) - 1:
        buttons.append(types.InlineKeyboardButton(text="Next", callback_data=f"help_next_{page}"))
    return types.InlineKeyboardMarkup(inline_keyboard=[buttons])

@router.callback_query(HelpStates.viewing_help, lambda c: c.data.startswith('help_'))
async def process_help_pagination(callback_query: types.CallbackQuery, state: FSMContext):
    _, direction, current_page = callback_query.data.split('_')
    current_page = int(current_page)
    if direction == 'next':
        new_page = current_page + 1
    elif direction == 'prev':
        new_page = current_page - 1
    else:
        new_page = current_page
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.id == callback_query.from_user.id)
        )
        user = result.scalar_one_or_none()
        language = user.language or 'en'
        await state.update_data(help_page=new_page)
        await callback_query.message.edit_text(help_pages[language][new_page], reply_markup=help_keyboard(new_page, language))
    await callback_query.answer()

def register_command_handlers(dp):
    dp.include_router(router)
