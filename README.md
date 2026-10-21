# Palma Viva

App móvil para palmicultores de Tumaco, Nariño — React Native (Expo) + Flask + PostgreSQL.

## 1. Requisitos

- Node.js LTS
- Android Studio con un emulador creado (ej. Pixel 2 XL, API 35)
- Python 3.10+
- PostgreSQL corriendo localmente

## 2. Frontend (Expo)

```bash
npm install
npx expo install --fix
```

`expo install --fix` ajusta las versiones de las librerías nativas a las que
exactamente espera tu SDK de Expo instalado (evita conflictos de versión).

## 3. Backend (Flask + PostgreSQL)

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

Crea la base de datos (ajusta usuario/clave si los tuyos son distintos):

```bash
psql -U postgres -c "CREATE DATABASE palma_viva;"
```

Crea las tablas con Alembic (Flask-Migrate):

```bash
set FLASK_APP=run.py        # Windows (PowerShell: $env:FLASK_APP="run.py")
# export FLASK_APP=run.py   # macOS/Linux

flask db init
flask db migrate -m "inicial"
flask db upgrade
```

Levanta el servidor (déjalo corriendo en esta terminal):

```bash
python run.py
```

Debe quedar escuchando en `0.0.0.0:5000`. El frontend ya está configurado
(`src/config/api.js`) para hablarle a `http://10.0.2.2:5000/api`, que es como
el emulador de Android ve al localhost de tu PC.

## 4. Ejecutar la app en Android Studio

1. Abre Android Studio → Device Manager → inicia tu emulador.
2. En otra terminal, en la raíz del proyecto (no en `backend/`):

```bash
npx expo run:android
```

Esto compila la app nativa y la instala en el emulador. La primera vez tarda
varios minutos.

## 5. Probar

En el emulador: "Regístrate ahora" → crea una cuenta como Palmicultor →
inicia sesión → deberías llegar al Dashboard. La tarjeta de precio y la
lista de compradores aparecerán vacías hasta que carguemos datos de prueba
(pendiente para la fase 2).

## Estructura

```
palma-viva/
├── App.js
├── package.json
├── app.json
├── src/
│   ├── theme/          estilos y paleta de colores compartidos
│   ├── screens/         Login, Register, PalmicultorDashboard + placeholders
│   ├── services/        llamadas a la API con caché offline (AsyncStorage)
│   └── config/api.js     cliente HTTP base
└── backend/
    ├── run.py
    ├── config.py
    └── app/
        ├── models.py     14 tablas del modelo entidad-relación
        └── routes/       auth, market, logistics
```

## SMS y USSD

El acceso sin datos móviles tiene dos canales, documentados por separado:

- **SMS real (Twilio)**: envío y recepción verificados con un operador real.
- **USSD con menú interactivo**: motor y sesión completos, probados contra un
  simulador interno — ver [`backend/docs/USSD.md`](backend/docs/USSD.md)
  para la arquitectura, qué falta para un proveedor real en Colombia y cómo
  probarlo desde la app (pantalla "Simulador SMS/USSD" → pestaña "Sesión USSD").

## Estado actual (Fase 1)

- ✅ Registro e inicio de sesión (JWT) — Palmicultor y Comprador
- ✅ Dashboard del Palmicultor (precio vigente, compradores, logística)
- ✅ Backend con las 14 tablas normalizadas
- ⏳ Pendiente: pantallas de Comprador, Transportador y Administrador;
  módulos de Lotes/Producción/Pronósticos; datos de prueba (seed)
