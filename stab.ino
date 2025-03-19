#include <Arduino_LSM6DSOX.h>
#include <Servo.h>
#include <ArduinoBLE.h> // === BLE désactivé ===

Servo servoX;
Servo servoY;
Servo servoZ;

// Offsets manuels (calibrés par toi)
int roll_offset = 5;
int pitch_offset = 10;
int yaw_offset = -25;

// Variables capteurs
float Ax, Ay, Az;
float Gx, Gy, Gz;
float roll = 0, pitch = 0, yaw = 90; // Positions initiales logiques

// Offsets gyroscope (pour dérive)
float Gx_offset = 0, Gy_offset = 0, Gz_offset = 0;

// Filtre complémentaire
const float alpha = 0.98; // Ajustable

// Temps pour calcul deltaT
unsigned long lastTime;

BLEService angleService("053c38bf-fcad-4014-bb61-611af9a9e6aa");
BLECharacteristic angleCharacteristic("4c5800c3-eca9-48ab-8d04-e1d02d7fe771", BLERead | BLENotify, 12);


void calibrateGyro() {
  Serial.println("Calibration gyroscope...");
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


  if (!BLE.begin()) {
    Serial.println("Échec de l'initialisation du BLE !");
    while (1);
  }
  angleService.addCharacteristic(angleCharacteristic);
  BLE.addService(angleService);
  BLE.advertise();
  Serial.println("Périphérique BLE démarré");
  

  if (!IMU.begin()) {
    Serial.println("Erreur : Impossible d'initialiser l'IMU !");
    while (1);
  }

  Serial.println("=======================================");
  Serial.println("!!! ATTENTION !!!");
  Serial.println("Posez la cuillère bien à plat, immobile.");
  Serial.println("Début de la calibration dans 3 secondes...");
  Serial.println("=======================================");
  delay(3000);

  calibrateGyro();

  // Moyenne initialisation accéléromètre
  float sumAx = 0, sumAy = 0, sumAz = 0;
  int samples = 100;
  for (int i = 0; i < samples; i++) {
    if (IMU.accelerationAvailable()) {
      IMU.readAcceleration(Ax, Ay, Az);
      sumAx += Ax;
      sumAy += Ay;
      sumAz += Az;
    }
    delay(5);
  }
  Ax = sumAx / samples;
  Ay = sumAy / samples;
  Az = sumAz / samples;
  float accelRoll  = atan2(Ay, Az) * 180 / PI;
  float accelPitch = atan2(-Ax, sqrt(Ay * Ay + Az * Az)) * 180 / PI;
  roll = accelRoll;
  pitch = accelPitch;
  Serial.println("Initialisation des angles terminée.");

  servoX.attach(9);
  servoY.attach(8);
  servoZ.attach(7);

  servoX.write(90 + roll_offset);
  servoY.write(90 + pitch_offset);
  servoZ.write(90 + yaw_offset);
  delay(1000);

  lastTime = millis();
  Serial.println("IMU + Servos prêts !");
}

void loop() {
  BLE.poll(); 

  unsigned long currentTime = millis();
  float deltaTime = (currentTime - lastTime) / 1000.0; // en secondes
  lastTime = currentTime;

  // Clamp deltaTime pour éviter les gros sauts
  if (deltaTime > 0.1) deltaTime = 0.01;

  if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
    IMU.readAcceleration(Ax, Ay, Az);
    IMU.readGyroscope(Gx, Gy, Gz);

    // Correction des offsets gyroscope
    Gx -= Gx_offset;
    Gy -= Gy_offset;
    Gz -= Gz_offset;

    float accelRoll  = atan2(Ay, Az) * 180 / PI;
    float accelPitch = atan2(-Ax, sqrt(Ay * Ay + Az * Az)) * 180 / PI;

    roll  = alpha * (roll + Gx * deltaTime) + (1 - alpha) * accelRoll;
    pitch = alpha * (pitch - Gy * deltaTime) + (1 - alpha) * (-accelPitch);
    yaw  -= Gz * deltaTime;

    int roll_servo  = constrain(90 + roll_offset + roll, 0, 180);
    int pitch_servo = constrain(90 + pitch_offset + pitch, 0, 180);
    int yaw_servo   = constrain(90 + yaw_offset + (yaw - 90), 0, 180);

    servoX.write(roll_servo);
    servoY.write(pitch_servo);
    servoZ.write(yaw_servo);


    float angles[3] = { (float)roll_servo, (float)pitch_servo, (float)yaw_servo };
    angleCharacteristic.writeValue((uint8_t*)angles, sizeof(angles));
    

   //Serial.print("Roll : ");
   //Serial.print(roll_servo);
   //Serial.print(" | Pitch : ");
   //Serial.print(pitch_servo);
   //Serial.print(" | Yaw : ");
   //Serial.print(yaw_servo);
   //Serial.println(); 


  } else {
    Serial.println("IMU non dispo !");
  }

  delay(10);
}
