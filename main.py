from machine import Pin, PWM
import time
import network
import json
import ubinascii
import machine
from umqtt.robust import MQTTClient

# =====================================================
# WIFI
# =====================================================
WIFI_SSID = "IFRS-ALUNOS"
WIFI_PASS = "aluno@ifrs2024"

# =====================================================
# THINGSBOARD
# =====================================================
BROKER = "demo.thingsboard.io"
ACCESS_TOKEN = "1aKGTdLscxtK3Fh14Cuh"
CLIENT_ID = b"ESP32_" + ubinascii.hexlify(machine.unique_id())

# =====================================================
# MOTOR 28BYJ-48 + ULN2003
# =====================================================
IN1 = Pin(27, Pin.OUT)
IN2 = Pin(26, Pin.OUT)
IN3 = Pin(25, Pin.OUT)
IN4 = Pin(33, Pin.OUT)

PINS = [IN1, IN2, IN3, IN4]

SEQUENCIA = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1]
]

RANGE_ULTRA_CM = 7

# =====================================================
# ULTRASSÔNICO HC-SR04
# =====================================================
TRIG = Pin(14, Pin.OUT)
ECHO = Pin(35, Pin.IN)

distancia_cm = -1

# =====================================================
# SENSORES TCRT5000
# =====================================================
TCRT_BLUE = Pin(17, Pin.IN)
TCRT_GREEN = Pin(4, Pin.IN)
TCRT_RED = Pin(15, Pin.IN)

tcrt_blue = 1
tcrt_green = 0
tcrt_red = 1

# =====================================================
# SENSOR RGB TCS230
# =====================================================
S0 = Pin(23, Pin.OUT)
S1 = Pin(22, Pin.OUT)
S2 = Pin(21, Pin.OUT)
S3 = Pin(19, Pin.OUT)
OUT = Pin(18, Pin.IN)

# Escala de frequência 20%
S0.value(1)
S1.value(0)
#time.sleep_ms(40)

red = 0
green = 0
blue = 0
unknow = 0

rgb_enviado = False
objeto_presente = False
rgb_liberado = False

tempo_primeira_deteccao = 0
ATRASO_RGB_MS = 8000  # 8 segundos


# =====================================================
# SERVOS
# =====================================================
SERVO1 = PWM(Pin(5), freq=50)
SERVO2 = PWM(Pin(16), freq=50)
SERVO3 = PWM(Pin(2), freq=50)

# =====================================================
# ESTADOS
# =====================================================
power = False
emergency = False
motor_speed_ms = 2
motor_estado_atual = "PARADO"
motor_estado_enviado = "PARADO"
passo_atual = 0
cliente = None
servos_acionados = False

# =====================================================
# WIFI
# =====================================================
def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.3)
    print("WiFi conectado")

# =====================================================
# ULTRASSÔNICO
# =====================================================
def ler_distancia():
    global distancia_cm

    TRIG.value(0)
    time.sleep_us(2)
    TRIG.value(1)
    time.sleep_us(10)
    TRIG.value(0)

    try:
        duracao = machine.time_pulse_us(ECHO, 1, 30000)

        if duracao <= 0:
            distancia_cm = 0
            return

        dist = (duracao * 0.0343) / 2

        if dist <= RANGE_ULTRA_CM:
            distancia_cm = round(dist, 2)
        else:
            distancia_cm = 0

    except:
        distancia_cm = 0


def enviar_telemetria_ultrassonico():
    try:
        cliente.publish(
            b"v1/devices/me/telemetry",
            json.dumps({"distancia_cm": distancia_cm})
        )
    except:
        pass

# =====================================================
# SERVO-MOTORES
# =====================================================

def mover_servo(servo, angulo):
    # ESP32 PWM 10 bits
    min_duty = 30    # ~0°
    max_duty = 100   # ~180°
    duty = int(min_duty + (angulo / 180) * (max_duty - min_duty))
    servo.duty(duty)


mover_servo(SERVO1, 0)
mover_servo(SERVO2, 20)
mover_servo(SERVO3, 0)

def acionar_servo_por_cor(cor):
    if cor == "blue":
        mover_servo(SERVO1, 60)
    elif cor == "red":
        mover_servo(SERVO2, 110)
    elif cor == "green":
        mover_servo(SERVO3, 85)

# =====================================================
# SENSORES TCRT
# =====================================================
def ler_tcrt():
    global tcrt_blue, tcrt_green, tcrt_red

    tcrt_blue = TCRT_BLUE.value()
    tcrt_green = TCRT_GREEN.value()
    tcrt_red = TCRT_RED.value()

def enviar_telemetria_tcrt():
    try:
        cliente.publish(
            b"v1/devices/me/telemetry",
            json.dumps({
                "tcrt_blue": tcrt_blue,
                "tcrt_green": tcrt_green,
                "tcrt_red": tcrt_red
            })
        )
    except:
        pass

# =====================================================
# FUNÇÕES TCS230
# =====================================================
def ler_canal(s2, s3):
    S2.value(s2)
    S3.value(s3)
    time.sleep_ms(30)

    try:
        pulso = machine.time_pulse_us(OUT, 1, 50000)
        if pulso <= 0:
            return 0
        return int(1_000_000 / pulso)
    except:
        return 0


