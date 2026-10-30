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
| `CORS_ORIGINS` | No | Orígenes permitidos, separados por coma. Vacío = todo permitido (cómodo en desarrollo). |
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

### 3.2 Compilar nativamente (opcional, solo si necesitas un APK real)

```bash
npx expo prebuild --platform android --clean
npx expo run:android
```

Requiere Android Studio + SDK instalados, un emulador (AVD) o dispositivo conectado, y un
**JDK 17 o superior** (Gradle moderno no funciona con JDK 8 — en Windows, si tienes Android
Studio instalado, usa su JBR: típicamente
`C:\Program Files\Android\Android Studio\jbr`, asegurándote de que sea el `java` que resuelve
tu PATH al compilar, no uno más viejo que puedas tener instalado aparte).

`npx expo prebuild` regenera la carpeta `android/` desde `app.json`/`package.json` — es el
camino soportado oficialmente por Expo en vez de mantener esa carpeta a mano.

**Nota (Windows):** si tu ruta del proyecto tiene caracteres no-ASCII (tildes, ñ, etc.),
Gradle puede fallar al interpretar esa ruta. Usa una ruta solo con caracteres ASCII si te
pasa esto.

## 4. Pruebas automatizadas

```bash
cd backend
pytest
```

Cubre autenticación (registro/login/JWT), autorización por rol, los CRUD principales
(fincas, puntos de comercialización, compradores) y el módulo SMS/USSD completo (webhook de
Twilio, firma, deduplicación, motor de sesión USSD). El frontend todavía no tiene lint ni
pruebas automatizadas configuradas — es una mejora pendiente, no bloqueante para evaluar el
prototipo.

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

Tras `npm audit fix` (sin `--force`) quedan sin resolver 2 cadenas, ambas en herramientas de
build de Node (no en código que corre dentro de la app):

- `deepmerge`/`zod` (vía `@expo/cli`/`@expo/config`, parte de la propia CLI de Expo): el único
  arreglo disponible instala `expo@51.0.39`, una regresión mayor desde el SDK 58 actual —
  riesgo aceptado conscientemente en vez de degradar el proyecto.
- `uuid` (vía `@expo/ngrok`, usado solo para `expo start --tunnel`): sin fix disponible todavía
  en origen.

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
