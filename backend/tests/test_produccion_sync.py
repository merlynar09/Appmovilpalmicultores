"""F5-01: la sincronización de censos offline debe ser idempotente — reenviar
el mismo `_local_id` no debe duplicar el registro."""
from app.models import RegistroProduccion


def _lote_del_palmicultor(client, auth_header):
    headers = auth_header(client, "palmicultor")
    finca_id = client.post(
        "/api/fincas", json={"nombre": "Finca Censo"}, headers=headers
    ).get_json()["id"]
    lote_id = client.post(
        f"/api/fincas/{finca_id}/lotes", json={"codigo": "CENSO-1"}, headers=headers
    ).get_json()["id"]
    return lote_id


def test_mismo_local_id_no_duplica(client, auth_header, app_ctx):
    headers = auth_header(client, "palmicultor")
    lote_id = _lote_del_palmicultor(client, auth_header)

    item = {
        "_local_id": "abc-123",
        "lote_id": lote_id,
        "palmas_evaluadas": 40,
        "palmas_improductivas": 2,
        "racimos_totales": 80,
    }

    primer_envio = client.post("/api/produccion/sync", json={"items": [item]}, headers=headers)
    segundo_envio = client.post("/api/produccion/sync", json={"items": [item]}, headers=headers)

    assert primer_envio.status_code == 200
    assert segundo_envio.status_code == 200
    assert primer_envio.get_json()["resultados"][0]["ok"] is True
    assert segundo_envio.get_json()["resultados"][0]["ok"] is True
    assert primer_envio.get_json()["resultados"][0]["id"] == segundo_envio.get_json()["resultados"][0]["id"]

    registros = RegistroProduccion.query.filter_by(lote_id=lote_id).all()
    assert len(registros) == 1


def test_sin_local_id_cada_envio_crea_uno_nuevo(client, auth_header, app_ctx):
    headers = auth_header(client, "palmicultor")
    lote_id = _lote_del_palmicultor(client, auth_header)

    item_sin_local_id = {
        "lote_id": lote_id,
        "palmas_evaluadas": 40,
        "palmas_improductivas": 2,
        "racimos_totales": 80,
    }

    client.post("/api/produccion/sync", json={"items": [item_sin_local_id]}, headers=headers)
    client.post("/api/produccion/sync", json={"items": [item_sin_local_id]}, headers=headers)

    registros = RegistroProduccion.query.filter_by(lote_id=lote_id).all()
    assert len(registros) == 2


def test_no_se_puede_registrar_censo_en_lote_inactivo(client, auth_header):
    headers = auth_header(client, "palmicultor")
    lote_id = _lote_del_palmicultor(client, auth_header)
    client.delete(f"/api/lotes/{lote_id}", headers=headers)

    resp = client.post(
        "/api/produccion",
        json={"lote_id": lote_id, "palmas_evaluadas": 10, "racimos_totales": 20},
        headers=headers,
    )
    assert resp.status_code == 400
