/*
 * ==============================================================================
 * PROYECTO: EcoGrow 2.0 — Torre Hidropónica Vertical Optimizada
 * CONTROLADOR: ESP32 (DevKit V1 / WROOM-32)
 * AUTOR: AJTecnology (Estándar Cero Retrabajo Evitable)
 * FECHA: 2026-10-05
 * ==============================================================================
 * SENSORES ESENCIALES INCORPORADOS:
 * 1. Nivel de Agua Continuo (% y Litros): Sensor Ultrasónico JSN-SR04T (sin contacto)
 * 2. Nutrientes (TDS/PPM): Con muestreo anti-electrólisis (GPIO 18) y compensación térmica
 * 3. Acidez/Alcalinidad (pH): Sonda analógica con calibración en 2 puntos
 * 4. Temperatura de Solución: Sonda sumergible DS18B20
 * ==============================================================================
 */

#include <WiFi.h>
#include <WiFiProv.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <esp_bt.h>
#include "safety.h"

// Evitar que el core de Arduino libere la memoria Bluetooth (BTDM) al arrancar
extern "C" bool btInUse() {
    return true;
}

// ------------------------------------------------------------------------------
// ASIGNACIÓN DE PINES (EXPEDIENTE TÉCNICO G2 OPTIMIZADO)
// ------------------------------------------------------------------------------
const uint8_t PIN_BOMBA       = 25; // Gate MOSFET bomba elevadora de columna
const uint8_t PIN_US_TRIG     = 5;  // Trigger sensor ultrasónico JSN-SR04T
const uint8_t PIN_US_ECHO     = 19; // Echo sensor ultrasónico JSN-SR04T (con divisor 1k/2k)
const uint8_t PIN_TDS_ANALOG  = 34; // Entrada analógica sensor TDS (ADC1)
const uint8_t PIN_PH_ANALOG   = 35; // Entrada analógica sensor pH (ADC1)
const uint8_t PIN_TDS_PWR     = 18; // Alimentación pulsada sensor TDS (anti-electrólisis)
const uint8_t PIN_TEMP_AGUA   = 32; // Sonda OneWire DS18B20 temperatura agua
const uint8_t PIN_LED_ESTADO  = 2;  // LED on-board de actividad
const uint8_t PIN_BOTON_RESET = 0;  // Botón físico BOOT (recuperación 5s)
const uint8_t PIN_BTN_BOMBA   = 26; // Botón físico bomba (conmutación manual)
const uint8_t PIN_BTN_MODO    = 27; // Botón físico modo (AUTO / MANUAL)

// ------------------------------------------------------------------------------
// RED Y CONFIGURACIÓN: config.h local, excluido de git
#if __has_include("config.h")
#include "config.h"
#endif

#ifndef ECOGROW_AP_NAME
#include "config.h.example"
#endif

// Parámetros de geometría del depósito base
const float TANQUE_ALTURA_CM   = ECOGROW_TANK_HEIGHT_CM; // Altura total del depósito
const float TANQUE_DIST_MIN_CM = ECOGROW_TANK_MIN_DISTANCE_CM; // Zona muerta (tanque al 100%)
const float TANQUE_CAPACIDAD_L = ECOGROW_TANK_CAPACITY_L; // Volumen nominal en litros

WebServer server(80);
Preferences prefs;
OneWire waterBus(PIN_TEMP_AGUA);
DallasTemperature waterSensors(&waterBus);
const char* ssid_ap = ECOGROW_AP_NAME;
const char* password_ap = ECOGROW_AP_PASSWORD;
const char* ssid_sta = ECOGROW_STA_NAME;
const char* password_sta = ECOGROW_STA_PASSWORD;

// ------------------------------------------------------------------------------
// ESTRUCTURAS Y VARIABLES DE CULTIVO
// ------------------------------------------------------------------------------
struct RecetaCultivo {
  const char* nombre;
  float ppmMin;
  float ppmMax;
  float phMin;
  float phMax;
  uint16_t timerOnMin;
  uint16_t timerOffMin;
};

const RecetaCultivo RECETAS[] = {
  {"Lechuga",  560.0,  840.0, 5.8, 6.2, 10, 20},
  {"Espinaca", 700.0, 1050.0, 6.0, 6.5, 10, 25},
  {"Albahaca", 700.0, 1120.0, 5.5, 6.2, 12, 20},
  {"Frutilla", 980.0, 1400.0, 5.5, 6.5, 15, 30}
};
const uint8_t TOTAL_RECETAS = 4;
uint8_t recetaActivaIdx = 0;

