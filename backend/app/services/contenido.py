"""Contenido de SMS/USSD editable por el administrador (CU17).

Diseño deliberadamente defensivo: `obtener_contenido` NUNCA debe poder
romper el flujo real de SMS/USSD. Si no hay override guardado, o si la
consulta a la base de datos falla por cualquier motivo, siempre devuelve el
texto por defecto que ya existía hardcodeado en el código.
"""

import logging

from app.models import ContenidoMensaje

logger = logging.getLogger("palma_viva.contenido")

# Registro fijo de claves gestionables desde el panel admin, con su canal y
# el texto por defecto actual (el mismo que ya estaba hardcodeado). Sirve
# para que el endpoint admin pueda listarlas aunque todavía no tengan override.
CLAVES_CONTENIDO = {
    "ussd_menu_principal": "ussd",
    "ussd_ayuda": "ussd",
    "sms_ayuda": "sms",
}


def obtener_contenido(clave, texto_por_defecto):
    try:
        fila = ContenidoMensaje.query.filter_by(clave=clave).first()
        if fila and fila.texto:
            return fila.texto
    except Exception as e:
        logger.warning("No se pudo leer contenido editable '%s', se usa el texto por defecto: %s", clave, e)
    return texto_por_defecto
