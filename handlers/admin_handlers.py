"""
Admin handlers for bot administration
Handles order management, product management, statistics, and broadcasts
"""

from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

import os
import sys
import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_manager import DataManager
from utils.keyboards import (
    get_admin_menu_keyboard,
    get_main_menu_keyboard,
    get_admin_orders_keyboard,
    get_admin_order_status_keyboard,
    get_admin_product_list_keyboard,
    get_admin_product_actions_keyboard,
    get_status_emoji,
    get_status_text
)

# Conversation states
ADMIN_WAITING_PRICE = 10
ADMIN_WAITING_DESC = 11
ADMIN_WAITING_BROADCAST = 12
ADMIN_ADDING_PRODUCT = 13

# Initialize data manager
data_manager = DataManager()


def load_config():
    """Load bot configuration"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    config = load_config()
    admin_ids = config.get('bot', {}).get('admin_ids', [])
    return user_id in admin_ids


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет доступа к панели администратора.")
        return
    
    await update.message.reply_text(
        "👨‍💼 *Панель администратора*\n\nВыберите действие:",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode='Markdown'
    )


async def admin_orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle active orders button"""
    if not is_admin(update.effective_user.id):
        return
    
    orders = data_manager.get_pending_orders()
    
    if not orders:
        await update.message.reply_text(
            "📋 *Активные заказы*\n\nНет активных заказов.",
            parse_mode='Markdown'
        )
        return
    
    text = f"📋 *Активные заказы ({len(orders)})*\n\nВыберите заказ:"
    
    await update.message.reply_text(
        text,
        reply_markup=get_admin_orders_keyboard(orders),
        parse_mode='Markdown'
    )


async def admin_order_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin order detail view"""
    query = update.callback_query
    
    if not is_admin(update.effective_user.id):
        await query.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await query.answer()
    
    order_id = int(query.data.split('_')[-1])
    order = data_manager.get_order(order_id)
    
    if not order:
        await query.edit_message_text("❌ Заказ не найден")
        return
    
    status_emoji = get_status_emoji(order['status'])
    status_text = get_status_text(order['status'])
    
    items_text = "\n".join([
        f"  • {item['product_name']} x{item['quantity']} = {item['price'] * item['quantity']}₽"
        for item in order['items']
    ])
    
    payment_methods = {
        'cash': 'Наличные',
        'card_on_delivery': 'Карта курьеру',
        'online': 'Онлайн'
    }
    
    text = (
        f"📦 *Заказ #{order['id']}*\n\n"
        f"{status_emoji} Статус: *{status_text}*\n\n"
        f"📋 *Товары:*\n{items_text}\n\n"
        f"💵 Сумма товаров: {order.get('subtotal', order['total'])}₽\n"
        f"🚗 Доставка: {order.get('delivery_cost', 0)}₽\n"
        f"🎟 Скидка: {order.get('discount', 0)}₽\n"
        f"💰 *Итого: {order['total']}₽*\n\n"
        f"📍 Адрес: {order['delivery_address']}\n"
        f"📱 Телефон: {order['phone']}\n"
        f"💳 Оплата: {payment_methods.get(order['payment_method'], order['payment_method'])}\n"
        f"📅 Создан: {order['created_at']}"
    )
    
    if order.get('comment'):
        text += f"\n💬 Комментарий: {order['comment']}"
    
    await query.edit_message_text(
        text,
        reply_markup=get_admin_order_status_keyboard(order_id, order['status']),
        parse_mode='Markdown'
    )


async def set_order_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order status change"""
    query = update.callback_query
    
    if not is_admin(update.effective_user.id):
        await query.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    # Parse: set_status_{order_id}_{status}
    parts = query.data.split('_')
    order_id = int(parts[2])
    new_status = parts[3]
    
    order = data_manager.get_order(order_id)
    if not order:
        await query.answer("❌ Заказ не найден", show_alert=True)
        return
    
    old_status = order['status']
    data_manager.update_order_status(order_id, new_status)
    
    status_text = get_status_text(new_status)
    await query.answer(f"✅ Статус изменён на: {status_text}")
    
    # Notify customer
    await notify_customer_status_change(context, order['user_id'], order_id, new_status)
    
    # Return to orders list
    orders = data_manager.get_pending_orders()
    if orders:
        await query.edit_message_text(
            f"📋 *Активные заказы ({len(orders)})*\n\nВыберите заказ:",
            reply_markup=get_admin_orders_keyboard(orders),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "📋 *Активные заказы*\n\nНет активных заказов.",
            parse_mode='Markdown'
        )


