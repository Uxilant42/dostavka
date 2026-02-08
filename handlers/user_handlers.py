"""
User handlers for customer interactions
Handles menu browsing, cart, checkout, and order history
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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_manager import DataManager
from utils.keyboards import (
    get_main_menu_keyboard,
    get_categories_keyboard,
    get_products_keyboard,
    get_product_quantity_keyboard,
    get_cart_keyboard,
    get_empty_cart_keyboard,
    get_checkout_keyboard,
    get_payment_method_keyboard,
    get_saved_addresses_keyboard,
    get_phone_request_keyboard,
    get_order_list_keyboard,
    get_order_detail_keyboard,
    get_status_emoji,
    get_status_text
)

# Conversation states
WAITING_ADDRESS = 1
WAITING_PHONE = 2
WAITING_PROMOCODE = 3

# Initialize data manager
data_manager = DataManager()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Create or get user in database
    db_user = data_manager.get_user(user.id)
    if not db_user:
        data_manager.create_user(user.id, user.username, user.first_name)
    
    # Initialize cart in context
    if 'cart' not in context.user_data:
        context.user_data['cart'] = []
    
    settings = data_manager.get_settings()
    restaurant_name = settings.get('restaurant', {}).get('name', 'Суши Экспресс')
    
    welcome_text = (
        f"🍣 Добро пожаловать в *{restaurant_name}*!\n\n"
        f"Привет, {user.first_name}! 👋\n\n"
        "Мы готовим свежие суши и роллы с доставкой прямо к вашей двери.\n\n"
        "Выберите пункт меню для начала:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "🍣 *Помощь по боту*\n\n"
        "📋 *Основные команды:*\n"
        "/start - Главное меню\n"
        "/menu - Посмотреть меню\n"
        "/cart - Корзина\n"
        "/orders - Мои заказы\n"
        "/bonus - Бонусный счёт\n"
        "/help - Эта справка\n\n"
        "🛒 *Как сделать заказ:*\n"
        "1. Выберите категорию в меню\n"
        "2. Выберите блюдо и количество\n"
        "3. Добавьте в корзину\n"
        "4. Оформите заказ\n\n"
        "📞 *Поддержка:* Используйте кнопку 'Контакты'"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu button press"""
    categories = data_manager.get_categories()
    
    text = "🍱 *Выберите категорию:*"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            reply_markup=get_categories_keyboard(categories),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=get_categories_keyboard(categories),
            parse_mode='Markdown'
        )


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection"""
    query = update.callback_query
    await query.answer()
    
    category_id = int(query.data.split('_')[1])
    context.user_data['current_category'] = category_id
    
    category = data_manager.get_category(category_id)
    products = data_manager.get_products(category_id)
    
    if not products:
        await query.edit_message_text(
            "😔 В этой категории пока нет доступных товаров.",
            reply_markup=get_categories_keyboard(data_manager.get_categories())
        )
        return
    
    category_name = category['name'] if category else "Товары"
    emoji = category.get('emoji', '') if category else ''
    
    text = f"{emoji} *{category_name}*\n\nВыберите блюдо:"
    
    await query.edit_message_text(
        text,
        reply_markup=get_products_keyboard(products, category_id),
        parse_mode='Markdown'
    )


async def product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product selection - show product details"""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[1])
    product = data_manager.get_product(product_id)
    
    if not product:
        await query.edit_message_text("❌ Товар не найден")
        return
    
    # Initialize quantity for this product
    context.user_data['current_product'] = product_id
    context.user_data['current_quantity'] = 1
    
    text = format_product_detail(product)
    
    await query.edit_message_text(
        text,
        reply_markup=get_product_quantity_keyboard(product_id, 1),
        parse_mode='Markdown'
    )


def format_product_detail(product: dict) -> str:
    """Format product details for display"""
    return (
        f"*{product['name']}*\n\n"
        f"📝 {product.get('description', '')}\n"
        f"⚖️ Вес: {product.get('weight', 'не указан')}\n"
        f"💰 Цена: *{product['price']}₽*\n\n"
        f"Выберите количество:"
    )


