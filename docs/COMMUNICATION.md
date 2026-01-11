# 📡 Diagrama de Comunicación Servidor ↔ Dispositivos

## Visión General

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MQTT BROKER                                           │
└─────────────────────────────────────────────────────────────────────────────────┘

                     ┌─────────────────────────┐
                     │   SERVIDOR (Dashboard)   │
                     └───────────┬─────────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
           ▼                     ▼                     ▼
    ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
    │  DISPOSITIVO│       │  DISPOSITIVO│       │  DISPOSITIVO│
    │     #1      │       │     #2      │       │     #3      │
    └─────────────┘       └─────────────┘       └─────────────┘
```

---

## ⚙️ Configuración MQTT del Servidor

El servidor usa settings configurables para la conexión MQTT:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   CONFIGURACIÓN MQTT DEL SERVIDOR                            │
└─────────────────────────────────────────────────────────────────────────────┘

 Settings almacenados en BD (tabla 'settings'):

 ┌──────────────────────┬──────────────────┬──────────────────────────────────┐
 │ Setting              │ Default          │ Descripción                      │
 ├──────────────────────┼──────────────────┼──────────────────────────────────┤
 │ mqtt_keepalive       │ 60 segundos      │ Intervalo keepalive              │
 │ mqtt_reconnect_delay │ 5 segundos       │ Delay inicial de reconexión      │
 │ mqtt_clean_session   │ true             │ Sesión limpia al conectar        │
 │ mqtt_default_qos     │ 1                │ QoS por defecto (0, 1, 2)        │
 └──────────────────────┴──────────────────┴──────────────────────────────────┘

 Lectura en conexión:
     keepalive = int(config['settings'].get('mqtt_keepalive', 60))
     clean_session = config['settings'].get('mqtt_clean_session', 'true') == 'true'
     qos = int(config['settings'].get('mqtt_default_qos', 1))

 Aplicado en:
     mqtt.Client(..., clean_session=clean_session)
     client.connect(broker, port, keepalive)
     client.reconnect_delay_set(min=delay, max=delay*2)
     client.publish(topic, payload, qos=qos)
```

---

## 📤 Mensajes del Servidor a Dispositivos

### 1. Ping (Latencia)

| Campo | Valor |
|-------|-------|
| **Topic** | `iot/ping/all` |
| **Payload** | `{"cmd": "PING", "time": <timestamp_unix>}` |
| **QoS** | Configurable (default: 1) |

**Propósito:** Medir latencia y verificar que los dispositivos están vivos.

**Frecuencia:** Cada 30 segundos (configurable en Ajustes)

---

### 2. Comando STATUS (Broadcast)

| Campo | Valor |
|-------|-------|
| **Topic** | `iot/cmd/all/all` |
| **Payload** | `{"cmd": "STATUS"}` |
| **QoS** | Configurable (default: 1) |

**Propósito:** Solicitar estado a todos los dispositivos simultáneamente.

---

### 3. Comando STATUS (Un dispositivo específico)

| Campo | Valor |
|-------|-------|
| **Topic** | `iot/cmd/<device_id>/<location>` |
| **Payload** | `{"cmd": "STATUS"}` |
| **QoS** | Configurable (default: 1) |

**Propósito:** Solicitar estado a un dispositivo específico.

**Ejemplo:**
```
Topic: iot/cmd/esp32/salon
Payload: {"cmd": "STATUS"}
```

---

### 4. Comando GET_CONFIG

| Campo | Valor |
|-------|-------|
| **Topic** | `iot/cmd/<device_id>/<location>` |
| **Payload** | `{"cmd": "GET_CONFIG"}` |
| **QoS** | Configurable (default: 1) |

**Propósito:** Solicitar configuración actual del dispositivo.

**Ejemplo:**
```
Topic: iot/cmd/esp32/salon
Payload: {"cmd": "GET_CONFIG"}
```

---

### 5. Comando REBOOT

