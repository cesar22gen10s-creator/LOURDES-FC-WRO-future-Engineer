# ============================================================
# PINES
# ============================================================

PIN_SERVO = 27
PIN_BTN_A = 33

PIN_SCL = 22
PIN_SDA = 21

PIN_PUENTEH_ENA = 15
PIN_PUENTEH_IN1 = 4
PIN_PUENTEH_IN2 = 2

PIN_SONAR_FRONTAL_TRIGGER = 5
PIN_SONAR_FRONTAL_ECHO = 18
PIN_SONAR_IZQUIERDO_TRIGGER = 26
PIN_SONAR_IZQUIERDO_ECHO = 25
PIN_SONAR_DERECHO_TRIGGER = 23
PIN_SONAR_DERECHO_ECHO = 19

PIN_XSHUT_FRONTAL = 13
PIN_XSHUT_IZQUIERDO = 32
PIN_XSHUT_DERECHO = 14

UART_PS4_ID = 2
UART_PS4_BAUDRATE = 115200
PIN_UART_PS4_RX = 16
PIN_UART_PS4_TX = 17


# ============================================================
# SERVO
# ============================================================

SERVO_CENTRO = 70
SERVO_DERECHA = 30
SERVO_IZQUIERDA = 110
PASO_SERVO = 10

# Comando logico: -1 izquierda, 0 centro, +1 derecha.
INVERTIR_COMANDO_SERVO = False
INVERTIR_SERVO_EN_RETROCESO = True


# ============================================================
# VELOCIDADES PWM (0..1023)
# ============================================================

VELOCIDAD_AVANCE = 800
VELOCIDAD_APROXIMACION = 700
VELOCIDAD_GIRO = 750
VELOCIDAD_RETROCESO = 800

# Contrapulso breve para cancelar la inercia al detectar frente critico.
PWM_FRENO_CONTRAPULSO = 500
PAUSA_NEUTRAL_FRENO_MS = 10
DURACION_FRENO_CONTRAPULSO_MS = 200


# ============================================================
# CADENCIAS COOPERATIVAS (ms)
# ============================================================

PERIODO_NAVEGACION_MS = 20
PERIODO_IMU_MS = 5
PERIODO_SONAR_MS = 30
SEPARACION_SONARES_MS = 8
PERIODO_TOF_MS = 8
PERIODO_ENCODER_MS = 10
PERIODO_ENTRADAS_MS = 20
PERIODO_CAMARA_MS = 100
PERIODO_ACTUADOR_MS = 10
PERIODO_DEBUG_MS = 1000


# ============================================================
# SONARES
# ============================================================

SONAR_MAX_CM = 260
SONAR_MIN_VALIDO_CM = 5
SONAR_PASILLO_MAX_CM = 130

FACTOR_APERTURA_SONAR = 1.5
DELTA_APERTURA_SONAR_CM = 30

SONAR_FRONTAL_ENTRAR_APROX_CM = 50
SONAR_FRONTAL_SALIR_APROX_CM = 70
SONAR_FRONTAL_CRITICO_CM = 25
SONAR_FRONTAL_CRITICO_MANUAL_CM = 15
SONAR_FRONTAL_LIBRE_CM = 70


# ============================================================
# TOF
# ============================================================

TOF_DIRECCION_FRONTAL = 0x2A
TOF_DIRECCION_IZQUIERDO = 0x2B
TOF_DIRECCION_DERECHO = 0x2C

TOF_MIN_VALIDO_CM = 2
TOF_MAX_VALIDO_CM = 800
TOF_SIN_OBJETIVO_DESDE_MM = 8180
TOF_DISTANCIA_ABIERTA_CM = 200
TOF_FRONTAL_RANGO_UTIL_CM = 200
TOF_LATERAL_RANGO_CONTROL_CM = 45
TOF_INICIO_DETECCION_APERTURA_CM = 45
TOF_LATERAL_PELIGRO_CM = 20

TOF_FRONTAL_ENTRAR_APROX_CM = 70
TOF_FRONTAL_SALIR_APROX_CM = 80
TOF_FRONTAL_CRITICO_CM = 28
TOF_FRONTAL_CRITICO_MANUAL_CM = 20
TOF_FRONTAL_LIBRE_CM = 80

FACTOR_APERTURA_TOF = 1.5
DELTA_APERTURA_TOF_CM = 10
ZONA_MUERTA_ASIMETRIA_TOF = 0.03
KP_CORRECCION_TOF = 1
SIGNO_CORRECCION_TOF = 1
COMANDO_EVASION_TOF = 0.8

TOF_MAX_INTENTOS_INICIALIZACION = 2
TOF_ERRORES_ANTES_REINICIO = 3
CICLOS_ENTRE_RECUPERACIONES_TOF = 50


# ============================================================
# IMU / HEADING
# ============================================================

ERROR_HEADING_MAX = 28.0
KP_HEADING_RECTA = 1
KP_HEADING_APROXIMACION = 1
KP_HEADING_GIRO = 1.35
COMANDO_GIRO_MIN = 0.45
ERROR_GIRO_PERMITIDO = 9.0
SIGNO_HEADING_DERECHA = -1


# ============================================================
# NAVEGACION
# ============================================================

DISTANCIA_FRONTAL_MIN_GIRO_CM = 40
DISTANCIA_FRONTAL_INICIO_GIRO_FLUIDO_CM = 60

MUESTRAS_CONFIRMAR_GIRO_LATERAL = 3
MUESTRAS_CONFIRMAR_FIN_GIRO = 3
CICLOS_PREPARACION_GIRO = 2

CICLOS_MAX_SIN_IMU = 15
CICLOS_MAX_SIN_SONAR = 20
CICLOS_MAX_SIN_TOF = 20

# 0 significa navegacion indefinida; N detiene despues de 4 * N esquinas.
VUELTAS_OBJETIVO = 0


# ============================================================
# ENCODER
# ============================================================

DISTANCIA_POR_VUELTA_RUEDA_CM = 25.0
SIGNO_DISTANCIA_ENCODER = -1
DELTA_ENCODER_MOVIMIENTO_MIN = 2


# ============================================================
# PS4
# ============================================================

PS4_GATILLO_MIN = 100
PS4_GATILLO_MAX = 1023
PS4_STICK_MIN = -511
PS4_STICK_MAX = 512
PS4_ZONA_MUERTA_STICK = 10
CICLOS_MAX_SIN_PS4 = 150
SIGNO_STICK_INVERTIDO = -1
