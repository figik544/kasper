from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import json
import sqlite3
import os
from datetime import datetime, timedelta
import requests

app = Flask(__name__)
app.secret_key = 'galactic_empire_admin_secret_2011'  # Пароль 2011 для админ панели

# Загрузка конфигурации
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# URL для API бота (предполагаем, что бот запущен с API)
BOT_API_BASE_URL = 'http://localhost:8080'  # Порт для API бота

# Путь к базе данных
DATABASE = 'galactic_empire_bot.db'

def init_db():
    """Инициализация базы данных с дополнительными таблицами для веб-приложения"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Создание таблицы для настроек сервера
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER UNIQUE,
            bot_status TEXT DEFAULT 'online',
            prefix TEXT DEFAULT '!',
            welcome_message TEXT,
            auto_moderation BOOLEAN DEFAULT 1,
            spam_threshold INTEGER DEFAULT 5,
            max_warnings INTEGER DEFAULT 5,
            daily_credits_min INTEGER DEFAULT 50,
            daily_credits_max INTEGER DEFAULT 150,
            salary_interval INTEGER DEFAULT 24,
            advertising_enabled BOOLEAN DEFAULT 0,
            ad_message TEXT,
            ad_frequency INTEGER DEFAULT 6,
            elections_enabled BOOLEAN DEFAULT 0,
            legislation_enabled BOOLEAN DEFAULT 0,
            election_cycle INTEGER DEFAULT 30,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создание таблицы для правительства
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS government_structure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supreme_ruler TEXT,
            chancellery TEXT,
            ministries TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создание таблицы для логов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Получение соединения с базой данных"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def log_action(user_id, action, details):
    """Логирование действий администратора"""
    conn = get_db_connection()
    conn.execute('INSERT INTO admin_logs (user_id, action, details) VALUES (?, ?, ?)',
                 (user_id, action, details))
    conn.commit()
    conn.close()

def call_bot_api(endpoint, method='GET', data=None):
    """Вызов API бота"""
    try:
        url = f"{BOT_API_BASE_URL}{endpoint}"
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        elif method == 'PUT':
            response = requests.put(url, json=data)
        elif method == 'DELETE':
            response = requests.delete(url)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            print(f"Ошибка API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка при вызове API: {e}")
        return None

@app.route('/')
def index():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем статистику
    conn = get_db_connection()
    
    # Количество серверов
    total_servers = 1  # Главный сервер всегда есть
    
    # Количество пользователей (приблизительно)
    user_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    
    # Количество онлайн пользователей (приблизительно)
    recent_users = conn.execute('SELECT COUNT(*) as count FROM users WHERE last_daily_claim > ?', 
                               (datetime.now() - timedelta(days=1),)).fetchone()['count']
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                          total_servers=total_servers, 
                          user_count=user_count,
                          recent_users=recent_users)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        # Проверяем пароль (2011)
        if password == '2011':
            session['admin_logged_in'] = True
            session['admin_id'] = 'system_admin'
            log_action(session['admin_id'], 'login', 'Администратор вошел в систему')
            return redirect(url_for('index'))
        else:
            return render_template('admin_login.html', error='Неверный пароль')
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    if session.get('admin_logged_in'):
        log_action(session.get('admin_id'), 'logout', 'Администратор вышел из системы')
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/20111102')  # Скрытая страница
def secret_page():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return redirect(url_for('full_control_panel'))

@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем статистику
    conn = get_db_connection()
    
    # Количество серверов
    total_servers = 1  # Главный сервер всегда есть
    
    # Количество пользователей (приблизительно)
    user_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    
    # Количество онлайн пользователей (приблизительно)
    recent_users = conn.execute('SELECT COUNT(*) as count FROM users WHERE last_daily_claim > ?', 
                               (datetime.now() - timedelta(days=1),)).fetchone()['count']
    
    # Количество сообщений (приблизительно)
    message_count = conn.execute('SELECT SUM(xp) as total_xp FROM users').fetchone()['total_xp'] or 0
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                          total_servers=total_servers, 
                          user_count=user_count,
                          recent_users=recent_users,
                          message_count=message_count)

@app.route('/government')
def government():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем структуру правительства из конфига
    gov_structure = config.get('government_structure', {})
    
    return render_template('government.html', government=gov_structure)

@app.route('/government/set_supreme_ruler', methods=['POST'])
def set_supreme_ruler():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = request.form['user_id']
    
    # Вызываем команду бота
    data = {'user_id': user_id}
    result = call_bot_api('/set_supreme_ruler', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        config['government_structure']['supreme_ruler'] = user_id
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'set_supreme_ruler', f'Установлен верховный правитель: {user_id}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/government/add_chancellor', methods=['POST'])
def add_chancellor():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = request.form['user_id']
    
    # Вызываем команду бота
    data = {'user_id': user_id}
    result = call_bot_api('/add_chancellor', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        if user_id not in config['government_structure']['chancellery']:
            config['government_structure']['chancellery'].append(user_id)
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'add_chancellor', f'Добавлен канцлер: {user_id}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/government/remove_chancellor', methods=['POST'])
def remove_chancellor():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = request.form['user_id']
    
    # Вызываем команду бота
    data = {'user_id': user_id}
    result = call_bot_api('/remove_chancellor', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        if user_id in config['government_structure']['chancellery']:
            config['government_structure']['chancellery'].remove(user_id)
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'remove_chancellor', f'Удален канцлер: {user_id}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/government/set_minister', methods=['POST'])
def set_minister():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    ministry = request.form['ministry']
    user_id = request.form['user_id']
    
    # Вызываем команду бота
    data = {'ministry': ministry, 'user_id': user_id}
    result = call_bot_api('/set_minister', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        config['government_structure']['ministries'][ministry] = user_id
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'set_minister', f'Назначен министр {ministry}: {user_id}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/government/remove_minister', methods=['POST'])
def remove_minister():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    ministry = request.form['ministry']
    
    # Вызываем команду бота
    data = {'ministry': ministry}
    result = call_bot_api('/remove_minister', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        if ministry in config['government_structure']['ministries']:
            del config['government_structure']['ministries'][ministry]
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'remove_minister', f'Удален министр ведомства: {ministry}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/advertising')
def advertising():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    ad_settings = {
        'enabled': config.get('advertising_enabled', False),
        'message': config.get('ad_message', 'Присоединяйся к Федерации Галактической Империи!'),
        'frequency': config.get('ad_frequency_hours', 6)
    }
    
    return render_template('advertising.html', ad_settings=ad_settings)

@app.route('/advertising/toggle', methods=['POST'])
def toggle_advertising():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    enabled = request.form.get('enabled') == 'true'
    
    # Вызываем команду бота
    if enabled:
        freq = int(request.form.get('frequency', 6))
        data = {'frequency_hours': freq}
        result = call_bot_api('/enable_ads', 'POST', data)
    else:
        result = call_bot_api('/disable_ads', 'POST')
    
    if result:
        # Обновляем конфиг локально
        config['advertising_enabled'] = enabled
        if enabled:
            config['ad_frequency_hours'] = int(request.form.get('frequency', 6))
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        action = 'enable_ads' if enabled else 'disable_ads'
        log_action(session['admin_id'], action, f'Реклама {"включена" if enabled else "выключена"}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/advertising/update_message', methods=['POST'])
def update_ad_message():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    message = request.form['message']
    
    # Вызываем команду бота
    data = {'message': message}
    result = call_bot_api('/set_ad_message', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        config['ad_message'] = message
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'update_ad_message', f'Обновлено рекламное сообщение: {message}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/settings')
def settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем текущие настройки
    conn = get_db_connection()
    settings = conn.execute('SELECT * FROM server_settings WHERE guild_id = ?', (1,)).fetchone()
    conn.close()
    
    if not settings:
        # Если настроек нет, используем значения из конфига
        settings = {
            'bot_status': 'online',
            'prefix': config.get('default_prefix', '!'),
            'welcome_message': 'Добро пожаловать в Галактическую Империю, солдат!',
            'auto_moderation': 1,
            'spam_threshold': config['spam_threshold']['message_count'],
            'max_warnings': config['max_warns_before_ban'],
            'daily_credits_min': config['daily_rewards']['min_credits'],
            'daily_credits_max': config['daily_rewards']['max_credits'],
            'salary_interval': 24,
            'advertising_enabled': config.get('advertising_enabled', 0),
            'ad_message': config.get('ad_message', ''),
            'ad_frequency': config.get('ad_frequency_hours', 6),
            'elections_enabled': 0,
            'legislation_enabled': 0,
            'election_cycle': 30
        }
    
    return render_template('settings.html', settings=settings)

@app.route('/settings/update', methods=['POST'])
def update_settings():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Получаем все настройки из формы
    bot_status = request.form.get('bot_status', 'online')
    prefix = request.form.get('prefix', '!')
    welcome_message = request.form.get('welcome_message', '')
    auto_moderation = request.form.get('auto_moderation') == 'on'
    spam_threshold = int(request.form.get('spam_threshold', 5))
    max_warnings = int(request.form.get('max_warnings', 5))
    daily_credits_min = int(request.form.get('daily_credits_min', 50))
    daily_credits_max = int(request.form.get('daily_credits_max', 150))
    salary_interval = int(request.form.get('salary_interval', 24))
    advertising_enabled = request.form.get('advertising_enabled') == 'on'
    ad_message = request.form.get('ad_message', '')
    ad_frequency = int(request.form.get('ad_frequency', 6))
    elections_enabled = request.form.get('elections_enabled') == 'on'
    legislation_enabled = request.form.get('legislation_enabled') == 'on'
    election_cycle = int(request.form.get('election_cycle', 30))
    
    # Обновляем настройки в базе данных
    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO server_settings 
        (guild_id, bot_status, prefix, welcome_message, auto_moderation, spam_threshold, max_warnings,
         daily_credits_min, daily_credits_max, salary_interval, advertising_enabled, ad_message, ad_frequency,
         elections_enabled, legislation_enabled, election_cycle)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (1, bot_status, prefix, welcome_message, auto_moderation, spam_threshold, max_warnings,
          daily_credits_min, daily_credits_max, salary_interval, advertising_enabled, ad_message, ad_frequency,
          elections_enabled, legislation_enabled, election_cycle))
    conn.commit()
    conn.close()
    
    # Обновляем конфиг локально
    config['default_prefix'] = prefix
    config['spam_threshold']['message_count'] = spam_threshold
    config['max_warns_before_ban'] = max_warnings
    config['daily_rewards']['min_credits'] = daily_credits_min
    config['daily_rewards']['max_credits'] = daily_credits_max
    config['advertising_enabled'] = advertising_enabled
    config['ad_message'] = ad_message
    config['ad_frequency_hours'] = ad_frequency
    
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    log_action(session['admin_id'], 'update_settings', 'Обновлены настройки бота')
    
    return jsonify({'success': True})

@app.route('/full_control')
def full_control_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем полную информацию
    conn = get_db_connection()
    
    # Информация о серверах
    servers = conn.execute('SELECT * FROM server_settings').fetchall()
    
    # Информация о правительстве
    government = config.get('government_structure', {})
    
    # Статистика пользователей
    user_stats = {
        'total': conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count'],
        'active_today': conn.execute('SELECT COUNT(*) as count FROM users WHERE last_daily_claim > ?', 
                                    (datetime.now() - timedelta(days=1),)).fetchone()['count'],
        'total_xp': conn.execute('SELECT SUM(xp) as total FROM users').fetchone()['total'] or 0,
        'total_credits': conn.execute('SELECT SUM(credits) as total FROM users').fetchone()['total'] or 0
    }
    
    # Последние действия
    recent_logs = conn.execute('SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT 10').fetchall()
    
    conn.close()
    
    return render_template('full_control.html', 
                          servers=servers, 
                          government=government, 
                          user_stats=user_stats,
                          recent_logs=recent_logs)

@app.route('/servers')
def servers_list():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем список серверов
    conn = get_db_connection()
    servers = conn.execute('SELECT * FROM server_settings ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('servers.html', servers=servers)

@app.route('/users')
def users_list():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем список пользователей
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY level DESC, xp DESC LIMIT 50').fetchall()
    conn.close()
    
    return render_template('users.html', users=users)

@app.route('/logs')
def logs():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем логи действий
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT 100').fetchall()
    conn.close()
    
    return render_template('logs.html', logs=logs)

# API эндпоинты для взаимодействия с ботом
@app.route('/api/government')
def api_government():
    return jsonify(config.get('government_structure', {}))

@app.route('/api/stats')
def api_stats():
    conn = get_db_connection()
    stats = {
        'total_users': conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count'],
        'active_users': conn.execute('SELECT COUNT(*) as count FROM users WHERE last_daily_claim > ?', 
                                    (datetime.now() - timedelta(days=1),)).fetchone()['count'],
        'total_servers': 1,  # условно
        'bot_uptime': 'Running',
        'advertising_active': config.get('advertising_enabled', False)
    }
    conn.close()
    return jsonify(stats)

# Инициализация базы данных при запуске приложения
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Используем другой порт для админ-панели
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import check_password_hash, generate_password_hash
import json
import sqlite3
import os
from datetime import datetime, timedelta
import discord
from discord.ext import commands
import asyncio
import threading
import requests
import time

app = Flask(__name__)
app.secret_key = 'galactic_empire_admin_secret_2011'  # Пароль 2011 для админ панели

# Загрузка конфигурации
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# URL для API бота (предполагаем, что бот запущен с API)
BOT_API_BASE_URL = 'http://localhost:8080'  # Порт для API бота

# Путь к базе данных
DATABASE = 'galactic_empire_bot.db'

def init_db():
    """Инициализация базы данных с дополнительными таблицами для веб-приложения"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Создание таблицы для настроек сервера
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER UNIQUE,
            bot_status TEXT DEFAULT 'online',
            prefix TEXT DEFAULT '!',
            welcome_message TEXT,
            auto_moderation BOOLEAN DEFAULT 1,
            spam_threshold INTEGER DEFAULT 5,
            max_warnings INTEGER DEFAULT 5,
            daily_credits_min INTEGER DEFAULT 50,
            daily_credits_max INTEGER DEFAULT 150,
            salary_interval INTEGER DEFAULT 24,
            advertising_enabled BOOLEAN DEFAULT 0,
            ad_message TEXT,
            ad_frequency INTEGER DEFAULT 6,
            elections_enabled BOOLEAN DEFAULT 0,
            legislation_enabled BOOLEAN DEFAULT 0,
            election_cycle INTEGER DEFAULT 30,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создание таблицы для правительства
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS government_structure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supreme_ruler TEXT,
            chancellery TEXT,
            ministries TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создание таблицы для логов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def log_action(user_id, action, details):
    """Логирование действий администратора"""
    conn = get_db_connection()
    conn.execute('INSERT INTO admin_logs (user_id, action, details) VALUES (?, ?, ?)',
                 (user_id, action, details))
    conn.commit()
    conn.close()

