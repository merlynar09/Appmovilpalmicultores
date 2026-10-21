# USSD en Palma Viva

Este documento explica cómo quedó implementado el menú USSD, qué es
simulación y qué es real, y qué falta para activar un proveedor de verdad
en Colombia.

## 1. Diferencia entre los tres canales del proyecto

| Canal | Dónde vive | Proveedor | Estado |
|---|---|---|---|
| SMS real | `app/routes/sms.py` + `app/services/twilio_sms.py` | Twilio | **Funcionando de verdad** (verificado con envío y recepción reales) |
| Comando SMS/USSD de una línea (mock) | `POST /api/sms/entrante` | Ninguno (simulado) | Como ya existía — intacto |
| **Menú USSD con sesión** | `app/services/ussd_engine.py` + `app/routes/ussd.py` | Ninguno contratado todavía | **Nuevo.** Motor completo y probado; falta solo el contrato con un proveedor/operador real |

Importante: **Twilio no ofrece USSD** (solo SMS, voz, WhatsApp, RCS). Es un
canal de telefonía completamente distinto (requiere interconexión directa
con la red del operador móvil), por eso el menú USSD es un sistema aparte,
nunca una extensión de la integración de Twilio.

## 2. Arquitectura

```
Proveedor USSD real          Simulador interno (app)
        │                              │
        ▼                              ▼
POST /ussd/webhook          POST /ussd/simular
(firma + formato                 (JSON, sin firma,
 del proveedor)                   pantalla de pruebas)
        │                              │
        └──────────────┬───────────────┘
                        ▼
         app/services/ussd_engine.py
         (máquina de estados, sesión en BD,
          reutiliza la lógica real de Palma Viva)
                        │
         ┌──────────────┼──────────────────────┐
         ▼              ▼                      ▼
   precios/compradores  _build_registro()   _procesar_transporte()
   /vías/avisos         (produccion.py)     (sms.py)
   (consultas directas)
```

El motor (`ussd_engine.py`) **no sabe nada de HTTP, firmas ni del formato
de ningún proveedor** — solo recibe `(teléfono, texto, session_id)` y
devuelve `(respuesta, continuar)`. Todo el conocimiento específico de un
proveedor vive en el adaptador (`routes/ussd.py`), así que conectar un
proveedor real el día de mañana es ajustar ese adaptador, no reescribir el
menú.

## 3. Menú implementado

```
Palma Viva
1 Precio de palma        -> precios vigentes por comprador (Precio/Comprador)
2 Compradores             -> lista de compradores activos
3 Mi transporte           -> mis solicitudes de transporte y su estado
4 Estado de vias          -> EstadoVia, lectura pública
5 Avisos                  -> mis notificaciones (reutiliza _generar_alertas_cosecha)
6 Registrar produccion    -> censo paso a paso + confirmación (reutiliza _build_registro)
7 Solicitar transporte    -> solicitud paso a paso + confirmación (reutiliza _procesar_transporte)
8 Ayuda                   -> texto de ayuda
0 Salir                   -> termina la sesión
```

Todas las opciones ejecutan una función real del backend — ninguna muestra
datos inventados. En submenús de solo lectura, `0` vuelve al menú
principal; en los flujos de captura de datos (6 y 7), `0` cancela en
cualquier paso.

### Ejemplo de sesión completa (registrar producción)
```
> (marca el código, sesión inicia)
< Palma Viva / 1 Precio... / 6 Registrar produccion / ...
> 6
< Codigo de tu lote:
> Lote-A1
< Palmas evaluadas en la muestra:
> 40
< Palmas improductivas en la muestra:
> 2
< Racimos contados en la muestra:
> 80
< Peso promedio del racimo en kg:
> 16.5
< Lote Lote-A1: 40 palmas, 2 improd, 80 racimos, 16.5kg/racimo.
  1 Confirmar  2 Cancelar
> 1
< Censo guardado. ID #123. Gracias.
```

## 4. Sesión: persistencia, expiración, concurrencia, duplicados

Tabla `ussd_sesiones` (migración `32133803a73b`, no toca tablas existentes):

