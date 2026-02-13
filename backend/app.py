from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_session import Session
from models import db, Server, User
from config import Config
import random
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
Session(app)
CORS(app, supports_credentials=True, origins=[
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174', 
    'http://localhost:5173',
    'http://localhost:5174'
])

# Authentication decorators
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Auth routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Username, email, and password are required'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully', 'user': user.to_dict()}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if user and user.check_password(data['password']) and user.is_active:
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({'message': 'Login successful', 'user': user.to_dict()}), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    user = User.query.get(session['user_id'])
    if user:
        return jsonify({'user': user.to_dict()}), 200
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/auth/profile', methods=['PUT'])
@login_required
def update_profile():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Validate current password if changing password
    if data.get('new_password'):
        if not data.get('current_password'):
            return jsonify({'error': 'Current password is required to change password'}), 400
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 400
    
    # Update username if provided and different
    if data.get('username') and data['username'] != user.username:
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400
        user.username = data['username']
    
    # Update email if provided and different
    if data.get('email') and data['email'] != user.email:
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'Email already exists'}), 400
        user.email = data['email']

    if (data.get('is_admin') is not None) and (data['is_admin'] != user.is_admin):
        user.is_admin = data['is_admin']

    
    # Update password if provided
    if data.get('new_password'):
        user.set_password(data['new_password'])
    
    db.session.commit()
    
    # Update session username if it changed
    if data.get('username'):
        session['username'] = user.username
    
    return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200

# User CRUD routes (admin only)
@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    users = User.query.all()
    return jsonify({'users': [user.to_dict() for user in users]}), 200

@app.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Username, email, and password are required'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(
        username=data['username'], 
        email=data['email'],
        is_admin=data.get('is_admin', False)
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201

@app.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({'user': user.to_dict()}), 200

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if data.get('username'):
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'error': 'Username already exists'}), 400
        user.username = data['username']
    
    if data.get('email'):
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user and existing_user.id != user_id:
            return jsonify({'error': 'Email already exists'}), 400
        user.email = data['email']
    
    if data.get('password'):
        user.set_password(data['password'])
    
    if 'is_active' in data:
        user.is_active = data['is_active']
    
    if 'is_admin' in data:
        user.is_admin = data['is_admin']
    
    db.session.commit()
    return jsonify({'message': 'User updated successfully', 'user': user.to_dict()}), 200

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200

# Server CRUD routes
@app.route('/api/servers', methods=['GET'])
@login_required
def get_servers():
    # Get pagination params
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)

    # Safety guard
    if limit <= 0:
        limit = 10
    if page <= 0:
        page = 1

    query = Server.query.order_by(Server.id.asc())

    total = query.count()

    servers = query.offset((page - 1) * limit).limit(limit).all()

    total_pages = (total + limit - 1) // limit  # ceiling division

    return jsonify({
        'servers': [server.to_dict() for server in servers],
        'total': total,
        'page': page,
        'limit': limit,
        'total_pages': total_pages
    }), 200

@app.route('/api/servers/<int:server_id>', methods=['GET'])
@login_required
def get_server(server_id):
    server = Server.query.get_or_404(server_id)
    return jsonify({'server': server.to_dict()}), 200

@app.route('/api/servers', methods=['POST'])
@login_required
def create_server():
    data = request.get_json()
    
    required_fields = ['name', 'hostname', 'ip_address']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Generate realistic random resource usage values to make new servers feel "live"
    random_cpu = round(random.uniform(0, 1), 2)  # 0-1 decimal (e.g. 0.5 = 50%)
    random_memory = round(random.uniform(0, 100))  # 0-100 whole percent
    random_disk = round(random.uniform(0, 1), 2)  # 0-1 decimal (e.g. 0.5 = 50%)
    # Uptime between 1 hour and 100 days (in seconds)
    random_uptime = random.randint(3600, 8640000)

    server = Server(
        name=data['name'],
        hostname=data['hostname'],
        ip_address=data['ip_address'],
        status=data.get('status', 'online'),
        cpu_usage=random_cpu,
        memory_usage=random_memory,
        disk_usage=random_disk,
        uptime=random_uptime,
        location=data.get('location', 'Unknown'),
        os=data.get('os', 'Linux')
    )
    
    db.session.add(server)
    db.session.commit()
    
    return jsonify({'message': 'Server created successfully', 'server': server.to_dict()}), 201

