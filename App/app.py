import asyncio
import struct
import threading
import time
from flask import Flask, render_template, redirect, url_for
from flask_socketio import SocketIO
from bleak import BleakClient, BleakScanner, BleakError

# Adresse BLE et UUID
DEVICE_ADDRESS = "58:BF:25:3B:FE:66"
ANGLE_CHAR_UUID = "4c5800c3-eca9-48ab-8d04-e1d02d7fe771"

app = Flask(__name__)
socketio = SocketIO(app, async_mode="eventlet")

# Stockage des données BLE
angle_data = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
data_lock = threading.Lock()
ble_connected = False  # Indicateur de connexion BLE

# Recherche du périphérique BLE
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

        # Envoi des données en direct au navigateur via WebSocket
        socketio.emit("update_angles", angle_data)

    except Exception as e:
        print(f"Erreur de lecture BLE : {e}")

# Connexion BLE avec reconnexion automatique
async def run_ble_client():
    global ble_connected
    while True:
        try:
            async with BleakClient(DEVICE_ADDRESS) as client:
                print(f"Connecté au périphérique BLE {DEVICE_ADDRESS}")
                ble_connected = True
                await client.start_notify(ANGLE_CHAR_UUID, notification_handler)

                while True:
                    await asyncio.sleep(1)

        except BleakError as e:
            print(f"Erreur de connexion BLE : {e}")
            ble_connected = False
            print("Reconnexion dans 1 secondes...")
            time.sleep(1)

#Lancement du client BLE dans un thread
def start_ble_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_ble_client())

ble_thread = threading.Thread(target=start_ble_loop, daemon=True)
ble_thread.start()

# Route principale de Flask
@app.route("/")
def index():
    return render_template("index.html")

# Page d'erreur si BLE non trouvé
# @app.route("/error")
# def error_page():
#     return render_template("error.html")

if __name__ == "__main__":
    socketio.run(app, debug=True)
