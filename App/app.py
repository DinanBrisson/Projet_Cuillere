import asyncio
import struct
import threading
import time
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, session, request, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_socketio import SocketIO
from bleak import BleakClient, BleakScanner, BleakError
from App.forms import LoginForm, RegistrationForm, ProfileUpdateForm
from App.models import User, db
from App.config import Config

# ========== CONFIGURATION DE L'APPLICATION FLASK ==========
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# ========== GESTION DES CONNEXIONS UTILISATEURS ==========
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== CONFIGURATION INTERFACE D'ADMINISTRATION ==========
class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Accès refusé ! Vous devez être administrateur.", "danger")
        return redirect(url_for('login'))

admin = Admin(app, name='Admin Panel', template_mode='bootstrap3')
admin.add_view(AdminModelView(User, db.session))

# ========== CONFIGURATION SOCKETIO POUR COMMUNICATION EN TEMPS RÉEL ==========
socketio = SocketIO(app, cors_allowed_origins="*")

# ========== CONFIGURATION DE LA COMMUNICATION BLUETOOTH (BLE) ==========
DEVICE_ADDRESS = "58:BF:25:3B:FE:66" # Adresse MAC du périphérique BLE
ANGLE_CHAR_UUID = "4c5800c3-eca9-48ab-8d04-e1d02d7fe771"  # UUID de la caractéristique BLE

angle_data = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
data_lock = threading.Lock()
ble_connected = False
last_send_time = 0

# Fonction de recherche asynchrone du périphérique BLE
async def find_device():
    global ble_connected
    print("Recherche du périphérique BLE...")
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Appareil trouvé : {device.name} - Adresse : {device.address}")
        if DEVICE_ADDRESS in device.address:
            ble_connected = True
            return device.address
    ble_connected = False
    return None

# Fonction appelée lors de la réception de nouvelles données BLE
def notification_handler(sender, data):
    global angle_data, last_send_time
    try:
        roll, pitch, yaw = struct.unpack("fff", data)
        with data_lock:
            angle_data["roll"] = round(roll, 2)
            angle_data["pitch"] = round(pitch, 2)
            angle_data["yaw"] = round(yaw, 2)
        print(f"Données reçues -> Roll: {roll}, Pitch: {pitch}, Yaw: {yaw}")

        current_time = time.time()
        if current_time - last_send_time > 0.2:
            socketio.emit("update_angles", angle_data)
            last_send_time = current_time
    except Exception as e:
        print(f"Erreur de lecture BLE : {e}")

# Fonction asynchrone principale qui gère la connexion BLE permanente
async def run_ble_client():
    global ble_connected
    while True:
        try:
            print(f"Tentative de connexion au périphérique BLE {DEVICE_ADDRESS}...")
            async with BleakClient(DEVICE_ADDRESS) as client:
                print(f"Connecté à {DEVICE_ADDRESS}")
                ble_connected = True
                await client.start_notify(ANGLE_CHAR_UUID, notification_handler)

                while client.is_connected:
                    await asyncio.sleep(1)
        except BleakError as e:
            print(f"Erreur connexion BLE : {e}")
            ble_connected = False
            print("Reconnexion dans 2 secondes...")
            await asyncio.sleep(2)

# Lancement du thread BLE pour gérer la connexion BLE en arrière-plan
def start_ble_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_ble_client())

ble_thread = threading.Thread(target=start_ble_loop, daemon=True)
ble_thread.start()

# ========== DÉFINITION DES ROUTES WEB DE L'APPLICATION ==========
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/status')
def status():
    return jsonify({"ble_connected": ble_connected})

@app.route('/connect_ble', methods=['POST'])
@login_required
def connect_ble():
    try:
        global ble_thread
        if not ble_thread.is_alive():
            ble_thread = threading.Thread(target=start_ble_loop, daemon=True)
            ble_thread.start()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Erreur connexion BLE manuelle : {e}")
        return jsonify({'success': False})


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('Cet email est déjà utilisé.', 'danger')
        else:
            birthdate = datetime.strptime(str(form.birthdate.data), "%Y-%m-%d").date()
            new_user = User(
                firstname=form.firstname.data,
                lastname=form.lastname.data,
                profession=form.profession.data,
                birthdate=birthdate,
                email=form.email.data,
                is_admin=False
            )
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash('Inscription réussie !', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Connexion réussie !', 'success')
            return redirect(url_for('index'))  # Redirigé vers index.html
        flash('Email ou mot de passe incorrect.', 'danger')
    return render_template('login.html', form=form)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileUpdateForm(obj=current_user)
    if form.validate_on_submit():
        current_user.firstname = form.firstname.data
        current_user.lastname = form.lastname.data
        current_user.profession = form.profession.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Profil mis à jour avec succès.', 'success')
        return redirect(url_for('index'))
    return render_template('profile.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('_flashes', None)
    flash('Déconnecté.', 'info')
    return redirect(url_for('login'))

# ========== MAIN ==========
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        email = "admin@gmail.com"
        password = "admin123"

        existing_admin = User.query.filter_by(email=email).first()
        if not existing_admin:
            admin_user = User(
                firstname="Admin",
                lastname="User",
                email=email,
                profession="Administrateur",
                birthdate=datetime.strptime("2000-01-01", "%Y-%m-%d").date(),
                is_admin=True
            )
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            print("Administrateur créé.")

    import eventlet
    eventlet.monkey_patch()

    socketio.run(app, debug=True, host='localhost', port=5000)