async def quantity_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quantity +/- buttons"""
    query = update.callback_query
    data = query.data
    
    product_id = int(data.split('_')[-1])
    current_qty = context.user_data.get('current_quantity', 1)
    
    if 'minus' in data and current_qty > 1:
        current_qty -= 1
    elif 'plus' in data and current_qty < 99:
        current_qty += 1
    
    context.user_data['current_quantity'] = current_qty
    
    await query.answer(f"Количество: {current_qty}")
    
    product = data_manager.get_product(product_id)
    text = format_product_detail(product)
    
    await query.edit_message_text(
        text,
        reply_markup=get_product_quantity_keyboard(product_id, current_qty),
        parse_mode='Markdown'
    )


async def add_to_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle add to cart button"""
    query = update.callback_query
    
    product_id = int(query.data.split('_')[-1])
    quantity = context.user_data.get('current_quantity', 1)
    
    product = data_manager.get_product(product_id)
    if not product:
        await query.answer("❌ Товар не найден", show_alert=True)
        return
    
    # Initialize cart if needed
    if 'cart' not in context.user_data:
        context.user_data['cart'] = []
    
    cart = context.user_data['cart']
    
    # Check if product already in cart
    existing_item = next((item for item in cart if item['product_id'] == product_id), None)
    
    if existing_item:
        existing_item['quantity'] += quantity
    else:
        cart.append({
            'product_id': product_id,
            'product_name': product['name'],
            'price': product['price'],
            'quantity': quantity
        })
    
    await query.answer(f"✅ {product['name']} x{quantity} добавлено в корзину!")
    
    # Return to products list
    category_id = context.user_data.get('current_category')
    if category_id:
        products = data_manager.get_products(category_id)
        category = data_manager.get_category(category_id)
        text = f"{category.get('emoji', '')} *{category['name']}*\n\nВыберите блюдо:"
        await query.edit_message_text(
            text,
            reply_markup=get_products_keyboard(products, category_id),
            parse_mode='Markdown'
        )


async def cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cart button/command"""
    cart = context.user_data.get('cart', [])
    
    if not cart:
        text = "🛒 *Ваша корзина пуста*\n\nДобавьте товары из меню!"
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text,
                reply_markup=get_empty_cart_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=get_empty_cart_keyboard(),
                parse_mode='Markdown'
            )
        return
    
    text = format_cart(cart)
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            reply_markup=get_cart_keyboard(cart),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=get_cart_keyboard(cart),
            parse_mode='Markdown'
        )


def format_cart(cart: list) -> str:
    """Format cart contents for display"""
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    lines = ["🛒 *Ваша корзина:*\n"]
    for item in cart:
        subtotal = item['price'] * item['quantity']
        lines.append(f"• {item['product_name']} x{item['quantity']} = {subtotal}₽")
    
    lines.append(f"\n💰 *Итого: {total}₽*")
    
    return "\n".join(lines)


async def cart_modify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cart item quantity modification"""
    query = update.callback_query
    data = query.data
    
    cart = context.user_data.get('cart', [])
    
    if 'cart_minus' in data or 'cart_plus' in data:
        product_id = int(data.split('_')[-1])
        
        for item in cart:
            if item['product_id'] == product_id:
                if 'minus' in data:
                    item['quantity'] -= 1
                    if item['quantity'] <= 0:
                        cart.remove(item)
                else:
                    item['quantity'] += 1
                break
        
        context.user_data['cart'] = cart
        await query.answer()
        
        if not cart:
            await query.edit_message_text(
                "🛒 *Ваша корзина пуста*",
                reply_markup=get_empty_cart_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                format_cart(cart),
                reply_markup=get_cart_keyboard(cart),
                parse_mode='Markdown'
            )
    
    elif 'remove_from_cart' in data:
        product_id = int(data.split('_')[-1])
        cart = [item for item in cart if item['product_id'] != product_id]
        context.user_data['cart'] = cart
        
        await query.answer("✅ Товар удалён")
        
        if not cart:
            await query.edit_message_text(
                "🛒 *Ваша корзина пуста*",
                reply_markup=get_empty_cart_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                format_cart(cart),
                reply_markup=get_cart_keyboard(cart),
                parse_mode='Markdown'
            )


