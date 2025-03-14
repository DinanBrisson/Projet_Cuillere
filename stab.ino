#include <ArduinoBLE.h>
#include <Arduino_LSM6DSOX.h>
#include <Servo.h>

Servo servoX; // Roll (X)
Servo servoY; // Pitch (Y)
Servo servoZ; // Yaw (Z)

float Ax, Ay, Az;
float Gx, Gy, Gz;
float Gx_offset = 0, Gy_offset = 0, Gz_offset = 0; // Offsets du gyroscope
float roll = 0, pitch = 0, yaw = 90; // Angles initiaux
unsigned long lastTime;
const float alpha = 0.98; // Poids du filtre complémentaire
const float threshold = 0.05; // Seuil pour détecter une immobilité

// Définition du service et de la caractéristique BLE
BLEService imuService("180A");
BLEStringCharacteristic imuData("2A57", BLERead | BLENotify, 50);

void calibrateIMU() {
    Serial.println("Calibration du gyroscope...");
    float sumGx = 0, sumGy = 0, sumGz = 0;
    int samples = 500;

    for (int i = 0; i < samples; i++) {
        if (IMU.gyroscopeAvailable()) {
            IMU.readGyroscope(Gx, Gy, Gz);
            sumGx += Gx;
            sumGy += Gy;
            sumGz += Gz;
        }
        delay(5);
    }

    Gx_offset = sumGx / samples;
    Gy_offset = sumGy / samples;
    Gz_offset = sumGz / samples;
    Serial.println("Calibration terminée !");
}

void setup() {
    Serial.begin(115200);
    while (!Serial);

    if (!IMU.begin()) {
        Serial.println("Erreur : Impossible d'initialiser l'IMU !");
        while (1);
    }

    // Initialisation du Bluetooth BLE
    if (!BLE.begin()) {
        Serial.println("Erreur : Impossible d'initialiser le Bluetooth !");
        while (1);
    }

    BLE.setLocalName("NanoRP2040_IMU");
    BLE.setAdvertisedService(imuService);
    imuService.addCharacteristic(imuData);
    BLE.addService(imuService);
    BLE.advertise();

    Serial.println("Bluetooth BLE actif !");
    calibrateIMU();

    servoX.attach(9);  // Roll (X)
    servoY.attach(8);  // Pitch (Y)
    servoZ.attach(7);  // Yaw (Z)

    servoX.write(roll);
    servoY.write(pitch);
    servoZ.write(yaw);

    Serial.println("IMU et Servos prêts !");
    lastTime = millis();
}

void loop() {
    BLEDevice central = BLE.central(); // Vérifie la connexion BLE

    if (central) {
        unsigned long currentTime = millis();
        float deltaTime = (currentTime - lastTime) / 1000.0;
        lastTime = currentTime;

        if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
            IMU.readAcceleration(Ax, Ay, Az);
            IMU.readGyroscope(Gx, Gy, Gz);

            // Retirer l'offset du gyroscope
            Gx -= Gx_offset;
            Gy -= Gy_offset;
            Gz -= Gz_offset;

            // Calculer l'angle avec l'accéléromètre
            float accelRoll  = atan2(Ay, Az) * 180 / PI;
            float accelPitch = atan2(-Ax, sqrt(Ay * Ay + Az * Az)) * 180 / PI;

            // Détection d'immobilité pour éviter le blocage
            if (abs(Gx) < threshold && abs(Gy) < threshold) {
                roll  = roll * 0.9 + accelRoll * 0.1;
                pitch = pitch * 0.9 + accelPitch * 0.1;
            } else {
                roll  = alpha * (roll + Gx * deltaTime) + (1 - alpha) * accelRoll;
                pitch = alpha * (pitch + Gy * deltaTime) + (1 - alpha) * accelPitch;
            }

            yaw += Gz * deltaTime; // Le yaw est toujours basé uniquement sur le gyroscope

            // Limiter les angles pour les servos
            roll  = constrain(roll, 0, 180);
            pitch = constrain(pitch, 0, 180);
            yaw   = constrain(yaw, 0, 180);

            // Appliquer les angles aux servos
            servoX.write(roll);
            servoY.write(pitch);
            servoZ.write(yaw);

            // Envoi des données BLE en JSON
            String data = String("{\"roll\":") + roll + ",\"pitch\":" + pitch + ",\"yaw\":" + yaw + "}";
            imuData.writeValue(data);
            Serial.println(data);
        }
    }

    delay(10); // Garder un délai court pour la fluidité
}