| Campo | Valor |
|-------|-------|
| **Topic** | `iot/cmd/<device_id>/<location>` |
| **Payload** | `{"cmd": "REBOOT"}` |
| **QoS** | Configurable (default: 1) |

**Propósito:** Reiniciar un dispositivo específico de forma remota.

**Ejemplo:**
```
Topic: iot/cmd/esp32/salon
Payload: {"cmd": "REBOOT"}
```

---

### 6. Tareas Programadas

| Campo | Valor |
|-------|-------|
| **Topic** | Personalizado (configurado en la tarea) |
| **Payload** | Personalizado con soporte de placeholders |
| **QoS** | Configurable (default: 1) |

**Placeholders disponibles:**

| Placeholder | Descripción | Ejemplo |
|-------------|-------------|---------|
| `{{timestamp}}` | Unix timestamp (segundos) | `1704067200` |
| `{{timestamp_ms}}` | Unix timestamp (milisegundos) | `1704067200000` |
| `{{datetime}}` | Fecha y hora completa | `2024-01-01 00:00:00` |
| `{{date}}` | Solo fecha | `2024-01-01` |
| `{{time}}` | Solo hora | `00:00:00` |
| `{{device_id}}` | ID del dispositivo | `esp32` |
| `{{location}}` | Ubicación | `salon` |

**Ejemplo de payload:**
```json
{
  "state": "on",
  "timestamp": "{{timestamp}}",
  "datetime": "{{datetime}}"
}
```

---

### 7. Message Triggers (Acción Publish)

| Campo | Valor |
|-------|-------|
| **Topic** | Personalizado (configurado en el trigger) |
| **Payload** | Personalizado (también soporta placeholders) |
| **QoS** | Configurable (default: 1) |

**Propósito:** Publicar un mensaje automáticamente cuando se recibe otro que cumple una condición.

**Ejemplo:**
```
Topic listening: iot/+/+/status
Condition: temp_c > 30
Action: publish to home/alerts/temperature
Payload: {"alert": "Temperatura alta", "temp_c": "{{temp_c}}"}
```

---

### 8. Publicación Manual

| Campo | Valor |
|-------|-------|
| **Topic** | Cualquier topic configurado por el usuario |
| **Payload** | Texto libre o JSON |
| **QoS** | Configurable (default: 1) |

**Propósito:** Envío de mensajes arbitrarios a topics MQTT.

---

## 📥 Mensajes de Dispositivos al Servidor

### 1. PONG (Respuesta a PING)

| Campo | Valor |
|-------|-------|
| **Topic** | `iot/pong/<device_id>/<location>` |
| **Payload** | `{"cmd": "PONG", "time": <timestamp_unix>}` |

**Ejemplo:**
```
Topic: iot/pong/esp32/salon
Payload: {"cmd": "PONG", "time": 1704067200}
```

**Respuesta del servidor:**
- Calcula latencia: `(ahora - time) * 1000` ms
- Actualiza estado a `"online"`
- Actualiza `"last_seen"` con hora actual
- Resetea contador de `"missed_pings"` a 0

---

### 2. STATUS (Reporte de estado completo)

| Campo | Valor |
|-------|-------|
| **Topic** | `iot/status/<device_id>/<location>` |
| **Payload** | Ver estructura abajo |

**Estructura del payload:**

```json
{
  "status": "online",
  "device": "esp32",
  "location": "salon",
  "ip": "192.168.1.100",
  "uptime": 3600,
  "temp_c": 22.5,
  "temp_h": 55.0,
  "temp_st": 23.1
}
```

**Campos obligatorios:**
- `status`: `"online"` o `"offline"`

**Campos opcionales:**
- `device`: ID del dispositivo
- `location`: Ubicación
- `ip`: Dirección IP
- `uptime`: Tiempo activo en segundos
- `temp_c`: Temperatura en °C
- `temp_h`: Humedad relativa en %
- `temp_st`: Sensación térmica en °C

