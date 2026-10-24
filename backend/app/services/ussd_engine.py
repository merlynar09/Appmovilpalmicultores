"""Motor de menús USSD — máquina de estados con sesión persistida en base de
datos (NUNCA en memoria del proceso Flask: una sesión real puede llegar a
cualquier instancia del backend entre una interacción y la siguiente).

Este módulo es deliberadamente agnóstico del proveedor: no sabe nada de
formatos HTTP, cabeceras ni firmas — eso vive en `app/routes/ussd.py`
(el adaptador). Aquí solo entra: ¿qué sesión es, qué escribió el usuario? Y
sale: ¿qué texto se le muestra, sigue la sesión o termina?

Reutiliza la lógica de negocio YA existente en vez de duplicarla:
- Censo de producción: `app.routes.produccion._build_registro`
- Solicitud de transporte: `app.routes.sms._procesar_transporte`
- Avisos: `app.routes.alertas._generar_alertas_cosecha` (misma función que
  usa la app — su propio guard evita duplicar notificaciones)

Acceso restringido a cuentas con rol "palmicultor" y estado "activo", igual
que el puente SMS existente (RN de privacidad: cada sesión solo puede ver y
operar sus propios datos, nunca los de otro usuario).
"""

import os
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import (
    Comprador,
    EstadoVia,
    Finca,
    Lote,
    Notificacion,
    Precio,
    SolicitudTransporte,
    Usuario,
    UssdSesion,
)
from app.services.contenido import obtener_contenido

TTL_SEGUNDOS = int(os.environ.get("USSD_SESSION_TTL_SEGUNDOS", "180"))
MAX_ITEMS_LISTA = 5  # pantallas USSD son pequeñas; se trunca con aviso si hay más

MENU_PRINCIPAL_TEXTO_DEFECTO = (
    "Palma Viva\n"
    "1 Precio de palma\n"
    "2 Compradores\n"
    "3 Mi transporte\n"
    "4 Estado de vias\n"
    "5 Avisos\n"
    "6 Registrar produccion\n"
    "7 Solicitar transporte\n"
    "8 Ayuda\n"
    "0 Salir"
)

AYUDA_TEXTO_DEFECTO = (
    "Palma Viva USSD: consulta precios, compradores, transporte y vias; "
    "registra tu censo de produccion y pide transporte, todo sin internet. "
    "0 Volver al menu."
)

# Valores efectivos usados por todo el resto del módulo (funciones y lambdas
# de abajo leen estos nombres globales en cada llamada, no al definirse) —
# _refrescar_contenido_editable() los actualiza justo antes de procesar cada
# entrada, para que un cambio del administrador (CU17) se refleje de
# inmediato sin reiniciar el servidor. Si la consulta a BD falla,
# obtener_contenido() ya devuelve el texto por defecto, así que esto nunca
# puede romper el flujo USSD.
MENU_PRINCIPAL_TEXTO = MENU_PRINCIPAL_TEXTO_DEFECTO
AYUDA_TEXTO = AYUDA_TEXTO_DEFECTO


def _refrescar_contenido_editable():
    global MENU_PRINCIPAL_TEXTO, AYUDA_TEXTO
    MENU_PRINCIPAL_TEXTO = obtener_contenido("ussd_menu_principal", MENU_PRINCIPAL_TEXTO_DEFECTO)
    AYUDA_TEXTO = obtener_contenido("ussd_ayuda", AYUDA_TEXTO_DEFECTO)