enum ModoOperacion { MODO_AUTO = 0, MODO_MANUAL = 1 };
ModoOperacion modoActual = MODO_AUTO;

bool estadoBomba = false;
bool nivelAguaOk = false;
String mensajeAlerta = "Torre en Funcionamiento Normal";

uint16_t tiempoOnMinutos  = 10;
uint16_t tiempoOffMinutos = 20;

// Factores de Calibración
float phCalibVoltMid = 1.65;
float phCalibPendiente = 3.5;
float tdsFactor = 1.0;

// Mediciones
float tempAguaC = NAN;
float valorTdsPpm = NAN;
float valorPh = NAN;
float nivelAguaPct = NAN; // Porcentaje de llenado (0 a 100%)
float litrosActuales = NAN; // Volumen en litros

const char* BLE_POP = "ecogrow20"; // Proof of Possession / PIN BLE y contraseña por defecto

#ifndef ECOGROW_BACKEND_URL
#define ECOGROW_BACKEND_URL "http://179.236.74.107:8000"
#endif

#ifndef ECOGROW_SENSOR_API_TOKEN
#define ECOGROW_SENSOR_API_TOKEN "ecogrow_sensor_secret_token_2026"
#endif

#ifndef ECOGROW_TORRE_CODIGO
#define ECOGROW_TORRE_CODIGO "TORRE-001"
#endif

// Temporizadores y Sincronización Remota
unsigned long timestampCiclo = 0;
unsigned long duracionCicloMs = 0;
unsigned long ultimoMuestreoSensores = 0;
const unsigned long INTERVALO_SENSADO_MS = 2500;
unsigned long ultimoSyncVps = 0;
const unsigned long INTERVALO_SYNC_VPS_MS = 10000;
String ultimoComandoId = "";
String estadoUltimoComando = "NONE";

// ------------------------------------------------------------------------------
// PWA MÓVIL EN PROGMEM
// ------------------------------------------------------------------------------
const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EcoGrow · Torre local</title>
<style>body{font:16px system-ui;background:#f1f6f2;color:#173b29;max-width:980px;margin:auto;padding:24px}button,select{font:inherit;min-height:48px;padding:10px;border:1px solid #92aa99;border-radius:10px}button{background:#195c3d;color:white}button:disabled{opacity:.45}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px}.card{background:white;padding:20px;border:1px solid #d1dfd4;border-radius:16px}.value{font-size:28px;font-weight:650}nav{display:flex;gap:12px;flex-wrap:wrap}#message{min-height:28px}h1{font-size:28px}</style>
<header><p>EcoGrow 2.0 · Conexión WiFi local</p><h1>Tu torre, bajo control</h1><p id="connection" role="status">Conectando…</p></header>
<p id="message" role="alert"></p><main class="grid"><section class="card"><h2>Agua</h2><div id="level" class="value">Sin dato</div><p id="liters">Sin dato de volumen calibrado</p></section><section class="card"><h2>pH</h2><div id="ph" class="value">Sin dato</div></section><section class="card"><h2>TDS</h2><div id="tds" class="value">Sin dato</div></section><section class="card"><h2>Temperatura del agua</h2><div id="temp" class="value">Sin dato</div></section></main>
<section class="card" style="margin-top:16px"><h2>Cascada y receta</h2><p id="pump">Esperando estado</p><p id="timer"></p><nav><button id="on" disabled>Iniciar cascada</button><button id="off" disabled>Detener cascada</button><button id="mode" disabled>Cambiar modo</button><label>Receta <select id="recipe" disabled><option value="0">Lechuga</option><option value="1">Espinaca</option><option value="2">Albahaca</option><option value="3">Frutilla</option></select></label></nav><p id="ranges"></p><p>El estado de bomba corresponde a la salida del controlador; no mide caudal.</p></section>
<script>
let state=null,busy=false,connected=false;const el=id=>document.getElementById(id);const format=(v,u)=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(1)+' '+u:'Sin dato';
function controls(){el('on').disabled=busy||!connected||!state?.water_level_ok;['off','mode','recipe'].forEach(id=>el(id).disabled=busy||!connected)}
async function refresh(){try{const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw Error();state=await r.json();connected=true;el('connection').textContent='Torre conectada · '+new Date().toLocaleTimeString();el('level').textContent=format(state.water_level_pct,'%');el('liters').textContent=format(state.water_liters,'L');el('ph').textContent=format(state.ph_val,'');el('tds').textContent=format(state.tds_ppm,'ppm');el('temp').textContent=format(state.temp_water,'°C');el('pump').textContent=(state.pump_state?'Cascada activa':'Bomba detenida')+' · '+state.pump_mode;el('timer').textContent=state.pump_mode==='AUTO'?'Tiempo restante: '+state.time_left_sec+' s':'';el('message').textContent=state.alert;el('recipe').value=state.recipe.idx;el('ranges').textContent=state.recipe.name+' · pH '+state.recipe.ph_min+'–'+state.recipe.ph_max+' · TDS '+state.recipe.ppm_min+'–'+state.recipe.ppm_max+' ppm';}catch{connected=false;el('connection').textContent='Sin conexión · datos anteriores';}controls()}
async function command(path,body){busy=true;controls();try{const r=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok){const e=await r.json();throw Error(e.error||'No se pudo aplicar el cambio')}await refresh()}catch(e){el('message').textContent=e.message}finally{busy=false;controls()}}
el('on').onclick=()=>command('pump',{on:true});el('off').onclick=()=>command('pump',{on:false});el('mode').onclick=()=>command('mode',{mode:state.pump_mode==='AUTO'?'MANUAL':'AUTO'});el('recipe').onchange=()=>command('recipe',{recipe_idx:Number(el('recipe').value)});setInterval(()=>{if(!document.hidden&&!busy)refresh()},2500);refresh();
</script></html>)rawliteral";

