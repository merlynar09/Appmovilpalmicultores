# Palma Viva

App móvil para palmicultores de Tumaco, Nariño — React Native (Expo) + Flask + PostgreSQL.
Prototipo funcional con los 4 roles (palmicultor, comprador, transportador, administrador),
SMS real (Twilio) y un motor de menú USSD con sesión (sin proveedor de telecomunicaciones
real conectado todavía — ver sección [SMS y USSD](#sms-y-ussd)).

## 1. Requisitos

- **Node.js 22** (probado con 22.18) y npm.
- **Python 3.11 o 3.12.** Python 3.13 falla al instalar `psycopg2-binary==2.9.9` — no lo uses
  todavía para este proyecto.
- **PostgreSQL** corriendo localmente.
- **Android Studio + Android SDK** — solo si vas a compilar la app nativamente
  (`npx expo run:android`). Para probar con **Expo Go** (la forma recomendada y con la que
  se prueba todo este proyecto) no hace falta nada de Android Studio, solo instalar la app
  **Expo Go** en un celular Android o iOS.

## 2. Backend (Flask + PostgreSQL)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux
```

Edita `backend/.env` y ajusta al menos `DATABASE_URL` con tu usuario/clave reales de
PostgreSQL. Variables disponibles (todas documentadas con comentarios en
[`backend/.env.example`](backend/.env.example)):

| Variable | Obligatoria | Para qué |
|---|---|---|
| `FLASK_ENV` | No (default `development`) | Fuera de `development`, `SECRET_KEY`/`JWT_SECRET_KEY`/`DATABASE_URL` son obligatorias — el backend no arranca con un secreto por defecto conocido. |
| `SECRET_KEY`, `JWT_SECRET_KEY` | Sí fuera de dev | Claves de Flask y de firma de JWT. |
| `DATABASE_URL` | Sí fuera de dev | Conexión a PostgreSQL (se normaliza internamente a `postgresql+psycopg2://`). |
| `CORS_ORIGINS` | Sí fuera de dev | Orígenes permitidos, separados por coma. En desarrollo, vacío = todo permitido; fuera de desarrollo es obligatoria (DEV-F4-06) — el backend no arranca sin ella. |
| `SMS_USSD_SIMULATOR_ENABLED` | No (default `true`) | Apaga `/api/sms/entrante` y `/api/ussd/simular` (los simuladores públicos) si los pones en `false`. |
| `SEED_CONFIRM` | Solo para correr `seed.py` | Debe ser `yes` — evita que el seed (contraseñas conocidas) corra por accidente en una base que no sea desechable. |
| `TWILIO_*` | Solo para SMS real | Ver la sección [SMS y USSD](#sms-y-ussd). |
| `USSD_PROVIDER_*` | Solo para USSD real | Ídem. |

Crea la base de datos (ajusta usuario/clave si los tuyos son distintos):

```bash
psql -U postgres -c "CREATE DATABASE palma_viva;"
```

Aplica las migraciones **ya existentes** en el repositorio (no vuelvas a correr
`flask db init` ni `flask db migrate` — esas ya se hicieron antes y sus resultados están
versionados en `backend/migrations/versions/`; repetirlas sobre un clon existente puede
generar un historial duplicado o inconsistente):

```bash
set FLASK_APP=run.py        # Windows (PowerShell: $env:FLASK_APP="run.py")
# export FLASK_APP=run.py   # macOS/Linux

flask db upgrade
```

Carga datos de prueba para los 4 roles (opcional pero muy recomendado):

```bash
SEED_CONFIRM=yes python seed.py        # bash
# $env:SEED_CONFIRM="yes"; python seed.py   (PowerShell)
```

Imprime las credenciales de las 4 cuentas de prueba al final. Es idempotente — se puede
correr varias veces sin duplicar datos.

Levanta el servidor (déjalo corriendo en esta terminal):

```bash
python run.py
```

Debe quedar escuchando en `0.0.0.0:5000` y `GET http://localhost:5000/api/health` debe
responder `{"status": "ok"}`.

## 3. Frontend (Expo)

```bash
npm ci
```

Usa `npm ci` (no `npm install`) para una instalación reproducible exacta desde
`package-lock.json`.

Copia `.env.example` a `.env` en la raíz del proyecto y define `EXPO_PUBLIC_API_URL` con la
URL de tu backend — hay 3 escenarios típicos documentados con ejemplos en
[`.env.example`](.env.example) (emulador, dispositivo físico en tu misma WiFi, o túnel). Si
no defines nada, cae a `http://10.0.2.2:5000/api` (solo funciona en el emulador de Android
Studio) y lo avisa por consola.

### 3.1 Probar con Expo Go (recomendado)

```bash
npm start
```

Escanea el código QR con la app **Expo Go** en tu celular (botón "Scan QR code" dentro de la
app, no la cámara del sistema). Si el celular está en otra red distinta a tu computador, usa
`npx expo start --tunnel` en su lugar (necesita haber iniciado sesión una vez con
`npx expo login`).

Esta es la forma en que se probó y evaluó todo este proyecto durante su desarrollo — no
requiere Android Studio, SDK, Gradle ni compilar nada nativo.

### 3.2 Producir un APK real

**Vía recomendada y verificada: EAS Build (compilación en la nube de Expo).** No depende del
toolchain nativo local (Android Studio/SDK/Gradle/JDK) ni de la RAM de la máquina de desarrollo:

```bash
npx eas-cli build --platform android --profile preview
```

Requiere una cuenta Expo (`npx eas-cli login`) y, la primera vez, `npx eas-cli init`. El perfil
`preview` (`eas.json`) genera un `.apk` instalable directamente (no un `.aab`). La URL del
backend para ese build se inyecta por variable de entorno EAS
(`npx eas-cli env:set --environment preview --name EXPO_PUBLIC_API_URL --value https://tu-backend...`),
no por un `.env` local — el archivo `.env` está en `.gitignore` y no viaja en el paquete que se
sube a EAS.

**Build nativo local (`npx expo run:android`): no reproducible en esta máquina de desarrollo —
limitación de hardware, no de código.** Se intentó corrigiendo el JDK del PATH y regenerando
`android/` con `npx expo prebuild --clean`, pero el proceso de Gradle/CMake para
`react-native-gesture-handler` requiere más memoria que la disponible (la máquina de desarrollo
tiene 6 GB de RAM; Gradle + un JDK moderno + CMake necesitan considerablemente más). Si tu
máquina tiene recursos suficientes, el camino es:

```bash
npx expo prebuild --platform android --clean
npx expo run:android
```

Con Android Studio + SDK, un emulador (AVD) o dispositivo conectado, y un **JDK 17 o superior**
(en Windows, usa el JBR de Android Studio: típicamente
`C:\Program Files\Android\Android Studio\jbr`, asegurándote de que sea el `java` que resuelve tu
PATH al compilar).

**Nota (Windows):** si tu ruta del proyecto tiene caracteres no-ASCII (tildes, ñ, etc.), Gradle
puede fallar al interpretar esa ruta (`DEV-F2-12`) — usa una ruta solo con caracteres ASCII. Esto
es una limitación conocida de Gradle en Windows, no algo que este proyecto pueda corregir desde
su propio código.

**`npx expo-doctor` (DEV-F2-01):** 19/20 checks — el único pendiente es un aviso informativo (no
un error) porque el proyecto tiene `android/` versionado junto a configuración nativa en
`app.json`; no se toca porque EAS Build ya usa ese flujo para producir el APK real. **Nota
(Windows + OneDrive):** si corres `npx expo export` o `npx expo start` desde una carpeta
sincronizada por OneDrive y Metro falla con
`EINVAL: invalid argument, readlink '...@expo/ws-tunnel/package.json'`, es un problema conocido
de Windows/OneDrive con el crawler de archivos de Metro sobre un archivo normal (no un symlink) —
no es un error del código del proyecto. Se resuelve típicamente reinstalando
(`rm -rf node_modules && npm ci`) o pausando la sincronización de OneDrive durante el desarrollo.

## 4. Pruebas automatizadas

```bash
cd backend
pytest --cov=app --cov-report=term-missing
```

Cada prueba corre contra una base Postgres local **dedicada y desechable** (`palma_viva_test`,
nunca `palma_viva` ni Supabase), que se reconstruye desde cero antes de cada prueba — por eso
cualquiera se puede ejecutar sola o en cualquier orden. Cubre autenticación (registro/login/JWT,
revocación de sesión al suspender o cambiar contraseña, rate limiting, recuperación de
contraseña), autorización por rol y propiedad horizontal, los CRUD principales (fincas, lotes,
compradores, puntos de comercialización), transporte (autorización de aceptar/rechazar),
producción (idempotencia de sincronización offline), mercado (interés de compra, distancia) y el
módulo SMS/USSD completo (webhook de Twilio, firma, deduplicación, motor de sesión USSD).

El pipeline de CI (`.github/workflows/tests.yml`) corre esta misma suite, con un Postgres de
servicio, en cada push/PR a `main`, junto con el lint y las pruebas del frontend.

Frontend:

```bash
npm run lint
npm test
```

Cubre el lint del proyecto completo y la lógica de la cola offline (`authService.js`,
`produccionService.js`): un error de red real se encola para reintentar, un error del servidor
(ej. dato inválido, duplicado) se muestra tal cual y no se encola.

## 5. SMS y USSD

El acceso sin datos móviles tiene dos canales, documentados por separado:

- **SMS**: real, mediante Twilio — envío y recepción verificados contra un número real, con
  firma validada en el webhook entrante. Requiere configurar `TWILIO_*` en `backend/.env`.
- **USSD**: el motor de sesión (máquina de estados persistida en base de datos, navegación de
  menú, expiración) es real y está probado — pero **no hay ningún proveedor de
  telecomunicaciones conectado todavía** para recibirlo desde un teléfono real por la red
  del operador. Se prueba contra un simulador interno (pantalla "Simulador SMS/USSD" → pestaña
  "Sesión USSD" en la app). Ver [`backend/docs/USSD.md`](backend/docs/USSD.md) para la
  arquitectura completa y qué falta para contratar un proveedor real en Colombia.

## 6. Vulnerabilidades conocidas (npm audit)

Tras `npm audit fix` (sin `--force`) y `npx expo install --fix` quedan **24 vulnerabilidades
moderadas, 0 altas/críticas** (DEV-F2-05 — verificado corriendo `npm audit` de nuevo después de
alinear todas las versiones con lo que pide el SDK 58, no es un conteo desactualizado):

- `expo`, `@expo/fingerprint`, `glob`, `minimatch`: el único arreglo que ofrece `npm audit fix`
  instala `expo@52.0.49`, una regresión mayor desde el SDK 58 actual.
- La mayoría (`jest`, `@jest/core`, `@jest/reporters`, `@jest/transform`, `babel-plugin-istanbul`,
  `test-exclude`, etc.): el arreglo que ofrece `npm audit fix` instala `jest@29.7.0`, que
  desalinearía de nuevo el proyecto de lo que `jest-expo@~58.0.0` (el preset de pruebas del SDK
  58) espera — el mismo tipo de disyuntiva que con Expo, así que se mantiene la versión alineada
  con el SDK en vez de perseguir el número de `npm audit`.
- `uuid` (vía `@expo/ngrok`, usado solo para `expo start --tunnel`): sin fix disponible todavía
  en origen.

Ninguna corre dentro de la app instalada en un teléfono — son herramientas de build/CLI/pruebas
de Node que solo se usan en la máquina de desarrollo. Forzar cualquiera de estos arreglos
(`--force`) degradaría Expo o el runner de pruebas a versiones incompatibles con el resto del
proyecto — riesgo aceptado conscientemente en vez de esa regresión.

## 7. Seguridad (segunda auditoría — Fase 4)

- **El registro público solo puede crear cuentas palmicultor, comprador o transportador.**
  Una cuenta administrador se crea exclusivamente desde `seed.py` (la primera) o desde
  `POST /api/admin/usuarios`, que exige estar ya autenticado como administrador.
- **Las sesiones se revocan de inmediato**, no solo al expirar el JWT (7 días): suspender una
  cuenta, cambiar su contraseña, o cerrar sesión (`POST /api/auth/logout`, ya invocado por el
  frontend al cerrar sesión) invalida en el siguiente request cualquier token emitido antes de
  ese momento (columna `token_version`). Antes, "cerrar sesión" solo borraba el token en el
  dispositivo — el mismo token seguía siendo válido contra el backend hasta expirar.
- **Recuperación de contraseña:** el código de 6 dígitos se guarda con hash (nunca en claro), y
  nunca viaja en la respuesta HTTP fuera de `FLASK_ENV=development`. Pedir un código nuevo
  invalida los anteriores sin usar.
- **Rate limiting** (`Flask-Limiter`, en memoria) en registro, login, y los tres pasos de
  recuperación de contraseña.
- **`CORS_ORIGINS` es obligatorio fuera de desarrollo** — ver tabla de variables en la sección 2.
- Validación de formato de teléfono/correo en registro y edición de perfil, y manejadores de
  error globales que siempre devuelven JSON (nunca la página HTML de error por defecto de Flask),
  con `rollback()` automático ante cualquier excepción no controlada.

## 8. Integridad de datos (segunda auditoría — Fase 5)

- Área (fincas, lotes) y capacidad (vehículos) deben ser mayores que cero, validado en la API y
  reforzado con `CHECK` en la base de datos.
- El código de un lote es único **por finca** (antes no había ninguna restricción).
- Una finca o lote inactivos ya no admiten operaciones nuevas (crear lotes, ciclos, censos de
  producción, solicitudes de transporte) — sí se pueden seguir consultando.
- La sincronización de censos de producción offline (`POST /api/produccion/sync`) es idempotente:
  reenviar el mismo `_local_id` (ej. por falta de confirmación de red) ya no duplica el registro.
- Solo el transportador aprobado y, si ya está asignada, el mismo transportador de la solicitud,
  puede aceptarla/rechazarla/cambiar su estado — antes `rechazar` no validaba nada de esto.
- Nuevo flujo de interés de compra: un comprador puede manifestar interés en una publicación del
  palmicultor (`POST /mercado/publicaciones/<id>/interes`), que notifica al palmicultor; este
  puede listar quién mostró interés (`GET .../intereses`).
- `GET /compradores/cercanos` calcula la distancia real (Haversine) cuando el cliente envía su
  posición (`?lat=&lon=`) y el comprador tiene coordenadas; si falta cualquiera de los dos datos,
  devuelve `distanciaKm: null` en vez de un `0` que antes era siempre un placeholder.
- Un comprador siempre debe tener `ubicacion` (registro público y alta administrativa).
- **Política de "eliminar" un comprador: se desactiva (`estado=inactivo`), igual que fincas,
  lotes y vehículos — nunca se borra físicamente**, para no perder el histórico de precios y
  solicitudes de transporte asociado. Es una decisión de diseño consistente con el resto del
  proyecto, no una limitación pendiente.
- Las 29 llaves foráneas del esquema declaran explícitamente `ON DELETE RESTRICT` (antes dependían
  del `NO ACTION` implícito de Postgres) y las 27 que no tenían índice propio ahora lo tienen.

## Estructura

```
palma-viva/
├── App.js
├── package.json
├── app.json
├── .env.example          variables del frontend (EXPO_PUBLIC_API_URL)
├── src/
│   ├── theme/             estilos y paleta de colores compartidos
│   ├── screens/            pantallas por rol (palmicultor, comprador, transportador, admin)
│   ├── services/           llamadas a la API con caché offline (AsyncStorage) y sesión (SecureStore)
│   └── config/api.js       cliente HTTP base
└── backend/
    ├── run.py
    ├── config.py
    ├── seed.py             datos de prueba para los 4 roles
    ├── .env.example        variables del backend
    └── app/
        ├── models.py       21 tablas del modelo entidad-relación
        ├── routes/         auth, market, logistics, fincas, produccion, pronosticos,
        │                   alertas, balance, admin, sms, ussd, puntos
        └── services/       twilio_sms, ussd_engine, contenido (textos editables)
```