def procesar_entrada(telefono, entrada, session_id, proveedor="simulador", request_id=None, nueva_sesion=False):
    """Punto de entrada único del motor. Devuelve
    {"respuesta": str, "continuar": bool}. NUNCA lanza excepción de negocio
    hacia el llamador: cualquier error se convierte en un mensaje breve."""
    _refrescar_contenido_editable()
    telefono = (telefono or "").strip()
    entrada = (entrada or "").strip()

    if not telefono or not session_id:
        return {"respuesta": "Error: faltan datos de sesion.", "continuar": False}

    sesion = (
        UssdSesion.query.filter_by(session_id=session_id).with_for_update().first()
    )

    if sesion is None:
        sesion = _crear_sesion(session_id, telefono, proveedor)
        # Primera interacción: no hay "entrada" de menú todavía que procesar
        # (el proveedor manda vacío o "*123#" al marcar) — se muestra el
        # menú principal directamente, sin tratarlo como una opción elegida.
        return _iniciar(sesion)

    # --- sesión ya cerrada (terminó en una interacción previa) ---
    if not sesion.activa:
        return {"respuesta": sesion.ultima_respuesta or "Sesion finalizada.", "continuar": False}

    # --- expiración (ventana deslizante desde la última interacción) ---
    if datetime.utcnow() > sesion.expira_en:
        sesion.activa = False
        sesion.resultado_final = "expirada"
        sesion.ultima_respuesta = "Sesion expirada por inactividad. Vuelve a marcar."
        db.session.commit()
        return {"respuesta": sesion.ultima_respuesta, "continuar": False}

    # --- deduplicación: reintento del proveedor sobre la misma interacción ---
    if request_id and sesion.ultimo_request_id == request_id:
        return {"respuesta": sesion.ultima_respuesta or "", "continuar": sesion.activa}
    if (
        not request_id
        and entrada == sesion.ultima_entrada
        and sesion.estado != sesion.ultimo_estado_previo
        and (sesion.ultimo_estado_previo or "").endswith("_CONFIRMAR")
    ):
        # Sin id de solicitud del proveedor: solo se trata como reintento
        # cuando la interacción anterior fue una CONFIRMACIÓN (la única con
        # efectos reales en la base de datos). Para simple navegación de
        # menús, dos entradas iguales seguidas son legítimas y deben
        # reprocesarse (si no, se arriesga mostrar datos desactualizados).
        return {"respuesta": sesion.ultima_respuesta or "", "continuar": sesion.activa}

    estado_previo = sesion.estado
    try:
        usuario = _usuario_autorizado(sesion)
        if isinstance(usuario, str):
            # mensaje de error de autorización — termina la sesión
            texto, continuar = usuario, False
        else:
            texto, nuevo_estado, continuar = _despachar(sesion, entrada, usuario)
            sesion.estado = nuevo_estado
    except Exception as e:  # nunca dejar una sesión USSD rota a medias
        texto = f"Ocurrio un error. Intenta de nuevo. ({_mensaje_corto(e)})"
        continuar = True

    sesion.ultimo_request_id = request_id
    sesion.ultima_entrada = entrada
    sesion.ultimo_estado_previo = estado_previo
    sesion.ultima_respuesta = texto
    sesion.expira_en = datetime.utcnow() + timedelta(seconds=TTL_SEGUNDOS)  # ventana deslizante
    if not continuar:
        sesion.activa = False
        if not sesion.resultado_final:
            sesion.resultado_final = "completada"
    db.session.commit()

    return {"respuesta": texto, "continuar": continuar}


def _crear_sesion(session_id, telefono, proveedor):
    usuario = Usuario.query.filter_by(telefono=telefono).first()
    sesion = UssdSesion(
        session_id=session_id,
        proveedor=proveedor,
        telefono=telefono,
        usuario_id=usuario.id if usuario else None,
        estado="MENU_PRINCIPAL",
        contexto={},
        expira_en=datetime.utcnow() + timedelta(seconds=TTL_SEGUNDOS),
    )
    db.session.add(sesion)
    db.session.commit()
    return sesion


def _iniciar(sesion):
    usuario = _usuario_autorizado(sesion)
    if isinstance(usuario, str):
        sesion.activa = False
        sesion.resultado_final = "error"
        sesion.ultima_respuesta = usuario
        db.session.commit()
        return {"respuesta": usuario, "continuar": False}

    sesion.ultima_respuesta = MENU_PRINCIPAL_TEXTO
    db.session.commit()
    return {"respuesta": MENU_PRINCIPAL_TEXTO, "continuar": True}


