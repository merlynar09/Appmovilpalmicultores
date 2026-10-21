from datetime import datetime
from app.extensions import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(150), nullable=False)
    telefono = db.Column(db.String(20), unique=True, nullable=False, index=True)
    correo = db.Column(db.String(150), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # palmicultor | transportador | comprador | administrador
    estado = db.Column(db.String(20), default="activo")
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    fincas = db.relationship("Finca", backref="propietario", lazy=True)
    transportador = db.relationship("Transportador", backref="usuario", uselist=False)
    comprador = db.relationship("Comprador", backref="usuario", uselist=False)
    notificaciones = db.relationship("Notificacion", backref="usuario", lazy=True)


class Finca(db.Model):
    __tablename__ = "fincas"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    ubicacion = db.Column(db.String(200))
    municipio = db.Column(db.String(100), default="Tumaco")
    vereda = db.Column(db.String(100))
    coordenadas_lat = db.Column(db.Float)
    coordenadas_long = db.Column(db.Float)
    area_hectareas = db.Column(db.Float)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.String(20), default="activa")

    lotes = db.relationship("Lote", backref="finca", lazy=True)


class Lote(db.Model):
    __tablename__ = "lotes"

    id = db.Column(db.Integer, primary_key=True)
    finca_id = db.Column(db.Integer, db.ForeignKey("fincas.id"), nullable=False)
    codigo = db.Column(db.String(60), nullable=False)  # nomenclatura flexible (RN02)
    nombre = db.Column(db.String(100))
    bloque = db.Column(db.String(50))
    sector = db.Column(db.String(50))
    area_hectareas = db.Column(db.Float)
    anio_siembra = db.Column(db.Integer)
    numero_palmas = db.Column(db.Integer)
    material_sembrado = db.Column(db.String(50))
    topografia = db.Column(db.String(50))
    drenaje = db.Column(db.String(50))
    estado_sanitario = db.Column(db.String(50))
    numero_lineas = db.Column(db.Integer)
    estado = db.Column(db.String(20), default="activo")

    ciclos_cosecha = db.relationship("CicloCosecha", backref="lote", lazy=True)
    registros_polinizacion = db.relationship("RegistroPolinizacion", backref="lote", lazy=True)
    registros_produccion = db.relationship("RegistroProduccion", backref="lote", lazy=True)
    pronosticos = db.relationship("PronosticoProduccion", backref="lote", lazy=True)


class CicloCosecha(db.Model):
    __tablename__ = "ciclos_cosecha"

    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=False)
    fecha_ultima_cosecha = db.Column(db.Date)
    fecha_inicio = db.Column(db.Date)
    duracion_dias = db.Column(db.Integer)  # 7-12 jóvenes / 9-15 adultas (RN03)
    dias_anticipacion_alerta = db.Column(db.Integer, default=3)  # 1-7 días (RN03)
    proxima_fecha_estimada = db.Column(db.Date)
    observaciones = db.Column(db.Text)
    estado = db.Column(db.String(20), default="Programado")
    # Programado | Próximo | En curso | Completado | Retrasado

    alertas = db.relationship("Notificacion", backref="ciclo_cosecha", lazy=True)


class RegistroPolinizacion(db.Model):
    __tablename__ = "registros_polinizacion"

    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=False)
    fecha = db.Column(db.Date, default=datetime.utcnow)
    numero_inflorescencias = db.Column(db.Integer)
    cantidad_producto = db.Column(db.Float)
    gramos_por_inflorescencia = db.Column(db.Float)
    responsable = db.Column(db.String(150))
    observaciones = db.Column(db.Text)


class RegistroProduccion(db.Model):
    __tablename__ = "registros_produccion"

    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=False)
    fecha = db.Column(db.Date, default=datetime.utcnow)
    palmas_evaluadas = db.Column(db.Integer)
    racimos_pequenos = db.Column(db.Integer)
    racimos_medianos = db.Column(db.Integer)
    racimos_maduros = db.Column(db.Integer)
    racimos_totales = db.Column(db.Integer)
    palmas_improductivas = db.Column(db.Integer)
    peso_promedio_racimo = db.Column(db.Float)
    fruto_suelto = db.Column(db.Float)
    observaciones = db.Column(db.Text)
    fuente = db.Column(db.String(20), default="app")  # app | sms | ussd
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    pronosticos = db.relationship("PronosticoProduccion", backref="registro_produccion", lazy=True)


