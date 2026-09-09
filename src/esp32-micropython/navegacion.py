import config
import estado
import utilidades


DETENIDO = "detenido"
CRUCERO = "crucero"
APROXIMACION = "aproximacion"
PREPARACION_GIRO = "preparacion_giro"
RETROCESO_GIRO = "retroceso_giro"
GIRO = "giro"
FALLO = "fallo"

IZQUIERDA = "izquierda"
DERECHA = "derecha"


def _orden(velocidad=0, direccion=0, servo=0.0, freno=False):
    motor = estado.estado["motor"]
    motor["freno"] = bool(freno)
    motor["velocidad"] = 0 if freno else velocidad
    motor["direccion"] = 0 if freno else direccion
    estado.estado["servo"]["comando"] = utilidades.limitar(
        servo, -1.0, 1.0
    )


def _cambiar_maniobra(nav, nueva, motivo):
    if nav["maniobra"] != nueva:
        nav["maniobra"] = nueva
        nav["ciclos_maniobra"] = 0
    nav["motivo_transicion"] = motivo


def activar():
    nav = estado.estado["navegacion"]
    nav.update({
        "activo": True,
        "maniobra": DETENIDO,
        "heading_ref": None,
        "heading_error": None,
        "sentido_pista": None,
        "sentido_giro": None,
        "giro_pendiente": None,
        "apertura_tof": None,
        "apertura_sonar": None,
        "candidato_giro": None,
        "candidato_giro_alta_confianza": False,
        "confirmaciones_giro_lateral": 0,
        "confirmaciones_fin_giro": 0,
        "esquinas": 0,
        "vueltas": 0,
        "frente_critico_enclavado": False,
        "fallo": None,
        "motivo_transicion": "activado",
    })
    nav["ultimo_seq"].clear()
    nav["ciclos_sin_actualizar"].clear()
    nav["ciclos_maniobra"] = 0
    _orden()


def desactivar(motivo="detenido_por_usuario"):
    nav = estado.estado["navegacion"]
    nav["activo"] = False
    nav["heading_ref"] = None
    nav["heading_error"] = None
    nav["fallo"] = None
    _cambiar_maniobra(nav, DETENIDO, motivo)
    _orden()


def boton_start():
    nav = estado.estado["navegacion"]
    boton = estado.estado["entradas"]["boton_start"]
    presionado = bool(boton["valor"]) if boton["valido"] else False
    if presionado and not nav["boton_start_anterior"]:
        desactivar() if nav["activo"] else activar()
    nav["boton_start_anterior"] = presionado


def _fuente_fresca(nav, nombre, muestra, limite):
    ultimo = nav["ultimo_seq"].get(nombre, 0)
    ciclos = nav["ciclos_sin_actualizar"].get(nombre, 0)
    ultimo, ciclos, _ = utilidades.actualizar_contador_seq(
        muestra.get("seq", 0), ultimo, ciclos
    )
    ciclos = min(ciclos, limite + 1)
    nav["ultimo_seq"][nombre] = ultimo
    nav["ciclos_sin_actualizar"][nombre] = ciclos
    return bool(muestra.get("valido") and ultimo > 0 and ciclos <= limite)


def _actualizar_frescura(nav, sistema):
    sonar = sistema["sonar"]
    tof = sistema["tof"]
    fuentes = (
        ("imu", sistema["imu"], config.CICLOS_MAX_SIN_IMU),
        ("sf", sonar["frontal"], config.CICLOS_MAX_SIN_SONAR),
        ("si", sonar["izquierdo"], config.CICLOS_MAX_SIN_SONAR),
        ("sd", sonar["derecho"], config.CICLOS_MAX_SIN_SONAR),
        ("tf", tof["frontal"], config.CICLOS_MAX_SIN_TOF),
        ("ti", tof["izquierdo"], config.CICLOS_MAX_SIN_TOF),
        ("td", tof["derecho"], config.CICLOS_MAX_SIN_TOF),
    )
    return {nombre: _fuente_fresca(nav, nombre, muestra, limite) for nombre, muestra, limite in fuentes}


