#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// =====================================================
// CONFIGURACIÓN OPTIMIZADA PARA ESP8266
// =====================================================
#define USE_DHT 1
#define STATIC_IP 1
#define ENABLE_OTA 0
#define SOFTWARE_WDT_TIMEOUT 10000

// Niveles de log (reducir a 2 o 3 para ahorrar RAM)
#define CURRENT_LOG_LEVEL 4 // 2=WARN, 3=INFO, 4=DEBUG

// -----------------------------
// WIFI
// -----------------------------
const char* WIFI_SSID = "3156";
const char* WIFI_PASS = "qjuimaq62bv3s9";
const char* WIFI_HOSTNAME = "esp8266-pcroom";

#if STATIC_IP
IPAddress ip(192,168,0,150);
IPAddress gateway(192,168,0,1);
IPAddress subnet(255,255,255,0);
IPAddress dns1(192,168,0,5);
#endif

// -----------------------------
// MQTT
// -----------------------------
const char* BROKER = "192.168.0.5";
const int   BROKER_PORT = 1883;

const char* DEVICE   = "esp8266";
const char* LOCATION = "bedroom";

// Topics simplificados (sin PROGMEM para evitar problemas)
char cmdTopic[45];
char statusTopic[45];
char pongTopic[45];
char pingTopic[45];

// -----------------------------
// LED - NodeMCU LED integrado
// -----------------------------
#define LED_PIN LED_BUILTIN // GPIO2 (D4) en NodeMCU
#define LED_ON_STATE LOW
#define LED_OFF_STATE HIGH

// =====================================================
// CLIENTES Y ESTADO
// =====================================================
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

struct SystemState {
  bool ledState;
  bool wifiConnected;
  bool mqttConnected;
  unsigned long lastWifiAttempt;
  unsigned long lastMqttAttempt;
  uint8_t wifiRetryCount;
  uint8_t mqttRetryCount;
  unsigned long lastSoftwareWdReset;
};

SystemState sysState = {false, false, false, 0, 0, 0, 0, 0};

// =====================================================
// DHT (si se habilita)
// =====================================================
#if USE_DHT
#include <DHT.h>
#define DHT_PIN D2
#define DHT_TYPE DHT22
DHT dht(DHT_PIN, DHT_TYPE);

struct SensorData {
  float temp_c;
  float temp_h;
  float temp_st;
  bool valid;
  unsigned long lastReadTime;
  uint8_t readErrors;
};

SensorData sensorData = {NAN, NAN, NAN, false, 0, 0};
#define DHT_READ_INTERVAL 3000
#define MAX_DHT_ERRORS 5
#endif

#if ENABLE_OTA
#include <ArduinoOTA.h>
#endif

// =====================================================
// HELPER: Alimentar watchdog de forma segura
// =====================================================
inline void feedWatchdog() {
  ESP.wdtFeed();
  yield();
}

// =====================================================
// SISTEMA DE LOG OPTIMIZADO
// =====================================================
enum LogLevel {
  LOG_NONE = 0,
  LOG_ERROR,
  LOG_WARN,
  LOG_INFO,
  LOG_DEBUG
};

class Logger {
private:
  static const char* getLevelStr(LogLevel level) {
    static const char* levels[] = {"", "ERROR", "WARN", "INFO", "DEBUG"};
    return levels[level];
  }

public:
  static void begin() {
    Serial.begin(115200);
    delay(10);
    Serial.println();
    feedWatchdog();
    info("Logger inicializado");
  }
  
  static void log(LogLevel level, const char* msg) {
    if (level > CURRENT_LOG_LEVEL) return;
    
    Serial.print("[");
    Serial.print(millis());
    Serial.print("][");
    Serial.print(getLevelStr(level));
    Serial.print("] ");
    Serial.println(msg);
    
    feedWatchdog(); // Alimentar después de cada log
  }
  
  static void log(LogLevel level, const String& msg) {
    log(level, msg.c_str());
  }
  
  static void error(const char* msg) { log(LOG_ERROR, msg); }
  static void warn(const char* msg) { log(LOG_WARN, msg); }
  static void info(const char* msg) { log(LOG_INFO, msg); }
  static void debug(const char* msg) { log(LOG_DEBUG, msg); }
  
  static void error(const String& msg) { log(LOG_ERROR, msg); }
  static void warn(const String& msg) { log(LOG_WARN, msg); }
  static void info(const String& msg) { log(LOG_INFO, msg); }
  static void debug(const String& msg) { log(LOG_DEBUG, msg); }
};