**Respuesta del servidor:**
1. Registra o actualiza el dispositivo en BD
2. Si es nuevo, notifica al frontend (`known_devices_update`)
3. Actualiza información en memoria
4. Emite `devices_update` al navegador
5. Si hay datos de sensores, guarda en `sensor_data` table
6. Verifica alertas configuradas

---

### 3. STATUS Offline

| Campo | Valor |
|-------|-------|
| **Topic** | `iot/status/<device_id>/<location>` |
| **Payload** | `{"status": "offline"}` |

**Ejemplo:**
```
Topic: iot/status/esp32/salon
Payload: {"status": "offline"}
```

**Respuesta del servidor:**
- Actualiza estado a `"offline"`
- Registra evento `"offline"` en `device_events`
- Verifica alertas (opcional)

---

## 🔍 Búsqueda de Dispositivos en Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   BÚSQUEDA DE DISPOSITIVOS (Frontend)                        │
└─────────────────────────────────────────────────────────────────────────────┘

 Input: deviceSearch (texto de búsqueda)
 Event: input (búsqueda en tiempo real)
 Render: renderDevices(searchTerm)

 Campos filtrados por búsqueda:
   • device.name     (nombre del dispositivo)
   • device.id       (ID del dispositivo)
   • device.location (ubicación)

 Ejemplo de filtrado:
   Input: "esp32" → Muestra solo dispositivos con "esp32" en cualquier campo
   Input: "salon" → Muestra solo dispositivos de la ubicación "salon"
   Input: ""     → Muestra todos los dispositivos permitidos

 Sin resultados:
   Si la búsqueda no encuentra dispositivos, muestra:
   "Sin resultados - Prueba con otros términos de búsqueda"
```

---

## 💾 Sistema de Backup

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SISTEMA DE BACKUP                                    │
└─────────────────────────────────────────────────────────────────────────────┘

 Backup Manual:
   Usuario hace click en "Backup Ahora"
           │
           ▼
   emit('trigger_backup')
           │
           ▼
   BackupManager.create_backup()
           │
           ▼
   1. Lee dashboard.db
   2. Comprime con gzip
   3. Guarda en /backups/dashboard_backup_YYYYMMDD_HHMMSS.db.gz
   4. Elimina backups antiguos (mantiene N)
           │
           ▼
   Emite 'backup_complete' al navegador

 Backup Automático:
   Scheduler ejecuta scheduled_backup_job()
           │
           ▼
   BackupManager.create_backup()
           │
           ▼
   Configurado por settings:
   • auto_backup_enabled: true/false
   • auto_backup_interval: horas entre backups
   • auto_backup_keep: número de backups a mantener

 Compresión:
   • Formato: gzip (.db.gz)
   • Algoritmo: standard gzip compression
```

---

## 🔄 Flujo Completo de Comunicación

### Inicialización de Conexión

```
1. Dispositivo se conecta al broker MQTT
2. Dispositivo publica en: iot/status/<id>/<loc> (STATUS completo)
3. Servidor procesa y actualiza BD
4. Dispositivo queda en lista "known_devices"
5. Si está en whitelist → aparece en dashboard
```

### Ping Periódico (cada 30s por defecto)

```
Servidor ──[PING]──► Broker ──► Todos los dispositivos
        │                    │
        │    (cada dispositivo responde)
        │
        ◄──[PONG]── Broker ◄─── Dispositivo #1
        │                    ◄─── Dispositivo #2
        │                    ◄─── Dispositivo #3
        │
        (actualiza latencia y last_seen de cada uno)
```

### Solicitud de Estado Manual

```
Admin hace click en "Status" en el dashboard
        │
        ▼
Dashboard ──Socket.IO──► Servidor Flask
                              │
                              ▼
                        Servidor MQTT ──[STATUS QoS=N]──► Broker ──► Dispositivo
                                                                  │
                                                                  ▼
                                              Dispositivo ──[STATUS]──► Broker ──► Servidor MQTT
                                                                    │                    │
                                                                    │                    ▼
                                                                    │              Servidor Flask
                                                                    │                    │
                                                                    │                    ▼
                                                                    │              Dashboard (actualiza UI)
```