def ler_rgb():
    r = ler_canal(0, 0)   # Vermelho
    g = ler_canal(1, 1)   # Verde
    b = ler_canal(0, 1)   # Azul
    return r, g, b


def detectar_cor(r, g, b):
    soma = r + g + b
    if soma < 2000:
        return "unknow"

    r_p = r / soma
    g_p = g / soma
    b_p = b / soma

    if r_p > 0.40:
        return "red"
    elif g_p > 0.40:
        return "green"
    elif b_p > 0.40:
        return "blue"
    else:
        return "unknow"

def enviar_telemetria_rgb():
    try:
        cliente.publish(
            b"v1/devices/me/telemetry",
            json.dumps({
                "red": red,
                "green": green,
                "blue": blue,
                "unknow": unknow
            })
        )
    except:
        pass

# =====================================================
# MOTOR
# =====================================================
def motor_passo():
    global passo_atual, motor_estado_atual

    if not power or emergency:
        for p in PINS:
            p.value(0)
        motor_estado_atual = "PARADO"
        return

    motor_estado_atual = "EM_MOVIMENTO"

    seq = SEQUENCIA[passo_atual]
    for pin, val in zip(PINS, seq):
        pin.value(val)

    passo_atual = (passo_atual + 1) % len(SEQUENCIA)

# =====================================================
# TELEMETRIA MOTOR
# =====================================================
def enviar_estado_motor():
    try:
        cliente.publish(
            b"v1/devices/me/telemetry",
            json.dumps({
                "motor_estado": motor_estado_atual,
                "power": power,
                "emergency": emergency
            })
        )
    except:
        pass

# =====================================================
# MQTT
# =====================================================
def conectar_mqtt():
    global cliente
    cliente = MQTTClient(CLIENT_ID, BROKER, user=ACCESS_TOKEN, password="")
    cliente.set_callback(rpc_callback)
    cliente.connect()
    cliente.subscribe(b"v1/devices/me/rpc/request/+")
    print("MQTT conectado")

# =====================================================
# RPC
# =====================================================
def rpc_callback(topic, msg):
    global power, emergency, motor_speed_ms
    try:
        data = json.loads(msg)
        metodo = data.get("method")
        params = data.get("params")
        if isinstance(params, dict):
            params = params.get("value")

        if metodo == "setPower":
            power = bool(params)
        elif metodo == "emergencyStop":
            emergency = bool(params)
        elif metodo == "setMotorSpeed":
            motor_speed_ms = max(1, min(15, int(params)))
    except:
        pass

# =====================================================
# START
# =====================================================
conectar_wifi()
conectar_mqtt()

last_motor_ms = time.ticks_ms()
last_ultra_ms = time.ticks_ms()
last_telemetry_ms = time.ticks_ms()

mover_servo(SERVO1, 0)
mover_servo(SERVO2, 20)
mover_servo(SERVO3, 0)

# =====================================================
# LOOP PRINCIPAL (SEM BLOQUEIO)
# =====================================================
while True:
    try:
        now = time.ticks_ms()

        cliente.check_msg()
       
        # ================= TCRT5000
        ler_tcrt()
        
        # MOTOR SEMPRE GIRA
        if time.ticks_diff(now, last_motor_ms) >= motor_speed_ms:
            motor_passo()
            last_motor_ms = now

        # ================= ULTRASSÔNICO - PRIMEIRA DETECÇÃO
        if time.ticks_diff(now, last_ultra_ms) >= 200:
            ler_distancia()

            if distancia_cm > 0 and distancia_cm <= RANGE_ULTRA_CM:
                if not objeto_presente:
                    objeto_presente = True
                    tempo_primeira_deteccao = now   # MARCA SÓ UMA VEZ
                    rgb_liberado = False
                    rgb_enviado = False
            else:
                # Objeto saiu totalmente → reset geral
                objeto_presente = False
                rgb_liberado = False
                rgb_enviado = False

            last_ultra_ms = now


        # ================= LIBERA RGB APÓS 7s DA PRIMEIRA DETECÇÃO
        if objeto_presente and not rgb_liberado:
            if time.ticks_diff(now, tempo_primeira_deteccao) >= ATRASO_RGB_MS:
                rgb_liberado = True


        # ================= SENSOR RGB
        if rgb_liberado and not rgb_enviado:
            r, g, b = ler_rgb()
            cor = detectar_cor(r, g, b)

            if cor == "red":
                red += 1
            elif cor == "green":
                green += 1
            elif cor == "blue":
                blue += 1
            else:
                unknow += 1

            enviar_telemetria_rgb()
            acionar_servo_por_cor(cor)
            time.sleep_ms(400)

            rgb_enviado = True
            servos_acionados = True

        # ================= SERVOS - TCRT5000
        if (tcrt_blue == 0 or tcrt_green == 0 or tcrt_red == 0) and servos_acionados:
            mover_servo(SERVO1, 0)
            mover_servo(SERVO2, 20)
            mover_servo(SERVO3, 0)
            servos_acionados = False

        # TELEMETRIA
        if time.ticks_diff(now, last_telemetry_ms) >= 500:
            enviar_telemetria_ultrassonico()
            enviar_estado_motor()
            enviar_telemetria_tcrt()
            last_telemetry_ms = now

    except Exception as e:
        print("Erro:", e)
        time.sleep(1)