// ------------------------------------------------------------------------------
// SENSADO CONTINUO DE NIVEL CON JSN-SR04T
// ------------------------------------------------------------------------------

float medirNivelUltrasonico(float& litrosOut) {
  digitalWrite(PIN_US_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_US_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_US_TRIG, LOW);

  long duracionUs = pulseIn(PIN_US_ECHO, HIGH, 25000);
  if (duracionUs == 0) {
    litrosOut = NAN;
    return NAN;
  }

  float distanciaCm = (duracionUs * 0.0343) / 2.0;
  if (!ECOGROW_TANK_CALIBRATED || TANQUE_ALTURA_CM <= TANQUE_DIST_MIN_CM || distanciaCm < TANQUE_DIST_MIN_CM || distanciaCm > TANQUE_ALTURA_CM + 2.0) { litrosOut = NAN; return NAN; }
  if (distanciaCm < TANQUE_DIST_MIN_CM) distanciaCm = TANQUE_DIST_MIN_CM;
  if (distanciaCm > TANQUE_ALTURA_CM) distanciaCm = TANQUE_ALTURA_CM;

  float pct = ((TANQUE_ALTURA_CM - distanciaCm) / (TANQUE_ALTURA_CM - TANQUE_DIST_MIN_CM)) * 100.0;
  if (pct < 0.0) pct = 0.0;
  if (pct > 100.0) pct = 100.0;

  litrosOut = (pct / 100.0) * TANQUE_CAPACIDAD_L;
  return pct;
}

// ------------------------------------------------------------------------------
// SENSADO DE NUTRIENTES Y PH
// ------------------------------------------------------------------------------

float leerTdsCompensado(float tempAgua) {
  if (!ECOGROW_TDS_CALIBRATED || !isfinite(tempAgua)) return NAN;
  digitalWrite(PIN_TDS_PWR, HIGH);
  delay(120);

  long sumaRaw = 0;
  for (int i = 0; i < 20; i++) {
    sumaRaw += analogRead(PIN_TDS_ANALOG);
    delay(2);
  }
  digitalWrite(PIN_TDS_PWR, LOW);

  float adcPromedio = (float)sumaRaw / 20.0;
  float voltaje = (adcPromedio / 4095.0) * 3.3;

  float coeficienteTemp = 1.0 + 0.02 * (tempAgua - 25.0);
  float voltajeCompensado = voltaje / coeficienteTemp;

  float tds = (133.42 * pow(voltajeCompensado, 3) - 255.86 * pow(voltajeCompensado, 2) + 857.39 * voltajeCompensado) * 0.5 * tdsFactor;
  if (tds < 0.0) tds = 0.0;
  return tds;
}