| Campo | Para qué |
|---|---|
| `session_id` | id de sesión del proveedor (único) |
| `telefono`, `usuario_id` | quién es — identificado por el teléfono que entrega el proveedor, nunca por un dato que el propio texto del menú pueda falsificar |
| `estado` | paso/menú actual (ej. `PRODUCCION_PALMAS_EVAL`) |
| `contexto` (JSON) | datos ya capturados en el flujo en curso (ej. `lote_id`, cantidades) — se descarta al terminar, nunca se usa como almacenamiento permanente |
| `activa`, `resultado_final` | `completada` \| `cancelada` \| `expirada` \| `error` |
| `ultimo_request_id`, `ultima_entrada`, `ultima_respuesta`, `ultimo_estado_previo` | deduplicación de reintentos del proveedor |
| `expira_en` | ventana deslizante: se extiende en cada interacción (por defecto 180s desde la última, configurable con `USSD_SESSION_TTL_SEGUNDOS`) |

- **Nunca en memoria del proceso**: todo vive en PostgreSQL, así que da igual
  a qué instancia del backend llegue la siguiente interacción.
- **Concurrencia**: cada solicitud bloquea la fila de sesión con
  `SELECT ... FOR UPDATE` (`with_for_update()`), así que dos peticiones
  simultáneas sobre la misma sesión se serializan en vez de corromperla.
- **Expirada**: si `ahora > expira_en`, la sesión se cierra con un mensaje
  claro y no se procesa la entrada como si fuera válida.
- **Duplicados**: si el proveedor manda un `requestId` estable, se usa
  directamente. Si no, se detecta un reintento cuando la entrada es
  idéntica a la anterior **y** esa interacción anterior fue una
  confirmación (los únicos pasos con efectos reales en la base de datos,
  ej. crear un censo). Para navegación normal no se aplica ese resguardo:
  repetir la misma opción de un menú de solo lectura se reprocesa
  normalmente, para no arriesgarse a mostrar datos desactualizados.

## 5. Autenticación e identidad

- El simulador (`/ussd/simular`) no exige firma — es una herramienta de
  pruebas interna, igual que el simulador SMS que ya existía.
- El webhook real (`/ussd/webhook`) exige la cabecera `X-Ussd-Secret`
  igual a `USSD_PROVIDER_SHARED_SECRET`. **Si esa variable no está
  configurada, el webhook rechaza TODO (falla cerrado)** — nunca queda
  "activo por accidente" sin que alguien haya puesto una credencial real.
- El usuario se identifica por el teléfono que entrega la sesión del
  proveedor (nunca un dato arbitrario del texto del menú). Se exige que la
  cuenta exista, esté `activa` y tenga rol `palmicultor` — igual que el
  canal SMS. Cada consulta/operación está filtrada por `usuario_id`: nunca
  se puede ver ni modificar información de otra cuenta.
- No se exige JWT de la app (el caso de uso es justamente operar sin sesión
  abierta en el celular).

## 6. Variables de entorno nuevas

Agregar a `backend/.env` (nunca a `.env.example` con valores reales):

```
USSD_PROVIDER_SHARED_SECRET=   # secreto compartido con el proveedor real; sin esto, /ussd/webhook rechaza todo
USSD_PROVIDER_NOMBRE=          # opcional, solo para identificar el proveedor en los logs (ej. "infobip")
USSD_SESSION_TTL_SEGUNDOS=180  # opcional, duración de la ventana de sesión (por defecto 180)
```

## 7. Endpoints

| Método | Ruta | Para qué | Auth |
|---|---|---|---|
| POST | `/api/ussd/simular` | Simulador interno (pantalla de pruebas) | Ninguna |
| POST | `/api/ussd/webhook` | Proveedor USSD real | `X-Ussd-Secret` |
| POST | `/api/sms/entrante` | Comando de una línea (mock SMS/USSD, sin cambios) | Ninguna |

### Formato del webhook real (`/api/ussd/webhook`)

Formato **genérico**, basado en los campos que comparten la mayoría de
gateways USSD documentados (sessionId, MSISDN, texto digitado, bandera de
continuar sesión):

```json
// Entrada esperada (JSON o form-urlencoded)
{
  "sessionId": "abc123",
  "phoneNumber": "+573001234567",
  "text": "6",
  "requestId": "opcional, para deduplicar reintentos"
}
```
```json
// Respuesta
{
  "sessionId": "abc123",
  "text": "Codigo de tu lote:",
  "continueSession": true
}
```

Si el proveedor que finalmente se contrate usa nombres de campo distintos
(ej. `msisdn` en vez de `phoneNumber`, o acumula el texto completo tipo
`"1*6"` en vez de solo el último dígito), el adaptador en
`app/routes/ussd.py` ya contempla variantes comunes y solo necesitaría un
ajuste puntual, no un rediseño — el motor de menús no cambia.

