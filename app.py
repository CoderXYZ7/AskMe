from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import hashlib
import os
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Database setup
DATABASE = 'askme.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_locked BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Requests table (now acts as chat conversations)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            username TEXT NOT NULL,
            user_ip TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            tags TEXT,
            is_blocked BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')
    
    # Messages table for chat functionality
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            sender_type TEXT NOT NULL, -- 'user' or 'admin'
            sender_name TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES requests (id)
        )
    ''')
    
    # User preferences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_ip TEXT NOT NULL UNIQUE,
            custom_nickname TEXT,
            language TEXT DEFAULT 'en',
            theme TEXT DEFAULT 'light',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_username_from_ip(ip):
    """Generate a consistent username from IP address"""
    hash_object = hashlib.md5(ip.encode())
    return f"user_{hash_object.hexdigest()[:8]}"

def get_user_preferences(ip):
    """Get user preferences or create default ones"""
    conn = get_db()
    prefs = conn.execute('SELECT * FROM user_preferences WHERE user_ip = ?', (ip,)).fetchone()
    
    if not prefs:
        # Create default preferences
        conn.execute('''
            INSERT INTO user_preferences (user_ip, language, theme) 
            VALUES (?, ?, ?)
        ''', (ip, 'en', 'light'))
        conn.commit()
        prefs = conn.execute('SELECT * FROM user_preferences WHERE user_ip = ?', (ip,)).fetchone()
    
    conn.close()
    return prefs

def get_display_name(ip):
    """Get user's display name (custom nickname or auto-generated)"""
    prefs = get_user_preferences(ip)
    if prefs['custom_nickname']:
        return prefs['custom_nickname']
    return get_username_from_ip(ip)

def update_user_preferences(ip, **kwargs):
    """Update user preferences"""
    conn = get_db()
    
    # Ensure user preferences exist
    get_user_preferences(ip)
    
    updates = []
    values = []
    
    for key, value in kwargs.items():
        if key in ['custom_nickname', 'language', 'theme']:
            updates.append(f"{key} = ?")
            values.append(value)
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(ip)
        
        query = f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_ip = ?"
        conn.execute(query, values)
        conn.commit()
    
    conn.close()

# Admin credentials (hardcoded)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # Change this in production

@app.context_processor
def utility_processor():
    return dict(get_username_from_ip=get_username_from_ip)

@app.route('/')
def index():
    user_ip = request.remote_addr
    user_prefs = get_user_preferences(user_ip)
    
    conn = get_db()
    projects = conn.execute('SELECT * FROM projects WHERE is_locked = 0').fetchall()
    conn.close()
    
    return render_template('index.html', projects=projects, user_prefs=user_prefs)

@app.route('/preferences', methods=['POST'])
def update_preferences():
    user_ip = request.remote_addr
    
    # For admin users, use 'admin' as identifier
    if session.get('admin'):
        user_ip = 'admin'
    
    # Get form data
    nickname = request.form.get('nickname', '').strip()
    language = request.form.get('language', 'en')
    theme = request.form.get('theme', 'light')
    
    # Update preferences
    update_user_preferences(user_ip, 
                          custom_nickname=nickname if nickname else None,
                          language=language,
                          theme=theme)
    
    flash('Preferences updated successfully!')
    return redirect(request.referrer or url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # Get admin preferences
    user_prefs = get_user_preferences('admin')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials')
    
    return render_template('admin_login.html', user_prefs=user_prefs)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    # Get admin preferences (using 'admin' as IP)
    user_prefs = get_user_preferences('admin')
    
    conn = get_db()
    projects = conn.execute('SELECT * FROM projects').fetchall()
    
    # Group requests by project with their messages
    projects_with_requests = []
    for project in projects:
        requests = conn.execute('''
            SELECT * FROM requests 
            WHERE project_id = ? 
            ORDER BY created_at DESC
        ''', (project['id'],)).fetchall()
        
        requests_with_messages = []
        for req in requests:
            messages = conn.execute('''
                SELECT * FROM messages 
                WHERE request_id = ? 
                ORDER BY created_at ASC
            ''', (req['id'],)).fetchall()
            requests_with_messages.append({
                'request': req,
                'messages': messages
            })
        
        projects_with_requests.append({
            'project': project,
            'requests_with_messages': requests_with_messages
        })
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         projects_with_requests=projects_with_requests,
                         user_prefs=user_prefs)

@app.route('/admin/project/create', methods=['POST'])
def create_project():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    name = request.form['name']
    description = request.form['description']
    
    conn = get_db()
    try:
        conn.execute('INSERT INTO projects (name, description) VALUES (?, ?)', 
                    (name, description))
        conn.commit()
        flash('Project created successfully')
    except sqlite3.IntegrityError:
        flash('Project name already exists')
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/project/<int:project_id>/toggle_lock', methods=['POST'])
def toggle_project_lock(project_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    new_status = 0 if project['is_locked'] else 1
    
    conn.execute('UPDATE projects SET is_locked = ? WHERE id = ?', (new_status, project_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/project/<int:project_id>/edit', methods=['POST'])
def edit_project(project_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    name = request.form['name']
    description = request.form['description']
    
    conn = get_db()
    try:
        conn.execute('UPDATE projects SET name = ?, description = ? WHERE id = ?', 
                    (name, description, project_id))
        conn.commit()
        flash('Project updated successfully')
    except sqlite3.IntegrityError:
        flash('Project name already exists')
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    # Delete messages first, then requests, then project
    conn.execute('DELETE FROM messages WHERE request_id IN (SELECT id FROM requests WHERE project_id = ?)', (project_id,))
    conn.execute('DELETE FROM requests WHERE project_id = ?', (project_id,))
    conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()
    
    flash('Project deleted successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/request/<int:request_id>/update', methods=['POST'])
def update_request(request_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    status = request.form.get('status')
    tags = request.form.get('tags')
    is_blocked = 1 if request.form.get('is_blocked') else 0
    
    conn = get_db()
    conn.execute('''
        UPDATE requests 
        SET status = ?, tags = ?, is_blocked = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (status, tags, is_blocked, request_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/request/<int:request_id>/delete', methods=['POST'])
def delete_request(request_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    # Delete messages first, then request
    conn.execute('DELETE FROM messages WHERE request_id = ?', (request_id,))
    conn.execute('DELETE FROM requests WHERE id = ?', (request_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/request/<int:request_id>/message', methods=['POST'])
def add_message(request_id):
    user_ip = request.remote_addr
    display_name = get_display_name(user_ip)
    message_text = request.form['message']
    
    # Check if request exists and user has access
    conn = get_db()
    req = conn.execute('SELECT * FROM requests WHERE id = ? AND user_ip = ? AND is_blocked = 0', 
                      (request_id, user_ip)).fetchone()
    
    if not req:
        flash('Request not found or access denied')
        return redirect(url_for('index'))
    
    # Add message
    conn.execute('''
        INSERT INTO messages (request_id, sender_type, sender_name, message) 
        VALUES (?, ?, ?, ?)
    ''', (request_id, 'user', display_name, message_text))
    conn.commit()
    conn.close()
    
    return redirect(url_for('project_detail', project_id=req['project_id']))

@app.route('/admin/request/<int:request_id>/message', methods=['POST'])
def admin_add_message(request_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    message_text = request.form['message']
    
    conn = get_db()
    conn.execute('''
        INSERT INTO messages (request_id, sender_type, sender_name, message) 
        VALUES (?, ?, ?, ?)
    ''', (request_id, 'admin', 'Admin', message_text))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    user_ip = request.remote_addr
    user_prefs = get_user_preferences(user_ip)
    display_name = get_display_name(user_ip)
    
    conn = get_db()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND is_locked = 0', 
                          (project_id,)).fetchone()
    
    if not project:
        flash('Project not found or locked')
        return redirect(url_for('index'))
    
    # Get user requests with their messages
    user_requests = conn.execute('''
        SELECT * FROM requests 
        WHERE project_id = ? AND user_ip = ? AND is_blocked = 0
        ORDER BY created_at DESC
    ''', (project_id, user_ip)).fetchall()
    
    # Get messages for each request
    requests_with_messages = []
    for req in user_requests:
        messages = conn.execute('''
            SELECT * FROM messages 
            WHERE request_id = ? 
            ORDER BY created_at ASC
        ''', (req['id'],)).fetchall()
        requests_with_messages.append({
            'request': req,
            'messages': messages
        })
    
    conn.close()
    
    return render_template('project_detail.html', project=project, 
                         requests_with_messages=requests_with_messages, 
                         username=display_name, user_prefs=user_prefs)

@app.route('/project/<int:project_id>/request', methods=['POST'])
def create_request(project_id):
    user_ip = request.remote_addr
    display_name = get_display_name(user_ip)
    
    conn = get_db()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND is_locked = 0', 
                          (project_id,)).fetchone()
    
    if not project:
        flash('Project not found or locked')
        return redirect(url_for('index'))
    
    title = request.form['title']
    description = request.form['description']
    
    # Create the request
    cursor = conn.execute('''
        INSERT INTO requests (project_id, username, user_ip, title, description) 
        VALUES (?, ?, ?, ?, ?)
    ''', (project_id, display_name, user_ip, title, description))
    request_id = cursor.lastrowid
    
    # Add initial message with the description
    if description:
        conn.execute('''
            INSERT INTO messages (request_id, sender_type, sender_name, message) 
            VALUES (?, ?, ?, ?)
        ''', (request_id, 'user', display_name, description))
    
    conn.commit()
    conn.close()
    
    flash('Request submitted successfully')
    return redirect(url_for('project_detail', project_id=project_id))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