float leerPhSolucion() {
  if (!ECOGROW_PH_CALIBRATED) return NAN;
  long sumaRaw = 0;
  for (int i = 0; i < 25; i++) {
    sumaRaw += analogRead(PIN_PH_ANALOG);
    delay(2);
  }
  float adcPromedio = (float)sumaRaw / 25.0;
  float voltaje = (adcPromedio / 4095.0) * 3.3;

  float ph = 7.0 + ((phCalibVoltMid - voltaje) * phCalibPendiente);
  if (ph < 0.0) ph = 0.0;
  if (ph > 14.0) ph = 14.0;
  return ph;
}

void verificarSeguridadAgua() {
  nivelAguaOk = safeWaterLevel(nivelAguaPct, ECOGROW_TANK_CALIBRATED);
  if (!nivelAguaOk) {
    digitalWrite(PIN_BOMBA, LOW); digitalWrite(PIN_LED_ESTADO, LOW);
    estadoBomba = false;
    mensajeAlerta = "Nivel crítico o no validado. Bomba protegida.";
  }
}

void encenderBomba() {
  if (!nivelAguaOk) {
    digitalWrite(PIN_BOMBA, LOW);
    estadoBomba = false;
    mensajeAlerta = "Imposible encender: Depósito sin agua";
    return;
  }
  digitalWrite(PIN_BOMBA, HIGH);
  digitalWrite(PIN_LED_ESTADO, HIGH);
  estadoBomba = true;
  mensajeAlerta = "Cascada vertical en recirculación";
}

void apagarBomba() {
  digitalWrite(PIN_BOMBA, LOW);
  digitalWrite(PIN_LED_ESTADO, LOW);
  estadoBomba = false;
  if (nivelAguaOk) {
    mensajeAlerta = "Reposo radicular y oxigenación";
  }
}

// ------------------------------------------------------------------------------
// CONTROLADORES DE RUTA DEL SERVIDOR WEB
// ------------------------------------------------------------------------------

bool authorized() {
  server.sendHeader("Cache-Control", "no-store");
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, Origin");
  // Seguridad fail-closed: si no se configuró credencial explícita en config.h,
  // se exige usuario 'admin' y contraseña igual al PIN de posesión BLE (BLE_POP).
  const char* expectedUser = (strlen(ECOGROW_CONTROL_USER) > 0) ? ECOGROW_CONTROL_USER : "admin";
  const char* expectedPass = (strlen(ECOGROW_CONTROL_PASSWORD) >= 8) ? ECOGROW_CONTROL_PASSWORD : BLE_POP;
  if (!server.authenticate(expectedUser, expectedPass)) {
    server.requestAuthentication();
    return false;
  }
  return true;
}

bool parseCommand(JsonDocument& doc) {
  if (!authorized()) return false;
  if (server.header("Content-Type") != "application/json" || server.arg("plain").length() > 256) {
    server.send(400,"application/json","{\"error\":\"Formato JSON requerido\"}");return false;
  }
  String origin = server.header("Origin");
  if (origin.length() && origin != "http://" + server.hostHeader() && !origin.startsWith("http://192.168.") && !origin.startsWith("http://10.") && !origin.startsWith("http://localhost")) {
    server.send(403,"application/json","{\"error\":\"Origen no autorizado\"}");return false;
  }
  if (deserializeJson(doc, server.arg("plain")) || !doc.is<JsonObject>()) {
    server.send(400,"application/json","{\"error\":\"JSON inválido\"}");return false;
  }
  return true;
}

void handleRoot() { if (authorized()) server.send_P(200,"text/html",INDEX_HTML); }

