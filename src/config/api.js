// config/api.js
// Cliente HTTP centralizado.
//
// MOD-01/DEV-F2-08: la URL base se lee de la variable de entorno
// EXPO_PUBLIC_API_URL (Expo la soporta de forma nativa, sin paquete
// adicional) en vez de quedar fija en el código — así cada quien la ajusta
// en su propio .env sin tocar este archivo ni arriesgarse a subir una URL
// de un túnel temporal al repositorio. Ver .env.example en la raíz del
// proyecto para los 3 escenarios típicos (emulador, dispositivo físico en
// la misma WiFi, túnel ngrok/ Expo tunnel).
import Constants from 'expo-constants';
import * as SecureStore from 'expo-secure-store';

const DEFAULT_EMULADOR = 'http://10.0.2.2:5000/api';

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ||
  Constants.expoConfig?.extra?.apiUrl ||
  DEFAULT_EMULADOR;

if (!process.env.EXPO_PUBLIC_API_URL && !Constants.expoConfig?.extra?.apiUrl) {
  console.warn(
    `[api] EXPO_PUBLIC_API_URL no está definida — usando ${DEFAULT_EMULADOR} ` +
      '(solo funciona en el emulador de Android). Define EXPO_PUBLIC_API_URL en tu .env ' +
      'para dispositivo físico o túnel — ver .env.example.'
  );
}

// MOD-03: el token JWT es un secreto real — vive en SecureStore (cifrado
// por el sistema operativo), no en AsyncStorage (texto plano). El usuario
// cacheado (@auth_user) no es secreto y se queda en AsyncStorage.
async function getToken() {
  return SecureStore.getItemAsync('auth_token');
}

export async function apiRequest(path, { method = 'GET', body, auth = true } = {}) {
  // El header ngrok-skip-browser-warning evita la página de advertencia que
  // ngrok (plan gratuito) inserta en la primera petición de cada túnel nuevo;
  // no afecta en nada cuando NO se usa ngrok (el backend simplemente la ignora).
  const headers = { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' };
  if (auth) {
    const token = await getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  try {
    data = await response.json();
  } catch (_e) {
    // respuesta sin cuerpo JSON
  }

  if (!response.ok) {
    const message = data?.message || data?.error || `Error ${response.status}`;
    throw new Error(message);
  }
  return data;
}