## 8. Qué proveedor usar en Colombia (investigación realizada)

**Verificado:**
- **Twilio no tiene producto de USSD** (confirmado: solo SMS, voz, WhatsApp,
  RCS y Flex; un blog de Twilio describe integrar USSD de un tercero *dentro*
  de Flex para un caso puntual, no es un producto propio).
- **Clickatell** documenta USSD solo para **Sudáfrica y Nigeria** — Colombia
  no está cubierto (fuente: su propio centro de ayuda).
- La **CRC (Comisión de Regulación de Comunicaciones)**, el regulador
  colombiano, confirma que el **código corto** es el mecanismo oficial de
  numeración tanto para SMS **como para USSD** en Colombia (Resolución CRC
  5050 de 2016, art. 6.4.2.1.1), y exige registrarse como "Proveedor de
  Contenidos y Aplicaciones e Integrador Tecnológico" ante la CRC.
- Claro tiene un producto comercial de mensajería empresarial con código
  corto asignado (ej. "Mensajería Empresarial Claro"), contratado
  directamente con Claro Empresas, con cargo fijo mensual + cobro por
  mensaje — este es el tipo de vía que normalmente también cubre USSD bajo
  el mismo marco regulatorio de código corto.

**No verificado / requiere contacto directo:**
- Infobip y Sinch tienen presencia comercial fuerte en Colombia (oficinas,
  SMS 2-way), pero no se encontró documentación pública que confirme
  cobertura **USSD** específicamente para Colombia — habría que preguntarle
  directamente a su equipo de ventas.
- No existe (hasta donde se pudo verificar) un proveedor internacional de
  USSD con auto-registro por API como Twilio para SMS — el acceso a USSD en
  Colombia es un proceso comercial/regulatorio, no un signup self-service.

### Pasos externos para activar USSD real (no se pueden completar desde aquí)
1. Elegir y contactar una vía: (a) directamente Claro Empresas / Movistar
   Empresas / Tigo Empresas, o (b) un integrador tecnológico ya registrado
   ante la CRC que tenga interconexión con esos operadores.
2. Registrar el servicio ante la CRC como Proveedor de Contenidos y
   Aplicaciones (si se contrata directo con el operador, normalmente el
   operador o el integrador gestiona este trámite).
3. Obtener el código corto asignado y la URL/formato exacto de webhook que
   use ese proveedor (puede diferir ligeramente del formato genérico de
   este documento — ajustar `app/routes/ussd.py` según corresponda).
4. Configurar `USSD_PROVIDER_SHARED_SECRET` (o el mecanismo de autenticación
   que exija ese proveedor específico — firma HMAC, IP allowlist, Basic
   Auth, etc.) y `USSD_PROVIDER_NOMBRE`.
5. Apuntar la URL del webhook del proveedor a
   `https://TU_DOMINIO_PUBLICO/api/ussd/webhook`.
6. Hacer una prueba real marcando el código corto desde un celular en la
   red del operador contratado.

**No se afirma que el USSD real esté funcionando** — solo está confirmado
que el motor de menús, la sesión, la seguridad y las pruebas automatizadas
funcionan correctamente contra el simulador. La activación real depende
enteramente de los pasos externos de arriba.

## 9. Pruebas automatizadas

`backend/tests/test_ussd.py` (pytest, sin red, sin proveedor real):
inicio de sesión, menú principal, navegación, volver, salir, opción
inválida, sesión expirada, usuario no registrado/suspendido/rol no
permitido, las 5 consultas de solo lectura, los 2 flujos completos con
confirmación (producción y transporte), cancelación, deduplicación de
reintentos (con y sin `requestId`), autenticación del webhook real
(sin secreto / secreto incorrecto / secreto correcto), lote inexistente,
y regresión del simulador SMS/USSD existente.

```bash
cd backend
../.venv/Scripts/python.exe -m pytest tests/ -v
```

## 10. Limitaciones del simulador

La pantalla "Simulador SMS/USSD -> Sesión USSD" de la app ejecuta el
**mismo motor** que usaría un proveedor real, pero:
- No simula los límites de tiempo de respuesta real de una red USSD (los
  proveedores suelen exigir responder en 1-10 segundos).
- No simula la codificación/límite de caracteres por pantalla de un
  teléfono básico real (se probó con mensajes cortos a propósito, pero no
  hay una validación automática de longitud máxima).
- No reemplaza una prueba real desde un teléfono en la red de un operador.
