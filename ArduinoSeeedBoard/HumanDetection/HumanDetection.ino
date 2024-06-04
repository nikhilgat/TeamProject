#include "Arduino.h"
#include "60ghzfalldetection.h"

// #define BLYNK_PRINT Serial

// #define BLYNK_TEMPLATE_ID "TMPL4gwBhC0_s"
// #define BLYNK_TEMPLATE_NAME "SensorData"
// #define BLYNK_AUTH_TOKEN "N67iEvuJ-J474RfZY9C3MTwa5PHf4PYK"

// #include <WiFi.h>
// #include <WiFiClient.h>
// #include <BlynkSimpleEsp32.h>

// char ssid[] = "euryblades";
// char pass[] = "Nikhil@213";

FallDetection_60GHz radar = FallDetection_60GHz(&Serial);

int someoneMovingLed = 5;
int stoppedMovingLed = 6;

void setup() {
  pinMode(stoppedMovingLed, OUTPUT);
  pinMode(someoneMovingLed, OUTPUT);
  Serial.begin(115200);
  // Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);

  while(!Serial);   

  Serial.println("Ready");
}

void loop()
{
    // Blynk.run();

  // put your main code here, to run repeatedly:
  radar.HumanExis_Func();           //Human existence information output
  if(radar.sensor_report != 0x00){
    switch(radar.sensor_report){
      case NOONE:
        Serial.println("Nobody here.");
        Serial.println("----------------------------");
        break;
      case SOMEONE:
        Serial.println("Someone is here.");
        Serial.println("----------------------------");
        break;
      case NONEPSE:
        Serial.println("No human activity messages.");
        Serial.println("----------------------------");
        break;
      case STATION:
        digitalWrite(someoneMovingLed, LOW);
        digitalWrite(stoppedMovingLed, HIGH);

        Serial.println("Someone stop");
        Serial.println("----------------------------");
        break;
      case MOVE:
        digitalWrite(stoppedMovingLed, LOW);
        digitalWrite(someoneMovingLed, HIGH);

        Serial.println("Someone moving");
        Serial.println("----------------------------");
        break;
      case BODYVAL:
        Serial.print("The parameters of human body signs are: ");
        Serial.println(radar.bodysign_val, DEC);
        Serial.println("----------------------------");
        break;
    }
  }
  delay(200);                       //Add time delay to avoid program jam
}