void sendStatus() {
  JsonDocument d;
  unsigned long passed=millis()-timestampCiclo;
  d["pump_state"]=estadoBomba; d["pump_mode"]=modoActual==MODO_AUTO?"AUTO":"MANUAL";
  d["water_level_ok"]=nivelAguaOk;
  if(isfinite(nivelAguaPct)) d["water_level_pct"]=nivelAguaPct; else d["water_level_pct"]=nullptr;
  if(isfinite(litrosActuales)) d["water_liters"]=litrosActuales; else d["water_liters"]=nullptr;
  if(isfinite(valorTdsPpm)) d["tds_ppm"]=valorTdsPpm; else d["tds_ppm"]=nullptr;
  if(isfinite(valorPh)) d["ph_val"]=valorPh; else d["ph_val"]=nullptr;
  if(isfinite(tempAguaC)) d["temp_water"]=tempAguaC; else d["temp_water"]=nullptr;
  d["time_left_sec"]=(modoActual==MODO_AUTO&&passed<duracionCicloMs)?(duracionCicloMs-passed)/1000:0;
  d["alert"]=mensajeAlerta; d["protocol_version"]=1; d["uptime_ms"]=millis();
  const auto& r=RECETAS[recetaActivaIdx];auto recipe=d["recipe"].to<JsonObject>();
  recipe["idx"]=recetaActivaIdx;recipe["name"]=r.nombre;recipe["ppm_min"]=r.ppmMin;recipe["ppm_max"]=r.ppmMax;recipe["ph_min"]=r.phMin;recipe["ph_max"]=r.phMax;
  String out;serializeJson(d,out);server.send(200,"application/json",out);
}
void handleStatus(){if(authorized())sendStatus();}
void handlePumpControl(){
  JsonDocument d;if(!parseCommand(d))return;
  if(!d["on"].is<bool>()){server.send(400,"application/json","{\"error\":\"on debe ser booleano\"}");return;}
  // Refrescar nivel antes de aceptar un encendido; nunca reutilizar un nivel antiguo.
  nivelAguaPct=medirNivelUltrasonico(litrosActuales);verificarSeguridadAgua();
  if(d["on"].as<bool>()&&!nivelAguaOk){server.send(409,"application/json","{\"error\":\"Nivel no seguro\"}");return;}
  modoActual=MODO_MANUAL;timestampCiclo=millis();
  if(d["on"].as<bool>())encenderBomba();else apagarBomba();sendStatus();
}
void handleModeControl(){
  JsonDocument d;if(!parseCommand(d))return;
  const char* mode=d["mode"]|"";
  if(strcmp(mode,"AUTO")&&strcmp(mode,"MANUAL")){server.send(400,"application/json","{\"error\":\"Modo inválido\"}");return;}
  modoActual=!strcmp(mode,"AUTO")?MODO_AUTO:MODO_MANUAL;
  apagarBomba();timestampCiclo=millis();duracionCicloMs=tiempoOffMinutos*60000UL;sendStatus();
}
void handleRecipeControl(){
  JsonDocument d;if(!parseCommand(d))return;
  if(!d["recipe_idx"].is<int>()||!validRecipe(d["recipe_idx"].as<int>(),TOTAL_RECETAS)){server.send(400,"application/json","{\"error\":\"Receta inválida\"}");return;}
  recetaActivaIdx=d["recipe_idx"].as<int>();tiempoOnMinutos=RECETAS[recetaActivaIdx].timerOnMin;tiempoOffMinutos=RECETAS[recetaActivaIdx].timerOffMin;
  prefs.putUChar("recipe",recetaActivaIdx);prefs.putUInt("t_on",tiempoOnMinutos);prefs.putUInt("t_off",tiempoOffMinutos);
  apagarBomba();timestampCiclo=millis();duracionCicloMs=tiempoOffMinutos*60000UL;sendStatus();
}

