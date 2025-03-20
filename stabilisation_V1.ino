#include <Arduino_LSM6DSOX.h> // Bibliothèque pour l'IMU intégrée
#include <Servo.h> // Contrôle des servomoteurs
#include <ArduinoBLE.h> // Communication Bluetooth Low Energy

// Déclaration des objets Servo pour contrôler les servomoteurs sur les axes X, Y, Z
Servo servoX;
Servo servoY;
Servo servoZ;

// Offsets manuels définis par l'utilisateur pour calibrer mécaniquement les servos
int roll_offset = 5;
int pitch_offset = 10;
int yaw_offset = -25;

// Variables globales pour les données des capteurs
float Ax, Ay, Az; // Accélérations sur axes X,Y,Z
float Gx, Gy, Gz; // Vitesses angulaires du gyroscope sur axes X,Y,Z
float roll = 0, pitch = 0, yaw = 90; // Angles d'orientation initiaux (en degrés)

// Offsets du gyroscope pour compenser la dérive initiale
float Gx_offset = 0, Gy_offset = 0, Gz_offset = 0;

// Coefficient pour le filtre complémentaire (ajustable entre 0 et 1)
const float alpha = 0.98;

// Temps pour calculer l'écart entre deux mesures (deltaT)
unsigned long lastTime;

// Définition du service BLE et caractéristique pour transmettre les angles
BLEService angleService("053c38bf-fcad-4014-bb61-611af9a9e6aa");
BLECharacteristic angleCharacteristic("4c5800c3-eca9-48ab-8d04-e1d02d7fe771", BLERead | BLENotify, 12);

// Fonction pour calibrer automatiquement les offsets du gyroscope au démarrage
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
  // Initialisation du port série pour debug
  Serial.begin(115200);
  while (!Serial);

  // Initialisation du BLE (Bluetooth Low Energy)
  if (!BLE.begin()) {
    Serial.println("Échec de l'initialisation du BLE !");
    while (1);
  }
  angleService.addCharacteristic(angleCharacteristic);
  BLE.addService(angleService);
  BLE.advertise();
  Serial.println("Périphérique BLE démarré");
  
  // Initialisation de l'IMU intégré (accéléromètre et gyroscope)
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

  // Calibration automatique du gyroscope
  calibrateGyro();

  // Initialisation des angles à partir de l'accéléromètre (mesure initiale)
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

  // Calcul des angles initiaux à partir de l'accéléromètre
  float accelRoll  = atan2(Ay, Az) * 180 / PI;
  float accelPitch = atan2(-Ax, sqrt(Ay * Ay + Az * Az)) * 180 / PI;
  roll = accelRoll;
  pitch = accelPitch;
  Serial.println("Initialisation des angles terminée.");

  // Attache les servos aux broches PWM correspondantes
  servoX.attach(9);
  servoY.attach(8);
  servoZ.attach(7);

  // Positionne les servos à leur angle initial avec offsets
  servoX.write(90 + roll_offset);
  servoY.write(90 + pitch_offset);
  servoZ.write(90 + yaw_offset);
  delay(1000);

  lastTime = millis();
  Serial.println("IMU + Servos prêts !");
}

void loop() {
  // Gestion des évènements BLE
  BLE.poll(); 

  // Calcul du temps écoulé depuis la dernière mesure
  unsigned long currentTime = millis();
  float deltaTime = (currentTime - lastTime) / 1000.0; // en secondes
  lastTime = currentTime;

  // Protection contre des écarts trop grands (erreurs potentielles)
  if (deltaTime > 0.1) deltaTime = 0.01;

  // Lecture des données du capteur IMU (accéléromètre + gyroscope)
  if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
    IMU.readAcceleration(Ax, Ay, Az);
    IMU.readGyroscope(Gx, Gy, Gz);

    // Correction des données gyroscope avec les offsets précédemment calculés
    Gx -= Gx_offset;
    Gy -= Gy_offset;
    Gz -= Gz_offset;

    // Calcul des angles depuis l'accéléromètre
    float accelRoll  = atan2(Ay, Az) * 180 / PI;
    float accelPitch = atan2(-Ax, sqrt(Ay * Ay + Az * Az)) * 180 / PI;

    // Application du filtre complémentaire pour combiner gyro et accéléro
    roll  = alpha * (roll + Gx * deltaTime) + (1 - alpha) * accelRoll;
    pitch = alpha * (pitch - Gy * deltaTime) + (1 - alpha) * (-accelPitch);
    yaw  -= Gz * deltaTime; // Yaw calculé uniquement avec gyro (peut dériver)

    // Conversion des angles en valeurs compatibles pour les servos (0-180°)
    int roll_servo  = constrain(90 + roll_offset + roll, 0, 180);
    int pitch_servo = constrain(90 + pitch_offset + pitch, 0, 180);
    int yaw_servo   = constrain(90 + yaw_offset + (yaw - 90), 0, 180);

    // Mise à jour des positions des servos
    servoX.write(roll_servo);
    servoY.write(pitch_servo);
    servoZ.write(yaw_servo);

    // Envoi des angles via BLE sous forme de tableau flottant
    float angles[3] = { (float)roll_servo, (float)pitch_servo, (float)yaw_servo };
    angleCharacteristic.writeValue((uint8_t*)angles, sizeof(angles));
    
   // Optionnel : affichage des valeurs sur le moniteur série (pour debug)
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

  delay(10); // Pause pour éviter saturation CPU
}
