from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import json
import os
import sqlite3
from datetime import datetime
import discord
from discord.ext import commands

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_for_dev')

# Путь к базе данных
DB_PATH = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def is_authorized():
    """Проверка, является ли пользователь авторизованным (верховный правитель)"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Получаем ID верховного правителя из конфига
        supreme_ruler_id = config['government_structure']['supreme_ruler']
        
        # Проверяем, совпадает ли ID в сессии с ID верховного правителя
        user_id = session.get('user_id')
        return str(user_id) == supreme_ruler_id
    except:
        return False

@app.route('/')
def index():
    if not is_authorized():
        return redirect(url_for('login'))
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Получаем статистику из базы данных
        conn = get_db_connection()
        users_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_credits = conn.execute('SELECT SUM(credits) FROM users').fetchone()[0] or 0
        conn.close()
        
        return render_template('index.html', 
                             config=config, 
                             users_count=users_count, 
                             total_credits=total_credits)
    except Exception as e:
        return f"Ошибка: {str(e)}"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            supreme_ruler_id = config['government_structure']['supreme_ruler']
            
            if str(user_id) == supreme_ruler_id:
                session['user_id'] = user_id
                return redirect(url_for('index'))
            else:
                return render_template('admin_login.html', error="Неверный ID пользователя")
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/api/status')
def api_status():
    """API endpoint для получения статуса бота"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Получаем статистику из базы данных
        conn = get_db_connection()
        users_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        conn.close()
        
        status = {
            "status": "online",
            "version": "1.0",
            "supreme_ruler": config['government_structure']['supreme_ruler'],
            "advertising_enabled": config.get('advertising_enabled', False),
            "users_registered": users_count,
            "modules_loaded": [
                "moderation", "economy", "levels", "rpg", 
                "star_wars", "help", "government"
            ]
        }
    except Exception as e:
        status = {
            "status": "offline",
            "error": str(e)
        }
    
    return jsonify(status)

@app.route('/api/stats')
def api_stats():
    """API endpoint для получения статистики бота"""
    try:
        conn = get_db_connection()
        
        # Получаем статистику пользователей
        users_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_credits = conn.execute('SELECT SUM(credits) FROM users').fetchone()[0] or 0
        
        # Получаем топ пользователей по уровню
        top_users = conn.execute('SELECT id, level, xp, credits FROM users ORDER BY level DESC, xp DESC LIMIT 10').fetchall()
        
        conn.close()
        
        stats = {
            "servers": 1,  # Placeholder - в реальной системе это будет подсчитываться
            "users": users_count,
            "total_credits": total_credits,
            "top_users": [{"id": u["id"], "level": u["level"], "xp": u["xp"], "credits": u["credits"]} for u in top_users]
        }
    except Exception as e:
        stats = {
            "error": str(e)
        }
    
    return jsonify(stats)

@app.route('/dashboard')
def dashboard():
    if not is_authorized():
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        
        # Получаем статистику
        users_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_credits = conn.execute('SELECT SUM(credits) FROM users').fetchone()[0] or 0
        
        # Получаем топ пользователей
        top_users = conn.execute('SELECT id, level, xp, credits FROM users ORDER BY level DESC, xp DESC LIMIT 10').fetchall()
        
        # Получаем последние действия (предупреждения)
        warnings = conn.execute('SELECT * FROM warnings ORDER BY date DESC LIMIT 10').fetchall()
        
        conn.close()
        
        return render_template('admin_dashboard.html',
                             users_count=users_count,
                             total_credits=total_credits,
                             top_users=top_users,
                             warnings=warnings)
    except Exception as e:
        return f"Ошибка: {str(e)}"

