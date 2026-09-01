#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
const char* backendUrl = "http://192.168.1.100:8000/api/iot/data";
const char* deviceId = "ESP32-01";

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected!");
}

void loop() {
  if(WiFi.status() == WL_CONNECTED){
    HTTPClient http;
    http.begin(backendUrl);
    http.addHeader("Content-Type", "application/json");

    // Simulated sensor readings
    float temperature = random(290, 310) / 10.0;
    float humidity = random(400, 600) / 10.0;
    float vibration = random(5, 15) / 100.0;
    float speed = random(1480, 1520);
    float torque = random(38, 42);
    float current = random(80, 120) / 100.0;
    
    // Construct JSON payload
    String payload = "{";
    payload += "\"device_id\":\"" + String(deviceId) + "\",";
    payload += "\"timestamp\":\"" + String(millis()) + "\",";
    payload += "\"temperature\":" + String(temperature) + ",";
    payload += "\"humidity\":" + String(humidity) + ",";
    payload += "\"vibration\":" + String(vibration) + ",";
    payload += "\"speed\":" + String(speed) + ",";
    payload += "\"torque\":" + String(torque) + ",";
    payload += "\"current\":" + String(current);
    payload += "}";

    int httpResponseCode = http.POST(payload);
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);
    http.end();
  }
  delay(1000); // 1Hz sampling rate
}
