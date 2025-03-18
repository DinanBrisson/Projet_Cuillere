import asyncio
import struct
import threading
from flask import Flask, render_template_string
from bleak import BleakClient

# Adresse BLE de votre Nano RP2040
DEVICE_ADDRESS = "58:BF:25:3B:FE:66"
# UUID de la caractéristique utilisée côté Arduino
ANGLE_CHAR_UUID = "4c5800c3-eca9-48ab-8d04-e1d02d7fe771"

app = Flask(__name__)

# Données partagées entre BLE et Flask
angle_data = {
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0
}
data_lock = threading.Lock()  # Pour protéger l'accès concurrent

# Fonction appelée à chaque notification BLE reçue
def notification_handler(sender, data):
    global angle_data
    roll, pitch, yaw = struct.unpack('fff', data)
    with data_lock:
        angle_data["roll"] = round(roll, 2)
        angle_data["pitch"] = round(pitch, 2)
        angle_data["yaw"] = round(yaw, 2)
    print(f"Notification reçue -> Roll: {roll}, Pitch: {pitch}, Yaw: {yaw}")

# Boucle BLE
async def run_ble_client():
    async with BleakClient(DEVICE_ADDRESS) as client:
        print("Connecté au périphérique BLE")
        await client.start_notify(ANGLE_CHAR_UUID, notification_handler)
        while True:
            await asyncio.sleep(1)  # Maintenir la connexion active

# Lancement du client BLE dans un thread séparé
def start_ble_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_ble_client())

ble_thread = threading.Thread(target=start_ble_loop, daemon=True)
ble_thread.start()

# Route Flask
@app.route("/")
def index():
    with data_lock:
        roll = angle_data["roll"]
        pitch = angle_data["pitch"]
        yaw = angle_data["yaw"]

    html = """
    <html>
      <head>
        <meta http-equiv="refresh" content="2"> <!-- Refresh toutes les 2 sec -->
      </head>
      <body>
        <h1>Angles du Nano RP2040</h1>
        <p><strong>Roll :</strong> {{ roll }}°</p>
        <p><strong>Pitch :</strong> {{ pitch }}°</p>
        <p><strong>Yaw :</strong> {{ yaw }}°</p>
      </body>
    </html>
    """
    return render_template_string(html, roll=roll, pitch=pitch, yaw=yaw)

# Lancer Flask sans debug pour éviter les problèmes de cache
if __name__ == '__main__':
    app.run(debug=False)
