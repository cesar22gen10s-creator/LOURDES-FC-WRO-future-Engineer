# componentes.py
from machine import Pin, PWM, time_pulse_us, I2C #type:ignore
import struct
import time
import math


class Servo:
    def __init__(self, pin, angulo_inicial=0, pulso_min=518, pulso_max=2510, freq_hz=50):
        self.PULSO_MIN_US = pulso_min
        self.PULSO_MAX_US = pulso_max
        self.angulo_inicial = angulo_inicial
        self.FREQ_HZ = freq_hz
        self._pwm = PWM(Pin(pin), freq=self.FREQ_HZ)
        self.angulo_actual = None

    def angulo_a_duty(self, angulo):
        """Convierte grados (0-360) a duty_u16 para el PWM."""
        angulo = max(0, min(360, angulo))
        # Mapeo correcto: 0° = PULSO_MIN, 360° = PULSO_MAX
        us = self.PULSO_MIN_US + (angulo / 360) * (self.PULSO_MAX_US - self.PULSO_MIN_US)
        duty = int((us / 20000) * 65535)
        return duty

    def mover(self, angulo, espera=True):
        angulo = max(0, min(360, angulo))
        duty = self.angulo_a_duty(angulo)
        self._pwm.duty_u16(duty)
        self.angulo_actual = angulo
        if espera:
            time.sleep_ms(800)


    def calibrar(self, pulso_min=None, pulso_max=None):
        if pulso_min is not None:
            self.PULSO_MIN_US = pulso_min
        if pulso_max is not None:
            self.PULSO_MAX_US = pulso_max
        self.mover(self.angulo_inicial, espera=True)
        print(f"[Servo] Calibracion actualizada: {self.PULSO_MIN_US}us - {self.PULSO_MAX_US}us")

    @property
    def angulo(self):
        return self.angulo_actual

    def apagar(self):   
        self._pwm.deinit()