def call_bot_api(endpoint, method='GET', data=None):
    """Вызов API бота"""
    try:
        url = f"{BOT_API_BASE_URL}{endpoint}"
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        elif method == 'PUT':
            response = requests.put(url, json=data)
        elif method == 'DELETE':
            response = requests.delete(url)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            print(f"Ошибка API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка при вызове API: {e}")
        return None

@app.route('/')
def index():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем статистику
    conn = get_db_connection()
    
    # Количество серверов
    total_servers = 1  # Главный сервер всегда есть
    
    # Количество пользователей (приблизительно)
    user_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    
    # Количество онлайн пользователей (приблизительно)
    recent_users = conn.execute('SELECT COUNT(*) as count FROM users WHERE last_daily_claim > ?', 
                               (datetime.now() - timedelta(days=1),)).fetchone()['count']
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                          total_servers=total_servers, 
                          user_count=user_count,
                          recent_users=recent_users)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        # Проверяем пароль (2011)
        if password == '2011':
            session['admin_logged_in'] = True
            session['admin_id'] = 'system_admin'
            log_action(session['admin_id'], 'login', 'Администратор вошел в систему')
            return redirect(url_for('index'))
        else:
            return render_template('admin_login.html', error='Неверный пароль')
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    if session.get('admin_logged_in'):
        log_action(session.get('admin_id'), 'logout', 'Администратор вышел из системы')
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/20111102')  # Скрытая страница
def secret_page():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return redirect(url_for('full_control_panel'))