class PronosticoProduccion(db.Model):
    __tablename__ = "pronosticos_produccion"

    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=False)
    registro_produccion_id = db.Column(db.Integer, db.ForeignKey("registros_produccion.id"), nullable=True)
    fecha_calculo = db.Column(db.DateTime, default=datetime.utcnow)
    palmas_totales = db.Column(db.Integer)
    palmas_improductivas_muestra = db.Column(db.Integer)
    palmas_productivas = db.Column(db.Float)
    palmas_productivas_muestreadas = db.Column(db.Integer)
    promedio_estructuras = db.Column(db.Float)
    racimos_estimados = db.Column(db.Float)
    peso_promedio = db.Column(db.Float)
    produccion_estimada_kg = db.Column(db.Float)
    produccion_estimada_ton = db.Column(db.Float)
    distribucion_mensual = db.Column(db.JSON)  # [{mes, porcentaje, produccion_kg, produccion_ton}, ...]
    metodologia = db.Column(db.String(100), default="RN04 - muestreo 4-5%")
    observaciones = db.Column(db.Text)


class Transportador(db.Model):
    __tablename__ = "transportadores"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, unique=True)
    ubicacion = db.Column(db.String(200))
    disponible = db.Column(db.Boolean, default=True)
    estado = db.Column(db.String(20), default="pendiente")  # pendiente | aprobado | rechazado
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehiculos = db.relationship("Vehiculo", backref="transportador", lazy=True)
    solicitudes = db.relationship("SolicitudTransporte", backref="transportador", lazy=True)


class Vehiculo(db.Model):
    __tablename__ = "vehiculos"

    id = db.Column(db.Integer, primary_key=True)
    transportador_id = db.Column(db.Integer, db.ForeignKey("transportadores.id"), nullable=False)
    placa = db.Column(db.String(10), unique=True, nullable=False)
    tipo_vehiculo = db.Column(db.String(50))
    capacidad_toneladas = db.Column(db.Float)
    disponible = db.Column(db.Boolean, default=True)
    estado = db.Column(db.String(20), default="activo")


class Comprador(db.Model):
    __tablename__ = "compradores"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, unique=True)
    empresa = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    telefono = db.Column(db.String(20))
    correo = db.Column(db.String(150))
    ubicacion = db.Column(db.String(200))
    latitud = db.Column(db.Float)
    longitud = db.Column(db.Float)
    estado = db.Column(db.String(20), default="activo")

    precios = db.relationship("Precio", backref="comprador", lazy=True)


class Precio(db.Model):
    __tablename__ = "precios"

    id = db.Column(db.Integer, primary_key=True)
    comprador_id = db.Column(db.Integer, db.ForeignKey("compradores.id"), nullable=False)
    producto = db.Column(db.String(100), default="Fruto de palma de aceite")
    valor_moneda = db.Column(db.Numeric(12, 2), nullable=False)
    unidad = db.Column(db.String(50), default="Tonelada")
    fecha_publicacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    fuente = db.Column(db.String(100))
    estado = db.Column(db.String(20), default="activo")  # activo/inactivo (histórico)


class PuntoComercializacion(db.Model):
    __tablename__ = "puntos_comercializacion"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    ubicacion = db.Column(db.String(200))
    latitud = db.Column(db.Float)
    longitud = db.Column(db.Float)
    contacto = db.Column(db.String(100))
    estado = db.Column(db.String(20), default="activo")


class SolicitudTransporte(db.Model):
    __tablename__ = "solicitudes_transporte"

    id = db.Column(db.Integer, primary_key=True)
    palmicultor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    transportador_id = db.Column(db.Integer, db.ForeignKey("transportadores.id"))
    vehiculo_id = db.Column(db.Integer, db.ForeignKey("vehiculos.id"))
    finca_id = db.Column(db.Integer, db.ForeignKey("fincas.id"), nullable=False)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"))
    comprador_id = db.Column(db.Integer, db.ForeignKey("compradores.id"))
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_servicio = db.Column(db.Date)
    hora_servicio = db.Column(db.Time)
    cantidad_estimada = db.Column(db.Float)
    origen = db.Column(db.String(200))
    destino = db.Column(db.String(200))
    tarifa_sugerida = db.Column(db.Numeric(12, 2))
    tarifa_acordada = db.Column(db.Numeric(12, 2))
    observaciones = db.Column(db.Text)
    motivo_rechazo = db.Column(db.Text)
    fecha_aceptacion = db.Column(db.DateTime)  # dispara la revelación de ubicación exacta (RN06)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    estado = db.Column(db.String(20), default="Pendiente")
    # Pendiente | Aceptada | Rechazada | En preparación | En tránsito | Entregada | Cancelada