async def clear_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle clear cart button"""
    query = update.callback_query
    context.user_data['cart'] = []
    
    await query.answer("🗑 Корзина очищена")
    await query.edit_message_text(
        "🛒 *Ваша корзина пуста*",
        reply_markup=get_empty_cart_keyboard(),
        parse_mode='Markdown'
    )


async def checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle checkout button"""
    query = update.callback_query
    await query.answer()
    
    cart = context.user_data.get('cart', [])
    if not cart:
        await query.edit_message_text(
            "🛒 Корзина пуста!",
            reply_markup=get_empty_cart_keyboard()
        )
        return
    
    user = data_manager.get_user(update.effective_user.id)
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    # Check minimum order
    import yaml
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    min_order = config.get('delivery', {}).get('min_order_amount', 0)
    if total < min_order:
        await query.answer(f"Минимальная сумма заказа: {min_order}₽", show_alert=True)
        return
    
    # Calculate delivery
    free_delivery_from = config.get('delivery', {}).get('free_delivery_from', 1500)
    delivery_cost = config.get('delivery', {}).get('delivery_cost', 200) if total < free_delivery_from else 0
    
    # Store order info
    context.user_data['order_subtotal'] = total
    context.user_data['delivery_cost'] = delivery_cost
    context.user_data['order_total'] = total + delivery_cost
    context.user_data['discount'] = 0
    
    # Get saved address if any
    address = user.get('addresses', [None])[0] if user and user.get('addresses') else None
    context.user_data['delivery_address'] = address
    
    phone = user.get('phone') if user else None
    context.user_data['phone'] = phone
    
    text = format_checkout(cart, total, delivery_cost, address, phone)
    
    await query.edit_message_text(
        text,
        reply_markup=get_checkout_keyboard(),
        parse_mode='Markdown'
    )


def format_checkout(cart: list, subtotal: float, delivery_cost: float, 
                   address: str = None, phone: str = None, 
                   discount: float = 0, promo_code: str = None) -> str:
    """Format checkout summary"""
    lines = ["📋 *Оформление заказа*\n"]
    
    for item in cart:
        lines.append(f"• {item['product_name']} x{item['quantity']} = {item['price'] * item['quantity']}₽")
    
    lines.append(f"\n💵 Сумма: {subtotal}₽")
    
    if discount > 0:
        lines.append(f"🎟 Скидка ({promo_code}): -{discount:.0f}₽")
    
    if delivery_cost > 0:
        lines.append(f"🚗 Доставка: {delivery_cost}₽")
    else:
        lines.append("🚗 Доставка: *Бесплатно* ✨")
    
    total = subtotal - discount + delivery_cost
    lines.append(f"\n💰 *Итого к оплате: {total:.0f}₽*")
    
    lines.append(f"\n📍 Адрес: {address or '❗️ Не указан'}")
    lines.append(f"📱 Телефон: {phone or '❗️ Не указан'}")
    
    return "\n".join(lines)


async def change_address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle change address button"""
    query = update.callback_query
    await query.answer()
    
    user = data_manager.get_user(update.effective_user.id)
    addresses = user.get('addresses', []) if user else []
    
    if addresses:
        await query.edit_message_text(
            "📍 *Выберите адрес доставки:*",
            reply_markup=get_saved_addresses_keyboard(addresses),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    else:
        await query.edit_message_text(
            "📍 Введите адрес доставки:",
            parse_mode='Markdown'
        )
        return WAITING_ADDRESS


async def use_address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle saved address selection"""
    query = update.callback_query
    
    address_index = int(query.data.split('_')[-1])
    user = data_manager.get_user(update.effective_user.id)
    addresses = user.get('addresses', []) if user else []
    
    if 0 <= address_index < len(addresses):
        context.user_data['delivery_address'] = addresses[address_index]
        await query.answer(f"✅ Адрес выбран")
        
        # Return to checkout
        cart = context.user_data.get('cart', [])
        subtotal = context.user_data.get('order_subtotal', 0)
        delivery_cost = context.user_data.get('delivery_cost', 0)
        phone = context.user_data.get('phone')
        discount = context.user_data.get('discount', 0)
        promo_code = context.user_data.get('promo_code')
        
        text = format_checkout(cart, subtotal, delivery_cost, 
                              addresses[address_index], phone, discount, promo_code)
        await query.edit_message_text(
            text,
            reply_markup=get_checkout_keyboard(),
            parse_mode='Markdown'
        )