// ------------------------------------------------------------------------------
// ENLACE Y SINCRONIZACIÓN REMOTA CON BACKEND / COOLIFY
// ------------------------------------------------------------------------------
void sincronizarConVps() {
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClient client;
  HTTPClient http;

  String endpoint = String(ECOGROW_BACKEND_URL) + "/api/iot/sync";
  if (!http.begin(client, endpoint)) {
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Token", ECOGROW_SENSOR_API_TOKEN);
  http.setTimeout(4000);

  JsonDocument txDoc;
  txDoc["torre_codigo"] = ECOGROW_TORRE_CODIGO;
  txDoc["dispositivo"] = "esp32_ecogrow2";
  txDoc["rele_principal"] = estadoBomba;
  if (!isnan(tempAguaC)) txDoc["temperatura_agua"] = tempAguaC;
  if (!isnan(valorPh)) txDoc["ph"] = valorPh;
  if (!isnan(valorTdsPpm)) txDoc["tds_ppm"] = valorTdsPpm;
  if (!isnan(nivelAguaPct)) txDoc["nivel_agua"] = nivelAguaPct;
  txDoc["modo"] = (modoActual == MODO_AUTO) ? "automatico" : "manual";
  txDoc["receta_idx"] = recetaActivaIdx;
  if (ultimoComandoId.length() > 0) {
    txDoc["last_command_id"] = ultimoComandoId;
    txDoc["last_command_status"] = estadoUltimoComando;
  }

  String payload;
  serializeJson(txDoc, payload);

  int httpCode = http.POST(payload);
  if (httpCode == 200 || httpCode == 201) {
    String resp = http.getString();
    JsonDocument rxDoc;
    if (!deserializeJson(rxDoc, resp)) {
      if (rxDoc["command"].is<JsonObject>()) {
        JsonObject cmd = rxDoc["command"];
        String cmdId = cmd["id"].as<String>();
        long expiresAt = cmd["expires_at"].as<long>();
        long nowEpoch = cmd["now"].as<long>();

        if (cmdId != ultimoComandoId) {
          if (expiresAt > 0 && nowEpoch > expiresAt) {
            Serial.printf("[VPS Command] Comando %s expirado. Descartado.\n", cmdId.c_str());
            ultimoComandoId = cmdId;
            estadoUltimoComando = "EXPIRED";
          } else {
            String action = cmd["action"].as<String>();
            Serial.printf("[VPS Command] Recibida orden: %s (id: %s)\n", action.c_str(), cmdId.c_str());
            if (action == "PUMP_ON") {
              if (nivelAguaOk) {
                encenderBomba();
                modoActual = MODO_MANUAL;
                timestampCiclo = millis();
                duracionCicloMs = tiempoOnMinutos * 60000UL;
                estadoUltimoComando = "EXECUTED";
              } else {
                estadoUltimoComando = "REJECTED_LOW_WATER";
                Serial.println("[VPS Command] Rechazado: Nivel insuficiente o no calibrado");
              }
            } else if (action == "PUMP_OFF") {
              apagarBomba();
              timestampCiclo = millis();
              duracionCicloMs = tiempoOffMinutos * 60000UL;
              estadoUltimoComando = "EXECUTED";
            } else if (action == "SET_MODE") {
              String m = cmd["mode"].as<String>();
              if (m == "AUTO") {
                modoActual = MODO_AUTO;
                apagarBomba();
                timestampCiclo = millis();
                duracionCicloMs = tiempoOffMinutos * 60000UL;
                estadoUltimoComando = "EXECUTED";
              } else if (m == "MANUAL") {
                modoActual = MODO_MANUAL;
                apagarBomba();
                timestampCiclo = millis();
                estadoUltimoComando = "EXECUTED";
              }
            } else if (action == "SET_RECIPE") {
              int rIdx = cmd["recipe_idx"].as<int>();
              if (validRecipe(rIdx, TOTAL_RECETAS)) {
                recetaActivaIdx = rIdx;
                tiempoOnMinutos = RECETAS[recetaActivaIdx].timerOnMin;
                tiempoOffMinutos = RECETAS[recetaActivaIdx].timerOffMin;
                prefs.putUChar("recipe", recetaActivaIdx);
                prefs.putUInt("t_on", tiempoOnMinutos);
                prefs.putUInt("t_off", tiempoOffMinutos);
                apagarBomba();
                timestampCiclo = millis();
                duracionCicloMs = tiempoOffMinutos * 60000UL;
                estadoUltimoComando = "EXECUTED";
              }
            }
            ultimoComandoId = cmdId;
          }
        }
      }
    }
  }
  http.end();
}

void SysProvEvent(arduino_event_t *sys_event) {
  switch (sys_event->event_id) {
    case ARDUINO_EVENT_WIFI_STA_GOT_IP:
      Serial.print("[BLE Prov] WiFi Conectado! IP: ");
      Serial.println(IPAddress(sys_event->event_info.got_ip.ip_info.ip.addr));
      break;
    case ARDUINO_EVENT_PROV_START:
      Serial.println("[BLE Prov] Anuncio BLE iniciado. Configura WiFi desde la app EcoGrow.");
      break;
    case ARDUINO_EVENT_PROV_CRED_RECV:
      Serial.println("[BLE Prov] Credenciales WiFi recibidas por BLE.");
      break;
    case ARDUINO_EVENT_PROV_CRED_SUCCESS:
      Serial.println("[BLE Prov] Credenciales validadas con éxito.");
      break;
    case ARDUINO_EVENT_PROV_END:
      Serial.println("[BLE Prov] Aprovisionamiento finalizado.");
      break;
    default:
      break;
  }
}

// ------------------------------------------------------------------------------
// SETUP
// ------------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\n=== EcoGrow 2.0: Torre Vertical Optimizada ===");

  // Configuración de Pines
  pinMode(PIN_BOMBA, OUTPUT);
  pinMode(PIN_US_TRIG, OUTPUT);
  pinMode(PIN_US_ECHO, INPUT);
  pinMode(PIN_TDS_PWR, OUTPUT);
  pinMode(PIN_LED_ESTADO, OUTPUT);
  pinMode(PIN_TDS_ANALOG, INPUT);
  pinMode(PIN_PH_ANALOG, INPUT);
  pinMode(PIN_BOTON_RESET, INPUT_PULLUP);
  pinMode(PIN_BTN_BOMBA, INPUT_PULLUP);
  pinMode(PIN_BTN_MODO, INPUT_PULLUP);

  digitalWrite(PIN_BOMBA, LOW);
  digitalWrite(PIN_US_TRIG, LOW);
  digitalWrite(PIN_TDS_PWR, LOW);
  digitalWrite(PIN_LED_ESTADO, LOW);

  prefs.begin("ecogrow", false);
  recetaActivaIdx = prefs.getUChar("recipe", 0);
  if (!validRecipe(recetaActivaIdx,TOTAL_RECETAS)) recetaActivaIdx=0;
  tiempoOnMinutos = prefs.getUInt("t_on", RECETAS[recetaActivaIdx].timerOnMin);
  tiempoOffMinutos = prefs.getUInt("t_off", RECETAS[recetaActivaIdx].timerOffMin);
  phCalibVoltMid = prefs.getFloat("ph_vmid", 1.65);
  phCalibPendiente = prefs.getFloat("ph_slope", 3.5);
  tdsFactor = prefs.getFloat("tds_f", 1.0);

  waterSensors.begin();
  waterSensors.setResolution(10);
  waterSensors.setWaitForConversion(false);
  waterSensors.requestTemperatures();
  // Primera medición de nivel ultrasónico
  nivelAguaPct = medirNivelUltrasonico(litrosActuales);
  verificarSeguridadAgua();

  // Aprovisionamiento WiFi mediante Bluetooth BLE (Espressif WiFiProv)
  WiFi.onEvent(SysProvEvent);
  char ble_service_name[24];
  uint8_t mac[6];
  WiFi.macAddress(mac);
  snprintf(ble_service_name, sizeof(ble_service_name), "PROV_EcoGrow_%02X%02X", mac[4], mac[5]);

  // beginProvision inicia BLE sin liberar memoria BT para evitar error ESP_ERR_INVALID_STATE (259)
  WiFiProv.beginProvision(WIFI_PROV_SCHEME_BLE, WIFI_PROV_SCHEME_HANDLER_NONE, WIFI_PROV_SECURITY_1, BLE_POP, ble_service_name, NULL, NULL, false);

  // WiFi Dual fallback si hay credenciales configuradas
  if (strlen(password_ap)>=12) {
    WiFi.softAP(ssid_ap, password_ap);
    Serial.print("Punto de Acceso iniciado: ");
    Serial.println(ssid_ap);
  }

  const char* headers[]={"Content-Type","Origin"};
  server.collectHeaders(headers,2);
  // Rutas Web
  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/api/pump", HTTP_POST, handlePumpControl);
  server.on("/api/mode", HTTP_POST, handleModeControl);
  server.on("/api/recipe", HTTP_POST, handleRecipeControl);

  server.begin();
  Serial.println("Servidor Web EcoGrow iniciado en puerto 80.");

  timestampCiclo = millis();
  apagarBomba();
  modoActual=MODO_MANUAL;
  duracionCicloMs=tiempoOffMinutos*60000UL;
}