def _usuario_autorizado(sesion):
    """Devuelve el Usuario si puede usar el menú, o un mensaje de error
    (str) si no. La identificación es por el teléfono que entrega el
    proveedor de la sesión — nunca un dato que el propio texto del menú
    pueda suplantar."""
    usuario = Usuario.query.filter_by(telefono=sesion.telefono).first()
    if not usuario:
        return "Numero no registrado en Palma Viva. Descarga la app o registrate con un agente."
    if usuario.estado != "activo":
        return "Tu cuenta no esta activa. Contacta a un administrador."
    if usuario.rol != "palmicultor":
        return "Este menu USSD esta disponible solo para cuentas de palmicultor."
    return usuario


# --------------------------------------------------------- despachador ---

def _despachar(sesion, entrada, usuario):
    handler = _HANDLERS.get(sesion.estado, _handler_menu_principal)
    return handler(sesion, entrada, usuario)


def _handler_menu_principal(sesion, entrada, usuario):
    opciones = {
        "1": lambda: _mostrar_precios(sesion),
        "2": lambda: _mostrar_compradores(sesion),
        "3": lambda: _mostrar_transporte_info(sesion, usuario),
        "4": lambda: _mostrar_vias(sesion),
        "5": lambda: _mostrar_avisos(sesion, usuario),
        "6": lambda: ("Codigo de tu lote:", "PRODUCCION_LOTE", True),
        "7": lambda: ("Codigo de tu lote:", "TRANSPORTE_LOTE", True),
        "8": lambda: (AYUDA_TEXTO, "MENU_PRINCIPAL", True),
        "0": lambda: ("Gracias por usar Palma Viva.", "FIN", False),
    }
    if entrada in opciones:
        return opciones[entrada]()
    return (f"Opcion invalida.\n{MENU_PRINCIPAL_TEXTO}", "MENU_PRINCIPAL", True)


def _handler_volver_si_cero(sesion, entrada, usuario):
    if entrada == "0":
        return (MENU_PRINCIPAL_TEXTO, "MENU_PRINCIPAL", True)
    return None


# --------------------------------------------------------------- precios -

def _mostrar_precios(sesion):
    precios = (
        db.session.query(Precio, Comprador)
        .join(Comprador, Precio.comprador_id == Comprador.id)
        .filter(Precio.estado == "activo", Comprador.estado == "activo")
        .order_by(Precio.fecha_publicacion.desc())
        .limit(MAX_ITEMS_LISTA)
        .all()
    )
    if not precios:
        return ("Sin precios publicados por ahora.\n0 Volver", "MENU_PRECIOS", True)

    lineas = ["Precios vigentes:"]
    for i, (precio, comprador) in enumerate(precios, start=1):
        fecha = precio.fecha_publicacion.strftime("%d/%m") if precio.fecha_publicacion else "-"
        lineas.append(f"{comprador.empresa[:18]}: ${int(precio.valor_moneda):,} ({fecha})")
    lineas.append("0 Volver")
    return ("\n".join(lineas), "MENU_PRECIOS", True)


# ----------------------------------------------------------- compradores -

def _mostrar_compradores(sesion):
    compradores = Comprador.query.filter_by(estado="activo").limit(MAX_ITEMS_LISTA).all()
    if not compradores:
        return ("Sin compradores registrados.\n0 Volver", "MENU_COMPRADORES", True)

    lineas = ["Compradores:"]
    for c in compradores:
        ubicacion = c.ubicacion or c.descripcion or "sin ubicacion"
        lineas.append(f"{c.empresa[:20]} - {ubicacion[:20]}")
    lineas.append("0 Volver")
    return ("\n".join(lineas), "MENU_COMPRADORES", True)


# ----------------------------------------------------------- transporte -

def _mostrar_transporte_info(sesion, usuario):
    solicitudes = (
        SolicitudTransporte.query.filter_by(palmicultor_id=usuario.id)
        .order_by(SolicitudTransporte.fecha_solicitud.desc())
        .limit(MAX_ITEMS_LISTA)
        .all()
    )
    if not solicitudes:
        return ("No tienes solicitudes de transporte.\n0 Volver", "MENU_TRANSPORTE_INFO", True)

    lineas = ["Tus solicitudes:"]
    for s in solicitudes:
        lineas.append(f"#{s.id} {s.cantidad_estimada}ton - {s.estado}")
    lineas.append("0 Volver")
    return ("\n".join(lineas), "MENU_TRANSPORTE_INFO", True)