@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем статистику
    conn = get_db_connection()
    
    # Количество серверов
    total_servers = 1  # Главный сервер всегда есть
    
    # Количество пользователей (приблизительно)
    user_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    
    # Количество онлайн пользователей (приблизительно)
    recent_users = conn.execute('SELECT COUNT(*) as count FROM users WHERE last_daily_claim > ?', 
                               (datetime.now() - timedelta(days=1),)).fetchone()['count']
    
    # Количество сообщений (приблизительно)
    message_count = conn.execute('SELECT SUM(xp) as total_xp FROM users').fetchone()['total_xp'] or 0
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                          total_servers=total_servers, 
                          user_count=user_count,
                          recent_users=recent_users,
                          message_count=message_count)

@app.route('/government')
def government():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем структуру правительства из конфига
    gov_structure = config.get('government_structure', {})
    
    return render_template('government.html', government=gov_structure)

@app.route('/government/set_supreme_ruler', methods=['POST'])
def set_supreme_ruler():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = request.form['user_id']
    
    # Вызываем команду бота
    data = {'user_id': user_id}
    result = call_bot_api('/set_supreme_ruler', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        config['government_structure']['supreme_ruler'] = user_id
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'set_supreme_ruler', f'Установлен верховный правитель: {user_id}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/government/add_chancellor', methods=['POST'])
def add_chancellor():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = request.form['user_id']
    
    # Вызываем команду бота
    data = {'user_id': user_id}
    result = call_bot_api('/add_chancellor', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        if user_id not in config['government_structure']['chancellery']:
            config['government_structure']['chancellery'].append(user_id)
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'add_chancellor', f'Добавлен канцлер: {user_id}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/government/remove_chancellor', methods=['POST'])
def remove_chancellor():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = request.form['user_id']
    
    # Вызываем команду бота
    data = {'user_id': user_id}
    result = call_bot_api('/remove_chancellor', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        if user_id in config['government_structure']['chancellery']:
            config['government_structure']['chancellery'].remove(user_id)
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'remove_chancellor', f'Удален канцлер: {user_id}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/government/set_minister', methods=['POST'])
def set_minister():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    ministry = request.form['ministry']
    user_id = request.form['user_id']
    
    # Вызываем команду бота
    data = {'ministry': ministry, 'user_id': user_id}
    result = call_bot_api('/set_minister', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        config['government_structure']['ministries'][ministry] = user_id
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'set_minister', f'Назначен министр {ministry}: {user_id}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/government/remove_minister', methods=['POST'])
def remove_minister():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    ministry = request.form['ministry']
    
    # Вызываем команду бота
    data = {'ministry': ministry}
    result = call_bot_api('/remove_minister', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        if ministry in config['government_structure']['ministries']:
            del config['government_structure']['ministries'][ministry]
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'remove_minister', f'Удален министр ведомства: {ministry}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/advertising')
def advertising():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    ad_settings = {
        'enabled': config.get('advertising_enabled', False),
        'message': config.get('ad_message', 'Присоединяйся к Федерации Галактической Империи!'),
        'frequency': config.get('ad_frequency_hours', 6)
    }
    
    return render_template('advertising.html', ad_settings=ad_settings)