async def new_address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new address button"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📍 *Введите новый адрес доставки:*\n\n"
        "Пример: Москва, ул. Ленина, д. 10, кв. 5",
        parse_mode='Markdown'
    )
    return WAITING_ADDRESS


async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle address text input"""
    address = update.message.text
    
    context.user_data['delivery_address'] = address
    
    # Save address to user profile
    data_manager.add_user_address(update.effective_user.id, address)
    
    await update.message.reply_text("✅ Адрес сохранён!")
    
    # Check if phone is needed
    if not context.user_data.get('phone'):
        await update.message.reply_text(
            "📱 Теперь укажите номер телефона для связи:",
            reply_markup=get_phone_request_keyboard()
        )
        return WAITING_PHONE
    
    # Return to checkout
    cart = context.user_data.get('cart', [])
    subtotal = context.user_data.get('order_subtotal', 0)
    delivery_cost = context.user_data.get('delivery_cost', 0)
    phone = context.user_data.get('phone')
    discount = context.user_data.get('discount', 0)
    promo_code = context.user_data.get('promo_code')
    
    text = format_checkout(cart, subtotal, delivery_cost, address, phone, discount, promo_code)
    await update.message.reply_text(
        text,
        reply_markup=get_checkout_keyboard(),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


async def receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number input (contact or text)"""
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text
    
    context.user_data['phone'] = phone
    
    # Save phone to user profile
    data_manager.update_user(update.effective_user.id, {'phone': phone})
    
    await update.message.reply_text(
        "✅ Номер телефона сохранён!",
        reply_markup=get_main_menu_keyboard()
    )
    
    # Return to checkout
    cart = context.user_data.get('cart', [])
    subtotal = context.user_data.get('order_subtotal', 0)
    delivery_cost = context.user_data.get('delivery_cost', 0)
    address = context.user_data.get('delivery_address')
    discount = context.user_data.get('discount', 0)
    promo_code = context.user_data.get('promo_code')
    
    text = format_checkout(cart, subtotal, delivery_cost, address, phone, discount, promo_code)
    await update.message.reply_text(
        text,
        reply_markup=get_checkout_keyboard(),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


async def apply_promocode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle apply promocode button"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🎟 *Введите промокод:*",
        parse_mode='Markdown'
    )
    return WAITING_PROMOCODE


async def receive_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle promocode text input"""
    code = update.message.text.strip().upper()
    subtotal = context.user_data.get('order_subtotal', 0)
    
    promo = data_manager.check_promocode(code, subtotal)
    
    if promo:
        discount = data_manager.calculate_discount(promo, subtotal)
        context.user_data['discount'] = discount
        context.user_data['promo_code'] = code
        context.user_data['order_total'] = subtotal + context.user_data.get('delivery_cost', 0) - discount
        
        await update.message.reply_text(f"✅ Промокод применён! Скидка: {discount:.0f}₽")
    else:
        await update.message.reply_text(
            "❌ Промокод недействителен или не применим к этому заказу"
        )
    
    # Return to checkout
    cart = context.user_data.get('cart', [])
    delivery_cost = context.user_data.get('delivery_cost', 0)
    address = context.user_data.get('delivery_address')
    phone = context.user_data.get('phone')
    discount = context.user_data.get('discount', 0)
    promo_code = context.user_data.get('promo_code')
    
    text = format_checkout(cart, subtotal, delivery_cost, address, phone, discount, promo_code)
    await update.message.reply_text(
        text,
        reply_markup=get_checkout_keyboard(),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


async def confirm_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order confirmation - ask for payment method"""
    query = update.callback_query
    
    # Check if address and phone are set
    if not context.user_data.get('delivery_address'):
        await query.answer("❗️ Укажите адрес доставки", show_alert=True)
        return
    
    if not context.user_data.get('phone'):
        await query.answer("❗️ Укажите номер телефона", show_alert=True)
        return
    
    await query.answer()
    await query.edit_message_text(
        "💳 *Выберите способ оплаты:*",
        reply_markup=get_payment_method_keyboard(),
        parse_mode='Markdown'
    )


