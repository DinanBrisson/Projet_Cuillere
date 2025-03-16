#include <Arduino_LSM6DSOX.h>
#include <Servo.h>

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

  if (!IMU.begin()) {
    Serial.println("Erreur : Impossible d'initialiser l'IMU !");
    while (1);
  }

  // Message clair avant calibration
  Serial.println("=======================================");
  Serial.println("!!! ATTENTION !!!");
  Serial.println("Posez la cuillère bien à plat, immobile.");
  Serial.println("Début de la calibration dans 3 secondes...");
  Serial.println("=======================================");
  delay(3000); // Temps pour que tu la poses tranquillement

  calibrateGyro(); // Calibration propre après délai

  // Initialisation des angles avec accéléromètre (IMPORTANT)
  if (IMU.accelerationAvailable()) {
    IMU.readAcceleration(Ax, Ay, Az);

    float accelRoll  = atan2(Ay, Az) * 180 / PI;
    float accelPitch = atan2(-Ax, sqrt(Ay * Ay + Az * Az)) * 180 / PI;

    roll = accelRoll;
    pitch = accelPitch;

    Serial.println("Initialisation des angles terminée.");
  }

  // Attache des servos
  servoX.attach(9);
  servoY.attach(8);
  servoZ.attach(7);

  // Position neutre (offsets manuels)
  servoX.write(90 + roll_offset);
  servoY.write(90 + pitch_offset);
  servoZ.write(90 + yaw_offset);
  delay(1000);

  lastTime = millis();

  Serial.println("IMU + Servos prêts !");
}

void loop() {
  unsigned long currentTime = millis();
  float deltaTime = (currentTime - lastTime) / 1000.0; // En secondes
  lastTime = currentTime;

  if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
    IMU.readAcceleration(Ax, Ay, Az);
    IMU.readGyroscope(Gx, Gy, Gz);

    // Enlever offset gyroscope
    Gx -= Gx_offset;
    Gy -= Gy_offset;
    Gz -= Gz_offset;

    // Calcul des angles par accéléromètre
    float accelRoll  = atan2(Ay, Az) * 180 / PI;
    float accelPitch = atan2(-Ax, sqrt(Ay * Ay + Az * Az)) * 180 / PI;

    // Filtre complémentaire pour lisser
    roll  = alpha * (roll + Gx * deltaTime) + (1 - alpha) * accelRoll;
    pitch = alpha * (pitch + Gy * deltaTime) + (1 - alpha) * accelPitch;
    yaw  -= Gz * deltaTime;

    // Centre les angles autour de 90° et limite
    int roll_servo  = constrain(90 + roll_offset + (roll), 0, 180);
    int pitch_servo = constrain(90 + pitch_offset + (pitch), 0, 180);
    int yaw_servo   = constrain(90 + yaw_offset + (yaw - 90), 0, 180); // Car yaw démarre à 90°

    // Appliquer aux servos
    servoX.write(roll_servo);
    servoY.write(pitch_servo);
    servoZ.write(yaw_servo);

    // Debug
    Serial.print("Roll : ");
    Serial.print(roll_servo);
    Serial.print(" | Pitch : ");
    Serial.print(pitch_servo);
    Serial.print(" | Yaw : ");
    Serial.println(yaw_servo);
  }

  delay(10);
}
