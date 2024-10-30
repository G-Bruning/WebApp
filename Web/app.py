import os
import sqlite3
import random
import string

from flask import Flask, jsonify, request, redirect, url_for, session, render_template
from flask_cors import CORS
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.github import make_github_blueprint, github
from email_sender import send


app = Flask(__name__, template_folder='templates')

DATABASE = 'Banco.db'

CORS(app)
app.secret_key = os.urandom(24)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"


google_bp = make_google_blueprint(
    client_id="725105872028-9hhv8k9615mdimg6f9vii4ucspk2ok3g.apps.googleusercontent.com",
    client_secret="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",
    reprompt_consent=True,
    scope=["profile", "email"],
    redirect_to="authorized_google"
)
app.register_blueprint(google_bp, url_prefix="/login")

github_bp = make_github_blueprint(
    client_id="Ov23liw42uHEj8MF4c73",
    client_secret="8f57bc6368ec14684f9dd91cb7c965776c587ea7",
    redirect_to="authorized_github",
    scope="user:email"
)
app.register_blueprint(github_bp, url_prefix="/login")

def get_connection():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_connection()
        with app.open_resource('bd.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.route('/')
def serve():
    return render_template('index.html')

@app.route('/init_db')
def init_database():
    init_db()
    return 'Banco de dados inicializado', 200


@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/block_user')
def block_user_page():
    return render_template('block_user.html')

@app.route('/forgot_password')
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/usuarios', methods=['GET'])
def get_users():
    try:
        db = get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM Usuarios")
        rows = cursor.fetchall()
        rows = [dict(row) for row in rows]
        
        return jsonify(rows)
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/usuarios', methods=['GET'])
def api_get_users():
    try:
        db = get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT id, email FROM Usuarios")
        rows = cursor.fetchall()
        users = [{'id': row['id'], 'email': row['email']} for row in rows]
        
        return jsonify(users)
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/usuarios/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        db = get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT id, email, nome, status, data_criacao, data_ultima_atualizacao FROM Usuarios WHERE id=?", (user_id,)) 
        row = cursor.fetchone()
        if row:
            row = dict(row)
            return jsonify(row)
        else:
            return jsonify({'error': 'User not found'}), 404
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/login', methods=['POST'])
def login():
    
    email = request.form.get('email')
    senha = request.form.get('senha')
    
    if not email or not senha:
        return jsonify({'error': 'Email e senha são obrigatórios'}), 400
    
    try:
        db = get_connection()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM Usuarios WHERE email=?", (email,))
        user = cursor.fetchone()

        if user is None:
            return jsonify({'error': 'Email ou senha inválidos'}), 400
        
        if user['status'] == 'bloqueado':
            return jsonify({'error': 'Usário bloqueado'}), 400

        if senha == user['senha']:
           return redirect(url_for('dashboard'))
        
        else:
            return jsonify({'error': 'Email ou senha inválidos'}), 400
        
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/login/google')
def login_google():
    if google.authorized:
        return redirect(url_for('authorized_google'))
    return redirect(url_for('google.login'))

@app.route('/api/login/google/authorized')
def authorized_google():
    
    if not google.authorized:
        return redirect(url_for('google.login'))

    response = google.get("/oauth2/v2/userinfo")
    if not response.ok:
        return 'Falha ao obter o perfil do usuário', 400
    
    user_info = response.json()
    email = user_info.get('email')
    nome = user_info.get('name', 'Usuário')

    try:
        db = get_connection()
        cursor = db.cursor()
        
        cursor.execute("SELECT * FROM Usuarios WHERE email=?", (email,))
        user = cursor.fetchone()
        
        if user is None:
            cursor.execute("INSERT INTO Usuarios (email, nome, status) VALUES (?, ?, ?)", (email, nome, 'ativo'))
            db.commit()
            user_id = cursor.lastrowid
        else:
            user_id = user['id']
        
        session['user_id'] = user_id
        session['email'] = email        
        return redirect(url_for('dashboard'))
    
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()
    


@app.route('/api/login/github')
def login_github():
    if github.authorized:
        return redirect(url_for('authorized_github'))
    return redirect(url_for('github.login'))

@app.route('/api/login/github/authorized')
def authorized_github():
    
    if not github.authorized:
        return redirect(url_for('github.login'))

    response = github.get("/user")
    if not response.ok:
        return 'Falha ao obter o perfil do usuário', 400
    
    user_info = response.json()
    email = user_info.get('email')
    nome = user_info.get('name', 'Usuário')
    
    if email is None:
        email_response = github.get("/user/emails")
        if email_response.ok:
            emails = email_response.json()
           
            email = next((item["email"] for item in emails if item["primary"] and item["verified"]), None)

    if email is None:
        return 'Não foi possível obter o email do usuário', 400

    try:
        db = get_connection()
        cursor = db.cursor()
        
        cursor.execute("SELECT * FROM Usuarios WHERE email=?", (email,))
        user = cursor.fetchone()
        
        if user is None:
            cursor.execute("INSERT INTO Usuarios (email, nome, status) VALUES (?, ?, ?)", (email, nome, 'ativo'))
            db.commit()
            user_id = cursor.lastrowid
        else:
            user_id = user['id']
        
        session['user_id'] = user_id
        session['email'] = email
        return redirect(url_for('dashboard'))

    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        db.close()


@app.route('/signup', methods=['POST'])
def signup():
    
    email = request.form.get('email')
    senha = request.form.get('senha')
    nome = request.form.get('nome')    
    
    
    if  not email or not senha or not nome:
        return jsonify({'error': 'Email, senha e nome são obrigatórios'}), 400

    try:
        db = get_connection()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM Usuarios WHERE email=?", (email,))
        user = cursor.fetchone()

        if user is not None:
            return jsonify({'error': 'Email ja esta Cadastrado!'}), 400

        cursor.execute("INSERT INTO Usuarios (email, senha, nome) VALUES (?, ?, ?)", (email, senha, nome))
        db.commit()

        return redirect(url_for('signup_page', success=True))

    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/users/<int:user_id>/block', methods=['PUT'])
def block_user(user_id):
    try:
        db = get_connection()
        cursor = db.cursor()

        cursor.execute("UPDATE Usuarios SET status='bloqueado', data_ultima_atualizacao=CURRENT_TIMESTAMP WHERE id=?", (user_id,))
        db.commit()

        return jsonify({'message': 'Usário bloqueado com sucesso'}), 200

    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    
    email = request.form.get('email')

    if not email:
        return jsonify({'error': 'Email obrigatório'}), 400

    try:
        db = get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM Usuarios WHERE email=?", (email,))
        user = cursor.fetchone()

        if user is None:
            return jsonify({'message': 'Se este email estiver cadastrado, uma nova senha será enviada.'}), 200
        
        nova_senha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        cursor.execute("UPDATE Usuarios SET senha=?, data_ultima_atualizacao=CURRENT_TIMESTAMP WHERE email=?", (nova_senha, email))
        db.commit()

        send(email, nova_senha)
        return redirect(url_for('forgot_password', success=True))
        
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()



if __name__ == '__main__':
    app.run(debug=True)