@app.route('/advertising/toggle', methods=['POST'])
def toggle_advertising():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    enabled = request.form.get('enabled') == 'true'
    
    # Вызываем команду бота
    if enabled:
        freq = int(request.form.get('frequency', 6))
        data = {'frequency_hours': freq}
        result = call_bot_api('/enable_ads', 'POST', data)
    else:
        result = call_bot_api('/disable_ads', 'POST')
    
    if result:
        # Обновляем конфиг локально
        config['advertising_enabled'] = enabled
        if enabled:
            config['ad_frequency_hours'] = int(request.form.get('frequency', 6))
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        action = 'enable_ads' if enabled else 'disable_ads'
        log_action(session['admin_id'], action, f'Реклама {"включена" if enabled else "выключена"}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/advertising/update_message', methods=['POST'])
def update_ad_message():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    message = request.form['message']
    
    # Вызываем команду бота
    data = {'message': message}
    result = call_bot_api('/set_ad_message', 'POST', data)
    
    if result:
        # Обновляем конфиг локально
        config['ad_message'] = message
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log_action(session['admin_id'], 'update_ad_message', f'Обновлено рекламное сообщение: {message}')
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update'}), 500

@app.route('/settings')
def settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем текущие настройки
    conn = get_db_connection()
    settings = conn.execute('SELECT * FROM server_settings WHERE guild_id = ?', (1,)).fetchone()
    conn.close()
    
    if not settings:
        # Если настроек нет, используем значения из конфига
        settings = {
            'bot_status': 'online',
            'prefix': config.get('default_prefix', '!'),
            'welcome_message': 'Добро пожаловать в Галактическую Империю, солдат!',
            'auto_moderation': 1,
            'spam_threshold': config['spam_threshold']['message_count'],
            'max_warnings': config['max_warns_before_ban'],
            'daily_credits_min': config['daily_rewards']['min_credits'],
            'daily_credits_max': config['daily_rewards']['max_credits'],
            'salary_interval': 24,
            'advertising_enabled': config.get('advertising_enabled', 0),
            'ad_message': config.get('ad_message', ''),
            'ad_frequency': config.get('ad_frequency_hours', 6),
            'elections_enabled': 0,
            'legislation_enabled': 0,
            'election_cycle': 30
        }
    
    return render_template('settings.html', settings=settings)