def _valor(muestra, fresca):
    valor = muestra.get("valor") if fresca else None
    return valor if utilidades.numero_finito(valor) else None


def _frente_critico(sf, tf, umbral_sonar, umbral_tof):
    return bool(
        (sf is not None and sf <= umbral_sonar)
        or (tf is not None and tf <= umbral_tof)
    )


def observar_frente(sistema, frescas):
    sf_muestra = sistema["sonar"]["frontal"]
    tf_muestra = sistema["tof"]["frontal"]
    sf = _valor(sf_muestra, frescas["sf"])
    tf = _valor(tf_muestra, frescas["tf"])
    disponible = sf is not None or tf is not None

    critico = bool((sf is not None and sf <= config.SONAR_FRONTAL_ENTRAR_APROX_CM) or (tf is not None and tf <= config.TOF_FRONTAL_ENTRAR_APROX_CM))
    
    aproximacion = bool((sf is not None and sf <= config.SONAR_FRONTAL_ENTRAR_APROX_CM) or (tf is not None and tf <= config.TOF_FRONTAL_ENTRAR_APROX_CM))
    libre = bool(disponible and (sf is None or sf >= config.SONAR_FRONTAL_LIBRE_CM) and (tf is None or tf >= config.TOF_FRONTAL_LIBRE_CM))
    salir = bool(disponible and (sf is None or sf >= config.SONAR_FRONTAL_SALIR_APROX_CM) and (tf is None or tf >= config.TOF_FRONTAL_SALIR_APROX_CM))

    espacio_pregiro = bool(disponible and (sf is None or sf >= config.DISTANCIA_FRONTAL_MIN_GIRO_CM) and (tf is None or tf >= config.DISTANCIA_FRONTAL_MIN_GIRO_CM))

    giro_fluido = bool(espacio_pregiro and (sf is None or sf <= config.DISTANCIA_FRONTAL_INICIO_GIRO_FLUIDO_CM) and (tf is None or tf <= config.DISTANCIA_FRONTAL_INICIO_GIRO_FLUIDO_CM))

    return {
        "disponible": disponible,
        "critico": critico,
        "aproximacion": aproximacion,
        "libre": libre,
        "salir": salir,
        "espacio_giro": espacio_pregiro,
        "giro_fluido": giro_fluido,
        "seq": (
            sf_muestra["seq"] if sf is not None else 0,
            tf_muestra["seq"] if tf is not None else 0,
        ),
    }


def aplicar_proteccion_frontal():
    sistema = estado.estado
    nav = sistema["navegacion"]
    sonar = sistema["sonar"]["frontal"]
    tof = sistema["tof"]["frontal"]
    sf = _valor(sonar, sonar.get("valido", False))
    tf = _valor(tof, tof.get("valido", False))

    if nav["modo"] == "manual":
        umbral_sonar = config.SONAR_FRONTAL_CRITICO_MANUAL_CM
        umbral_tof = config.TOF_FRONTAL_CRITICO_MANUAL_CM
    else:
        umbral_sonar = config.SONAR_FRONTAL_CRITICO_CM
        umbral_tof = config.TOF_FRONTAL_CRITICO_CM

    motor = sistema["motor"]
    critico = _frente_critico(sf, tf, umbral_sonar, umbral_tof)
    hay_lectura = sf is not None or tf is not None
    enclavado_anterior = bool(nav["frente_critico_enclavado"])
    if motor.get("direccion") == -1:
        enclavado = False
    elif hay_lectura:
        enclavado = critico
    else:
        enclavado = enclavado_anterior
    nav["frente_critico_enclavado"] = enclavado
    if enclavado and not enclavado_anterior:
        nav["motivo_transicion"] = "freno_frontal_critico"
    frenar = bool(motor.get("freno", False) or enclavado)
    motor["freno"] = frenar
    if frenar:
        motor["velocidad"] = 0
        motor["direccion"] = 0
    return frenar


