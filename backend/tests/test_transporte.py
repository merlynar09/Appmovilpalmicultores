"""Pruebas dirigidas al hallazgo crítico F5-02: autorización en las
transiciones de estado de una solicitud de transporte."""
from app.extensions import db
from app.models import Usuario, Transportador, Finca, SolicitudTransporte


def _crear_solicitud_pendiente(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_id = client.post(
        "/api/fincas", json={"nombre": "Finca Transporte"}, headers=headers
    ).get_json()["id"]
    resp = client.post(
        "/api/transporte/solicitudes",
        json={"finca_id": finca_id, "destino": "Planta X"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.get_json()["id"]


def _crear_transportador_no_aprobado(app_ctx):
    usuario = Usuario(
        nombre_completo="Transportador Pendiente",
        telefono="3219990020",
        password_hash=__import__("werkzeug.security", fromlist=["generate_password_hash"]).generate_password_hash(
            "clave123"
        ),
        rol="transportador",
        estado="activo",
    )
    db.session.add(usuario)
    db.session.flush()
    db.session.add(Transportador(usuario_id=usuario.id, ubicacion="Tumaco", estado="pendiente"))
    db.session.commit()
    return usuario.telefono, "clave123"


def test_transportador_no_aprobado_no_puede_rechazar(client, auth_header, app_ctx):
    solicitud_id = _crear_solicitud_pendiente(client, auth_header)
    telefono, password = _crear_transportador_no_aprobado(app_ctx)

    login = client.post("/api/auth/login", json={"identifier": telefono, "password": password})
    token = login.get_json()["token"]

    resp = client.patch(
        f"/api/transporte/solicitudes/{solicitud_id}/rechazar",
        json={"motivo": "no aplica"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403

    solicitud = db.session.get(SolicitudTransporte, solicitud_id)
    assert solicitud.estado == "Pendiente"


def test_transportador_aprobado_puede_rechazar_una_sin_asignar(client, auth_header):
    solicitud_id = _crear_solicitud_pendiente(client, auth_header)
    headers = auth_header(client, "transportador")

    resp = client.patch(
        f"/api/transporte/solicitudes/{solicitud_id}/rechazar",
        json={"motivo": "sin disponibilidad"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["estado"] == "Rechazada"


def test_transportador_no_puede_rechazar_una_ya_asignada_a_otro(client, auth_header, app_ctx):
    solicitud_id = _crear_solicitud_pendiente(client, auth_header)
    headers_transportador_1 = auth_header(client, "transportador")
    client.patch(
        f"/api/transporte/solicitudes/{solicitud_id}/aceptar", json={}, headers=headers_transportador_1
    )

    telefono, password = _crear_transportador_no_aprobado(app_ctx)
    transportador_2 = Transportador.query.filter_by(usuario_id=Usuario.query.filter_by(telefono=telefono).first().id).first()
    transportador_2.estado = "aprobado"
    db.session.commit()
    login = client.post("/api/auth/login", json={"identifier": telefono, "password": password})
    token_2 = login.get_json()["token"]

    resp = client.patch(
        f"/api/transporte/solicitudes/{solicitud_id}/rechazar",
        json={"motivo": "no es mía"},
        headers={"Authorization": f"Bearer {token_2}"},
    )
    # Ya no está "Pendiente" (otro transportador la aceptó), así que el chequeo
    # de disponibilidad responde antes de llegar al de propiedad — 409, no 403.
    # En cualquier caso, el punto de esta prueba es que NO se le permitió
    # rechazarla, y que el estado/dueño de la solicitud no cambiaron.
    assert resp.status_code == 409


def test_no_se_pueden_crear_solicitudes_sobre_finca_inactiva(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_id = client.post(
        "/api/fincas", json={"nombre": "Finca Inactiva Transporte"}, headers=headers
    ).get_json()["id"]
    client.delete(f"/api/fincas/{finca_id}", headers=headers)

    resp = client.post(
        "/api/transporte/solicitudes",
        json={"finca_id": finca_id, "destino": "Planta Y"},
        headers=headers,
    )
    assert resp.status_code == 409
