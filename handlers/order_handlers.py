"""
Order handlers for order processing
Contains shared order-related utilities and notification handlers
"""
from telegram import Update
from telegram.ext import ContextTypes
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_manager import DataManager
from utils.keyboards import get_status_emoji, get_status_text

# Initialize data manager
data_manager = DataManager()


# Order status flow
ORDER_STATUSES = ['new', 'accepted', 'preparing', 'on_the_way', 'delivered']


def get_next_status(current_status: str) -> str:
    """Get the next status in the order flow"""
    if current_status in ORDER_STATUSES:
        current_index = ORDER_STATUSES.index(current_status)
        if current_index < len(ORDER_STATUSES) - 1:
            return ORDER_STATUSES[current_index + 1]
    return current_status


def format_order_for_admin(order: dict) -> str:
    """Format order details for admin view"""
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
        f"📦 *Заказ #{order['id']}*\n"
        f"{status_emoji} {status_text}\n\n"
        f"📋 *Товары:*\n{items_text}\n\n"
        f"💰 Итого: *{order['total']}₽*\n"
        f"📍 {order['delivery_address']}\n"
        f"📱 {order['phone']}\n"
        f"💳 {payment_methods.get(order['payment_method'], order['payment_method'])}\n"
        f"📅 {order['created_at']}"
    )
    
    return text


def format_order_for_customer(order: dict) -> str:
    """Format order details for customer view"""
    status_emoji = get_status_emoji(order['status'])
    status_text = get_status_text(order['status'])
    
    items_text = "\n".join([
        f"  • {item['product_name']} x{item['quantity']}"
        for item in order['items']
    ])
    
    text = (
        f"📦 *Заказ #{order['id']}*\n\n"
        f"Статус: {status_emoji} *{status_text}*\n\n"
        f"📋 Товары:\n{items_text}\n\n"
        f"💰 Сумма: *{order['total']}₽*\n"
        f"📍 Адрес: {order['delivery_address']}"
    )
    
    return text


def calculate_order_totals(cart: list, delivery_cost: float = 0, 
                          discount: float = 0) -> dict:
    """Calculate order totals"""
    subtotal = sum(item['price'] * item['quantity'] for item in cart)
    total = subtotal + delivery_cost - discount
    
    return {
        'subtotal': subtotal,
        'delivery_cost': delivery_cost,
        'discount': discount,
        'total': max(0, total)  # Ensure total is not negative
    }


def get_delivery_cost(subtotal: float, config: dict) -> float:
    """Calculate delivery cost based on order subtotal and config"""
    delivery_config = config.get('delivery', {})
    free_from = delivery_config.get('free_delivery_from', 1500)
    delivery_cost = delivery_config.get('delivery_cost', 200)
    
    if subtotal >= free_from:
        return 0
    return delivery_cost


def is_order_within_working_hours(config: dict) -> bool:
    """Check if current time is within working hours"""
    from datetime import datetime
    
    delivery_config = config.get('delivery', {})
    working_hours = delivery_config.get('working_hours', {})
    
    start_str = working_hours.get('start', '10:00')
    end_str = working_hours.get('end', '23:00')
    
    try:
        start_time = datetime.strptime(start_str, '%H:%M').time()
        end_time = datetime.strptime(end_str, '%H:%M').time()
        current_time = datetime.now().time()
        
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:
            # Handles overnight working hours (e.g., 22:00 - 02:00)
            return current_time >= start_time or current_time <= end_time
    except ValueError:
        return True  # If parsing fails, assume we're open


def validate_order(cart: list, config: dict) -> tuple:
    """
    Validate order before checkout
    Returns (is_valid, error_message)
    """
    if not cart:
        return False, "Корзина пуста"
    
    subtotal = sum(item['price'] * item['quantity'] for item in cart)
    
    min_order = config.get('delivery', {}).get('min_order_amount', 0)
    if subtotal < min_order:
        return False, f"Минимальная сумма заказа: {min_order}₽"
    
    if not is_order_within_working_hours(config):
        working_hours = config.get('delivery', {}).get('working_hours', {})
        start = working_hours.get('start', '10:00')
        end = working_hours.get('end', '23:00')
        return False, f"Мы работаем с {start} до {end}"
    
    return True, None


async def send_order_notification(context: ContextTypes.DEFAULT_TYPE,
                                  user_id: int, order_id: int, 
                                  notification_type: str, **kwargs):
    """
    Send order notification to user
    notification_type: 'created', 'status_changed', 'cancelled'
    """
    order = data_manager.get_order(order_id)
    if not order:
        return
    
    if notification_type == 'created':
        text = (
            f"✅ *Заказ #{order_id} создан!*\n\n"
            f"Сумма: {order['total']}₽\n"
            f"Ожидайте подтверждения от ресторана."
        )
    
    elif notification_type == 'status_changed':
        new_status = kwargs.get('new_status', order['status'])
        status_emoji = get_status_emoji(new_status)
        status_text = get_status_text(new_status)
        
        messages = {
            'accepted': 'Ресторан принял ваш заказ! 👨‍🍳',
            'preparing': 'Ваш заказ готовится. Скоро будет готов! 🍣',
            'on_the_way': 'Курьер выехал! Ждите доставку! 🚗',
            'delivered': 'Заказ доставлен! Приятного аппетита! 🎉'
        }
        
        text = (
            f"{status_emoji} *Обновление заказа #{order_id}*\n\n"
            f"Статус: *{status_text}*\n\n"
            f"{messages.get(new_status, '')}"
        )
    
    elif notification_type == 'cancelled':
        text = (
            f"❌ *Заказ #{order_id} отменён*\n\n"
            f"Причина: {kwargs.get('reason', 'Не указана')}"
        )
    
    else:
        return
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode='Markdown'
        )
    except Exception:
        pass  # User might have blocked the bot


def get_order_statistics(orders: list) -> dict:
    """Calculate statistics from orders list"""
    if not orders:
        return {
            'total_orders': 0,
            'total_revenue': 0,
            'average_order': 0,
            'by_status': {}
        }
    
    total_revenue = sum(o['total'] for o in orders if o['status'] != 'cancelled')
    completed = [o for o in orders if o['status'] == 'delivered']
    
    by_status = {}
    for order in orders:
        status = order['status']
        if status not in by_status:
            by_status[status] = {'count': 0, 'revenue': 0}
        by_status[status]['count'] += 1
        by_status[status]['revenue'] += order['total']
    
    return {
        'total_orders': len(orders),
        'total_revenue': total_revenue,
        'average_order': total_revenue / len(orders) if orders else 0,
        'completed_orders': len(completed),
        'by_status': by_status
    }
