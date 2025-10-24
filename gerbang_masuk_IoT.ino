#include <Servo.h>

const int sensorPin1 = 2; 
const int sensorPin2 = 3;
const int servoPin = 9;  

const unsigned long durasiDeteksiSensor = 3000;
const unsigned long durasiGerbangBuka = 5000;   
const int sudutBuka = 90;  
const int sudutTutup = 0;  

Servo gerbangServo;
unsigned long waktuDeteksiAwal = 0;
bool mobilMenunggu = false; 

unsigned long waktuGerbangBuka = 0;
bool gerbangSedangTerbuka = false;

void setup() {
  Serial.begin(9600);
  pinMode(sensorPin1, INPUT);
  pinMode(sensorPin2, INPUT);
  gerbangServo.attach(servoPin);
  gerbangServo.write(sudutTutup); 
  Serial.println("Sistem Gerbang Parkir Siap.");
}

void loop() {
  if (digitalRead(sensorPin1) == LOW && !mobilMenunggu) {
    if (waktuDeteksiAwal == 0) {
      waktuDeteksiAwal = millis();
    }
    if (millis() - waktuDeteksiAwal >= durasiDeteksiSensor) {
      Serial.println("SENSOR1_AKTIF"); 
      mobilMenunggu = true; 
      waktuDeteksiAwal = 0;
    }
  } else if (digitalRead(sensorPin1) == HIGH) {
    waktuDeteksiAwal = 0; 
  }

  if (digitalRead(sensorPin2) == LOW && gerbangSedangTerbuka) {
    Serial.println("SENSOR2_AKTIF"); 
  }

  if (Serial.available() > 0) {
    char perintah = Serial.read();
    if (perintah == 'B' && !gerbangSedangTerbuka) { 
      gerbangServo.write(sudutBuka);
      gerbangSedangTerbuka = true;
      waktuGerbangBuka = millis(); 
    } else if (perintah == 'T') { 
      gerbangServo.write(sudutTutup);
      gerbangSedangTerbuka = false;
      mobilMenunggu = false;
    }
  }
  

  if (gerbangSedangTerbuka) {
    if (millis() - waktuGerbangBuka >= durasiGerbangBuka) {
      gerbangServo.write(sudutTutup);
      gerbangSedangTerbuka = false;
      mobilMenunggu = false; 
      Serial.println("TUTUP_OTOMATIS_TIMEOUT"); 
    }
  }
}