### Tarea Programada

```
Scheduler (APScheduler) ──► Ejecutar tarea
                                  │
                                  ▼
                            Servidor MQTT ──[topic + payload QoS=N]──► Broker ──► Dispositivo
                                                                          │
                                                                          ▼
                                                                Dispositivo procesa comando
```

### Análisis de Respuesta de Tarea

```
1. Tarea publica mensaje en topic principal
2. Servidor suscribe al topic de respuesta configurado
3. Espera hasta timeout (default 10s)
4. Dispositivo publica en topic de respuesta
5. Servidor evalúa condición:
   - Condición simple: temp_c > 30
   - Expresión: temp_c > 25 and humidity < 60
   - JSONPath: $.status == 'ok'
   │
   ├─► Si cumple (log):   Registra en historial
   ├─► Si cumple (notify): Notificación al navegador
   └─► Si cumple (error):  Notificación de error
```

### Message Trigger

```
Dispositivo ──[publica]──► Broker ──► Servidor MQTT
                                          │
                                          ▼
                                   check_message_triggers()
                                          │
                                          ▼
                                   ¿Topic coincide con patrón?
                                          │
                              ┌──────────────┴──────────────┐
                              │                             │
                              ▼                             ▼
                         [NO]Condición                   [SÍ]Evalúa condición
                            no ejecuta                        │
                                                          ▼
                                                 ¿Condición cumple?
                                                    │
                                     ┌──────────────┴──────────────┐
                                     │                             │
                                     ▼                             ▼
                                [NO]No hace nada           [SÍ]Ejecuta acción
                                                               │
                                               ┌───────────────┴───────────────┐
                                               │                               │
                                               ▼                               ▼
                                         [notify]                     [publish]
                                    Notificación al                    Publica MQTT
                                    navegador                          a otro topic
```

---

## 📋 Suscripciones del Servidor

| Topic | Descripción | Wildcards |
|-------|-------------|-----------|
| `iot/status/+/+` | Recibir estados de dispositivos | Sí (`+`) |
| `iot/pong/+/+` | Recibir respuestas PONG | Sí (`+`) |
| `custom topics` | Temas suscritos manualmente por el usuario | Depende |
| `response topics` | Temas de respuesta de tareas | Depende |

---

## 📊 Resumen de Todos los Comandos MQTT

| Comando | Tipo | Direction | Topic | QoS | Payload |
|---------|------|-----------|-------|-----|---------|
| `PING` | Sistema | Servidor→Todos | `iot/ping/all` | config | `{"cmd": "PING", "time": <ts>}` |
| `PONG` | Sistema | Dispositivo→Servidor | `iot/pong/<id>/<loc>` | 0 | `{"cmd": "PONG", "time": <ts>}` |
| `STATUS` (broadcast) | Sistema | Servidor→Todos | `iot/cmd/all/all` | config | `{"cmd": "STATUS"}` |
| `STATUS` (un dispositivo) | Sistema | Servidor→Uno | `iot/cmd/<id>/<loc>` | config | `{"cmd": "STATUS"}` |
| `GET_CONFIG` | Sistema | Servidor→Uno | `iot/cmd/<id>/<loc>` | config | `{"cmd": "GET_CONFIG"}` |
| `STATUS` (respuesta) | Sistema | Dispositivo→Servidor | `iot/status/<id>/<loc>` | 0 | `{status, device, ip, uptime, ...}` |
| `REBOOT` | Sistema | Servidor→Uno | `iot/cmd/<id>/<loc>` | config | `{"cmd": "REBOOT"}` |
| Tarea programada | Usuario | Servidor→topic | Topic configurable | config | Payload configurable |
| Message Trigger | Automático | Servidor→topic | Topic configurable | config | Payload configurable |
| Publish manual | Usuario | Servidor→topic | Personalizado | config | Personalizado |

