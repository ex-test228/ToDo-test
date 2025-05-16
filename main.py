import os
from flask import Flask, redirect, render_template, request, jsonify, session, url_for
import sqlite3
import bcrypt # type: ignore

app = Flask(__name__)
app.secret_key = os.urandom(24)
DATABASE = 'todo.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, args)
    rv = cursor.fetchall()
    cursor.close()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, args)
    conn.commit()
    cursor.close()
    conn.close()

# @app.route('/')
# def index():
#     return render_template('index.html')

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/api/todos/get', methods=['GET'])
def get_todos():
    user_id = session['user_id']
    todos = query_db('SELECT task_id,task,complete,add_date FROM todos WHERE user_id = ?',(user_id,))
    return jsonify([dict(row) for row in todos])

@app.route('/api/todos/add', methods=['POST'])
def add_todo():
    data = request.get_json()
    user_id = session['user_id']
    task = data.get('task')
    date = data.get('date')
    if task:
        execute_db('INSERT INTO todos (task,user_id,add_date) VALUES (?,?,?)', (task,user_id,date))
        return jsonify({'message': 'TODO added successfully'}), 201
    return jsonify({'error': 'Task is required'}), 400

@app.route('/api/todos/delete', methods=['POST'])
def delete_todo():
    data = request.get_json()
    user_id = session['user_id']
    task_id = data.get('task_id')
    if task_id:
        execute_db('DELETE FROM todos WHERE task_id = ? AND user_id = ?',(task_id,user_id,))
        return jsonify({'message': 'TODO deleted successfully'}), 201
    return jsonify({'error': 'Task is required'}), 400

@app.route('/api/todos/complete', methods=['POST'])
def complete_todo():
    data = request.get_json()
    task_id = data.get('task_id')
    complete_date = data.get('complete_date')
    if task_id:
        execute_db('UPDATE todos SET complete =?,complete_date=? WHERE task_id = ?',(1,complete_date,task_id,))
        return jsonify({'message': 'TODO completed successfully'}), 201
    return jsonify({'error': 'Task is required'}), 400

@app.route('/api/todos/update', methods=['POST'])
def update_todo():
    data = request.get_json()
    task_id = data.get('task_id')
    task = data.get('task_name')
    if task_id:
        execute_db('UPDATE todos SET task =? WHERE task_id = ?',(task,task_id,))
        return jsonify({'message': 'TODO completed successfully'}), 201
    return jsonify({'error': 'Task is required'}), 400

@app.route('/api/users', methods=['GET'])
def get_users():
    users = query_db('SELECT task FROM users')
    return jsonify([dict(row) for row in users])

@app.route('/api/users', methods=['POST'])
def add_member():
    data = request.get_json()
    name = data.get('name')
    password = data.get('password')

    salt = bcrypt.gensalt()
    # パスワードをハッシュ化
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    if name and password:
        execute_db('INSERT INTO users (name) VALUES (?)', (name,))
    # ハッシュ値とソルトをデータベースに保存 (例: user テーブルの password_hash, salt カラム)
        try:
            execute_db('UPDATE users SET password_hash = ?, salt = ? WHERE name = ?', (hashed_password, salt.decode('utf-8'), name)) # user_id は仮の値
            return jsonify({'message': 'パスワードが安全に保存されました'}), 200
        except sqlite3.Error as e:
            return jsonify({'error': f'データベースエラー: {str(e)}'}), 500
        
def check_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

@app.route('/api/login', methods=['POST'])
def log_in():
    data = request.get_json()
    name = data.get('id')
    password = data.get('password')

    user = query_db('SELECT user_id, password_hash FROM users WHERE name = ?', (name,), one=True)

    if user and user['password_hash']:
        if check_password(password, user['password_hash']):
            session['user_id'] = user['user_id'] # セッションにユーザーIDを保存
            return jsonify({'message': 'ログイン成功'}), 200
        else:
            return jsonify({'message': 'パスワードが違います'}), 401
    else:
        return jsonify({'message': '存在しないIDです'}), 401
    
@app.route('/index')
def index():
    if 'user_id' in session:
        user_id = session['user_id']
        return render_template('index.html',user_id = user_id)
    return redirect(url_for('login'))

if __name__ == '__main__':
    # データベースの初期化 (初回起動時など)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            add_date DATE,
            complete_date DATE,
            complete INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        password_hash TEXT,
        salt TEXT
    );
''')
    conn.commit()
    conn.close()

    app.run(debug=True)