def _observar_tof_lateral(sistema, frescas):
    tof = sistema["tof"]
    ti = _valor(tof["izquierdo"], frescas["ti"])
    td = _valor(tof["derecho"], frescas["td"])
    pareja_control = bool(
        ti is not None
        and td is not None
        and ti <= config.TOF_LATERAL_RANGO_CONTROL_CM
        and td <= config.TOF_LATERAL_RANGO_CONTROL_CM
    )
    asimetria = (ti - td) / (ti + td) if pareja_control and ti + td > 0 else None
    apertura_tof = None
    if ti is not None and td is not None:
        abre_izquierda = bool(
            ti >= config.TOF_INICIO_DETECCION_APERTURA_CM
            and ti - td >= config.DELTA_APERTURA_TOF_CM
            and ti >= td * config.FACTOR_APERTURA_TOF
        )
        abre_derecha = bool(
            td >= config.TOF_INICIO_DETECCION_APERTURA_CM
            and td - ti >= config.DELTA_APERTURA_TOF_CM
            and td >= ti * config.FACTOR_APERTURA_TOF
        )
        if abre_izquierda != abre_derecha:
            apertura_tof = IZQUIERDA if abre_izquierda else DERECHA
    peligro_i = ti is not None and ti <= config.TOF_LATERAL_PELIGRO_CM
    peligro_d = td is not None and td <= config.TOF_LATERAL_PELIGRO_CM
    proteccion = 0.0
    if peligro_i and not peligro_d:
        proteccion = -abs(config.COMANDO_EVASION_TOF)
    elif peligro_d and not peligro_i:
        proteccion = abs(config.COMANDO_EVASION_TOF)
    return {
        "apertura_tof": apertura_tof,
        "correccion": utilidades.control_correccion_tof(asimetria),
        "peligro_i": peligro_i,
        "peligro_d": peligro_d,
        "peligro_ambos": peligro_i and peligro_d,
        "proteccion": proteccion,
    }


def _observar_apertura_sonar(sistema, frescas):
    sonar = sistema["sonar"]
    izquierdo = _valor(sonar["izquierdo"], frescas["si"])
    derecho = _valor(sonar["derecho"], frescas["sd"])
    if izquierdo is None or derecho is None:
        return None, None
    abre_i = bool(
        derecho <= config.SONAR_PASILLO_MAX_CM
        and izquierdo - derecho >= config.DELTA_APERTURA_SONAR_CM
        and izquierdo >= derecho * config.FACTOR_APERTURA_SONAR
    )
    abre_d = bool(
        izquierdo <= config.SONAR_PASILLO_MAX_CM
        and derecho - izquierdo >= config.DELTA_APERTURA_SONAR_CM
        and derecho >= izquierdo * config.FACTOR_APERTURA_SONAR
    )
    apertura_sonar = None
    if abre_i != abre_d:
        apertura_sonar = IZQUIERDA if abre_i else DERECHA
    return apertura_sonar, (
        sonar["izquierdo"]["seq"],
        sonar["derecho"]["seq"],
    )


def _consumir_secuencias_sonar(nav, secuencias):
    if secuencias is None:
        return False
    if (
        secuencias[0] == nav["ultimo_seq_izquierdo"]
        or secuencias[1] == nav["ultimo_seq_derecho"]
    ):
        return False
    nav["ultimo_seq_izquierdo"], nav["ultimo_seq_derecho"] = secuencias
    return True


def _resolver_evidencia_giro(
    apertura_tof,
    apertura_sonar,
    aceptar_sonar,
    sentido_pista,
):
    if apertura_tof is not None and apertura_sonar is not None:
        if apertura_tof == apertura_sonar:
            return apertura_tof, True
        if sentido_pista in (apertura_tof, apertura_sonar):
            return sentido_pista, False
        return None, False
    if apertura_tof is not None:
        return apertura_tof, False
    if aceptar_sonar:
        return apertura_sonar, False
    return None, False


