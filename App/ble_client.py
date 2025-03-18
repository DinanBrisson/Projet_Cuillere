import asyncio
import struct
import threading
from bleak import BleakClient, BleakScanner, BleakError

# Adresse BLE de votre Arduino Nano RP2040 Connect (mettre à jour après scan)
DEVICE_ADDRESS = "58:BF:25:3B:FE:66"
# UUID de la caractéristique utilisée pour recevoir les angles
ANGLE_CHAR_UUID = "4c5800c3-eca9-48ab-8d04-e1d02d7fe771"

# Stockage des données partagées entre BLE et Flask
angle_data = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
data_lock = threading.Lock()
ble_connected = False  # Indicateur de connexion BLE

# Fonction appelée à chaque notification BLE reçue
def notification_handler(sender, data):
    global angle_data
    try:
        roll, pitch, yaw = struct.unpack("fff", data)  # Lire les 3 valeurs float
        with data_lock:
            angle_data["roll"] = round(roll, 2)
            angle_data["pitch"] = round(pitch, 2)
            angle_data["yaw"] = round(yaw, 2)
        print(f"Notification reçue -> Roll: {roll}, Pitch: {pitch}, Yaw: {yaw}")
    except Exception as e:
        print(f"Erreur de lecture BLE : {e}")

# Vérifier si l'appareil BLE est visible
async def find_device():
    global ble_connected
    print("Recherche du périphérique BLE...")
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"{device.name} - Adresse : {device.address}")
        if DEVICE_ADDRESS in device.address:
            print(f"Périphérique trouvé : {device.name} - {device.address}")
            ble_connected = True
            return device.address
    print("Aucun périphérique trouvé.")
    ble_connected = False
    return None

# Boucle principale pour la connexion BLE
async def run_ble_client():
    global ble_connected
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

# Lancer le client BLE dans un thread séparé pour ne pas bloquer Flask
def start_ble_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_ble_client())

# Lancement du thread BLE au démarrage
ble_thread = threading.Thread(target=start_ble_loop, daemon=True)
ble_thread.start()

# Fonction pour récupérer les données en temps réel depuis Flask
def get_ble_data():
    with data_lock:
        return angle_data.copy()