// =====================================================
// MANEJO DE CONEXIONES
// =====================================================
namespace NetManager {
  const unsigned long WIFI_RETRY_DELAY = 5000;
  const unsigned long MQTT_RETRY_DELAY = 3000;
  const uint8_t MAX_WIFI_RETRIES = 10;
  
  void buildTopics() {
    Logger::debug("Construyendo topics...");
    feedWatchdog();
    
    // Construcción simple sin snprintf_P para evitar problemas
    strcpy(pingTopic, "iot/ping/all");
    
    strcpy(cmdTopic, "iot/cmd/");
    strcat(cmdTopic, DEVICE);
    strcat(cmdTopic, "/");
    strcat(cmdTopic, LOCATION);
    
    strcpy(statusTopic, "iot/status/");
    strcat(statusTopic, DEVICE);
    strcat(statusTopic, "/");
    strcat(statusTopic, LOCATION);
    
    strcpy(pongTopic, "iot/pong/");
    strcat(pongTopic, DEVICE);
    strcat(pongTopic, "/");
    strcat(pongTopic, LOCATION);
    
    feedWatchdog();
    Logger::info("Topics OK");
    Logger::debug(String("CMD: ") + cmdTopic);
  }
  
  bool connectWiFi() {
    if (WiFi.status() == WL_CONNECTED) {
      sysState.wifiConnected = true;
      return true;
    }
    
    unsigned long now = millis();
    if (now - sysState.lastWifiAttempt < WIFI_RETRY_DELAY) {
      return false;
    }
    
    sysState.lastWifiAttempt = now;
    sysState.wifiRetryCount++;
    
    Logger::info("Conectando WiFi...");
    feedWatchdog();
    
    WiFi.mode(WIFI_STA);
    WiFi.hostname(WIFI_HOSTNAME);
    feedWatchdog();
    
    #if STATIC_IP
    if (!WiFi.config(ip, gateway, subnet, dns1)) {
      Logger::error("Error config IP");
    }
    feedWatchdog();
    #endif
    
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    WiFi.setOutputPower(17);
    feedWatchdog();
    
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
      delay(100);
      feedWatchdog(); // CRÍTICO: alimentar durante espera
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      sysState.wifiConnected = true;
      sysState.wifiRetryCount = 0;
      
      Serial.print("WiFi OK: ");
      Serial.println(WiFi.localIP());
      feedWatchdog();
      
      if (MDNS.begin(WIFI_HOSTNAME)) {
        Logger::debug("mDNS OK");
      }
      feedWatchdog();
      
      #if ENABLE_OTA
      ArduinoOTA.begin();
      Logger::info("OTA habilitado");
      feedWatchdog();
      #endif
      
      return true;
    } else {
      Logger::warn("WiFi fallo");
      
      if (sysState.wifiRetryCount >= MAX_WIFI_RETRIES) {
        Logger::error("Max reintentos. Reiniciando...");
        delay(1000);
        ESP.restart();
      }
      return false;
    }
  }

  void publishSystemStatus() {
    StaticJsonDocument<256> doc;
    
    doc["status"] = "online";
    doc["device"] = DEVICE;
    doc["location"] = LOCATION;
    doc["ip"] = WiFi.localIP().toString();
    doc["uptime"] = millis() / 1000;
    doc["heap"] = ESP.getFreeHeap();
    
    #if USE_DHT
    if (sensorData.valid) {
      doc["temp_c"] = sensorData.temp_c;
      doc["temp_h"] = sensorData.temp_h;
      doc["temp_st"] = sensorData.temp_st;
    }
    #endif
    
    char buffer[256];
    serializeJson(doc, buffer);
    feedWatchdog();
    
    if (mqtt.publish(statusTopic, buffer, false)) {
      Logger::debug("Estado publicado");
    } else {
      Logger::warn("Fallo publicar");
    }
  }
  
  bool connectMQTT() {
    if (!sysState.wifiConnected) return false;
    
    if (mqtt.connected()) {
      sysState.mqttConnected = true;
      return true;
    }
    
    unsigned long now = millis();
    if (now - sysState.lastMqttAttempt < MQTT_RETRY_DELAY) {
      return false;
    }
    
    sysState.lastMqttAttempt = now;
    sysState.mqttRetryCount++;
    
    Logger::info("Conectando MQTT...");
    feedWatchdog();
    
    mqtt.setBufferSize(512);
    feedWatchdog();
    
    String clientId = String(DEVICE) + "-" + String(random(0xffff), HEX);
    
    if (mqtt.connect(clientId.c_str())) {
      sysState.mqttConnected = true;
      sysState.mqttRetryCount = 0;
      
      feedWatchdog();
      mqtt.subscribe(pingTopic);
      feedWatchdog();
      mqtt.subscribe(cmdTopic);
      feedWatchdog();
      
      publishSystemStatus();
      
      Logger::info("MQTT conectado");
      return true;
    } else {
      Logger::warn("MQTT fallo");
      delay(MQTT_RETRY_DELAY);
      feedWatchdog();
      return false;
    }
  }
}