@app.route('/api/servers/<int:server_id>', methods=['PUT'])
@login_required
def update_server(server_id):
    server = Server.query.get_or_404(server_id)
    data = request.get_json()
    
    # Update fields if provided
    for field in ['name', 'hostname', 'ip_address', 'status', 'cpu_usage', 
                  'memory_usage', 'disk_usage', 'uptime', 'location', 'os']:
        if field in data:
            setattr(server, field, data[field])
    
    server.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Server updated successfully', 'server': server.to_dict()}), 200

@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
@login_required
def delete_server(server_id):
    server = Server.query.get_or_404(server_id)
    db.session.delete(server)
    db.session.commit()
    return jsonify({'message': 'Server deleted successfully'}), 200

# Dashboard stats route
@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    total_servers = Server.query.count()
    online_servers = Server.query.filter_by(status='online').count()
    offline_servers = Server.query.filter_by(status='offline').count()
    maintenance_servers = Server.query.filter_by(status='maintenance').count()
    error_servers = Server.query.filter_by(status='error').count()
    
    # Calculate average usage
    servers = Server.query.all()
    avg_cpu = sum(s.cpu_usage for s in servers) / len(servers) if servers else 0
    avg_memory = sum(s.memory_usage for s in servers) / len(servers) if servers else 0
    avg_disk = sum(s.disk_usage for s in servers) / len(servers) if servers else 0
    
    return jsonify({
        'total_servers': total_servers,
        'status_breakdown': {
            'online': online_servers,
            'offline': offline_servers,
            'maintenance': maintenance_servers,
            'error': error_servers
        },
        'average_usage': {
            'cpu': round(avg_cpu, 2),
            'memory': round(avg_memory, 2),
            'disk': round(avg_disk, 2)
        }
    }), 200

def create_sample_data():
    """Create sample users and servers"""
    # Create admin user
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
    
    # Create sample user
    user = User.query.filter_by(username='demo').first()
    if not user:
        user = User(username='demo', email='demo@example.com')
        user.set_password('demo123')
        db.session.add(user)
    
    # Create 50 sample servers
    if Server.query.count() == 0:
        statuses = ['online', 'offline', 'maintenance', 'error']
        locations = ['US-East', 'US-West', 'EU-Central', 'Asia-Pacific', 'Canada', 'Australia']
        os_types = ['Ubuntu 20.04', 'Ubuntu 22.04', 'CentOS 7', 'CentOS 8', 'RHEL 8', 'Windows Server 2019', 'Windows Server 2022']
        
        for i in range(1, 51):
            server = Server(
                name=f'server-{i:02d}',
                hostname=f'srv{i:02d}.example.com',
                ip_address=f'192.168.{(i-1)//256}.{(i-1)%256 + 1}',
                status=random.choice(statuses),
                cpu_usage=round(random.uniform(0, 1), 2),  # 0-1 decimal
                memory_usage=round(random.uniform(0, 100)),  # 0-100 whole percent
                disk_usage=round(random.uniform(0, 1), 2),  # 0-1 decimal
                uptime=random.randint(3600, 8640000),  # 1 hour to 100 days in seconds
                location=random.choice(locations),
                os=random.choice(os_types)
            )
            db.session.add(server)
    
    db.session.commit()

# Removed deprecated before_first_request decorator

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_sample_data()
    app.run(debug=True, host='127.0.0.1', port=5000)