@app.route('/settings/update', methods=['POST'])
def update_settings():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Получаем все настройки из формы
    bot_status = request.form.get('bot_status', 'online')
    prefix = request.form.get('prefix', '!')
    welcome_message = request.form.get('welcome_message', '')
    auto_moderation = request.form.get('auto_moderation') == 'on'
    spam_threshold = int(request.form.get('spam_threshold', 5))
    max_warnings = int(request.form.get('max_warnings', 5))
    daily_credits_min = int(request.form.get('daily_credits_min', 50))
    daily_credits_max = int(request.form.get('daily_credits_max', 150))
    salary_interval = int(request.form.get('salary_interval', 24))
    advertising_enabled = request.form.get('advertising_enabled') == 'on'
    ad_message = request.form.get('ad_message', '')
    ad_frequency = int(request.form.get('ad_frequency', 6))
    elections_enabled = request.form.get('elections_enabled') == 'on'
    legislation_enabled = request.form.get('legislation_enabled') == 'on'
    election_cycle = int(request.form.get('election_cycle', 30))
    
    # Обновляем настройки в базе данных
    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO server_settings 
        (guild_id, bot_status, prefix, welcome_message, auto_moderation, spam_threshold, max_warnings,
         daily_credits_min, daily_credits_max, salary_interval, advertising_enabled, ad_message, ad_frequency,
         elections_enabled, legislation_enabled, election_cycle)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (1, bot_status, prefix, welcome_message, auto_moderation, spam_threshold, max_warnings,
          daily_credits_min, daily_credits_max, salary_interval, advertising_enabled, ad_message, ad_frequency,
          elections_enabled, legislation_enabled, election_cycle))
    conn.commit()
    conn.close()
    
    # Обновляем конфиг локально
    config['default_prefix'] = prefix
    config['spam_threshold']['message_count'] = spam_threshold
    config['max_warns_before_ban'] = max_warnings
    config['daily_rewards']['min_credits'] = daily_credits_min
    config['daily_rewards']['max_credits'] = daily_credits_max
    config['advertising_enabled'] = advertising_enabled
    config['ad_message'] = ad_message
    config['ad_frequency_hours'] = ad_frequency
    
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    log_action(session['admin_id'], 'update_settings', 'Обновлены настройки бота')
    
    return jsonify({'success': True})