// =====================================================
// MANEJO DE SENSORES
// =====================================================
#if USE_DHT
namespace SensorManager {
  void init() {
    Logger::debug("Inicializando DHT...");
    feedWatchdog();
    dht.begin();
    feedWatchdog();
    Logger::info("Sensor DHT OK");
  }
  
  bool readData() {
    unsigned long now = millis();
    
    if (now - sensorData.lastReadTime < DHT_READ_INTERVAL && sensorData.valid) {
      return sensorData.valid;
    }
    
    sensorData.lastReadTime = now;
    feedWatchdog();
    
    float t = dht.readTemperature();
    feedWatchdog();
    float h = dht.readHumidity();
    feedWatchdog();
    
    if (isnan(t) || isnan(h) || t < -40 || t > 80 || h < 0 || h > 100) {
      sensorData.readErrors++;
      Logger::warn("DHT lectura invalida");
      
      if (sensorData.readErrors >= MAX_DHT_ERRORS) {
        Logger::error("Max errores DHT");
      }
      return false;
    }
    
    sensorData.temp_c = t;
    sensorData.temp_h = h;
    sensorData.temp_st = dht.computeHeatIndex(t, h, false);
    sensorData.valid = true;
    sensorData.readErrors = 0;
    
    return true;
  }
}
#endif

// =====================================================
// MANEJO DE COMANDOS
// =====================================================
namespace CommandHandler {
  void sendPong(uint32_t time) {
    Logger::debug("sendPong INICIA");
    StaticJsonDocument<96> doc;
    doc["cmd"] = "PONG";
    doc["time"] = time;
    
    char buffer[96];
    serializeJson(doc, buffer);
    Logger::debug(String("PONG payload: ") + buffer);
    Logger::debug(String("PONG topic: ") + pongTopic);
    
    bool publishResult = mqtt.publish(pongTopic, buffer);
    Logger::debug(publishResult ? "PONG enviado OK" : "PONG ERROR - publish falló");
    
    feedWatchdog();
  }
  
  void publishConfiguration() {
    StaticJsonDocument<256> doc;
    
    doc["firmware"] = "1.1.1-ESP8266";
    doc["ip"] = WiFi.localIP().toString();
    doc["mac"] = WiFi.macAddress();
    doc["heap"] = ESP.getFreeHeap();
    doc["chip_id"] = String(ESP.getChipId(), HEX);
    
    #if USE_DHT
    doc["sensor"] = "DHT22";
    #endif
    
    char buffer[256];
    serializeJson(doc, buffer);
    feedWatchdog();
    
    char configTopic[50];
    strcpy(configTopic, "iot/config/");
    strcat(configTopic, DEVICE);
    strcat(configTopic, "/");
    strcat(configTopic, LOCATION);
    
    mqtt.publish(configTopic, buffer, true);
    feedWatchdog();
  }
  
  void process(const JsonDocument& doc) {
    if (!doc.containsKey("cmd")) {
      Logger::warn("Sin campo cmd");
      return;
    }
    
    const char* cmd = doc["cmd"];
    Logger::info(String("CMD: ") + cmd);
    feedWatchdog();
    
    if (strcmp(cmd, "PING") == 0) {
      Logger::debug("PING reconocido, calling sendPong...");
      sendPong(doc["time"] | millis());
    }
    else if (strcmp(cmd, "STATUS") == 0) {
      NetManager::publishSystemStatus();
    }
    else if (strcmp(cmd, "LED_ON") == 0) {
      digitalWrite(LED_PIN, LED_ON_STATE);
      sysState.ledState = true;
      Logger::info("LED ON");
    }
    else if (strcmp(cmd, "LED_OFF") == 0) {
      digitalWrite(LED_PIN, LED_OFF_STATE);
      sysState.ledState = false;
      Logger::info("LED OFF");
    }
    else if (strcmp(cmd, "LED_TOGGLE") == 0) {
      sysState.ledState = !sysState.ledState;
      digitalWrite(LED_PIN, sysState.ledState ? LED_ON_STATE : LED_OFF_STATE);
      Logger::info(sysState.ledState ? "LED ON" : "LED OFF");
    }
    else if (strcmp(cmd, "REBOOT") == 0) {
      Logger::warn("Reiniciando...");
      delay(500);
      ESP.restart();
    }
    else if (strcmp(cmd, "GET_CONFIG") == 0) {
      publishConfiguration();
    }
    else {
      Logger::warn("CMD desconocido");
    }
  }
  