async def payment_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection and create order"""
    query = update.callback_query
    data = query.data
    
    # Determine payment method
    if 'cash' in data:
        payment_method = 'cash'
        payment_text = 'Наличные'
    elif 'card_on_delivery' in data:
        payment_method = 'card_on_delivery'
        payment_text = 'Карта курьеру'
    else:
        payment_method = 'online'
        payment_text = 'Онлайн оплата'
    
    cart = context.user_data.get('cart', [])
    
    # Create order
    order_data = {
        'user_id': update.effective_user.id,
        'items': cart,
        'subtotal': context.user_data.get('order_subtotal', 0),
        'delivery_cost': context.user_data.get('delivery_cost', 0),
        'discount': context.user_data.get('discount', 0),
        'promo_code': context.user_data.get('promo_code'),
        'total': context.user_data.get('order_total', 0),
        'delivery_address': context.user_data.get('delivery_address'),
        'phone': context.user_data.get('phone'),
        'payment_method': payment_method,
        'comment': ''
    }
    
    order_id = data_manager.create_order(order_data)
    
    # Use promocode if applied
    if context.user_data.get('promo_code'):
        data_manager.use_promocode(context.user_data['promo_code'])
    
    # Clear cart
    context.user_data['cart'] = []
    context.user_data['discount'] = 0
    context.user_data['promo_code'] = None
    
    await query.answer("✅ Заказ создан!")
    
    text = (
        f"🎉 *Заказ #{order_id} оформлен!*\n\n"
        f"📍 Адрес: {order_data['delivery_address']}\n"
        f"📱 Телефон: {order_data['phone']}\n"
        f"💳 Оплата: {payment_text}\n"
        f"💰 Сумма: {order_data['total']:.0f}₽\n\n"
        f"Статус заказа: 🆕 Новый\n\n"
        f"Мы уведомим вас об изменении статуса заказа."
    )
    
    await query.edit_message_text(text, parse_mode='Markdown')
    
    # Notify admins
    await notify_admins_new_order(context, order_id, order_data)


async def notify_admins_new_order(context: ContextTypes.DEFAULT_TYPE, 
                                   order_id: int, order_data: dict):
    """Send notification to admins about new order"""
    import yaml
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    admin_ids = config.get('bot', {}).get('admin_ids', [])
    
    items_text = "\n".join([
        f"  • {item['product_name']} x{item['quantity']} = {item['price'] * item['quantity']}₽"
        for item in order_data['items']
    ])
    
    text = (
        f"🆕 *Новый заказ #{order_id}!*\n\n"
        f"📦 Товары:\n{items_text}\n\n"
        f"💰 Сумма: {order_data['total']:.0f}₽\n"
        f"📍 Адрес: {order_data['delivery_address']}\n"
        f"📱 Телефон: {order_data['phone']}\n"
        f"💳 Оплата: {order_data['payment_method']}"
    )
    
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode='Markdown'
            )
        except Exception:
            pass  # Admin might have blocked the bot


async def orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle orders button/command"""
    orders = data_manager.get_user_orders(update.effective_user.id)
    
    if not orders:
        text = "📦 *Мои заказы*\n\nУ вас пока нет заказов."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                text,
                reply_markup=get_empty_cart_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=get_empty_cart_keyboard(),
                parse_mode='Markdown'
            )
        return
    
    text = "📦 *Мои заказы:*\n\nВыберите заказ для подробностей:"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            reply_markup=get_order_list_keyboard(orders),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=get_order_list_keyboard(orders),
            parse_mode='Markdown'
        )