async def notify_customer_status_change(context: ContextTypes.DEFAULT_TYPE, 
                                        user_id: int, order_id: int, status: str):
    """Notify customer about order status change"""
    status_emoji = get_status_emoji(status)
    status_text = get_status_text(status)
    
    messages = {
        'accepted': 'Ваш заказ принят и скоро начнёт готовиться! 👨‍🍳',
        'preparing': 'Ваш заказ готовится. Уже скоро! 🍣',
        'on_the_way': 'Курьер уже в пути! Ждите доставку! 🚗',
        'delivered': 'Заказ доставлен! Приятного аппетита! 🎉',
        'cancelled': 'К сожалению, ваш заказ был отменён. Свяжитесь с нами для уточнения.'
    }
    
    text = (
        f"{status_emoji} *Обновление заказа #{order_id}*\n\n"
        f"Статус: *{status_text}*\n\n"
        f"{messages.get(status, '')}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode='Markdown'
        )
    except Exception:
        pass  # User might have blocked the bot


async def admin_back_to_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to orders button in admin"""
    query = update.callback_query
    await query.answer()
    
    orders = data_manager.get_pending_orders()
    
    if orders:
        await query.edit_message_text(
            f"📋 *Активные заказы ({len(orders)})*\n\nВыберите заказ:",
            reply_markup=get_admin_orders_keyboard(orders),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "📋 *Активные заказы*\n\nНет активных заказов.",
            parse_mode='Markdown'
        )


async def admin_statistics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle statistics button"""
    if not is_admin(update.effective_user.id):
        return
    
    stats = data_manager.get_statistics()
    all_orders = data_manager.get_all_orders()
    users = data_manager.get_all_users()
    
    # Count orders by status
    status_counts = {}
    for order in all_orders:
        status = order['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Today's orders
    from datetime import datetime, timedelta
    today = datetime.now().strftime('%Y-%m-%d')
    today_orders = [o for o in all_orders if o['created_at'].startswith(today)]
    today_revenue = sum(o['total'] for o in today_orders)
    
    text = (
        "📊 *Статистика*\n\n"
        f"📦 *Всего заказов:* {stats.get('total_orders', 0)}\n"
        f"💰 *Общая выручка:* {stats.get('total_revenue', 0):.0f}₽\n"
        f"📈 *Средний чек:* {stats.get('average_order', 0):.0f}₽\n"
        f"👥 *Пользователей:* {len(users)}\n\n"
        
        f"📅 *Сегодня:*\n"
        f"  • Заказов: {len(today_orders)}\n"
        f"  • Выручка: {today_revenue:.0f}₽\n\n"
        
        f"📋 *По статусам:*\n"
    )
    
    for status, count in status_counts.items():
        emoji = get_status_emoji(status)
        status_name = get_status_text(status)
        text += f"  {emoji} {status_name}: {count}\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def admin_products_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product management button"""
    if not is_admin(update.effective_user.id):
        return
    
    products = data_manager.get_all_products()
    
    text = f"🍣 *Управление меню*\n\nТоваров: {len(products)}\nВыберите товар для редактирования:"
    
    await update.message.reply_text(
        text,
        reply_markup=get_admin_product_list_keyboard(products),
        parse_mode='Markdown'
    )


async def admin_products_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product list callback (from back button)"""
    query = update.callback_query
    
    if not is_admin(update.effective_user.id):
        await query.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await query.answer()
    
    products = data_manager.get_all_products()
    
    await query.edit_message_text(
        f"🍣 *Управление меню*\n\nТоваров: {len(products)}\nВыберите товар:",
        reply_markup=get_admin_product_list_keyboard(products),
        parse_mode='Markdown'
    )


async def admin_product_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product detail view in admin"""
    query = update.callback_query
    
    if not is_admin(update.effective_user.id):
        await query.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await query.answer()
    
    product_id = int(query.data.split('_')[-1])
    product = data_manager.get_product(product_id)
    
    if not product:
        await query.edit_message_text("❌ Товар не найден")
        return
    
    context.user_data['admin_product_id'] = product_id
    
    available = "✅ Доступен" if product.get('available', True) else "❌ Скрыт"
    
    text = (
        f"🍣 *{product['name']}*\n\n"
        f"📝 {product.get('description', 'Нет описания')}\n"
        f"⚖️ Вес: {product.get('weight', 'не указан')}\n"
        f"💰 Цена: *{product['price']}₽*\n"
        f"📊 Статус: {available}"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=get_admin_product_actions_keyboard(product_id, product.get('available', True)),
        parse_mode='Markdown'
    )


async def admin_edit_price_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle edit price button"""
    query = update.callback_query
    
    if not is_admin(update.effective_user.id):
        await query.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await query.answer()
    
    product_id = int(query.data.split('_')[-1])
    context.user_data['admin_product_id'] = product_id
    
    product = data_manager.get_product(product_id)
    
    await query.edit_message_text(
        f"✏️ *Изменение цены*\n\n"
        f"Товар: {product['name']}\n"
        f"Текущая цена: {product['price']}₽\n\n"
        f"Введите новую цену (только число):",
        parse_mode='Markdown'
    )
    return ADMIN_WAITING_PRICE


async def receive_admin_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new price input"""
    try:
        new_price = int(update.message.text.strip())
        if new_price <= 0:
            raise ValueError("Price must be positive")
    except ValueError:
        await update.message.reply_text("❌ Введите корректную цену (целое положительное число)")
        return ADMIN_WAITING_PRICE
    
    product_id = context.user_data.get('admin_product_id')
    if product_id:
        data_manager.update_product(product_id, {'price': new_price})
        await update.message.reply_text(
            f"✅ Цена обновлена: {new_price}₽",
            reply_markup=get_admin_menu_keyboard()
        )
    
    return ConversationHandler.END


async def admin_edit_desc_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle edit description button"""
    query = update.callback_query
    
    if not is_admin(update.effective_user.id):
        await query.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await query.answer()
    
    product_id = int(query.data.split('_')[-1])
    context.user_data['admin_product_id'] = product_id
    
    product = data_manager.get_product(product_id)
    
    await query.edit_message_text(
        f"📝 *Изменение описания*\n\n"
        f"Товар: {product['name']}\n"
        f"Текущее описание: {product.get('description', 'Нет')}\n\n"
        f"Введите новое описание:",
        parse_mode='Markdown'
    )
    return ADMIN_WAITING_DESC


async def receive_admin_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new description input"""
    new_desc = update.message.text.strip()
    
    product_id = context.user_data.get('admin_product_id')
    if product_id:
        data_manager.update_product(product_id, {'description': new_desc})
        await update.message.reply_text(
            "✅ Описание обновлено!",
            reply_markup=get_admin_menu_keyboard()
        )
    
    return ConversationHandler.END


async def admin_toggle_product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle show/hide product button"""
    query = update.callback_query
    
    if not is_admin(update.effective_user.id):
        await query.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    data = query.data
    product_id = int(data.split('_')[-1])
    
    if 'hide' in data:
        data_manager.update_product(product_id, {'available': False})
        await query.answer("🚫 Товар скрыт")
    else:
        data_manager.update_product(product_id, {'available': True})
        await query.answer("✅ Товар показан")
    
    # Refresh product list
    products = data_manager.get_all_products()
    await query.edit_message_text(
        f"🍣 *Управление меню*\n\nТоваров: {len(products)}\nВыберите товар:",
        reply_markup=get_admin_product_list_keyboard(products),
        parse_mode='Markdown'
    )


async def admin_promocodes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle promocodes button"""
    if not is_admin(update.effective_user.id):
        return
    
    promocodes = data_manager.get_all_promocodes()
    
    if not promocodes:
        text = "🎟 *Промокоды*\n\nНет активных промокодов."
    else:
        text = "🎟 *Промокоды*\n\n"
        for promo in promocodes:
            status = "✅" if promo['active'] else "❌"
            if promo.get('discount_percent'):
                discount = f"{promo['discount_percent']}%"
            else:
                discount = f"{promo.get('discount_fixed', 0)}₽"
            
            uses = f"{promo.get('current_uses', 0)}"
            if promo.get('max_uses'):
                uses += f"/{promo['max_uses']}"
            
            text += (
                f"{status} *{promo['code']}*\n"
                f"   Скидка: {discount} | Мин. заказ: {promo.get('min_order', 0)}₽\n"
                f"   Использований: {uses} | До: {promo['expiry_date']}\n\n"
            )
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def admin_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle users button"""
    if not is_admin(update.effective_user.id):
        return
    
    users = data_manager.get_all_users()
    
    # Sort by total orders
    users = sorted(users, key=lambda x: x.get('total_orders', 0), reverse=True)
    
    text = f"👥 *Пользователи ({len(users)})*\n\n"
    
    for user in users[:20]:  # Show top 20
        username = user.get('username', 'нет')
        first_name = user.get('first_name', 'Пользователь')
        orders = user.get('total_orders', 0)
        bonus = user.get('bonus_points', 0)
        
        text += f"• *{first_name}* (@{username})\n"
        text += f"  Заказов: {orders} | Бонусы: {bonus}\n"
    
    if len(users) > 20:
        text += f"\n_...и ещё {len(users) - 20} пользователей_"
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def admin_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast button"""
    if not is_admin(update.effective_user.id):
        return
    
    users = data_manager.get_all_users()
    
    await update.message.reply_text(
        f"📢 *Рассылка сообщений*\n\n"
        f"Получателей: {len(users)}\n\n"
        f"Введите текст сообщения для рассылки\n"
        f"(или /cancel для отмены):",
        parse_mode='Markdown'
    )
    return ADMIN_WAITING_BROADCAST


async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message input and send"""
    message_text = update.message.text
    
    if message_text.lower() == '/cancel':
        await update.message.reply_text(
            "❌ Рассылка отменена",
            reply_markup=get_admin_menu_keyboard()
        )
        return ConversationHandler.END
    
    users = data_manager.get_all_users()
    sent = 0
    failed = 0
    
    await update.message.reply_text(f"📤 Начинаю рассылку {len(users)} пользователям...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['telegram_id'],
                text=f"📢 *Рассылка*\n\n{message_text}",
                parse_mode='Markdown'
            )
            sent += 1
        except Exception:
            failed += 1
    
    await update.message.reply_text(
        f"✅ *Рассылка завершена*\n\n"
        f"Отправлено: {sent}\n"
        f"Ошибок: {failed}",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


async def admin_exit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle exit from admin panel"""
    await update.message.reply_text(
        "👋 Вы вышли из панели администратора.",
        reply_markup=get_main_menu_keyboard()
    )


async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button in admin"""
    query = update.callback_query
    await query.answer()
    await query.delete_message()


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages in admin menu"""
    if not is_admin(update.effective_user.id):
        return
    
    text = update.message.text
    
    if text == "📋 Активные заказы":
        await admin_orders_handler(update, context)
    elif text == "📊 Статистика":
        await admin_statistics_handler(update, context)
    elif text == "🍣 Управление меню":
        await admin_products_handler(update, context)
    elif text == "🎟 Промокоды":
        await admin_promocodes_handler(update, context)
    elif text == "👥 Пользователи":
        await admin_users_handler(update, context)
    elif text == "📢 Рассылка":
        return await admin_broadcast_handler(update, context)
    elif text == "⬅️ Выход из админки":
        await admin_exit_handler(update, context)


def get_admin_handlers() -> list:
    """Get list of all admin handlers"""
    
    # Conversation handlers for admin inputs
    price_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_edit_price_callback, pattern="^admin_edit_price_")
        ],
        states={
            ADMIN_WAITING_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_price)
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True
    )
    
    desc_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_edit_desc_callback, pattern="^admin_edit_desc_")
        ],
        states={
            ADMIN_WAITING_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_desc)
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True
    )
    
    broadcast_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📢 Рассылка$") & filters.ChatType.PRIVATE, admin_broadcast_handler)
        ],
        states={
            ADMIN_WAITING_BROADCAST: [
                MessageHandler(filters.TEXT, receive_broadcast_message)
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True
    )
    
    return [
        CommandHandler("admin", admin_command),
        
        price_conv,
        desc_conv,
        broadcast_conv,
        
        CallbackQueryHandler(admin_order_detail_callback, pattern="^admin_order_"),
        CallbackQueryHandler(set_order_status_callback, pattern="^set_status_"),
        CallbackQueryHandler(admin_back_to_orders_callback, pattern="^admin_back_to_orders$"),
        
        CallbackQueryHandler(admin_product_detail_callback, pattern="^admin_product_"),
        CallbackQueryHandler(admin_toggle_product_callback, pattern="^admin_(hide|show)_"),
        CallbackQueryHandler(admin_products_callback, pattern="^admin_products$"),
        CallbackQueryHandler(admin_back_callback, pattern="^admin_back$"),
        
        # Text handlers for admin menu buttons (lower priority)
        MessageHandler(
            filters.Regex("^(📋 Активные заказы|📊 Статистика|🍣 Управление меню|🎟 Промокоды|👥 Пользователи|⬅️ Выход из админки)$") 
            & filters.ChatType.PRIVATE,
            admin_text_handler
        )
    ]