---

## 🏠 Estructura de Topics MQTT

```
iot/
├── ping/          # Comandos PING (servidor → dispositivos)
│   └── all        # Para todos los dispositivos
├── pong/          # Respuestas PONG (dispositivo → servidor)
│   └── <id>/<loc> # ID y ubicación del dispositivo
├── cmd/           # Comandos a dispositivos
│   ├── all/all    # Broadcast a todos
│   └── <id>/<loc> # Comando a dispositivo específico
├── status/        # Estados de dispositivos
│   └── <id>/<loc> # Estado de dispositivo específico
└── <custom>/...   # Topics personalizados por el usuario
```

---

## 🔧 Configuración de Topics (src/globals.py)

```python
DEVICE_STATUS_TOPIC = "iot/status/+/+"      # Suscripción a estados
DEVICE_PONG_TOPIC = "iot/pong/+/+"          # Suscripción a PONG
DEVICE_PING_TOPIC = "iot/ping/all"          # Envío de PING
DEVICE_CMD_BROADCAST_TOPIC = "iot/cmd/all/all"  # Broadcast STATUS
DEVICE_CMD_TOPIC_PREFIX = "iot/cmd"         # Prefijo para comandos
```

---

## 📝 Formato de Topics con Wildcards

| Pattern | Descripción | Ejemplo |
|---------|-------------|---------|
| `+` | Un nivel cualquiera | `iot/+/salon` → `iot/esp32/salon`, `iot/sensor1/salon` |
| `#` | Varios niveles | `iot/status/#` → `iot/status/esp32/salon`, `iot/status/sensor1/dormitorio` |

---

## ⚠️ Notas Importantes

1. **QoS:** Todos los comandos usan QoS configurable (default: 1)
2. **Retain:** Solo los mensajes de estado pueden usar retain para persistencia
3. **Autenticación:** Los dispositivos deben estar en la whitelist para aparecer en el dashboard
4. **Tolerancia a fallos:** Si un dispositivo no responde a 2 PINGs (configurable), se marca como offline
5. **Clean Session:** Configurable al conectar al broker MQTT
6. **Reconnect Delay:** Configurable, con backoff automático (delay * 2 como máximo)

---

## 📈 Mejoras Implementadas (Última Actualización)

### MQTT Configuration
- Settings almacenados en BD: keepalive, reconnect_delay, clean_session, default_qos
- QoS configurable por tipo de mensaje (PING, STATUS, tareas, triggers, publish)
- Clean session configurable al conectar

### Device Search
- Búsqueda en tiempo real en el dashboard
- Filtra por nombre, ID y ubicación del dispositivo
- Mensaje "Sin resultados" cuando no hay coincidencias

### Backup System
- Backup manual y automático con compresión gzip
- Rotación automática de backups antiguos
- Settings configurables: enabled, interval (horas), keep (número)

### Settings System
- Todos los settings almacenados en tabla 'settings' (key/value)
- Migración automática de nuevos settings en BD existente
- Lectura desde Python (config['settings']) y JavaScript (state.config.settings)

### Placeholders en Tareas
- Soporte para `{{timestamp}}`, `{{timestamp_ms}}`, `{{datetime}}`, `{{date}}`, `{{time}}`
- Nuevos placeholders: `{{device_id}}`, `{{location}}`
- Procesamiento automático en `src/task_utils.py:process_placeholders()`

### Análisis de Respuesta de Tareas
- Espera respuesta del dispositivo después de publicar
- Condiciones soportadas:
  - Simple: `temp_c > 30`
  - Expresión: `temp_c > 25 and humidity < 60`
  - JSONPath: `$.status == 'ok'`
- Acciones: log, notify, error

### Message Triggers
- Disparadores basados en mensajes MQTT entrantes
- Soporte para wildcards (`+` y `#`) en topics
- Condiciones evaluadas sobre el payload JSON
- Acciones: notificación o publicación MQTT con QoS configurable