async def view_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order detail view"""
    query = update.callback_query
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
    
    text = (
        f"📦 *Заказ #{order['id']}*\n\n"
        f"{status_emoji} Статус: *{status_text}*\n\n"
        f"📋 Товары:\n{items_text}\n\n"
        f"💰 Сумма: {order['total']}₽\n"
        f"📍 Адрес: {order['delivery_address']}\n"
        f"📅 Дата: {order['created_at']}"
    )
    
    if order.get('delivered_at'):
        text += f"\n✅ Доставлен: {order['delivered_at']}"
    
    await query.edit_message_text(
        text,
        reply_markup=get_order_detail_keyboard(order_id, order['status']),
        parse_mode='Markdown'
    )


async def reorder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reorder button"""
    query = update.callback_query
    
    order_id = int(query.data.split('_')[-1])
    order = data_manager.get_order(order_id)
    
    if not order:
        await query.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Copy items to cart
    context.user_data['cart'] = []
    for item in order['items']:
        product = data_manager.get_product(item['product_id'])
        if product and product.get('available', True):
            context.user_data['cart'].append({
                'product_id': item['product_id'],
                'product_name': item['product_name'],
                'price': product['price'],  # Use current price
                'quantity': item['quantity']
            })
    
    if not context.user_data['cart']:
        await query.answer("❌ Товары из этого заказа недоступны", show_alert=True)
        return
    
    await query.answer("✅ Товары добавлены в корзину")
    await cart_handler(update, context)


