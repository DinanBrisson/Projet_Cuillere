import asyncio
import json
import numpy as np
import tkinter as tk
from bleak import BleakClient, BleakScanner
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Nom du périphérique BLE et UUID de la caractéristique
BLE_DEVICE_NAME = "NanoRP2040_IMU"
BLE_CHARACTERISTIC_UUID = "2A57"

# Stockage des angles
roll, pitch, yaw = 0, 0, 90


async def find_device():
    print("Recherche du périphérique BLE...")
    devices = await BleakScanner.discover()
    for device in devices:
        if BLE_DEVICE_NAME in device.name:
            print(f"Périphérique trouvé : {device.name} - {device.address}")
            return device.address
    print("Aucun périphérique trouvé.")
    return None


async def receive_data(address):
    async with BleakClient(address) as client:
        print(f"Connecté à {address}")
        await client.start_notify(BLE_CHARACTERISTIC_UUID, handle_data)

        while True:
            await asyncio.sleep(0.1)


def handle_data(_, data):
    global roll, pitch, yaw
    try:
        data_str = data.decode("utf-8").strip()
        json_data = json.loads(data_str)
        roll = float(json_data["roll"]) - 90
        pitch = float(json_data["pitch"]) - 90
        yaw = float(json_data["yaw"]) - 90
        update_labels()
    except Exception as e:
        print("Erreur de réception:", e)


def update_labels():
    roll_label.config(text=f"Roll (X) : {roll:.2f}")
    pitch_label.config(text=f"Pitch (Y) : {pitch:.2f}")
    yaw_label.config(text=f"Yaw (Z) : {yaw:.2f}")
    update_plot()


def update_plot():
    ax.clear()
    ax.bar(["Roll", "Pitch", "Yaw"], [roll, pitch, yaw], color=['r', 'g', 'b'])
    ax.set_ylim(-90, 90)
    canvas.draw()


def draw_spoon():
    glBegin(GL_QUADS)
    glColor3f(0.8, 0.8, 0.8)

    # Manche de la cuillère
    glVertex3f(-0.05, -1, 0)
    glVertex3f(0.05, -1, 0)
    glVertex3f(0.05, 0.3, 0)
    glVertex3f(-0.05, 0.3, 0)

    # Partie arrondie (tête de la cuillère)
    glVertex3f(-0.15, 0.3, 0)
    glVertex3f(0.15, 0.3, 0)
    glVertex3f(0.1, 0.6, 0.1)
    glVertex3f(-0.1, 0.6, 0.1)

    glEnd()


def run_3d_simulation():
    pygame.init()
    display = (400, 400)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)
    glTranslatef(0, 0, -3)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPushMatrix()

        glRotatef(roll, 1, 0, 0)
        glRotatef(pitch, 0, 1, 0)
        glRotatef(yaw, 0, 0, 1)

        draw_spoon()
        glPopMatrix()
        pygame.display.flip()
        pygame.time.wait(10)


async def main():
    global root, roll_label, pitch_label, yaw_label, ax, canvas

    root = tk.Tk()
    root.title("Interface Gyroscope & Simulation 3D")

    roll_label = tk.Label(root, text="Roll (X) : 0.00", font=("Arial", 14))
    roll_label.pack()
    pitch_label = tk.Label(root, text="Pitch (Y) : 0.00", font=("Arial", 14))
    pitch_label.pack()
    yaw_label = tk.Label(root, text="Yaw (Z) : 0.00", font=("Arial", 14))
    yaw_label.pack()

    fig, ax = plt.subplots(figsize=(4, 3))
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack()

    address = await find_device()
    if address:
        asyncio.create_task(receive_data(address))
        asyncio.create_task(asyncio.to_thread(run_3d_simulation))
        root.mainloop()


asyncio.run(main())