def _actualizar_confirmaciones_giro(
    nav,
    evidencia_ciclo,
    evidencia_alta_confianza,
):
    candidato_actual = nav["candidato_giro"]
    if evidencia_ciclo is None:
        nav["candidato_giro"] = None
        nav["candidato_giro_alta_confianza"] = False
        nav["confirmaciones_giro_lateral"] = 0
    elif candidato_actual is None:
        nav["candidato_giro"] = evidencia_ciclo
        nav["candidato_giro_alta_confianza"] = evidencia_alta_confianza
        nav["confirmaciones_giro_lateral"] = 1
    elif evidencia_ciclo == candidato_actual:
        nav["candidato_giro_alta_confianza"] = bool(
            nav["candidato_giro_alta_confianza"]
            and evidencia_alta_confianza
        )
        nav["confirmaciones_giro_lateral"] += 1
    else:
        nav["candidato_giro"] = None
        nav["candidato_giro_alta_confianza"] = False
        nav["confirmaciones_giro_lateral"] = 0


def _promover_candidato_confirmado(nav):
    if (
        nav["candidato_giro"] in (IZQUIERDA, DERECHA)
        and nav["confirmaciones_giro_lateral"]
        >= config.MUESTRAS_CONFIRMAR_GIRO_LATERAL
    ):
        nav["giro_pendiente"] = nav["candidato_giro"]
        if (
            nav["sentido_pista"] is None
            and nav["candidato_giro_alta_confianza"]
        ):
            nav["sentido_pista"] = nav["candidato_giro"]


def _actualizar_candidato(nav, sistema, frescas, tofs, aceptar_sonar=False):
    if nav["giro_pendiente"] in (IZQUIERDA, DERECHA):
        return
    apertura_tof = tofs["apertura_tof"]
    apertura_sonar, secuencias = _observar_apertura_sonar(sistema, frescas)
    if not _consumir_secuencias_sonar(nav, secuencias):
        return
    nav["apertura_tof"] = apertura_tof
    nav["apertura_sonar"] = apertura_sonar
    evidencia_ciclo, evidencia_alta_confianza = _resolver_evidencia_giro(
        apertura_tof,
        apertura_sonar,
        aceptar_sonar,
        nav["sentido_pista"],
    )
    _actualizar_confirmaciones_giro(
        nav,
        evidencia_ciclo,
        evidencia_alta_confianza,
    )
    _promover_candidato_confirmado(nav)


def _orden_recta(nav, velocidad, tofs):
    heading = utilidades.control_heading(
        nav["heading_error"],
        config.KP_HEADING_RECTA if velocidad == config.VELOCIDAD_AVANCE
        else config.KP_HEADING_APROXIMACION,
    )
    if abs(nav["heading_error"]) > config.ERROR_GIRO_PERMITIDO:
        comando = heading
    else:
        comando = utilidades.combinar_controles(heading, tofs["correccion"])
    if tofs["peligro_ambos"]:
        _orden()
    elif tofs["peligro_i"] or tofs["peligro_d"]:
        _orden(velocidad, 1, tofs["proteccion"])
    else:
        _orden(velocidad, 1, comando)


def _iniciar_giro(nav, sentido, heading_actual):
    reanudando = nav["sentido_giro"] == sentido and utilidades.numero_finito(
        nav["heading_ref"]
    )
    if not reanudando:
        signo = 1 if sentido == DERECHA else -1
        nav["heading_ref"] = utilidades.normalizar_angulo(
            nav["heading_ref"]
            + 90.0 * config.SIGNO_HEADING_DERECHA * signo
        )
    nav["sentido_giro"] = sentido
    nav["giro_pendiente"] = None
    nav["confirmaciones_fin_giro"] = 0
    nav["ultimo_seq_imu_giro"] = estado.estado["imu"]["seq"]
    nav["heading_error"] = utilidades.error_angular(
        nav["heading_ref"], heading_actual
    )
    _cambiar_maniobra(nav, GIRO, "giro_" + sentido)