@app.route('/full_control')
def full_control_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем полную информацию
    conn = get_db_connection()
    
    # Информация о серверах
    servers = conn.execute('SELECT * FROM server_settings').fetchall()
    
    # Информация о правительстве
    government = config.get('government_structure', {})
    
    # Статистика пользователей
    user_stats = {
        'total': conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count'],
        'active_today': conn.execute('SELECT COUNT(*) as count FROM users WHERE last_daily_claim > ?', 
                                    (datetime.now() - timedelta(days=1),)).fetchone()['count'],
        'total_xp': conn.execute('SELECT SUM(xp) as total FROM users').fetchone()['total'] or 0,
        'total_credits': conn.execute('SELECT SUM(credits) as total FROM users').fetchone()['total'] or 0
    }
    
    # Последние действия
    recent_logs = conn.execute('SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT 10').fetchall()
    
    conn.close()
    
    return render_template('full_control.html', 
                          servers=servers, 
                          government=government, 
                          user_stats=user_stats,
                          recent_logs=recent_logs)

@app.route('/servers')
def servers_list():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем список серверов
    conn = get_db_connection()
    servers = conn.execute('SELECT * FROM server_settings ORDER BY created_at DESC').fetchall()
    conn.close()
    
    return render_template('servers.html', servers=servers)

@app.route('/users')
def users_list():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем список пользователей
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY level DESC, xp DESC LIMIT 50').fetchall()
    conn.close()
    
    return render_template('users.html', users=users)

@app.route('/logs')
def logs():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Получаем логи действий
    conn = get_db_connection()
    logs = conn.execute('SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT 100').fetchall()
    conn.close()
    
    return render_template('logs.html', logs=logs)

# API эндпоинты для взаимодействия с ботом
@app.route('/api/government')
def api_government():
    return jsonify(config.get('government_structure', {}))

@app.route('/api/stats')
def api_stats():
    conn = get_db_connection()
    stats = {
        'total_users': conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count'],
        'active_users': conn.execute('SELECT COUNT(*) as count FROM users WHERE last_daily_claim > ?', 
                                    (datetime.now() - timedelta(days=1),)).fetchone()['count'],
        'total_servers': 1,  # условно
        'bot_uptime': 'Running',
        'advertising_active': config.get('advertising_enabled', False)
    }
    conn.close()
    return jsonify(stats)

# Инициализация базы данных при запуске приложения
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)  # Используем другой порт для админ-панели