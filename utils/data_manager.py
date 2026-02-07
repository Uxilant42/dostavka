"""
Data Manager for YAML-based storage
Handles all CRUD operations for users, products, orders, and promocodes
"""
import yaml
from datetime import datetime
from typing import Dict, List, Optional
import os
from threading import Lock


class DataManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.lock = Lock()  # For thread safety
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
    
    def _load_yaml(self, filename: str) -> Dict:
        """Load YAML file"""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            return {}
        with self.lock:
            with open(filepath, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
    
    def _save_yaml(self, filename: str, data: Dict):
        """Save to YAML file"""
        filepath = os.path.join(self.data_dir, filename)
        with self.lock:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    # ==================== Categories ====================
    def get_categories(self) -> List[Dict]:
        """Get all product categories"""
        data = self._load_yaml('products.yaml')
        return data.get('categories', [])
    
    def get_category(self, category_id: int) -> Optional[Dict]:
        """Get a single category by ID"""
        categories = self.get_categories()
        return next((c for c in categories if c['id'] == category_id), None)
    
    # ==================== Products ====================
    def get_products(self, category_id: Optional[int] = None) -> List[Dict]:
        """Get products, optionally filtered by category"""
        data = self._load_yaml('products.yaml')
        products = data.get('products', [])
        if category_id:
            return [p for p in products if p['category_id'] == category_id and p.get('available', True)]
        return [p for p in products if p.get('available', True)]
    
    def get_all_products(self) -> List[Dict]:
        """Get all products including unavailable ones"""
        data = self._load_yaml('products.yaml')
        return data.get('products', [])
    
    def get_product(self, product_id: int) -> Optional[Dict]:
        """Get a single product by ID"""
        data = self._load_yaml('products.yaml')
        products = data.get('products', [])
        return next((p for p in products if p['id'] == product_id), None)
    
    def add_product(self, product: Dict) -> int:
        """Add a new product"""
        data = self._load_yaml('products.yaml')
        if 'products' not in data:
            data['products'] = []
        product_id = max([p['id'] for p in data['products']], default=0) + 1
        product['id'] = product_id
        data['products'].append(product)
        self._save_yaml('products.yaml', data)
        return product_id
    
    def update_product(self, product_id: int, updates: Dict):
        """Update an existing product"""
        data = self._load_yaml('products.yaml')
        products = data.get('products', [])
        for product in products:
            if product['id'] == product_id:
                product.update(updates)
                break
        self._save_yaml('products.yaml', data)
    
    def delete_product(self, product_id: int):
        """Delete a product (set available to false)"""
        self.update_product(product_id, {'available': False})
    
    # ==================== Users ====================
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by Telegram ID"""
        data = self._load_yaml('users.yaml')
        users = data.get('users', [])
        return next((u for u in users if u['telegram_id'] == telegram_id), None)
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        data = self._load_yaml('users.yaml')
        return data.get('users', [])
    
    def create_user(self, telegram_id: int, username: str = None, first_name: str = None) -> Dict:
        """Create a new user"""
        data = self._load_yaml('users.yaml')
        if 'users' not in data:
            data['users'] = []
        
        # Check if user already exists
        existing = next((u for u in data['users'] if u['telegram_id'] == telegram_id), None)
        if existing:
            return existing
        
        new_user = {
            'telegram_id': telegram_id,
            'username': username,
            'first_name': first_name,
            'phone': None,
            'addresses': [],
            'bonus_points': 0,
            'total_orders': 0,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        data['users'].append(new_user)
        self._save_yaml('users.yaml', data)
        return new_user
    
    def update_user(self, telegram_id: int, updates: Dict):
        """Update user data"""
        data = self._load_yaml('users.yaml')
        users = data.get('users', [])
        for user in users:
            if user['telegram_id'] == telegram_id:
                user.update(updates)
                break
        self._save_yaml('users.yaml', data)
    
    def add_user_address(self, telegram_id: int, address: str):
        """Add address to user's saved addresses"""
        user = self.get_user(telegram_id)
        if user:
            addresses = user.get('addresses', [])
            if address not in addresses:
                addresses.append(address)
                self.update_user(telegram_id, {'addresses': addresses})
    
    def add_bonus_points(self, telegram_id: int, points: int):
        """Add bonus points to user"""
        user = self.get_user(telegram_id)
        if user:
            current_points = user.get('bonus_points', 0)
            self.update_user(telegram_id, {'bonus_points': current_points + points})
    
    # ==================== Orders ====================
    def create_order(self, order_data: Dict) -> int:
        """Create a new order"""
        data = self._load_yaml('orders.yaml')
        if 'orders' not in data:
            data['orders'] = []
        
        order_id = max([o['id'] for o in data['orders']], default=0) + 1
        
        order_data['id'] = order_id
        order_data['status'] = 'new'
        order_data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        data['orders'].append(order_data)
        self._save_yaml('orders.yaml', data)
        
        # Update user statistics
        user = self.get_user(order_data['user_id'])
        if user:
            self.update_user(order_data['user_id'], {
                'total_orders': user.get('total_orders', 0) + 1
            })
            # Add bonus points (1% of order total)
            bonus = int(order_data.get('total', 0) * 0.01)
            if bonus > 0:
                self.add_bonus_points(order_data['user_id'], bonus)
        
        # Update statistics
        self._update_statistics(order_data.get('total', 0))
        
        return order_id
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        """Get order by ID"""
        data = self._load_yaml('orders.yaml')
        orders = data.get('orders', [])
        return next((o for o in orders if o['id'] == order_id), None)
    
    def get_user_orders(self, telegram_id: int) -> List[Dict]:
        """Get all orders for a user"""
        data = self._load_yaml('orders.yaml')
        orders = data.get('orders', [])
        return sorted(
            [o for o in orders if o['user_id'] == telegram_id],
            key=lambda x: x['created_at'],
            reverse=True
        )
    
    def get_all_orders(self, status: Optional[str] = None) -> List[Dict]:
        """Get all orders, optionally filtered by status"""
        data = self._load_yaml('orders.yaml')
        orders = data.get('orders', [])
        if status:
            return [o for o in orders if o['status'] == status]
        return sorted(orders, key=lambda x: x['created_at'], reverse=True)
    
    def get_pending_orders(self) -> List[Dict]:
        """Get orders that need attention (not delivered or cancelled)"""
        data = self._load_yaml('orders.yaml')
        orders = data.get('orders', [])
        return sorted(
            [o for o in orders if o['status'] not in ('delivered', 'cancelled')],
            key=lambda x: x['created_at'],
            reverse=True
        )
    
    def update_order_status(self, order_id: int, status: str):
        """Update order status"""
        data = self._load_yaml('orders.yaml')
        orders = data.get('orders', [])
        for order in orders:
            if order['id'] == order_id:
                order['status'] = status
                if status == 'delivered':
                    order['delivered_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break
        self._save_yaml('orders.yaml', data)
    
    # ==================== Promocodes ====================
    def get_promocode(self, code: str) -> Optional[Dict]:
        """Get promocode by code"""
        data = self._load_yaml('promocodes.yaml')
        promocodes = data.get('promocodes', [])
        return next((p for p in promocodes if p['code'].upper() == code.upper()), None)
    
    def check_promocode(self, code: str, order_total: float) -> Optional[Dict]:
        """Check if promocode is valid for order total"""
        data = self._load_yaml('promocodes.yaml')
        promocodes = data.get('promocodes', [])
        
        promo = next((p for p in promocodes if p['code'].upper() == code.upper() and p['active']), None)
        
        if promo:
            # Check minimum order
            if order_total < promo.get('min_order', 0):
                return None
            
            # Check expiry
            expiry = datetime.strptime(promo['expiry_date'], '%Y-%m-%d')
            if datetime.now() > expiry:
                return None
            
            # Check usage limit
            max_uses = promo.get('max_uses')
            if max_uses is not None:
                current_uses = promo.get('current_uses', 0)
                if current_uses >= max_uses:
                    return None
            
            return promo
        return None
    
    def calculate_discount(self, promo: Dict, order_total: float) -> float:
        """Calculate discount amount from promocode"""
        if promo.get('discount_percent'):
            return order_total * promo['discount_percent'] / 100
        elif promo.get('discount_fixed'):
            return min(promo['discount_fixed'], order_total)
        return 0
    
    def use_promocode(self, code: str):
        """Increment promocode usage count"""
        data = self._load_yaml('promocodes.yaml')
        promocodes = data.get('promocodes', [])
        for promo in promocodes:
            if promo['code'].upper() == code.upper():
                promo['current_uses'] = promo.get('current_uses', 0) + 1
                break
        self._save_yaml('promocodes.yaml', data)
    
    def get_all_promocodes(self) -> List[Dict]:
        """Get all promocodes"""
        data = self._load_yaml('promocodes.yaml')
        return data.get('promocodes', [])
    
    def add_promocode(self, promo_data: Dict):
        """Add a new promocode"""
        data = self._load_yaml('promocodes.yaml')
        if 'promocodes' not in data:
            data['promocodes'] = []
        data['promocodes'].append(promo_data)
        self._save_yaml('promocodes.yaml', data)
    
    def update_promocode(self, code: str, updates: Dict):
        """Update promocode"""
        data = self._load_yaml('promocodes.yaml')
        promocodes = data.get('promocodes', [])
        for promo in promocodes:
            if promo['code'].upper() == code.upper():
                promo.update(updates)
                break
        self._save_yaml('promocodes.yaml', data)
    
    # ==================== Settings ====================
    def get_settings(self) -> Dict:
        """Get restaurant settings"""
        return self._load_yaml('settings.yaml')
    
    def update_settings(self, updates: Dict):
        """Update settings"""
        data = self._load_yaml('settings.yaml')
        data.update(updates)
        self._save_yaml('settings.yaml', data)
    
    def _update_statistics(self, order_total: float):
        """Update sales statistics"""
        settings = self.get_settings()
        stats = settings.get('statistics', {})
        
        total_orders = stats.get('total_orders', 0) + 1
        total_revenue = stats.get('total_revenue', 0) + order_total
        average_order = total_revenue / total_orders if total_orders > 0 else 0
        
        settings['statistics'] = {
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'average_order': round(average_order, 2)
        }
        self._save_yaml('settings.yaml', settings)
    
    def get_statistics(self) -> Dict:
        """Get sales statistics"""
        settings = self.get_settings()
        return settings.get('statistics', {
            'total_orders': 0,
            'total_revenue': 0,
            'average_order': 0
        })