# ----------------------------------------------------------------- vias --

def _mostrar_vias(sesion):
    vias = EstadoVia.query.order_by(EstadoVia.fecha_actualizacion.desc()).limit(MAX_ITEMS_LISTA).all()
    if not vias:
        return ("Sin novedades de vias.\n0 Volver", "MENU_VIAS", True)

    lineas = ["Estado de vias:"]
    for v in vias:
        lineas.append(f"{v.via[:20]}: {v.estado}")
    lineas.append("0 Volver")
    return ("\n".join(lineas), "MENU_VIAS", True)


# --------------------------------------------------------------- avisos --

def _mostrar_avisos(sesion, usuario):
    # Reutiliza EXACTAMENTE la misma función que usa la app (GET /alertas):
    # su propio guard (`ya_existe`) evita crear notificaciones duplicadas al
    # consultar el menú repetidas veces.
    from app.routes.alertas import _generar_alertas_cosecha

    _generar_alertas_cosecha(usuario.id)

    avisos = (
        Notificacion.query.filter_by(usuario_id=usuario.id)
        .order_by(Notificacion.fecha.desc())
        .limit(MAX_ITEMS_LISTA)
        .all()
    )
    if not avisos:
        return ("Sin avisos nuevos.\n0 Volver", "MENU_AVISOS", True)

    lineas = ["Tus avisos:"]
    for a in avisos:
        marca = "*" if not a.leida else ""
        lineas.append(f"{marca}{a.titulo[:28]}")
    lineas.append("0 Volver")
    return ("\n".join(lineas), "MENU_AVISOS", True)


# ------------------------------------------- registro de produccion (6) --

def _handler_produccion_lote(sesion, entrada, usuario):
    volver = _handler_volver_si_cero(sesion, entrada, usuario)
    if volver:
        return volver
    lote = (
        Lote.query.join(Finca)
        .filter(Finca.usuario_id == usuario.id, Lote.codigo == entrada, Lote.estado == "activo")
        .first()
    )
    if not lote:
        return (f"No se encontro el lote '{entrada[:30]}'. Intenta de nuevo (0 cancelar):", "PRODUCCION_LOTE", True)
    _set_contexto(sesion, codigo_lote=entrada, lote_id=lote.id)
    return ("Palmas evaluadas en la muestra:", "PRODUCCION_PALMAS_EVAL", True)


def _handler_produccion_palmas_eval(sesion, entrada, usuario):
    volver = _handler_volver_si_cero(sesion, entrada, usuario)
    if volver:
        return volver
    valor = _validar_entero_positivo(entrada)
    if valor is None:
        return ("Valor invalido. Escribe un numero mayor a 0 (0 cancelar):", "PRODUCCION_PALMAS_EVAL", True)
    _set_contexto(sesion, palmas_evaluadas=valor)
    return ("Palmas improductivas en la muestra:", "PRODUCCION_PALMAS_IMPROD", True)


def _handler_produccion_palmas_improd(sesion, entrada, usuario):
    volver = _handler_volver_si_cero(sesion, entrada, usuario)
    if volver:
        return volver
    valor = _validar_entero_no_negativo(entrada)
    if valor is None or valor > sesion.contexto.get("palmas_evaluadas", 0):
        return ("Valor invalido (no puede superar las evaluadas). Intenta de nuevo (0 cancelar):", "PRODUCCION_PALMAS_IMPROD", True)
    _set_contexto(sesion, palmas_improductivas=valor)
    return ("Racimos contados en la muestra:", "PRODUCCION_RACIMOS", True)


