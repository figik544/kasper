from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import json
import sqlite3
import os
from datetime import datetime
import discord
from discord.ext import commands
import asyncio
import threading

app = Flask(__name__)
app.secret_key = 'galactic_empire_secret_key_2011'  # Пароль 2011 для админ панели

# Загрузка конфигурации
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Путь к базе данных
DATABASE = 'galactic_empire_bot.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/community_plan')
def community_plan():
    return render_template('community_plan.html')

@app.route('/servers')
def servers():
    return render_template('servers.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        # Проверяем пароль (2011)
        if password == '2011':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error='Неверный пароль')
    return render_template('admin_login.html')

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_panel.html')

@app.route('/admin/settings')
def admin_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_settings.html')

@app.route('/admin/servers')
def admin_servers():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    # Получаем список серверов из базы данных
    conn = get_db_connection()
    servers = conn.execute('SELECT * FROM guilds').fetchall()
    conn.close()
    return render_template('admin_servers.html', servers=servers)

@app.route('/join_federation', methods=['GET', 'POST'])
def join_federation():
    if request.method == 'POST':
        server_name = request.form['server_name']
        owner_nickname = request.form['owner_nickname']
        server_description = request.form['server_description']
        
        # Сохраняем заявку на вступление
        conn = get_db_connection()
        conn.execute('INSERT INTO federation_applications (server_name, owner_nickname, server_description, status, created_at) VALUES (?, ?, ?, ?, ?)',
                     (server_name, owner_nickname, server_description, 'pending', datetime.now()))
        conn.commit()
        conn.close()
        
        return redirect(url_for('federation_success'))
    return render_template('join_federation.html')

@app.route('/federation_success')
def federation_success():
    return render_template('federation_success.html')

@app.route('/api/user/<int:user_id>')
def api_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return jsonify(dict(user))
    else:
        return jsonify({'error': 'User not found'}), 404

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)