class Notificacion(db.Model):
    __tablename__ = "notificaciones"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    ciclo_cosecha_id = db.Column(db.Integer, db.ForeignKey("ciclos_cosecha.id"), nullable=True)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=True)
    tipo = db.Column(db.String(50))
    titulo = db.Column(db.String(150))
    mensaje = db.Column(db.Text)
    enlace = db.Column(db.String(50))  # nombre de pantalla destino en la app
    leida = db.Column(db.Boolean, default=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


class EstadoVia(db.Model):
    __tablename__ = "estados_vias"

    id = db.Column(db.Integer, primary_key=True)
    via = db.Column(db.String(150), nullable=False)
    municipio = db.Column(db.String(100), default="Tumaco")
    estado = db.Column(db.String(20), default="habilitada")
    # habilitada | precaucion | restringida | cerrada
    observaciones = db.Column(db.Text)
    actualizado_por = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    codigo = db.Column(db.String(6), nullable=False)
    expira_en = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, default=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship("Usuario", backref="reset_tokens")


class SmsUssdLog(db.Model):
    __tablename__ = "sms_ussd_logs"

    id = db.Column(db.Integer, primary_key=True)
    telefono = db.Column(db.String(20), nullable=False)
    canal = db.Column(db.String(10), default="sms")  # sms | ussd
    comando = db.Column(db.String(50))
    payload = db.Column(db.Text)
    respuesta = db.Column(db.Text)
    estado = db.Column(db.String(20), default="procesado")  # procesado | error
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Twilio (SMS real) ---
    direccion = db.Column(db.String(10), default="entrante")  # entrante | saliente
    proveedor = db.Column(db.String(10), default="mock")  # mock | twilio
    twilio_sid = db.Column(db.String(50), unique=True, nullable=True)
    estado_entrega = db.Column(db.String(20), nullable=True)
    # queued | sent | delivered | undelivered | failed (StatusCallback de Twilio)

    usuario = db.relationship("Usuario", backref="sms_logs")


class BalanceIndustrial(db.Model):
    __tablename__ = "balances_industriales"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    pronostico_id = db.Column(db.Integer, db.ForeignKey("pronosticos_produccion.id"), nullable=True)
    entrada_kg = db.Column(db.Float, nullable=False)
    desglose = db.Column(db.JSON)  # {humedad, tusas, fibras, aguas_impurezas, cuesco, palmiste, aceite_crudo}
    aceite_crudo_kg = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship("Usuario", backref="balances_industriales")
    pronostico = db.relationship("PronosticoProduccion", backref="balances_industriales")


class PublicacionMercado(db.Model):
    __tablename__ = "publicaciones_mercado"

    id = db.Column(db.Integer, primary_key=True)
    palmicultor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=True)
    cantidad_toneladas = db.Column(db.Float, nullable=False)
    # El precio lo fija siempre el comprador (ver Precio/Comprador), nunca el
    # palmicultor: su publicación solo anuncia cantidad disponible. El
    # palmicultor revisa los precios vigentes por comprador y decide a quién
    # vender.
    unidad = db.Column(db.String(50), default="Tonelada")
    municipio = db.Column(db.String(100), default="Tumaco")
    descripcion = db.Column(db.Text)
    estado = db.Column(db.String(20), default="activa")  # activa | vendida | cancelada
    fecha_publicacion = db.Column(db.DateTime, default=datetime.utcnow)


class UssdSesion(db.Model):
    """Sesión de un menú USSD en curso. Persistida en base de datos (no en
    memoria del proceso Flask) porque una sesión real puede llegar a
    cualquier instancia del backend entre una interacción y la siguiente.

    `contexto` guarda únicamente los datos mínimos que el usuario ya
    digitó dentro del flujo actual (ej. código de lote, cantidades) — se
    borra al terminar la sesión, nunca se usa como almacenamiento
    permanente."""

    __tablename__ = "ussd_sesiones"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    proveedor = db.Column(db.String(20), default="simulador")  # simulador | <proveedor real>
    telefono = db.Column(db.String(20), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    estado = db.Column(db.String(40), default="MENU_PRINCIPAL")  # paso/menú actual
    contexto = db.Column(db.JSON, default=dict)
    activa = db.Column(db.Boolean, default=True)
    resultado_final = db.Column(db.String(20), nullable=True)  # completada|cancelada|expirada|error

    # --- deduplicación / idempotencia frente a reintentos del proveedor ---
    ultimo_request_id = db.Column(db.String(100), nullable=True)
    ultima_entrada = db.Column(db.String(200), nullable=True)
    ultima_respuesta = db.Column(db.Text, nullable=True)
    ultimo_estado_previo = db.Column(db.String(40), nullable=True)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expira_en = db.Column(db.DateTime, nullable=False)

    usuario = db.relationship("Usuario", backref="ussd_sesiones")