async def cancel_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order cancellation"""
    query = update.callback_query
    
    order_id = int(query.data.split('_')[-1])
    order = data_manager.get_order(order_id)
    
    if not order:
        await query.answer("❌ Заказ не найден", show_alert=True)
        return
    
    if order['status'] in ('on_the_way', 'delivered', 'cancelled'):
        await query.answer("❌ Этот заказ нельзя отменить", show_alert=True)
        return
    
    data_manager.update_order_status(order_id, 'cancelled')
    await query.answer("✅ Заказ отменён")
    
    await query.edit_message_text(
        f"❌ *Заказ #{order_id} отменён*",
        parse_mode='Markdown'
    )


async def bonus_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bonus/loyalty button"""
    user = data_manager.get_user(update.effective_user.id)
    bonus_points = user.get('bonus_points', 0) if user else 0
    total_orders = user.get('total_orders', 0) if user else 0
    
    text = (
        f"💰 *Бонусная программа*\n\n"
        f"🎁 Ваши бонусы: *{bonus_points} баллов*\n"
        f"📦 Всего заказов: {total_orders}\n\n"
        f"ℹ️ Начисление бонусов: 1% от суммы заказа\n"
        f"💡 Бонусами можно оплатить до 50% заказа"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle about us button"""
    settings = data_manager.get_settings()
    restaurant = settings.get('restaurant', {})
    
    text = (
        f"ℹ️ *{restaurant.get('name', 'Суши Экспресс')}*\n\n"
        f"📝 {restaurant.get('description', '')}\n\n"
        f"📍 Адрес: {restaurant.get('address', 'Не указан')}\n"
        f"🕐 Время работы: 10:00 - 23:00\n\n"
        f"🚗 Бесплатная доставка от 1500₽\n"
        f"💰 Минимальный заказ: 500₽"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def contacts_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contacts button"""
    settings = data_manager.get_settings()
    restaurant = settings.get('restaurant', {})
    
    text = (
        f"📞 *Контакты*\n\n"
        f"☎️ Телефон: {restaurant.get('phone', '+79001234567')}\n"
        f"📧 Email: {restaurant.get('email', 'info@sushi.ru')}\n\n"
        f"📍 Адрес: {restaurant.get('address', 'Не указан')}"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle various back buttons"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_main" or data == "go_to_menu":
        await menu_handler(update, context)
    
    elif data == "back_to_categories":
        categories = data_manager.get_categories()
        await query.edit_message_text(
            "🍱 *Выберите категорию:*",
            reply_markup=get_categories_keyboard(categories),
            parse_mode='Markdown'
        )
    
    elif data == "back_to_products":
        category_id = context.user_data.get('current_category')
        if category_id:
            products = data_manager.get_products(category_id)
            category = data_manager.get_category(category_id)
            text = f"{category.get('emoji', '')} *{category['name']}*\n\nВыберите блюдо:"
            await query.edit_message_text(
                text,
                reply_markup=get_products_keyboard(products, category_id),
                parse_mode='Markdown'
            )
    
    elif data == "back_to_cart":
        await cart_handler(update, context)
    
    elif data == "back_to_checkout":
        cart = context.user_data.get('cart', [])
        subtotal = context.user_data.get('order_subtotal', 0)
        delivery_cost = context.user_data.get('delivery_cost', 0)
        address = context.user_data.get('delivery_address')
        phone = context.user_data.get('phone')
        discount = context.user_data.get('discount', 0)
        promo_code = context.user_data.get('promo_code')
        
        text = format_checkout(cart, subtotal, delivery_cost, address, phone, discount, promo_code)
        await query.edit_message_text(
            text,
            reply_markup=get_checkout_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "back_to_orders":
        await orders_handler(update, context)
    
    elif data == "continue_shopping":
        await menu_handler(update, context)


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from main menu buttons"""
    text = update.message.text
    
    if text == "🍱 Меню":
        await menu_handler(update, context)
    elif text == "🛒 Корзина":
        await cart_handler(update, context)
    elif text == "📦 Мои заказы":
        await orders_handler(update, context)
    elif text == "💰 Бонусы":
        await bonus_handler(update, context)
    elif text == "ℹ️ О нас":
        await about_handler(update, context)
    elif text == "📞 Контакты":
        await contacts_handler(update, context)
    elif text == "⬅️ Отмена":
        await update.message.reply_text(
            "Действие отменено.",
            reply_markup=get_main_menu_keyboard()
        )


def get_user_handlers() -> list:
    """Get list of all user handlers"""
    
    # Conversation handler for address/phone/promocode input
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(new_address_callback, pattern="^new_address$"),
            CallbackQueryHandler(apply_promocode_callback, pattern="^apply_promocode$"),
            CallbackQueryHandler(change_address_callback, pattern="^change_address$")
        ],
        states={
            WAITING_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address)
            ],
            WAITING_PHONE: [
                MessageHandler(filters.CONTACT, receive_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone)
            ],
            WAITING_PROMOCODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promocode)
            ]
        },
        fallbacks=[
            CommandHandler("start", start_command)
        ],
        allow_reentry=True
    )
    
    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("menu", menu_handler),
        CommandHandler("cart", cart_handler),
        CommandHandler("orders", orders_handler),
        CommandHandler("bonus", bonus_handler),
        
        conv_handler,
        
        # Callback handlers
        CallbackQueryHandler(category_callback, pattern="^category_"),
        CallbackQueryHandler(product_callback, pattern="^product_"),
        CallbackQueryHandler(quantity_callback, pattern="^qty_(minus|plus)_"),
        CallbackQueryHandler(add_to_cart_callback, pattern="^add_to_cart_"),
        
        CallbackQueryHandler(cart_modify_callback, pattern="^(cart_minus|cart_plus|remove_from_cart)_"),
        CallbackQueryHandler(clear_cart_callback, pattern="^clear_cart$"),
        
        CallbackQueryHandler(checkout_callback, pattern="^checkout$"),
        # Change address moved to conversation handler
        CallbackQueryHandler(use_address_callback, pattern="^use_address_"),
        CallbackQueryHandler(confirm_order_callback, pattern="^confirm_order$"),
        CallbackQueryHandler(payment_method_callback, pattern="^pay_(cash|card_on_delivery|online)$"),
        
        CallbackQueryHandler(view_order_callback, pattern="^view_order_"),
        CallbackQueryHandler(reorder_callback, pattern="^reorder_"),
        CallbackQueryHandler(cancel_order_callback, pattern="^cancel_order_"),
        
        CallbackQueryHandler(back_callback, pattern="^(back_to_|continue_shopping|go_to_menu)"),
        
        # Text message handler for main menu buttons
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler)
    ]
