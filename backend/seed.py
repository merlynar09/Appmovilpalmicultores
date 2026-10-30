"""Datos de prueba (seed) para Palma Viva.

Uso:
    python seed.py

Es idempotente: si el teléfono ya existe, reutiliza el registro en vez de
duplicarlo, así que se puede correr varias veces sin problema.

DEV-F2-11: inserta usuarios con contraseñas conocidas (admin123, palma123,
etc.) — por eso exige SEED_CONFIRM=yes en el entorno antes de tocar la base,
para que no se ejecute por accidente contra algo que no sea una base de
desarrollo/pruebas desechable.
"""
import os
import sys
from datetime import date, timedelta, datetime, timezone

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import (
    Usuario,
    Finca,
    Lote,
    CicloCosecha,
    RegistroProduccion,
    PronosticoProduccion,
    Transportador,
    Vehiculo,
    Comprador,
    Precio,
    PuntoComercializacion,
    SolicitudTransporte,
    PublicacionMercado,
    EstadoVia,
)

CREDENCIALES = []


def get_or_create_usuario(nombre, telefono, password, rol, correo=None):
    usuario = Usuario.query.filter_by(telefono=telefono).first()
    if usuario:
        return usuario
    usuario = Usuario(
        nombre_completo=nombre,
        telefono=telefono,
        correo=correo,
        password_hash=generate_password_hash(password),
        rol=rol,
        estado="activo",
    )
    db.session.add(usuario)
    db.session.flush()
    CREDENCIALES.append((rol, telefono, password))
    return usuario


def _confirmar_ambiente_seguro():
    if os.environ.get("SEED_CONFIRM", "").lower() == "yes":
        return
    print(
        "seed.py crea usuarios con contraseñas conocidas (admin123, palma123, "
        "compra123, transp123) — pensado SOLO para una base de desarrollo/pruebas.\n"
        "Para confirmar que esta base es desechable, vuelve a ejecutar con "
        "SEED_CONFIRM=yes, por ejemplo:\n"
        "  SEED_CONFIRM=yes python seed.py   (bash)\n"
        '  $env:SEED_CONFIRM="yes"; python seed.py   (PowerShell)'
    )
    sys.exit(1)