@app.route('/users')
def users():
    if not is_authorized():
        return redirect(url_for('login'))
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page
        
        conn = get_db_connection()
        
        # Получаем пользователей с пагинацией
        users = conn.execute('SELECT * FROM users ORDER BY level DESC, xp DESC LIMIT ? OFFSET ?', 
                           (per_page, offset)).fetchall()
        
        # Получаем общее количество пользователей
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        
        conn.close()
        
        total_pages = (total_users + per_page - 1) // per_page
        
        return render_template('admin_users.html',
                             users=users,
                             page=page,
                             total_pages=total_pages,
                             total_users=total_users)
    except Exception as e:
        return f"Ошибка: {str(e)}"

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not is_authorized():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Получаем новые настройки из формы
            new_config = {
                "default_prefix": request.form.get('prefix', '!'),
                "max_warns_before_ban": int(request.form.get('max_warns', 5)),
                "xp_rewards": {
                    "message_range_min": int(request.form.get('xp_min', 15)),
                    "message_range_max": int(request.form.get('xp_max', 25)),
                    "command_bonus": int(request.form.get('command_bonus', 10))
                },
                "daily_rewards": {
                    "min_credits": int(request.form.get('daily_min', 50)),
                    "max_credits": int(request.form.get('daily_max', 150))
                },
                "advertising_enabled": 'advertising_enabled' in request.form,
                "ad_message": request.form.get('ad_message', 'Присоединяйся к Федерации Галактической Империи!'),
                "ad_frequency_hours": int(request.form.get('ad_frequency', 6))
            }
            
            # Сохраняем настройки в config.json
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            
            return redirect(url_for('settings'))
        except Exception as e:
            return f"Ошибка сохранения настроек: {str(e)}"
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return render_template('admin_settings.html', config=config)
    except Exception as e:
        return f"Ошибка: {str(e)}"

@app.route('/government', methods=['GET', 'POST'])
def government():
    if not is_authorized():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if action == 'set_supreme_ruler':
                new_supreme_ruler = request.form.get('supreme_ruler_id')
                config['government_structure']['supreme_ruler'] = new_supreme_ruler
            
            elif action == 'add_chancellor':
                chancellor_id = request.form.get('chancellor_id')
                chancellors = config['government_structure']['chancellery']
                if chancellor_id not in chancellors:
                    chancellors.append(chancellor_id)
            
            elif action == 'remove_chancellor':
                chancellor_id = request.form.get('chancellor_id')
                chancellors = config['government_structure']['chancellery']
                if chancellor_id in chancellors:
                    chancellors.remove(chancellor_id)
            
            elif action == 'set_minister':
                ministry = request.form.get('ministry')
                minister_id = request.form.get('minister_id')
                config['government_structure']['ministries'][ministry] = minister_id
            
            elif action == 'remove_minister':
                ministry = request.form.get('ministry')
                ministries = config['government_structure']['ministries']
                if ministry in ministries:
                    del ministries[ministry]
            
            # Сохраняем изменения
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return redirect(url_for('government'))
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return render_template('government.html', config=config)
    except Exception as e:
        return f"Ошибка: {str(e)}"

@app.route('/advertising', methods=['GET', 'POST'])
def advertising():
    if not is_authorized():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            config['advertising_enabled'] = 'advertising_enabled' in request.form
            config['ad_message'] = request.form.get('ad_message', config['ad_message'])
            config['ad_frequency_hours'] = int(request.form.get('ad_frequency', config['ad_frequency_hours']))
            
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return redirect(url_for('advertising'))
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return render_template('advertising.html', config=config)
    except Exception as e:
        return f"Ошибка: {str(e)}"

@app.route('/moderate', methods=['GET', 'POST'])
def moderate():
    if not is_authorized():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            user_id = request.form.get('user_id')
            
            conn = get_db_connection()
            
            if action == 'ban':
                # В реальной системе здесь будет вызов Discord API для бана
                pass
            elif action == 'clear_warnings':
                conn.execute('DELETE FROM warnings WHERE user_id = ?', (user_id,))
                conn.commit()
            
            conn.close()
            return redirect(url_for('moderate'))
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    try:
        conn = get_db_connection()
        warnings = conn.execute('SELECT * FROM warnings ORDER BY date DESC').fetchall()
        conn.close()
        
        return render_template('admin_moderate.html', warnings=warnings)
    except Exception as e:
        return f"Ошибка: {str(e)}"

if __name__ == '__main__':
    # Получаем порт из переменной окружения или используем 5000 по умолчанию
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)