def _entrar_preparacion(nav, frente, motivo):
    if nav["sentido_giro"] in (IZQUIERDA, DERECHA):
        nav["giro_pendiente"] = nav["sentido_giro"]
    nav["seq_frontal_preparacion"] = frente["seq"]
    _cambiar_maniobra(nav, PREPARACION_GIRO, motivo)


def _frente_actualizado(frente, referencia):
    if not isinstance(referencia, tuple):
        return False
    return any(
        actual > 0 and actual != anterior
        for actual, anterior in zip(frente["seq"], referencia)
    )


def _entrar_fallo(nav, fuente, motivo):
    if nav["sentido_giro"] in (IZQUIERDA, DERECHA):
        nav["giro_pendiente"] = nav["sentido_giro"]
    nav["fallo"] = {"fuente": fuente, "motivo": motivo}
    _cambiar_maniobra(nav, FALLO, motivo)
    _orden(freno=nav["activo"])


def _actualizar_fallo(nav, frescas, frente):
    _orden(freno=nav["activo"])
    fallo = nav["fallo"] or {}
    listo = bool(
        frescas["imu"]
        and frente["disponible"]
        and estado.estado["motor"]["ok"]
        and estado.estado["servo"]["ok"]
    )
    if listo:
        if fallo.get("fuente") == "imu":
            nav["heading_ref"] = estado.estado["imu"]["heading"]
            nav["heading_error"] = 0.0
            nav["sentido_giro"] = None
        nav["fallo"] = None
        _cambiar_maniobra(nav, DETENIDO, "subsistema_recuperado")


def _confirmar_fin_giro(nav, frente):
    imu = estado.estado["imu"]
    if imu["seq"] == nav["ultimo_seq_imu_giro"]:
        return False
    nav["ultimo_seq_imu_giro"] = imu["seq"]
    if abs(nav["heading_error"]) <= config.ERROR_GIRO_PERMITIDO:
        nav["confirmaciones_fin_giro"] += 1
    else:
        nav["confirmaciones_fin_giro"] = 0
    if nav["confirmaciones_fin_giro"] < config.MUESTRAS_CONFIRMAR_FIN_GIRO:
        return False

    nav["esquinas"] += 1
    nav["vueltas"] = nav["esquinas"] // 4
    nav["sentido_giro"] = None
    nav["giro_pendiente"] = None
    nav["candidato_giro"] = None
    nav["candidato_giro_alta_confianza"] = False
    nav["confirmaciones_giro_lateral"] = 0
    if (
        config.VUELTAS_OBJETIVO > 0
        and nav["vueltas"] >= config.VUELTAS_OBJETIVO
    ):
        nav["activo"] = False
        _cambiar_maniobra(nav, DETENIDO, "vueltas_completadas")
    elif frente["aproximacion"]:
        _cambiar_maniobra(nav, APROXIMACION, "giro_completado_frente_cerca")
    else:
        _cambiar_maniobra(nav, CRUCERO, "giro_completado_frente_libre")
    return True


