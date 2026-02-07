"""
Keyboard utilities for Telegram bot
Creates inline and reply keyboards for menu navigation
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict, Optional


# ==================== Main Menu ====================
def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard for customers"""
    keyboard = [
        [KeyboardButton("🍱 Меню"), KeyboardButton("🛒 Корзина")],
        [KeyboardButton("📦 Мои заказы"), KeyboardButton("💰 Бонусы")],
        [KeyboardButton("ℹ️ О нас"), KeyboardButton("📞 Контакты")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    """Admin panel keyboard"""
    keyboard = [
        [KeyboardButton("📋 Активные заказы"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("🍣 Управление меню"), KeyboardButton("🎟 Промокоды")],
        [KeyboardButton("👥 Пользователи"), KeyboardButton("📢 Рассылка")],
        [KeyboardButton("⬅️ Выход из админки")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ==================== Categories ====================
def get_categories_keyboard(categories: List[Dict]) -> InlineKeyboardMarkup:
    """Keyboard with product categories"""
    buttons = []
    for category in categories:
        emoji = category.get('emoji', '')
        name = category['name']
        buttons.append([InlineKeyboardButton(
            f"{emoji} {name}",
            callback_data=f"category_{category['id']}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(buttons)


# ==================== Products ====================
def get_products_keyboard(products: List[Dict], category_id: int) -> InlineKeyboardMarkup:
    """Keyboard with products in a category"""
    buttons = []
    for product in products:
        name = product['name']
        price = product['price']
        buttons.append([InlineKeyboardButton(
            f"{name} - {price}₽",
            callback_data=f"product_{product['id']}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ К категориям", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(buttons)


def get_product_detail_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Keyboard for product detail view"""
    buttons = [
        [
            InlineKeyboardButton("➖", callback_data=f"qty_minus_{product_id}"),
            InlineKeyboardButton("1", callback_data=f"qty_show_{product_id}"),
            InlineKeyboardButton("➕", callback_data=f"qty_plus_{product_id}")
        ],
        [InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"add_to_cart_{product_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_products")]
    ]
    return InlineKeyboardMarkup(buttons)


def get_product_quantity_keyboard(product_id: int, quantity: int) -> InlineKeyboardMarkup:
    """Keyboard with current quantity for product"""
    buttons = [
        [
            InlineKeyboardButton("➖", callback_data=f"qty_minus_{product_id}"),
            InlineKeyboardButton(str(quantity), callback_data=f"qty_show_{product_id}"),
            InlineKeyboardButton("➕", callback_data=f"qty_plus_{product_id}")
        ],
        [InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"add_to_cart_{product_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_products")]
    ]
    return InlineKeyboardMarkup(buttons)


# ==================== Cart ====================
def get_cart_keyboard(cart_items: List[Dict], has_items: bool = True) -> InlineKeyboardMarkup:
    """Cart management keyboard"""
    buttons = []
    
    if has_items:
        for item in cart_items:
            product_name = item['product_name'][:20]
            buttons.append([
                InlineKeyboardButton(f"❌ {product_name}", callback_data=f"remove_from_cart_{item['product_id']}"),
                InlineKeyboardButton("➖", callback_data=f"cart_minus_{item['product_id']}"),
                InlineKeyboardButton(str(item['quantity']), callback_data="noop"),
                InlineKeyboardButton("➕", callback_data=f"cart_plus_{item['product_id']}")
            ])
        buttons.append([InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear_cart")])
        buttons.append([InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")])
    
    buttons.append([InlineKeyboardButton("🍱 Продолжить покупки", callback_data="continue_shopping")])
    return InlineKeyboardMarkup(buttons)


def get_empty_cart_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for empty cart"""
    buttons = [
        [InlineKeyboardButton("🍱 Перейти в меню", callback_data="go_to_menu")]
    ]
    return InlineKeyboardMarkup(buttons)


# ==================== Checkout ====================
def get_checkout_keyboard() -> InlineKeyboardMarkup:
    """Checkout confirmation keyboard"""
    buttons = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_order")],
        [InlineKeyboardButton("📍 Изменить адрес", callback_data="change_address")],
        [InlineKeyboardButton("🎟 Применить промокод", callback_data="apply_promocode")],
        [InlineKeyboardButton("⬅️ Назад к корзине", callback_data="back_to_cart")]
    ]
    return InlineKeyboardMarkup(buttons)


def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    """Payment method selection keyboard"""
    buttons = [
        [InlineKeyboardButton("💵 Наличные", callback_data="pay_cash")],
        [InlineKeyboardButton("💳 Карта курьеру", callback_data="pay_card_on_delivery")],
        [InlineKeyboardButton("🌐 Онлайн оплата", callback_data="pay_online")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_checkout")]
    ]
    return InlineKeyboardMarkup(buttons)


def get_saved_addresses_keyboard(addresses: List[str]) -> InlineKeyboardMarkup:
    """Keyboard with saved addresses and option to add new"""
    buttons = []
    for i, address in enumerate(addresses[:5]):  # Max 5 addresses
        short_address = address[:35] + "..." if len(address) > 35 else address
        buttons.append([InlineKeyboardButton(f"📍 {short_address}", callback_data=f"use_address_{i}")])
    buttons.append([InlineKeyboardButton("➕ Новый адрес", callback_data="new_address")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_checkout")])
    return InlineKeyboardMarkup(buttons)


def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard for phone number request"""
    keyboard = [
        [KeyboardButton("📱 Отправить номер телефона", request_contact=True)],
        [KeyboardButton("⬅️ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


# ==================== Orders ====================
def get_order_list_keyboard(orders: List[Dict]) -> InlineKeyboardMarkup:
    """Keyboard with user's orders"""
    buttons = []
    for order in orders[:10]:  # Show last 10 orders
        status_emoji = get_status_emoji(order['status'])
        buttons.append([InlineKeyboardButton(
            f"{status_emoji} Заказ #{order['id']} - {order['total']}₽",
            callback_data=f"view_order_{order['id']}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(buttons)


def get_order_detail_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    """Keyboard for order detail view"""
    buttons = []
    if status == 'delivered':
        buttons.append([InlineKeyboardButton("🔄 Повторить заказ", callback_data=f"reorder_{order_id}")])
    elif status not in ('cancelled', 'on_the_way', 'delivered'):
        buttons.append([InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_order_{order_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К списку заказов", callback_data="back_to_orders")])
    return InlineKeyboardMarkup(buttons)


# ==================== Admin ====================
def get_admin_orders_keyboard(orders: List[Dict]) -> InlineKeyboardMarkup:
    """Admin keyboard for order management"""
    buttons = []
    for order in orders[:15]:  # Show first 15 pending orders
        status_emoji = get_status_emoji(order['status'])
        buttons.append([InlineKeyboardButton(
            f"{status_emoji} #{order['id']} - {order['total']}₽",
            callback_data=f"admin_order_{order['id']}"
        )])
    return InlineKeyboardMarkup(buttons)


def get_admin_order_status_keyboard(order_id: int, current_status: str) -> InlineKeyboardMarkup:
    """Keyboard for changing order status"""
    statuses = [
        ('new', '🆕 Новый'),
        ('accepted', '✅ Принят'),
        ('preparing', '👨‍🍳 Готовится'),
        ('on_the_way', '🚗 В пути'),
        ('delivered', '📦 Доставлен'),
        ('cancelled', '❌ Отменён')
    ]
    
    buttons = []
    for status_code, status_name in statuses:
        if status_code != current_status:
            buttons.append([InlineKeyboardButton(
                status_name,
                callback_data=f"set_status_{order_id}_{status_code}"
            )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_to_orders")])
    return InlineKeyboardMarkup(buttons)


def get_admin_product_list_keyboard(products: List[Dict]) -> InlineKeyboardMarkup:
    """Admin keyboard for product management"""
    buttons = []
    for product in products[:15]:
        available = "✅" if product.get('available', True) else "❌"
        buttons.append([InlineKeyboardButton(
            f"{available} {product['name']} - {product['price']}₽",
            callback_data=f"admin_product_{product['id']}"
        )])
    buttons.append([InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add_product")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(buttons)


def get_admin_product_actions_keyboard(product_id: int, is_available: bool) -> InlineKeyboardMarkup:
    """Admin keyboard for product actions"""
    buttons = [
        [InlineKeyboardButton("✏️ Изменить цену", callback_data=f"admin_edit_price_{product_id}")],
        [InlineKeyboardButton("📝 Изменить описание", callback_data=f"admin_edit_desc_{product_id}")]
    ]
    if is_available:
        buttons.append([InlineKeyboardButton("🚫 Скрыть товар", callback_data=f"admin_hide_{product_id}")])
    else:
        buttons.append([InlineKeyboardButton("✅ Показать товар", callback_data=f"admin_show_{product_id}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_products")])
    return InlineKeyboardMarkup(buttons)


def get_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Generic confirmation keyboard"""
    buttons = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("❌ Нет", callback_data=f"cancel_{action}")
        ]
    ]
    return InlineKeyboardMarkup(buttons)


# ==================== Utilities ====================
def get_status_emoji(status: str) -> str:
    """Get emoji for order status"""
    status_emojis = {
        'new': '🆕',
        'accepted': '✅',
        'preparing': '👨‍🍳',
        'on_the_way': '🚗',
        'delivered': '📦',
        'cancelled': '❌'
    }
    return status_emojis.get(status, '❓')


def get_status_text(status: str) -> str:
    """Get Russian text for order status"""
    status_texts = {
        'new': 'Новый',
        'accepted': 'Принят',
        'preparing': 'Готовится',
        'on_the_way': 'В пути',
        'delivered': 'Доставлен',
        'cancelled': 'Отменён'
    }
    return status_texts.get(status, 'Неизвестно')


def get_back_keyboard(callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """Simple back button keyboard"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=callback_data)]])
