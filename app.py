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
    
    # Requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            username TEXT NOT NULL,
            user_ip TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            admin_response TEXT,
            tags TEXT,
            is_blocked BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
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

# Admin credentials (hardcoded)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # Change this in production

@app.route('/')
def index():
    conn = get_db()
    projects = conn.execute('SELECT * FROM projects WHERE is_locked = 0').fetchall()
    conn.close()
    return render_template('index.html', projects=projects)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    projects = conn.execute('SELECT * FROM projects').fetchall()
    requests = conn.execute('''
        SELECT r.*, p.name as project_name 
        FROM requests r 
        JOIN projects p ON r.project_id = p.id 
        ORDER BY r.created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin_dashboard.html', projects=projects, requests=requests)

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

@app.route('/admin/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
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
    response = request.form.get('response')
    tags = request.form.get('tags')
    is_blocked = 1 if request.form.get('is_blocked') else 0
    
    conn = get_db()
    conn.execute('''
        UPDATE requests 
        SET status = ?, admin_response = ?, tags = ?, is_blocked = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (status, response, tags, is_blocked, request_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/request/<int:request_id>/delete', methods=['POST'])
def delete_request(request_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db()
    conn.execute('DELETE FROM requests WHERE id = ?', (request_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    conn = get_db()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND is_locked = 0', 
                          (project_id,)).fetchone()
    
    if not project:
        flash('Project not found or locked')
        return redirect(url_for('index'))
    
    user_ip = request.remote_addr
    username = get_username_from_ip(user_ip)
    
    user_requests = conn.execute('''
        SELECT * FROM requests 
        WHERE project_id = ? AND user_ip = ? AND is_blocked = 0
        ORDER BY created_at DESC
    ''', (project_id, user_ip)).fetchall()
    
    conn.close()
    
    return render_template('project_detail.html', project=project, 
                         user_requests=user_requests, username=username)

@app.route('/project/<int:project_id>/request', methods=['POST'])
def create_request(project_id):
    conn = get_db()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND is_locked = 0', 
                          (project_id,)).fetchone()
    
    if not project:
        flash('Project not found or locked')
        return redirect(url_for('index'))
    
    title = request.form['title']
    description = request.form['description']
    user_ip = request.remote_addr
    username = get_username_from_ip(user_ip)
    
    conn.execute('''
        INSERT INTO requests (project_id, username, user_ip, title, description) 
        VALUES (?, ?, ?, ?, ?)
    ''', (project_id, username, user_ip, title, description))
    conn.commit()
    conn.close()
    
    flash('Request submitted successfully')
    return redirect(url_for('project_detail', project_id=project_id))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