def actualizar():
    sistema = estado.estado
    nav = sistema["navegacion"]
    boton_start()

    if nav["modo"] != "automatico":
        return
    if not nav["activo"]:
        _cambiar_maniobra(nav, DETENIDO, "automatico_inactivo")
        _orden()
        return

    frescas = _actualizar_frescura(nav, sistema)
    frente = observar_frente(sistema, frescas)
    if nav["maniobra"] == FALLO:
        _actualizar_fallo(nav, frescas, frente)
        return
    if not sistema["motor"]["ok"] or not sistema["servo"]["ok"]:
        _entrar_fallo(nav, "actuador", "actuador_no_disponible")
        return
    if not frescas["imu"]:
        _entrar_fallo(nav, "imu", "imu_sin_lectura_nueva")
        return
    if not frente["disponible"]:
        _entrar_fallo(nav, "frontal", "frontal_sin_lectura_nueva")
        return

    heading = utilidades.normalizar_angulo(sistema["imu"]["heading"])
    if nav["heading_ref"] is None:
        nav["heading_ref"] = heading
    nav["heading_error"] = utilidades.error_angular(
        nav["heading_ref"], heading
    )
    tofs = _observar_tof_lateral(sistema, frescas)
    nav["ciclos_maniobra"] += 1
    maniobra = nav["maniobra"]

    if maniobra == DETENIDO:
        _orden()
        if nav["giro_pendiente"] in (IZQUIERDA, DERECHA):
            _entrar_preparacion(nav, frente, "reanudar_giro_pendiente")
        elif frente["aproximacion"]:
            _cambiar_maniobra(nav, APROXIMACION, "inicio_frente_cerca")
        else:
            _cambiar_maniobra(nav, CRUCERO, "sensores_listos")

    elif maniobra == CRUCERO:
        if frente["critico"]:
            _cambiar_maniobra(nav, APROXIMACION, "freno_frontal_critico")
            _orden(freno=True)
        elif frente["aproximacion"] or not frente["libre"]:
            _cambiar_maniobra(nav, APROXIMACION, "frente_cercano")
            _orden_recta(nav, config.VELOCIDAD_APROXIMACION, tofs)
        else:
            _orden_recta(nav, config.VELOCIDAD_AVANCE, tofs)

    elif maniobra == APROXIMACION:
        _actualizar_candidato(
            nav, sistema, frescas, tofs, aceptar_sonar=frente["critico"]
        )
        if frente["critico"]:
            if nav["giro_pendiente"] in (IZQUIERDA, DERECHA):
                _entrar_preparacion(nav, frente, "freno_frontal_critico")
            else:
                nav["motivo_transicion"] = "freno_frontal_critico"
            _orden(freno=True)
        elif (
            nav["giro_pendiente"] in (IZQUIERDA, DERECHA)
            and frente["giro_fluido"]
            and abs(nav["heading_error"]) <= config.ERROR_GIRO_PERMITIDO
        ):
            _iniciar_giro(nav, nav["giro_pendiente"], heading)
            _orden(
                config.VELOCIDAD_GIRO,
                1,
                utilidades.control_giro(nav["heading_error"]),
            )
        elif frente["salir"] and nav["candidato_giro"] is None:
            _cambiar_maniobra(nav, CRUCERO, "frente_liberado")
            _orden_recta(nav, config.VELOCIDAD_AVANCE, tofs)
        else:
            _orden_recta(nav, config.VELOCIDAD_APROXIMACION, tofs)

    elif maniobra == PREPARACION_GIRO:
        _orden(freno=True)
        if nav["ciclos_maniobra"] < config.CICLOS_PREPARACION_GIRO:
            return
        if not _frente_actualizado(frente, nav["seq_frontal_preparacion"]):
            return
        if nav["giro_pendiente"] not in (IZQUIERDA, DERECHA):
            _entrar_fallo(nav, "laterales", "sentido_giro_no_disponible")
        elif frente["espacio_giro"]:
            _iniciar_giro(nav, nav["giro_pendiente"], heading)
        else:
            _cambiar_maniobra(nav, RETROCESO_GIRO, "retroceso_para_giro")

    elif maniobra == RETROCESO_GIRO:
        if frente["espacio_giro"]:
            _entrar_preparacion(nav, frente, "objetivo_frontal_alcanzado")
            _orden(freno=True)
        else:
            comando = 1.0 if nav["giro_pendiente"] == IZQUIERDA else -1.0
            _orden(config.VELOCIDAD_RETROCESO, -1, comando)

    elif maniobra == GIRO:
        if frente["critico"]:
            _entrar_preparacion(nav, frente, "freno_frontal_critico")
            _orden(freno=True)
        elif _confirmar_fin_giro(nav, frente):
            _orden()
        else:
            _orden(
                config.VELOCIDAD_GIRO,
                1,
                utilidades.control_giro(nav["heading_error"]),
            )

    else:
        _entrar_fallo(nav, "estado", "maniobra_desconocida")
