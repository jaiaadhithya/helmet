#include <Wire.h>
#include <math.h>
#include <WiFi.h>
#define I2C_SDA 16
#define I2C_SCL 17

uint8_t mpuAddr = 0x68;
WiFiServer wifiServer(8080);
WiFiClient wifiClient;
const char* AP_SSID = "MYOSA-HELMET-AP";
bool i2cPresent(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

void mpuWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(mpuAddr);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

bool mpuRead(uint8_t reg, uint8_t* buf, uint8_t len) {
  Wire.beginTransmission(mpuAddr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  uint8_t n = Wire.requestFrom((int)mpuAddr, (int)len, (int)true);
  if (n != len) return false;
  for (uint8_t i = 0; i < len; i++) buf[i] = Wire.read();
  return true;
}

float prevGx = 0.0f, prevGy = 0.0f, prevGz = 0.0f;
unsigned long prevUs = 0;
float peak_a_g = 0.0f;
float peak_alpha_rad_s2 = 0.0f;

const float BETA0 = -10.2f;
const float BETA1 = 0.433f;
const float BETA2 = 0.00873f;

  void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID);
  wifiServer.begin();
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000);

  if (i2cPresent(0x68)) mpuAddr = 0x68; else if (i2cPresent(0x69)) mpuAddr = 0x69;
  mpuWrite(0x6B, 0x00);
  mpuWrite(0x1C, 0x00);
  mpuWrite(0x1B, 0x00);
  prevUs = micros();
}

void loop() {
  if (!wifiClient || !wifiClient.connected()) {
    WiFiClient nc = wifiServer.available();
    if (nc) {
      wifiClient = nc;
      wifiClient.setNoDelay(true);
      wifiClient.println("0 0 0");
    }
  }
  uint8_t buf[14];
  bool ok = mpuRead(0x3B, buf, 14);
  unsigned long nowUs = micros();
  float dt = (nowUs - prevUs) / 1000000.0f;
  if (ok) {
    // client acceptance handled above
    int16_t axr = (int16_t)((buf[0] << 8) | buf[1]);
    int16_t ayr = (int16_t)((buf[2] << 8) | buf[3]);
    int16_t azr = (int16_t)((buf[4] << 8) | buf[5]);
    int16_t gxr = (int16_t)((buf[8] << 8) | buf[9]);
    int16_t gyr = (int16_t)((buf[10] << 8) | buf[11]);
    int16_t gzr = (int16_t)((buf[12] << 8) | buf[13]);
    float ax_g = axr / 16384.0f;
    float ay_g = ayr / 16384.0f;
    float az_g = azr / 16384.0f;
    float a_g = sqrtf(ax_g * ax_g + ay_g * ay_g + az_g * az_g);
    float gx_dps = gxr / 131.0f;
    float gy_dps = gyr / 131.0f;
    float gz_dps = gzr / 131.0f;
    float gx_rad = gx_dps * (3.14159265358979323846f / 180.0f);
    float gy_rad = gy_dps * (3.14159265358979323846f / 180.0f);
    float gz_rad = gz_dps * (3.14159265358979323846f / 180.0f);
    float alpha_mag = 0.0f;
    if (dt > 0.0f) {
      float agx = (gx_rad - prevGx) / dt;
      float agy = (gy_rad - prevGy) / dt;
      float agz = (gz_rad - prevGz) / dt;
      alpha_mag = sqrtf(agx * agx + agy * agy + agz * agz);
      prevGx = gx_rad;
      prevGy = gy_rad;
      prevGz = gz_rad;
    }
    if (a_g > peak_a_g) peak_a_g = a_g;
    if (alpha_mag > peak_alpha_rad_s2) peak_alpha_rad_s2 = alpha_mag;
    float cp = 1.0f / (1.0f + expf(-(BETA0 + BETA1 * peak_a_g + BETA2 * peak_alpha_rad_s2)));
    Serial.print(a_g, 4);
    Serial.print(" ");
    Serial.print(alpha_mag, 4);
    Serial.print(" ");
    Serial.println(cp, 4);
    if (wifiClient && wifiClient.connected()) {
      wifiClient.print(a_g, 4);
      wifiClient.print(" ");
      wifiClient.print(alpha_mag, 4);
      wifiClient.print(" ");
      wifiClient.println(cp, 4);
    }
  }
  else {
    if (wifiClient && wifiClient.connected()) {
      wifiClient.println("0 0 0");
    }
  }
  prevUs = nowUs;
  delay(10);
}

