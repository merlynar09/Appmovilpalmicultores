"""DEV-F3-07: cobertura mínima de reportes administrativos (CU16) y
contenido SMS/USSD editable (CU17) — antes sin pruebas automatizadas."""


def test_reportes_generales_estructura(client, auth_header):
    resp = client.get("/api/admin/reportes", headers=auth_header(client, "administrador"))
    assert resp.status_code == 200
    data = resp.get_json()
    for clave in ("usuarios", "produccion", "mercado", "logistica", "compradores_activos"):
        assert clave in data
    assert "por_rol" in data["usuarios"]


def test_reportes_generales_no_expone_datos_personales(client, auth_header):
    data = client.get("/api/admin/reportes", headers=auth_header(client, "administrador")).get_json()
    texto = str(data)
    # Solo agregados — nunca nombres, teléfonos ni ubicaciones exactas.
    assert "telefono" not in texto
    assert "nombre_completo" not in texto


def test_no_admin_no_accede_a_reportes(client, auth_header):
    resp = client.get("/api/admin/reportes", headers=auth_header(client, "palmicultor"))
    assert resp.status_code == 403


def test_contenido_sms_ussd_por_defecto(client, auth_header):
    resp = client.get("/api/admin/contenido-sms-ussd", headers=auth_header(client, "administrador"))
    assert resp.status_code == 200
    claves = {c["clave"] for c in resp.get_json()}
    assert "sms_ayuda" in claves
    sms_ayuda = next(c for c in resp.get_json() if c["clave"] == "sms_ayuda")
    assert sms_ayuda["personalizado"] is False


def test_editar_y_restaurar_contenido_sms_ussd(client, auth_header):
    headers = auth_header(client, "administrador")
    editado = client.put(
        "/api/admin/contenido-sms-ussd/sms_ayuda",
        json={"texto": "Texto de ayuda personalizado por prueba"},
        headers=headers,
    )
    assert editado.status_code == 200
    assert editado.get_json()["personalizado"] is True

    listado = client.get("/api/admin/contenido-sms-ussd", headers=headers).get_json()
    sms_ayuda = next(c for c in listado if c["clave"] == "sms_ayuda")
    assert sms_ayuda["personalizado"] is True
    assert sms_ayuda["texto"] == "Texto de ayuda personalizado por prueba"

    restaurado = client.delete("/api/admin/contenido-sms-ussd/sms_ayuda", headers=headers)
    assert restaurado.status_code == 200
    assert restaurado.get_json()["personalizado"] is False


def test_editar_contenido_texto_vacio_rechazado(client, auth_header):
    resp = client.put(
        "/api/admin/contenido-sms-ussd/sms_ayuda", json={"texto": ""}, headers=auth_header(client, "administrador")
    )
    assert resp.status_code == 400


def test_editar_contenido_clave_invalida_rechazada(client, auth_header):
    resp = client.put(
        "/api/admin/contenido-sms-ussd/clave_inexistente",
        json={"texto": "algo"},
        headers=auth_header(client, "administrador"),
    )
    assert resp.status_code == 400


def test_no_admin_no_puede_editar_contenido(client, auth_header):
    resp = client.put(
        "/api/admin/contenido-sms-ussd/sms_ayuda",
        json={"texto": "intento no autorizado"},
        headers=auth_header(client, "palmicultor"),
    )
    assert resp.status_code == 403
