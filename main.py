import json
import time
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# ==========================================
# MQTT CONFIGURATION
# ==========================================
DEFAULT_BROKER   = "a1fdaff2.ala.eu-central-1.emqxsl.com"
DEFAULT_PORT     = 8883
DEFAULT_USER     = "esp32_user"
DEFAULT_PASSWORD = "Fireguard123!"

TOPIC_SENSORS    = "fireguard/sensors"
TOPIC_STATUS     = "fireguard/status"
TOPIC_ALERTS     = "fireguard/alerts"

sys_data = {
    "smoke_pct": 0.0,
    "temperature": 0.0,
    "humidity": 0.0,
    "flame_detected": False,
    "state_name": "CONNECTING...",
    "suppression_valve": False,
    "buzzer_active": False
}

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        sys_data["state_name"] = "CONNECTED"
        client.subscribe([(TOPIC_SENSORS, 0), (TOPIC_STATUS, 0), (TOPIC_ALERTS, 0)])
        socketio.emit('update_data', sys_data)

def on_disconnect(client, userdata, rc):
    sys_data["state_name"] = "OFFLINE"
    socketio.emit('update_data', sys_data)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        if msg.topic == TOPIC_SENSORS:
            sys_data["smoke_pct"] = payload.get("smoke_pct", sys_data["smoke_pct"])
            sys_data["flame_detected"] = payload.get("flame_detected", sys_data["flame_detected"])
            sys_data["temperature"] = payload.get("temperature", sys_data["temperature"])
            sys_data["humidity"] = payload.get("humidity", sys_data["humidity"])
        elif msg.topic in [TOPIC_STATUS, TOPIC_ALERTS]:
            sys_data["state_name"] = payload.get("state_name", sys_data["state_name"])
            sys_data["suppression_valve"] = payload.get("suppression_valve", sys_data["suppression_valve"])
            sys_data["buzzer_active"] = payload.get("alarm_buzzer", sys_data["buzzer_active"])

        socketio.emit('update_data', sys_data)
    except Exception:
        pass

def mqtt_thread():
    client_id = f"FlaskDash-{int(time.time())}"
    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id, protocol=mqtt.MQTTv311)
    except AttributeError:
        mqtt_client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)

    mqtt_client.username_pw_set(DEFAULT_USER, DEFAULT_PASSWORD)
    mqtt_client.tls_set()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message

    mqtt_client.connect(DEFAULT_BROKER, DEFAULT_PORT, keepalive=60)
    mqtt_client.loop_forever()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    thread = threading.Thread(target=mqtt_thread, daemon=True)
    thread.start()
    print("🔥 Web Dashboard berjalan di http://127.0.0.1:5000")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, use_reloader=False)