def _handler_produccion_racimos(sesion, entrada, usuario):
    volver = _handler_volver_si_cero(sesion, entrada, usuario)
    if volver:
        return volver
    valor = _validar_entero_no_negativo(entrada)
    if valor is None:
        return ("Valor invalido. Escribe un numero (0 cancelar):", "PRODUCCION_RACIMOS", True)
    _set_contexto(sesion, racimos_totales=valor)
    return ("Peso promedio del racimo en kg:", "PRODUCCION_PESO", True)


def _handler_produccion_peso(sesion, entrada, usuario):
    if entrada == "0":
        return (MENU_PRINCIPAL_TEXTO, "MENU_PRINCIPAL", True)
    valor = _validar_decimal_positivo(entrada)
    if valor is None:
        return ("Valor invalido. Escribe un numero, ej. 16.5 (0 cancelar):", "PRODUCCION_PESO", True)
    _set_contexto(sesion, peso_promedio_racimo=valor)
    c = sesion.contexto
    resumen = (
        f"Lote {c['codigo_lote']}: {c['palmas_evaluadas']} palmas, "
        f"{c['palmas_improductivas']} improd, {c['racimos_totales']} racimos, "
        f"{c['peso_promedio_racimo']}kg/racimo.\n1 Confirmar  2 Cancelar"
    )
    return (resumen, "PRODUCCION_CONFIRMAR", True)


def _handler_produccion_confirmar(sesion, entrada, usuario):
    if entrada == "2" or entrada == "0":
        return ("Censo cancelado.\n" + MENU_PRINCIPAL_TEXTO, "MENU_PRINCIPAL", True)
    if entrada != "1":
        c = sesion.contexto
        resumen = (
            f"Opcion invalida.\nLote {c['codigo_lote']}: {c['palmas_evaluadas']} palmas, "
            f"{c['racimos_totales']} racimos, {c['peso_promedio_racimo']}kg.\n1 Confirmar  2 Cancelar"
        )
        return (resumen, "PRODUCCION_CONFIRMAR", True)

    from app.routes.produccion import _build_registro

    c = sesion.contexto
    registro, error = _build_registro(
        {
            "lote_id": c["lote_id"],
            "palmas_evaluadas": c["palmas_evaluadas"],
            "palmas_improductivas": c["palmas_improductivas"],
            "racimos_totales": c["racimos_totales"],
            "peso_promedio_racimo": c["peso_promedio_racimo"],
            "fuente": "ussd",
        },
        usuario.id,
    )
    if error:
        return (f"No se pudo guardar: {error}", "MENU_PRINCIPAL", True)
    db.session.add(registro)
    db.session.commit()
    return (f"Censo guardado. ID #{registro.id}. Gracias.", "FIN", False)


# ------------------------------------------ solicitud de transporte (7) --

def _handler_transporte_lote(sesion, entrada, usuario):
    volver = _handler_volver_si_cero(sesion, entrada, usuario)
    if volver:
        return volver
    lote = (
        Lote.query.join(Finca)
        .filter(Finca.usuario_id == usuario.id, Lote.codigo == entrada, Lote.estado == "activo")
        .first()
    )
    if not lote:
        return (f"No se encontro el lote '{entrada[:30]}'. Intenta de nuevo (0 cancelar):", "TRANSPORTE_LOTE", True)
    _set_contexto(sesion, codigo_lote=entrada)
    return ("Cantidad estimada en toneladas:", "TRANSPORTE_CANTIDAD", True)


def _handler_transporte_cantidad(sesion, entrada, usuario):
    volver = _handler_volver_si_cero(sesion, entrada, usuario)
    if volver:
        return volver
    valor = _validar_decimal_positivo(entrada)
    if valor is None:
        return ("Valor invalido. Escribe un numero (0 cancelar):", "TRANSPORTE_CANTIDAD", True)
    _set_contexto(sesion, cantidad=valor)
    return ("Fecha del servicio AAAA-MM-DD (o 9 para omitir):", "TRANSPORTE_FECHA", True)