def run():
    _confirmar_ambiente_seguro()
    app = create_app()
    with app.app_context():
        # --- usuarios base -------------------------------------------------
        palmicultor = get_or_create_usuario(
            "Carlos Quiñonez", "3001234567", "palma123", "palmicultor", "carlos.palmicultor@example.com"
        )
        comprador_user = get_or_create_usuario(
            "Extractora del Pacífico S.A.S.", "3002345678", "compra123", "comprador", "compras@extractorapacifico.example.com"
        )
        transportador_user = get_or_create_usuario(
            "Jhon Caicedo", "3003456789", "transp123", "transportador", "jhon.transportador@example.com"
        )
        admin_user = get_or_create_usuario(
            "Administrador Palma Viva", "3000000000", "admin123", "administrador", "admin@palmaviva.example.com"
        )
        db.session.commit()

        # --- comprador -------------------------------------------------
        comprador = Comprador.query.filter_by(usuario_id=comprador_user.id).first()
        if not comprador:
            comprador = Comprador(
                usuario_id=comprador_user.id,
                empresa="Extractora del Pacífico S.A.S.",
                descripcion="Planta extractora de aceite de palma en Tumaco.",
                telefono=comprador_user.telefono,
                correo=comprador_user.correo,
                ubicacion="Zona industrial, Tumaco",
                latitud=1.7912,
                longitud=-78.7813,
                estado="activo",
            )
            db.session.add(comprador)
            db.session.flush()
        elif comprador.latitud is None or comprador.longitud is None:
            comprador.latitud = 1.7912
            comprador.longitud = -78.7813

        if not Precio.query.filter_by(comprador_id=comprador.id).first():
            db.session.add(
                Precio(
                    comprador_id=comprador.id,
                    producto="Tonelada de Aceite de Palma",
                    valor_moneda=4125000,
                    unidad="Tonelada",
                    fuente="Extractora del Pacífico",
                    estado="activo",
                )
            )

        if not PuntoComercializacion.query.first():
            db.session.add(
                PuntoComercializacion(
                    nombre="Extractora del Norte",
                    descripcion="Punto de compra y acopio de fruto de palma.",
                    ubicacion="Tumaco, Nariño",
                    contacto="3002345678",
                    estado="activo",
                )
            )

        # --- transportador -----------------------------------------------
        transportador = Transportador.query.filter_by(usuario_id=transportador_user.id).first()
        if not transportador:
            transportador = Transportador(
                usuario_id=transportador_user.id,
                ubicacion="Tumaco, Nariño",
                disponible=True,
                estado="aprobado",  # ya validado por el admin para poder probar el flujo completo
            )
            db.session.add(transportador)
            db.session.flush()
        else:
            transportador.estado = "aprobado"

        vehiculo = Vehiculo.query.filter_by(placa="TUM123").first()
        if not vehiculo:
            vehiculo = Vehiculo(
                transportador_id=transportador.id,
                placa="TUM123",
                tipo_vehiculo="Camión estacas",
                capacidad_toneladas=8,
                disponible=True,
                estado="activo",
            )
            db.session.add(vehiculo)
            db.session.flush()

        db.session.commit()

        # --- finca / lote --------------------------------------------------
        finca = Finca.query.filter_by(usuario_id=palmicultor.id).first()
        if not finca:
            finca = Finca(
                usuario_id=palmicultor.id,
                nombre="Finca La Esperanza",
                ubicacion="Vía Tumaco - Llorente, km 12",
                municipio="Tumaco",
                vereda="El Pital",
                coordenadas_lat=1.7986,
                coordenadas_long=-78.7896,
                area_hectareas=25,
                estado="activa",
            )
            db.session.add(finca)
            db.session.flush()

        lote = Lote.query.filter_by(finca_id=finca.id, codigo="Lote-A1").first()
        if not lote:
            lote = Lote(
                finca_id=finca.id,
                codigo="Lote-A1",
                nombre="Sector norte",
                bloque="A",
                sector="1",
                area_hectareas=8,
                anio_siembra=2016,
                numero_palmas=960,
                material_sembrado="Híbrido OxG",
                topografia="Plano",
                drenaje="Bueno",
                estado_sanitario="Sano",
                numero_lineas=32,
                estado="activo",
            )
            db.session.add(lote)
            db.session.flush()

        db.session.commit()

        # --- ciclo de cosecha -----------------------------------------------
        ciclo = CicloCosecha.query.filter_by(lote_id=lote.id).first()
        if not ciclo:
            fecha_ultima = date.today() - timedelta(days=8)
            ciclo = CicloCosecha(
                lote_id=lote.id,
                fecha_ultima_cosecha=fecha_ultima,
                fecha_inicio=fecha_ultima,
                duracion_dias=10,
                dias_anticipacion_alerta=3,
                proxima_fecha_estimada=fecha_ultima + timedelta(days=10),
                estado="Programado",
                observaciones="Palma adulta, ciclo estándar de 10 días.",
            )
            db.session.add(ciclo)
            db.session.flush()

        # --- registro de producción / censo ---------------------------------
        registro = RegistroProduccion.query.filter_by(lote_id=lote.id).first()
        if not registro:
            # Muestra ~4.7% de las 960 palmas del lote (RN04).
            registro = RegistroProduccion(
                lote_id=lote.id,
                fecha=date.today() - timedelta(days=1),
                palmas_evaluadas=45,
                palmas_improductivas=3,
                racimos_pequenos=20,
                racimos_medianos=35,
                racimos_maduros=35,
                racimos_totales=90,
                peso_promedio_racimo=16.5,
                fruto_suelto=4.2,
                observaciones="Censo mensual de muestreo.",
                fuente="app",
            )
            db.session.add(registro)
            db.session.flush()

        db.session.commit()

        # --- pronóstico (RN04) -----------------------------------------------
        pronostico = PronosticoProduccion.query.filter_by(lote_id=lote.id).first()
        if not pronostico:
            palmas_totales = lote.numero_palmas
            palmas_improductivas_muestra = registro.palmas_improductivas
            palmas_productivas_muestreadas = registro.palmas_evaluadas - palmas_improductivas_muestra
            palmas_productivas = palmas_totales - palmas_improductivas_muestra
            promedio_estructuras = registro.racimos_totales / palmas_productivas_muestreadas
            racimos_estimados = palmas_productivas * promedio_estructuras
            produccion_estimada_kg = racimos_estimados * registro.peso_promedio_racimo
            produccion_estimada_ton = produccion_estimada_kg / 1000

            distribucion = [
                ("Julio", 14), ("Agosto", 16), ("Septiembre", 20),
                ("Octubre", 25), ("Noviembre", 13), ("Diciembre", 12),
            ]
            distribucion_mensual = [
                {
                    "mes": mes,
                    "porcentaje": pct,
                    "produccion_kg": round(produccion_estimada_kg * pct / 100, 2),
                    "produccion_ton": round(produccion_estimada_ton * pct / 100, 3),
                }
                for mes, pct in distribucion
            ]

            pronostico = PronosticoProduccion(
                lote_id=lote.id,
                registro_produccion_id=registro.id,
                # naive-UTC a propósito: la columna no es timezone-aware y el
                # resto del proyecto usa datetimes naive consistentemente.
                fecha_calculo=datetime.now(timezone.utc).replace(tzinfo=None),
                palmas_totales=palmas_totales,
                palmas_improductivas_muestra=palmas_improductivas_muestra,
                palmas_productivas=palmas_productivas,
                palmas_productivas_muestreadas=palmas_productivas_muestreadas,
                promedio_estructuras=round(promedio_estructuras, 4),
                racimos_estimados=round(racimos_estimados, 2),
                peso_promedio=registro.peso_promedio_racimo,
                produccion_estimada_kg=round(produccion_estimada_kg, 2),
                produccion_estimada_ton=round(produccion_estimada_ton, 3),
                distribucion_mensual=distribucion_mensual,
                observaciones="Pronóstico inicial generado por el seed.",
            )
            db.session.add(pronostico)

        # --- publicación de mercado ------------------------------------------
        if not PublicacionMercado.query.filter_by(palmicultor_id=palmicultor.id).first():
            db.session.add(
                PublicacionMercado(
                    palmicultor_id=palmicultor.id,
                    lote_id=lote.id,
                    cantidad_toneladas=12,
                    unidad="Tonelada",
                    municipio=finca.municipio,
                    descripcion="Fruto fresco de palma africana, cosecha reciente.",
                    estado="activa",
                )
            )

        # --- solicitud de transporte -------------------------------------------
        if not SolicitudTransporte.query.filter_by(palmicultor_id=palmicultor.id).first():
            db.session.add(
                SolicitudTransporte(
                    palmicultor_id=palmicultor.id,
                    finca_id=finca.id,
                    lote_id=lote.id,
                    comprador_id=comprador.id,
                    cantidad_estimada=12,
                    origen=f"{finca.municipio}, {finca.vereda}",
                    destino="Extractora del Pacífico, Tumaco",
                    fecha_servicio=date.today() + timedelta(days=3),
                    tarifa_sugerida=350000,
                    observaciones="Transporte de cosecha reciente del Lote-A1.",
                    estado="Pendiente",
                )
            )

        # --- estado de vías --------------------------------------------------
        if not EstadoVia.query.first():
            db.session.add(
                EstadoVia(
                    via="Vía Tumaco - Llorente",
                    municipio="Tumaco",
                    estado="habilitada",
                    observaciones="Sin novedades.",
                    actualizado_por=admin_user.id,
                )
            )

        db.session.commit()
        print("Seed completado correctamente.\n")
        print("Credenciales de prueba:")
        print(f"{'ROL':<15}{'TELÉFONO':<15}{'CONTRASEÑA'}")
        filas = [
            ("palmicultor", "3001234567", "palma123"),
            ("comprador", "3002345678", "compra123"),
            ("transportador", "3003456789", "transp123"),
            ("administrador", "3000000000", "admin123"),
        ]
        for rol, tel, pw in filas:
            print(f"{rol:<15}{tel:<15}{pw}")


if __name__ == "__main__":
    run()