class Encoder_AS5600:

    #ADDR ES LA DIRECCION I2C (SCL,)
    ADDR = 0x36
    REG_RAW_ANGLE = 0x0C
    PASOS_POR_VUELTA = 4096

    def __init__(self, i2c, sentido = 1):
        self.i2c = i2c
        self.sentido = 1 if sentido >= 0 else -1
        try:
            self._raw_anterior = self.raw()
        except OSError:
            print("[AS5600] No detectado")
            self._raw_anterior = 0
        self._pasos_acumulados = 0

    def raw(self):
        data = self.i2c.readfrom_mem(self.ADDR, self.REG_RAW_ANGLE, 2)
        return ((data[0] << 8) | data[1]) & 0x0FFF

    def degrees(self):
        return self.raw() * 360.0 / self.PASOS_POR_VUELTA

    def actualizar(self):
        actual = self.raw()
        delta = actual - self._raw_anterior

        if delta > self.PASOS_POR_VUELTA // 2:
            delta -= self.PASOS_POR_VUELTA
        elif delta < -(self.PASOS_POR_VUELTA // 2):
            delta += self.PASOS_POR_VUELTA
        delta *= self.sentido

        self._pasos_acumulados += delta
        self._raw_anterior = actual
        return delta

    def reset_encoder(self):
        self._raw_anterior = self.raw()
        self._pasos_acumulados = 0

    def pasos_acumulados(self):
        return self._pasos_acumulados

    def vueltas(self):
        return -self._pasos_acumulados / self.PASOS_POR_VUELTA
    
class FlyingFlash:
    def __init__(self, pin):
        self.pin_out = Pin(pin, Pin.IN)

class SonarBit:
    def __init__(self, trigger_pin, echo_pin, distancia_max_cm=400):
        self.trigger = Pin(trigger_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        
        self.trigger.value(0)
        self.distancia_max_cm = distancia_max_cm

        # Tiempo máximo de espera del eco en microsegundos
        # Aproximado según la distancia máxima
        self.timeout_us = int((distancia_max_cm * 2 * 29.1))

    def _pulso_trigger(self):

        self.trigger.value(0)
        time.sleep_us(2)
        self.trigger.value(1)
        time.sleep_us(10)
        self.trigger.value(0)

    def leer_cm(self):

        self._pulso_trigger()

        try:
            duracion = time_pulse_us(self.echo, 1, self.timeout_us)
        except OSError:
            return None

        if duracion < 0:
            return None 

        # Velocidad del sonido aproximada:
        # 343 m/s a 20°C
        # Fórmula práctica:
        # distancia_cm = duracion_us / 58
        distancia = duracion / 58.0

        if distancia <= 0 or distancia > self.distancia_max_cm:
            return None

        return distancia

    def leer_mm(self):
        distancia_cm = self.leer_cm()
        if distancia_cm is None:
            return None
        return distancia_cm * 10

class MotorPuenteH:
    def __init__(self, pin_ena, pin_in1, pin_in2, freq_pwm=1000):
        self.in1 = Pin(pin_in1, Pin.OUT)
        self.in2 = Pin(pin_in2, Pin.OUT)
        self.ena = PWM(Pin(pin_ena), freq=freq_pwm)

        self.velocidad_actual = 0
        self.direccion_actual = None   # "adelante", "atras" o None
        self.detener()

    def _limitar_velocidad(self, velocidad):
        if velocidad < 0:
            return 0
        if velocidad > 800:
            return 800
        return int(velocidad)

    def _aplicar_velocidad(self, velocidad):
        velocidad = self._limitar_velocidad(velocidad)
        self.ena.duty(velocidad)
        self.velocidad_actual = velocidad

    def _poner_direccion(self, direccion):
        if direccion == "adelante":
            self.in1.value(1)
            self.in2.value(0)
        elif direccion == "atras":
            self.in1.value(0)
            self.in2.value(1)
        else:
            raise ValueError("La direccion debe ser 'adelante' o 'atras'")

        self.direccion_actual = direccion

    def _mover_suave(self, desde, hasta, paso=400, delay_ms=50):
        if desde == hasta:
            self._aplicar_velocidad(hasta)
            return

        if desde < hasta:
            for v in range(desde, hasta + 1, paso):
                self._aplicar_velocidad(v)
                time.sleep_ms(delay_ms)
        else:
            for v in range(desde, hasta - 1, -paso):
                self._aplicar_velocidad(v)
                time.sleep_ms(delay_ms)

        # asegura valor final exacto
        self._aplicar_velocidad(hasta)

    def mover_directo(self, velocidad, direccion=0):
        """
        direccion:
            0  = detenido
            1  = adelante
            -1 = atras
        """

        velocidad = self._limitar_velocidad(velocidad)

        if direccion == 0 or velocidad == 0:
            self.detener()
            return

        if direccion == 1:
            if self.direccion_actual != "adelante":
                self._poner_direccion("adelante")
            self._aplicar_velocidad(velocidad)
            return

        if direccion == -1:
            if self.direccion_actual != "atras":
                self._poner_direccion("atras")
            self._aplicar_velocidad(velocidad)
            return

        raise ValueError("direccion debe ser 0, 1 o -1")

    def frenar(self, velocidad):
        """Aplica el contrapulso usando la polaridad de retroceso probada."""
        self.mover_directo(velocidad, -1)

    def acelerar(self, velocidad_objetivo, direccion="adelante", paso=200, delay_ms=50):
        velocidad_objetivo = self._limitar_velocidad(velocidad_objetivo)

        # si nunca se ha definido direccion, la fija
        if self.direccion_actual is None:
            self._poner_direccion(direccion)

        # si cambia de sentido, primero desacelera a 0
        elif self.direccion_actual != direccion:
            self._mover_suave(self.velocidad_actual, 0, paso=paso, delay_ms=delay_ms)
            self._poner_direccion(direccion)

        # luego acelera o desacelera suavemente hasta el objetivo
        self._mover_suave(self.velocidad_actual, velocidad_objetivo, paso=paso, delay_ms=delay_ms)

    def detener(self):
        self.in1.value(0)
        self.in2.value(0)
        self.ena.duty(0)
        self.velocidad_actual = 0
        self.direccion_actual = None

class BMI160:
    REG_CHIP_ID    = 0x00
    REG_ERR        = 0x02
    REG_PMU_STATUS = 0x03
    REG_GYR_X_L    = 0x0C
    REG_SENSORTIME = 0x18
    REG_CMD        = 0x7E
    REG_GYR_CONF   = 0x42
    REG_GYR_RANGE  = 0x43 #ajustar grados / tiempo 

    CHIP_ID = 0xD1

    CMD_ACC_NORMAL = 0x11
    CMD_GYR_NORMAL = 0x15
    CMD_SOFT_RESET = 0xB6

    def __init__(self, i2c, addr=0x69):
        self.i2c = i2c
        self.addr = addr

        self.angulo_z = 0.0
        self.bias_gz = 0.0

        # Para ±250 dps
        self.lsb_por_dps = 131.2

        # Ajustable
        self.umbral_ruido_dps = 0.8

        # Tiempo interno para integración
        self._t_anterior_us = None

    # =========================
    # Bajo nivel (lectura y escritura de bytes)
    # =========================
    def _write_reg(self, reg, value):
        self.i2c.writeto_mem(self.addr, reg, bytes([value]))

    def _read_reg(self, reg, n=1):
        return self.i2c.readfrom_mem(self.addr, reg, n)

    def _read_u8(self, reg):
        return self._read_reg(reg, 1)[0]

    def _s16_le(self, lo, hi):
        value = lo | (hi << 8)
        if value & 0x8000:
            value -= 65536
        return value

    def _gyro_modo(self):
        # bits 3:2 de PMU_STATUS (para giros)
        return (self._read_u8(self.REG_PMU_STATUS) >> 2) & 0x03

    def _acc_modo(self):
        # bits 5:4 de PMU_STATUS (para acelerometro)
        return (self._read_u8(self.REG_PMU_STATUS) >> 4) & 0x03

    def _esperar_modo_normal(self, sensor="gyro", timeout_ms=200):
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
            if sensor == "gyro":
                if self._gyro_modo() == 0x01:
                    return True
            elif sensor == "acc":
                if self._acc_modo() == 0x01:
                    return True
            time.sleep_ms(2)
        return False

    # =========================
    # Inicialización
    # =========================
    def iniciar(self, rango = 250):
        chip = self._read_u8(self.REG_CHIP_ID)
        print("CHIP_ID:", hex(chip))
        if chip != self.CHIP_ID:
            raise Exception("BMI160 no detectado o dirección incorrecta")

        # Soft reset
        self._write_reg(self.REG_CMD, self.CMD_SOFT_RESET)
        time.sleep_ms(15)

        chip = self._read_u8(self.REG_CHIP_ID)
        if chip != self.CHIP_ID:
            raise Exception("BMI160 no responde después del reset")

        # Acelerómetro normal
        self._write_reg(self.REG_CMD, self.CMD_ACC_NORMAL)
        if not self._esperar_modo_normal("acc", timeout_ms=100):
            raise Exception("El acelerómetro no entró en modo normal")

        # Giroscopio normal
        self._write_reg(self.REG_CMD, self.CMD_GYR_NORMAL)
        if not self._esperar_modo_normal("gyro", timeout_ms=150):
            raise Exception("El giroscopio no entró en modo normal")

        # 0x28 es una configuración válida/reset común de GYR_CONF

        self._write_reg(self.REG_GYR_CONF, 0x28)

            # rango en dps: ±2000, ±1000, ±500, ±250, ±125
        if rango == 2000:
            self._write_reg(self.REG_GYR_RANGE, 0x00)
            self.lsb_por_dps = 16.4
        elif rango == 1000:
            self._write_reg(self.REG_GYR_RANGE, 0x01)
            self.lsb_por_dps = 32.8
        elif rango == 500:
            self._write_reg(self.REG_GYR_RANGE, 0x02)
            self.lsb_por_dps = 65.6
        elif rango == 250:
            self._write_reg(self.REG_GYR_RANGE, 0x03)
            self.lsb_por_dps = 131.2
        elif rango == 125:
            self._write_reg(self.REG_GYR_RANGE, 0x04)
            self.lsb_por_dps = 262.4
        else:
            raise ValueError("Rango no válido, use 125, 250, 500, 1000, 2000")
        
        time.sleep_ms(10)

        self.angulo_z = 0.0
        self.bias_gz = 0.0
        self._t_anterior_us = time.ticks_us()

    # =========================
    # Lecturas
    # =========================
    def leer_gyro_raw(self):
        # Lectura burst de 6 bytes para que los 3 ejes salgan del mismo bloque
        data = self._read_reg(self.REG_GYR_X_L, 6)

        gx = self._s16_le(data[0], data[1])
        gy = self._s16_le(data[2], data[3])
        gz = self._s16_le(data[4], data[5])

        return gx, gy, gz

    def leer_gyro_dps(self):
        gx, gy, gz = self.leer_gyro_raw()
        return (
            gx / self.lsb_por_dps,
            gy / self.lsb_por_dps,
            gz / self.lsb_por_dps,
        )

    def leer_sensortime(self):
        data = self._read_reg(self.REG_SENSORTIME, 3)
        ticks39us = data[0] | (data[1] << 8) | (data[2] << 16)
        return ticks39us

    # =========================
    # Calibración
    # =========================
    def calibrar_bias_gyro(self, muestras=500, delay_ms=5):
        print("No muevas el carro. Calibrando bias...")
        suma = 0.0

        # descartar primeras lecturas
        for _ in range(20):
            self.leer_gyro_dps()
            time.sleep_ms(2)

        for _ in range(muestras):
            _, _, gz = self.leer_gyro_dps()
            suma += gz
            time.sleep_ms(delay_ms)

        self.bias_gz = suma / muestras
        self.angulo_z = 0.0
        self._t_anterior_us = time.ticks_us()
        print("Bias GZ:", self.bias_gz)

    # =========================
    # Orientación
    # =========================
    def reset_orientacion(self, angulo_inicial=0.0):
        self.angulo_z = angulo_inicial
        self._t_anterior_us = time.ticks_us()

    def actualizar_orientacion(self, normalizar=True):
        ahora_us = time.ticks_us()

        if self._t_anterior_us is None:
            self._t_anterior_us = ahora_us
            return self.angulo_z, 0.0

        dt_us = time.ticks_diff(ahora_us, self._t_anterior_us)
        self._t_anterior_us = ahora_us

        dt = dt_us / 1_000_000.0

        # evita saltos si la función se dejó de llamar mucho tiempo
        if dt <= 0 or dt > 0.2:
            _, _, gz = self.leer_gyro_dps()
            gz_corregido = gz - self.bias_gz
            if abs(gz_corregido) < self.umbral_ruido_dps:
                gz_corregido = 0.0
            return self.angulo_z, gz_corregido

        _, _, gz = self.leer_gyro_dps()
        gz_corregido = gz - self.bias_gz

        if abs(gz_corregido) < self.umbral_ruido_dps:
            gz_corregido = 0.0

        self.angulo_z += gz_corregido * dt

        if normalizar:
            while self.angulo_z > 180:
                self.angulo_z -= 360
            while self.angulo_z <= -180:
                self.angulo_z += 360

        return self.angulo_z, gz_corregido

class TCS3200:
    def __init__(self, oe, s0, s1, s2, s3, out_pin):
        self.oe = Pin(oe, Pin.OUT)
        self.s0 = Pin(s0, Pin.OUT)
        self.s1 = Pin(s1, Pin.OUT)
        self.s2 = Pin(s2, Pin.OUT)
        self.s3 = Pin(s3, Pin.OUT)
        self.out = Pin(out_pin, Pin.IN)

        self.habilitar(True)
        self.set_escala(20)

        # perfiles personalizados:
        # nombre -> {
        #   "rgb": (rn, gn, bn),
        #   "clear_min": valor_minimo_opcional,
        #   "clear_max": valor_maximo_opcional,
        # }
        self.perfiles = {}

        # filtro temporal para uso en movimiento
        self._ultima_zona_cruda = None
        self._conteo_estable = 0
        self._zona_confirmada = None
        self._ultimo_cambio_ms = time.ticks_ms()

    def habilitar(self, activo=True):
        # OE activo en bajo
        self.oe.value(0 if activo else 1)

    def set_escala(self, porcentaje):
        if porcentaje == 2:
            self.s0.value(0)
            self.s1.value(1)
        elif porcentaje == 20:
            self.s0.value(1)
            self.s1.value(0)
        elif porcentaje == 100:
            self.s0.value(1)
            self.s1.value(1)
        else:
            self.s0.value(0)
            self.s1.value(0)

    def set_filtro(self, color):
        if color == "rojo":
            self.s2.value(0)
            self.s3.value(0)
        elif color == "azul":
            self.s2.value(0)
            self.s3.value(1)
        elif color == "clear":
            self.s2.value(1)
            self.s3.value(0)
        elif color == "verde":
            self.s2.value(1)
            self.s3.value(1)
        else:
            raise ValueError("Color invalido")

    def leer_frecuencia(self, muestras=3, timeout_us=120000):
        total_periodo = 0
        validas = 0

        for _ in range(muestras):
            t_alto = time_pulse_us(self.out, 1, timeout_us)
            t_bajo = time_pulse_us(self.out, 0, timeout_us)

            if t_alto > 0 and t_bajo > 0:
                total_periodo += (t_alto + t_bajo)
                validas += 1

        if validas == 0:
            return None

        periodo_promedio = total_periodo / validas
        return 1_000_000 / periodo_promedio

    def leer_rgb(self):
        resultado = {}

        for color in ("rojo", "verde", "azul", "clear"):
            self.set_filtro(color)
            time.sleep_ms(2)  # pequeño tiempo de asentamiento
            resultado[color] = self.leer_frecuencia(muestras=3)

        return resultado

    def leer_normalizado(self):
        datos = self.leer_rgb()

        r = datos["rojo"]
        g = datos["verde"]
        b = datos["azul"]
        c = datos["clear"]

        if None in (r, g, b, c) or c <= 0:
            return None

        return {
            "rojo": r,
            "verde": g,
            "azul": b,
            "clear": c,
            "rn": r / c,
            "gn": g / c,
            "bn": b / c,
        }

    def registrar_perfil(self, nombre, rn, gn, bn, clear_min=0, clear_max=999999):
        self.perfiles[nombre] = {
            "rgb": (rn, gn, bn),
            "clear_min": clear_min,
            "clear_max": clear_max,
        }

    def registrar_perfil_desde_lectura(self, nombre, lecturas_promedio=8, pausa_ms=60):
        suma_rn = 0.0
        suma_gn = 0.0
        suma_bn = 0.0
        suma_c = 0.0
        validas = 0

        for _ in range(lecturas_promedio):
            dato = self.leer_normalizado()
            if dato is not None:
                suma_rn += dato["rn"]
                suma_gn += dato["gn"]
                suma_bn += dato["bn"]
                suma_c += dato["clear"]
                validas += 1
            time.sleep_ms(pausa_ms)

        if validas == 0:
            return None

        prom_rn = suma_rn / validas
        prom_gn = suma_gn / validas
        prom_bn = suma_bn / validas
        prom_c = suma_c / validas

        # margen razonable para clear
        clear_min = prom_c * 0.65
        clear_max = prom_c * 1.35

        self.registrar_perfil(
            nombre,
            prom_rn,
            prom_gn,
            prom_bn,
            clear_min=clear_min,
            clear_max=clear_max
        )

        return {
            "nombre": nombre,
            "rn": prom_rn,
            "gn": prom_gn,
            "bn": prom_bn,
            "clear_prom": prom_c,
            "clear_min": clear_min,
            "clear_max": clear_max,
        }

    def _distancia(self, rn, gn, bn, perfil_rgb):
        pr, pg, pb = perfil_rgb
        return math.sqrt(
            (rn - pr) ** 2 +
            (gn - pg) ** 2 +
            (bn - pb) ** 2
        )

    def clasificar_crudo(self, umbral_distancia=0.08):
        dato = self.leer_normalizado()
        if dato is None:
            return None, None

        rn = dato["rn"]
        gn = dato["gn"]
        bn = dato["bn"]
        c = dato["clear"]

        mejor_nombre = None
        mejor_dist = None

        for nombre, perfil in self.perfiles.items():
            if not (perfil["clear_min"] <= c <= perfil["clear_max"]):
                continue

            dist = self._distancia(rn, gn, bn, perfil["rgb"])

            if mejor_dist is None or dist < mejor_dist:
                mejor_dist = dist
                mejor_nombre = nombre

        if mejor_nombre is None:
            return "desconocido", dato

        if mejor_dist > umbral_distancia:
            return "desconocido", dato

        return mejor_nombre, dato

    def clasificar_estable(self, umbral_distancia=0.08, repeticiones=3, bloqueo_ms=250):
        zona_cruda, dato = self.clasificar_crudo(umbral_distancia=umbral_distancia)

        ahora = time.ticks_ms()

        if zona_cruda == self._ultima_zona_cruda:
            self._conteo_estable += 1
        else:
            self._ultima_zona_cruda = zona_cruda
            self._conteo_estable = 1

        evento = None

        if (
            zona_cruda not in (None, "desconocido")
            and self._conteo_estable >= repeticiones
            and zona_cruda != self._zona_confirmada
            and time.ticks_diff(ahora, self._ultimo_cambio_ms) > bloqueo_ms
        ):
            self._zona_confirmada = zona_cruda
            self._ultimo_cambio_ms = ahora
            evento = zona_cruda

        return {
            "zona_cruda": zona_cruda,
            "zona_confirmada": self._zona_confirmada,
            "evento": evento,   # solo se activa cuando entra estable a una nueva zona
            "dato": dato,
            "conteo_estable": self._conteo_estable,
        }
    

    class WonderCam:
        DEFAULT_ADDR = 0x32

        FUNC_NONE           = 0
        FUNC_FACE           = 1   # Reconocimiento facial
        FUNC_OBJECT         = 2   # Reconocimiento de objetos
        FUNC_CLASSIFICATION = 3   # Clasificación de imagen
        FUNC_FEATURE        = 4   # Aprendizaje de características
        FUNC_COLOR          = 5   # Reconocimiento de color (inferido:
                                # el doc deja el 5 libre y describe
                                # registros de color en 0x1000)
        FUNC_LINE           = 6   # Seguimiento visual de línea
        FUNC_TAG            = 7   # AprilTag
        FUNC_QR             = 8   # QR
        FUNC_BARCODE        = 9   # Código de barras

        FUNC_NAMES = {
            0: "Ninguna",
            1: "Reconocimiento facial",
            2: "Reconocimiento de objetos",
            3: "Clasificación de imagen",
            4: "Aprendizaje de características",
            5: "Reconocimiento de color",
            6: "Seguimiento de línea",
            7: "Reconocimiento de tag",
            8: "Lectura QR",
            9: "Lectura de código de barras",
        }

        # ---- Registros del sistema ----
        REG_FIRMWARE     = 0x0000   # 16 bytes ASCII tipo "v0.6.5"
        REG_LIGHT        = 0x0030   # luz de relleno: 0=off, 1=on
        REG_CURRENT_FUNC = 0x0035   # número de función (RW)

        # ---- Registros de detección de color ----
        REG_COLOR_BASE      = 0x1000   # leer aquí refresca resultados
        REG_COLOR_NUM       = 0x1001   # cantidad de colores detectados
        REG_COLOR_IDS       = 0x1002   # IDs (1 byte/color, hasta 0x1029)
        REG_COLOR_RESULT1   = 0x1030   # primer bloque de 16 bytes
        COLOR_RESULT_STRIDE = 0x10     # 16 bytes por resultado

        # ============================================================
        #   Constructor
        # ============================================================
        def __init__(self, i2c, addr=DEFAULT_ADDR):
            self.i2c = i2c
            self.addr = addr

        # ============================================================
        # bajo nivel
        # ============================================================
        def _read(self, reg, n):
            return self.i2c.readfrom_mem(self.addr, reg, n, addrsize=16)

        def _write(self, reg, data):
            if isinstance(data, int):
                data = bytes([data & 0xFF])
            self.i2c.writeto_mem(self.addr, reg, data, addrsize=16)

        def is_present(self):
            return self.addr in self.i2c.scan()

        def get_firmware_version(self):
            raw = self._read(self.REG_FIRMWARE, 16)
            cleaned = raw.split(b'\x00')[0]   # cortar en el primer null
            try:
                return cleaned.decode('utf-8').strip()
            except Exception:
                return str(cleaned)

        def get_current_function(self):
            return self._read(self.REG_CURRENT_FUNC, 1)[0]

        def get_current_function_name(self):
            f = self.get_current_function()
            return self.FUNC_NAMES.get(f, "Function ({})".format(f))

        def set_function(self, func_num):
            self._write(self.REG_CURRENT_FUNC, func_num)
            if self.get_current_function() == func_num:
                return True
            else:
                return False

        def get_color_detections(self):
            self._read(self.REG_COLOR_BASE, 1)

            # Leer: 0x1000..0x102F
            #   offset 0  (0x1000) -> función actual / refresh
            #   offset 1  (0x1001) -> número de colores
            #   offset 2.. (0x1002) -> IDs (1 byte cada uno)
            header = self._read(self.REG_COLOR_BASE, 48)
            num = header[1]
            if num == 0:
                return []

            results = []
            for i in range(num):
                color_id = header[2 + i]
                # Cada resultado: 16 bytes a partir de 0x1030
                # Los primeros 8 bytes son X, Y, W, H (16-bit signed, little-endian, si la camara presenta error con esta traduccion probablemente los bytes se lean al reves)
                block_addr = self.REG_COLOR_RESULT1 + i * self.COLOR_RESULT_STRIDE
                data = self._read(block_addr, 8)
                x, y, w, h = struct.unpack('<hhhh', data)
                results.append({
                    'id': color_id,
                    'x' : x,
                    'y' : y,
                    'w' : w,
                    'h' : h,
                })
            return results

        def iniciar_modo_color(self, luz=None):
            if not self.is_present():
                return False
            if not self.set_function(self.FUNC_COLOR):
                return False
            if luz is not None:
                self.set_light(luz)
            return True

        def set_light(self, on):
            self._write(self.REG_LIGHT, 1 if on else 0)

        def get_light(self):
            return self._read(self.REG_LIGHT, 1)[0] != 0


# Conserva el driver humano y permite importarlo como dispositivo independiente.
WonderCam = TCS3200.WonderCam