// ------------------------------------------------------------------------------
// LOOP PRINCIPAL (NON-BLOCKING)
// ------------------------------------------------------------------------------

void loop() {
  server.handleClient();

  // Botón físico de recuperación (GPIO 0 / BOOT presionado 5s continuo)
  static unsigned long botonPresionadoInicio = 0;
  if (digitalRead(PIN_BOTON_RESET) == LOW) {
    if (botonPresionadoInicio == 0) botonPresionadoInicio = millis();
    if (millis() - botonPresionadoInicio >= 5000) {
      Serial.println("[RESET] Botón presionado 5s. Borrando NVS y reiniciando aprovisionamiento BLE...");
      prefs.clear();
      WiFi.disconnect(true, true);
      delay(500);
      ESP.restart();
    }
  } else {
    botonPresionadoInicio = 0;
  }

  // Pulsador Físico 1: Bomba manual (GPIO 26)
  static unsigned long ultimoDebounceBomba = 0;
  static bool estadoPrevBomba = HIGH;
  bool lecturaBomba = digitalRead(PIN_BTN_BOMBA);
  if (lecturaBomba == LOW && estadoPrevBomba == HIGH && (millis() - ultimoDebounceBomba > 250)) {
    ultimoDebounceBomba = millis();
    modoActual = MODO_MANUAL;
    timestampCiclo = millis();
    if (!estadoBomba) {
      nivelAguaPct = medirNivelUltrasonico(litrosActuales);
      verificarSeguridadAgua();
      if (nivelAguaOk) {
        encenderBomba();
        Serial.println("[BOTÓN FÍSICO] Bomba encendida (modo MANUAL)");
      } else {
        Serial.println("[BOTÓN FÍSICO] Encendido bloqueado: Depósito sin agua");
        for (int i = 0; i < 3; i++) {
          digitalWrite(PIN_LED_ESTADO, HIGH); delay(40);
          digitalWrite(PIN_LED_ESTADO, LOW); delay(40);
        }
      }
    } else {
      apagarBomba();
      Serial.println("[BOTÓN FÍSICO] Bomba apagada");
    }
  }
  estadoPrevBomba = lecturaBomba;

  // Pulsador Físico 2: Modo AUTO/MANUAL (GPIO 27)
  static unsigned long ultimoDebounceModo = 0;
  static bool estadoPrevModo = HIGH;
  bool lecturaModo = digitalRead(PIN_BTN_MODO);
  if (lecturaModo == LOW && estadoPrevModo == HIGH && (millis() - ultimoDebounceModo > 250)) {
    ultimoDebounceModo = millis();
    if (modoActual == MODO_AUTO) {
      modoActual = MODO_MANUAL;
      apagarBomba();
      Serial.println("[BOTÓN FÍSICO] Modo conmutado a MANUAL");
    } else {
      modoActual = MODO_AUTO;
      apagarBomba();
      timestampCiclo = millis();
      duracionCicloMs = tiempoOffMinutos * 60000UL;
      Serial.println("[BOTÓN FÍSICO] Modo conmutado a AUTO");
    }
  }
  estadoPrevModo = lecturaModo;

  uint32_t ahora = millis();

  // Muestreo de sensores cada 2.5 segundos
  if (ahora - ultimoMuestreoSensores >= INTERVALO_SENSADO_MS) {
    ultimoMuestreoSensores = ahora;
    nivelAguaPct = medirNivelUltrasonico(litrosActuales);
    verificarSeguridadAgua();
    tempAguaC = waterSensors.getTempCByIndex(0);
    if (tempAguaC == DEVICE_DISCONNECTED_C || tempAguaC < 0 || tempAguaC > 60) tempAguaC = NAN;
    waterSensors.requestTemperatures();
    valorTdsPpm = leerTdsCompensado(tempAguaC);
    valorPh     = leerPhSolucion();
  }

  // Máquina de estados de la cascada vertical (segura frente a rollover y sin saltos de reposo)
  if (modoActual == MODO_AUTO) {
    if (cycleElapsed(ahora, timestampCiclo, duracionCicloMs)) {
      timestampCiclo = millis();
      if (estadoBomba) {
        apagarBomba();
        duracionCicloMs = tiempoOffMinutos * 60000UL;
        Serial.println("[AUTO] Cascada finalizada. Iniciando oxigenación y reposo radicular.");
      } else {
        if (nivelAguaOk) {
          encenderBomba();
          duracionCicloMs = tiempoOnMinutos * 60000UL;
          Serial.println("[AUTO] Iniciando ciclo de cascada vertical.");
        } else {
          duracionCicloMs = 30000UL;
          Serial.println("[AUTO] Cascada cancelada: Nivel insuficiente en depósito (<10%).");
        }
      }
    }
  } else {
    // MODO MANUAL: protección de apagado por tiempo máximo de seguridad
    if (manualLimitExceeded(estadoBomba, ahora, timestampCiclo, tiempoOnMinutos * 60000UL)) {
      apagarBomba();
      timestampCiclo = millis();
      Serial.println("[MANUAL] Límite de tiempo máximo alcanzado. Bomba apagada por seguridad.");
    }
  }

  // Sincronización periódica con el backend / VPS
  if (ahora - ultimoSyncVps >= INTERVALO_SYNC_VPS_MS) {
    ultimoSyncVps = ahora;
    sincronizarConVps();
  }
}
