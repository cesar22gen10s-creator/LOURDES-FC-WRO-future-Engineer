import ble_debug
import config
import navegacion
import utilidades


class LectorPS4UART:
    # Mascaras de flechas.
    DPAD_ARRIBA = 1
    DPAD_ABAJO = 2
    DPAD_DERECHA = 4
    DPAD_IZQUIERDA = 8

    # Mascaras de botones.
    BTN_X = 1
    BTN_CIRCULO = 2
    BTN_CUADRADO = 4
    BTN_TRIANGULO = 8
    BTN_L1 = 16
    BTN_R1 = 32
    BTN_L2 = 64
    BTN_R2 = 128

    def __init__(self, uart):
        self.uart = uart
        self.buffer = b""

    def _parsear(self, linea_bytes):
        try:
            partes = linea_bytes.decode("utf-8").strip().split(",")

            if len(partes) != 8 or partes[0] != "P":
                return None

            return {
                "conectado": bool(int(partes[1])),
                "stick": int(partes[2]),
                "flechas": int(partes[3]),
                "botones": int(partes[4]),
                "auxiliar": int(partes[5]),
                "gatillo_izq": int(partes[6]),
                "gatillo_der": int(partes[7]),
            }
        except Exception:
            return None

    def leer(self):
        """Lee la UART y devuelve el paquete completo mas reciente o None."""
        while self.uart.any():
            datos = self.uart.read()
            if not datos:
                break
            self.buffer += datos

        ultimo = None

        while b"\n" in self.buffer:
            linea, self.buffer = self.buffer.split(b"\n", 1)
            estado = self._parsear(linea)
            if estado is not None:
                ultimo = estado

        return ultimo


def boton_activo(paquete, mascara):
    try:
        return bool(int(paquete.get("botones", 0)) & mascara)
    except (AttributeError, TypeError, ValueError):
        return False


def _valor_gatillo(valor):
    if not utilidades.numero_finito(valor):
        return 0
    return int(utilidades.limitar(valor, 0, config.PS4_GATILLO_MAX))


def _pwm_desde_gatillo(valor, pwm_maximo):
    valor = _valor_gatillo(valor)
    if valor <= config.PS4_GATILLO_MIN:
        return 0
    return int(valor * pwm_maximo / config.PS4_GATILLO_MAX)


def _comando_stick(valor):
    if not utilidades.numero_finito(valor):
        return 0.0
    valor = utilidades.limitar(
        int(valor),
        config.PS4_STICK_MIN,
        config.PS4_STICK_MAX,
    )
    if abs(valor) <= config.PS4_ZONA_MUERTA_STICK:
        return 0.0
    if config.SIGNO_STICK_INVERTIDO == -1:
        valor = -valor
    if valor < 0:
        return valor / abs(config.PS4_STICK_MIN)
    return valor / config.PS4_STICK_MAX


def calcular_orden_manual(muestra_ps4):
    if not muestra_ps4.get("valido"):
        return 0, 0, 0.0, "ps4_sin_paquete"

    paquete = muestra_ps4.get("valor")
    if not isinstance(paquete, dict) or not paquete.get("conectado"):
        return 0, 0, 0.0, "ps4_desconectado"

    gatillo_izquierdo = _valor_gatillo(paquete.get("gatillo_izq"))
    gatillo_derecho = _valor_gatillo(paquete.get("gatillo_der"))
    comando_servo = _comando_stick(paquete.get("stick"))

    if gatillo_derecho == gatillo_izquierdo:
        return 0, 0, comando_servo, "manual_detenido"

    avance = gatillo_derecho > gatillo_izquierdo
    gatillo = gatillo_derecho if avance else gatillo_izquierdo
    pwm_maximo = (
        config.VELOCIDAD_AVANCE if avance else config.VELOCIDAD_RETROCESO
    )
    velocidad = _pwm_desde_gatillo(gatillo, pwm_maximo)
    direccion = (1 if avance else -1) if velocidad else 0
    motivo = "manual_avance" if avance else "manual_retroceso"
    return velocidad, direccion, comando_servo, motivo


def cuadrado_cambiar_modo(sistema):
    muestra = sistema["entradas"]["ps4"]
    paquete = muestra.get("valor") if muestra.get("valido") else None
    cuadrado = bool(isinstance(paquete, dict) and paquete.get("conectado") and boton_activo(paquete, LectorPS4UART.BTN_CUADRADO))
    nav = sistema["navegacion"]
    if cuadrado and not nav.get("cuadrado_anterior", False):
        nuevo = "manual" if nav["modo"] == "automatico" else "automatico"
        navegacion.desactivar("cambio_modo_" + nuevo)
        nav["modo"] = nuevo
    nav["cuadrado_anterior"] = cuadrado

def equis_activar(sistema):
    muestra = sistema["entradas"]["ps4"]
    paquete = muestra.get("valor") if muestra.get("valido") else None
    equis = bool(isinstance(paquete, dict) and paquete.get("conectado") and boton_activo(paquete, LectorPS4UART.BTN_X))
    nav = sistema["navegacion"]
    if equis and not nav.get("equis_anterior", False):
        navegacion.desactivar() if nav["activo"] else navegacion.activar()
    nav["equis_anterior"] = equis 

def circulo_ble(sistema):
    muestra = sistema["entradas"]["ps4"]
    paquete = muestra.get("valor") if muestra.get("valido") else None
    circulo = bool(isinstance(paquete, dict) and paquete.get("conectado") and boton_activo(paquete, LectorPS4UART.BTN_CIRCULO))
    nav = sistema["navegacion"]
    if circulo and not nav.get("circulo_anterior", False):
        ble_debug.alternar_actualizacion()
    nav["circulo_anterior"] = circulo


def actualizar_manual(sistema):
    cuadrado_cambiar_modo(sistema)
    equis_activar(sistema)
    circulo_ble(sistema)
    if sistema["navegacion"]["modo"] != "manual":
        return
    navegacion.boton_start()
    velocidad, direccion, comando, motivo = calcular_orden_manual(
        sistema["entradas"]["ps4"]
    )
    if not sistema["navegacion"]["activo"]:
        velocidad, direccion, comando = 0, 0, 0.0
    sistema["motor"]["velocidad"] = velocidad
    sistema["motor"]["direccion"] = direccion
    sistema["motor"]["freno"] = False
    sistema["servo"]["comando"] = comando
    return motivo