  void mqttCallback(char* topic, byte* payload, unsigned int length) {
    if (length > 384) {
      Logger::error("Mensaje muy largo");
      return;
    }
    
    feedWatchdog();
    
    StaticJsonDocument<384> doc;
    DeserializationError error = deserializeJson(doc, payload, length);
    
    if (error) {
      Logger::error("JSON invalido");
      return;
    }
    
    feedWatchdog();
    process(doc);
  }
}

// =====================================================
// WATCHDOG Y MONITOREO
// =====================================================
namespace SystemMonitor {
  void feedSoftwareWatchdog() {
    sysState.lastSoftwareWdReset = millis();
    feedWatchdog();
  }
  
  void checkSoftwareWatchdog() {
    unsigned long now = millis();
    if (now - sysState.lastSoftwareWdReset > SOFTWARE_WDT_TIMEOUT) {
      Logger::error("WDT expirado!");
      ESP.restart();
    }
  }
  
  void periodicUpdate() {
    #if USE_DHT
    static unsigned long lastSensorRead = 0;
    unsigned long now = millis();
    if (now - lastSensorRead > 10000) {
      lastSensorRead = now;
      SensorManager::readData();
    }
    #endif
    
    feedSoftwareWatchdog();
  }
}

// =====================================================
// SETUP
// =====================================================
void setup() {
  // 1. Configurar watchdog PRIMERO
  ESP.wdtDisable();
  ESP.wdtEnable(WDTO_8S);
  feedWatchdog();
  
  // 2. Logger
  Logger::begin();
  Logger::info("=== ESP8266 MQTT Client ===");
  feedWatchdog();
  
  // 3. Hardware
  Logger::debug("Configurando LED...");
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LED_OFF_STATE);
  feedWatchdog();
  
  // 4. Topics
  NetManager::buildTopics();
  feedWatchdog();
  
  // 5. DHT si está habilitado
  #if USE_DHT
  SensorManager::init();
  feedWatchdog();
  #endif
  
  // 6. MQTT config
  Logger::debug("Configurando MQTT...");
  mqtt.setServer(BROKER, BROKER_PORT);
  feedWatchdog();
  mqtt.setCallback(CommandHandler::mqttCallback);
  feedWatchdog();
  mqtt.setKeepAlive(60);
  feedWatchdog();
  
  // 7. OTA si está habilitado
  #if ENABLE_OTA
  Logger::debug("Configurando OTA...");
  ArduinoOTA.setHostname(WIFI_HOSTNAME);
  ArduinoOTA.setPassword("ota_password");
  ArduinoOTA.onStart([]() { Logger::warn("OTA inicio"); });
  ArduinoOTA.onEnd([]() { Logger::warn("OTA fin"); });
  ArduinoOTA.onError([](ota_error_t error) { 
    Logger::error("OTA error");
  });
  feedWatchdog();
  #endif
  
  Logger::info("Setup OK");
  Serial.print("Heap libre: ");
  Serial.println(ESP.getFreeHeap());
  feedWatchdog();
}

// =====================================================
// LOOP
// =====================================================
void loop() {
  feedWatchdog(); // Al inicio del loop
  
  #if ENABLE_OTA
  ArduinoOTA.handle();
  feedWatchdog();
  #endif
  
  // Verificar WiFi
  if (WiFi.status() != WL_CONNECTED) {
    if (sysState.wifiConnected) {
      Logger::warn("WiFi desconectado");
      sysState.mqttConnected = false;
    }
    sysState.wifiConnected = false;
    NetManager::connectWiFi();
  } else {
    if (!sysState.wifiConnected) {
      sysState.wifiConnected = true;
      Logger::info("WiFi conectado");
    }
    
    // Verificar MQTT
    if (!mqtt.connected()) {
      if (sysState.mqttConnected) {
        Logger::warn("MQTT desconectado");
      }
      sysState.mqttConnected = false;
      NetManager::connectMQTT();
    } else {
      if (!sysState.mqttConnected) {
        sysState.mqttConnected = true;
        Logger::info("MQTT conectado");
      }
    }
  }
  
  if (sysState.mqttConnected) {
    mqtt.loop();
    feedWatchdog();
  }
  
  SystemMonitor::periodicUpdate();
  SystemMonitor::checkSoftwareWatchdog();
  
  delay(10);
}
