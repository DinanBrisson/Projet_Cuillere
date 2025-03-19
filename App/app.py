import asyncio
import struct
import threading
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from bleak import BleakClient, BleakScanner, BleakError

# Adresse BLE et UUID
DEVICE_ADDRESS = "58:BF:25:3B:FE:66"
ANGLE_CHAR_UUID = "4c5800c3-eca9-48ab-8d04-e1d02d7fe771"

app = Flask(__name__)
socketio = SocketIO(app, async_mode="eventlet")  # Optionnel : peut être changé en 'gevent' ou 'threading' si besoin

# Stockage des données BLE
angle_data = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
data_lock = threading.Lock()
ble_connected = False  # Indicateur de connexion BLE

# Recherche du périphérique BLE (non utilisé directement, mais conservé si besoin d'auto-scan)
async def find_device():
    global ble_connected
    print("Recherche du périphérique BLE...")
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Appareil trouvé : {device.name} - Adresse : {device.address}")
        if DEVICE_ADDRESS in device.address:
            print(f"Périphérique détecté : {device.name} - {device.address}")
            ble_connected = True
            return device.address
    print("Aucun périphérique BLE trouvé.")
    ble_connected = False
    return None

# Gestion des notifications BLE
def notification_handler(sender, data):
    global angle_data
    try:
        roll, pitch, yaw = struct.unpack("fff", data)
        with data_lock:
            angle_data["roll"] = round(roll, 2)
            angle_data["pitch"] = round(pitch, 2)
            angle_data["yaw"] = round(yaw, 2)
        print(f"Données reçues -> Roll: {roll}, Pitch: {pitch}, Yaw: {yaw}")

        # Envoi des données en temps réel au navigateur via WebSocket
        socketio.emit("update_angles", angle_data)

    except Exception as e:
        print(f"Erreur de lecture BLE : {e}")

# Connexion BLE avec reconnexion automatique
async def run_ble_client():
    global ble_connected
    while True:
        try:
            print(f"Tentative de connexion au périphérique BLE {DEVICE_ADDRESS}...")
            async with BleakClient(DEVICE_ADDRESS) as client:
                print(f"Connecté au périphérique BLE {DEVICE_ADDRESS}")
                ble_connected = True
                await client.start_notify(ANGLE_CHAR_UUID, notification_handler)

                # Reste connecté tant que le périphérique est disponible
                while client.is_connected:
                    await asyncio.sleep(1)

        except BleakError as e:
            print(f"Erreur de connexion BLE : {e}")
            ble_connected = False
            print("Reconnexion dans 2 secondes...")
            await asyncio.sleep(2)  # IMPORTANT : Remplacé time.sleep par asyncio.sleep pour éviter les blocages

# Lancement du client BLE dans un thread séparé
def start_ble_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_ble_client())

# Démarrage du thread BLE
ble_thread = threading.Thread(target=start_ble_loop, daemon=True)
ble_thread.start()

# Route principale Flask
@app.route("/")
def index():
    return render_template("index.html")  # Assurez-vous que index.html existe

# Route pour vérifier l'état de la connexion BLE
@app.route("/status")
def status():
    return jsonify({"ble_connected": ble_connected})

# Démarrage du serveur Flask + WebSocket
if __name__ == "__main__":
    socketio.run(app, debug=True, host='localhost', port=5000)  # Optionnel : ouvert sur le réseau local
