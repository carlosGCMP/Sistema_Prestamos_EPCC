"""Comprueba permisos, consulta global y carga CSV sin escrituras parciales."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("accion", ["preview", "import"])
def test_csv_rechaza_caracter_nulo(
    client: TestClient, flujo_basico: dict[str, str], accion: str
) -> None:
    respuesta = client.post(
        f"/reports/catalog/{accion}",
        headers={"Authorization": flujo_basico["admin"]},
        json={"contenido": "tipo,categoria,descripcion\nAudio,Parlantes,Texto\x00\n"},
    )
    assert respuesta.status_code == 422
    assert "carácter nulo" in respuesta.json()["detail"]


def test_reportes_requieren_sesion(client: TestClient) -> None:
    assert client.get("/reports/summary").status_code == 401
    assert client.post("/reports/catalog/import", json={"contenido": "x"}).status_code == 401


def test_resumen_e_importacion(client: TestClient, flujo_basico: dict[str, str]) -> None:
    estudiante = {"Authorization": flujo_basico["estudiante"]}
    assert client.get("/reports/summary", headers=estudiante).status_code == 403
    assert (
        client.post(
            "/reports/catalog/import", headers=estudiante, json={"contenido": "x"}
        ).status_code
        == 403
    )
    headers = {"Authorization": flujo_basico["admin"]}
    antes = client.get("/reports/summary", headers=headers)
    assert antes.status_code == 200, antes.text
    contenido = "tipo,categoria,descripcion\nAudiovisual,Proyectores,Para exposición\n"
    vista = client.post("/reports/catalog/preview", headers=headers, json={"contenido": contenido})
    assert vista.status_code == 200, vista.text
    assert client.get("/reports/summary", headers=headers).json()["tipos"] == antes.json()["tipos"]
    guardado = client.post(
        "/reports/catalog/import", headers=headers, json={"contenido": contenido}
    )
    assert guardado.status_code == 201, guardado.text
    assert guardado.json() == {"tipos_creados": 1, "categorias_creadas": 1}
    despues = client.get("/reports/summary", headers=headers).json()
    assert despues["tipos"] == antes.json()["tipos"] + 1
    assert despues["categorias"] == antes.json()["categorias"] + 1
    duplicado = client.post(
        "/reports/catalog/import", headers=headers, json={"contenido": contenido}
    )
    assert duplicado.status_code == 409


def test_csv_invalido_no_guarda_parcialmente(
    client: TestClient, flujo_basico: dict[str, str]
) -> None:
    headers = {"Authorization": flujo_basico["admin"]}
    antes = client.get("/reports/summary", headers=headers).json()
    contenido = "tipo,categoria,descripcion\nAudio,Parlantes,Nuevo\nX,Invalida,Error\n"
    respuesta = client.post(
        "/reports/catalog/import", headers=headers, json={"contenido": contenido}
    )
    assert respuesta.status_code == 422
    despues = client.get("/reports/summary", headers=headers).json()
    assert despues["tipos"] == antes["tipos"]
    assert despues["categorias"] == antes["categorias"]