def _handler_transporte_fecha(sesion, entrada, usuario):
    if entrada == "0":
        return (MENU_PRINCIPAL_TEXTO, "MENU_PRINCIPAL", True)
    fecha = None
    if entrada != "9":
        try:
            fecha = date.fromisoformat(entrada)
        except ValueError:
            return ("Fecha invalida. Formato AAAA-MM-DD, o 9 para omitir (0 cancelar):", "TRANSPORTE_FECHA", True)
    _set_contexto(sesion, fecha=entrada if entrada != "9" else None)
    c = sesion.contexto
    resumen = (
        f"Lote {c['codigo_lote']}: {c['cantidad']} ton"
        + (f", fecha {c['fecha']}" if c.get("fecha") else "")
        + ".\n1 Confirmar  2 Cancelar"
    )
    return (resumen, "TRANSPORTE_CONFIRMAR", True)


def _handler_transporte_confirmar(sesion, entrada, usuario):
    if entrada == "2" or entrada == "0":
        return ("Solicitud cancelada.\n" + MENU_PRINCIPAL_TEXTO, "MENU_PRINCIPAL", True)
    if entrada != "1":
        c = sesion.contexto
        resumen = f"Opcion invalida.\nLote {c['codigo_lote']}: {c['cantidad']} ton.\n1 Confirmar  2 Cancelar"
        return (resumen, "TRANSPORTE_CONFIRMAR", True)

    from app.routes.sms import _procesar_transporte

    c = sesion.contexto
    args = [c["codigo_lote"], str(c["cantidad"])]
    if c.get("fecha"):
        args.append(c["fecha"])
    try:
        respuesta = _procesar_transporte(usuario, args)
    except ValueError as e:
        return (f"No se pudo crear: {e}", "MENU_PRINCIPAL", True)
    return (respuesta, "FIN", False)


# --------------------------------------------------------------- utils --

def _set_contexto(sesion, **kwargs):
    contexto = dict(sesion.contexto or {})
    contexto.update(kwargs)
    sesion.contexto = contexto


def _validar_entero_positivo(texto):
    try:
        v = int(texto)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _validar_entero_no_negativo(texto):
    try:
        v = int(texto)
        return v if v >= 0 else None
    except (TypeError, ValueError):
        return None


def _validar_decimal_positivo(texto):
    try:
        v = float(texto)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _mensaje_corto(e):
    texto = str(e)
    return texto[:60] if texto else type(e).__name__


_HANDLERS = {
    "MENU_PRINCIPAL": _handler_menu_principal,
    "MENU_PRECIOS": lambda s, e, u: (MENU_PRINCIPAL_TEXTO, "MENU_PRINCIPAL", True) if e == "0" else _mostrar_precios(s),
    "MENU_COMPRADORES": lambda s, e, u: (MENU_PRINCIPAL_TEXTO, "MENU_PRINCIPAL", True) if e == "0" else _mostrar_compradores(s),
    "MENU_TRANSPORTE_INFO": lambda s, e, u: (MENU_PRINCIPAL_TEXTO, "MENU_PRINCIPAL", True) if e == "0" else _mostrar_transporte_info(s, u),
    "MENU_VIAS": lambda s, e, u: (MENU_PRINCIPAL_TEXTO, "MENU_PRINCIPAL", True) if e == "0" else _mostrar_vias(s),
    "MENU_AVISOS": lambda s, e, u: (MENU_PRINCIPAL_TEXTO, "MENU_PRINCIPAL", True) if e == "0" else _mostrar_avisos(s, u),
    "PRODUCCION_LOTE": _handler_produccion_lote,
    "PRODUCCION_PALMAS_EVAL": _handler_produccion_palmas_eval,
    "PRODUCCION_PALMAS_IMPROD": _handler_produccion_palmas_improd,
    "PRODUCCION_RACIMOS": _handler_produccion_racimos,
    "PRODUCCION_PESO": _handler_produccion_peso,
    "PRODUCCION_CONFIRMAR": _handler_produccion_confirmar,
    "TRANSPORTE_LOTE": _handler_transporte_lote,
    "TRANSPORTE_CANTIDAD": _handler_transporte_cantidad,
    "TRANSPORTE_FECHA": _handler_transporte_fecha,
    "TRANSPORTE_CONFIRMAR": _handler_transporte_confirmar,
}
