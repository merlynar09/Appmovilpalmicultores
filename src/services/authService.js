// services/authService.js
// Registro / login. Guarda el usuario y token localmente para operar offline
// y sincronizar cuando vuelva la conexión (puente SMS/USSD para zonas sin señal).

import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiRequest } from '../config/api';

const PENDING_KEY = '@pending_registrations';

export async function registerUser(payload) {
  try {
    const data = await apiRequest('/auth/register', {
      method: 'POST',
      body: payload,
      auth: false,
    });
    return data;
  } catch (err) {
    // Sin conexión: guardamos localmente para reenviar luego
    // (por API o por el puente SMS/USSD simulado con Twilio).
    const pendingRaw = await AsyncStorage.getItem(PENDING_KEY);
    const pending = pendingRaw ? JSON.parse(pendingRaw) : [];
    pending.push({ ...payload, _queuedAt: new Date().toISOString() });
    await AsyncStorage.setItem(PENDING_KEY, JSON.stringify(pending));
    throw new Error(
      'No hay conexión. Tu registro se guardó en este dispositivo y se enviará automáticamente cuando haya señal.'
    );
  }
}

export async function loginUser({ identifier, password, remember }) {
  const data = await apiRequest('/auth/login', {
    method: 'POST',
    body: { identifier, password },
    auth: false,
  });

  await AsyncStorage.setItem('@auth_token', data.token);
  await AsyncStorage.setItem('@auth_user', JSON.stringify(data.usuario));
  if (remember) {
    await AsyncStorage.setItem('@auth_remember', 'true');
  }
  return data.usuario; // { id, nombre_completo, rol, ... }
}

export async function actualizarPerfil(payload) {
  const usuarioActualizado = await apiRequest('/auth/perfil', { method: 'PATCH', body: payload });
  await AsyncStorage.setItem('@auth_user', JSON.stringify(usuarioActualizado));
  return usuarioActualizado;
}

export async function logoutUser() {
  await AsyncStorage.multiRemove(['@auth_token', '@auth_user']);
}

export async function getStoredUser() {
  const raw = await AsyncStorage.getItem('@auth_user');
  return raw ? JSON.parse(raw) : null;
}

export async function syncPendingRegistrations() {
  const pendingRaw = await AsyncStorage.getItem(PENDING_KEY);
  const pending = pendingRaw ? JSON.parse(pendingRaw) : [];
  if (!pending.length) return { enviados: 0, pendientes: 0 };

  const restantes = [];
  let enviados = 0;
  for (const payload of pending) {
    const { _queuedAt, ...body } = payload;
    try {
      await apiRequest('/auth/register', { method: 'POST', body, auth: false });
      enviados += 1;
    } catch (_e) {
      restantes.push(payload);
    }
  }
  await AsyncStorage.setItem(PENDING_KEY, JSON.stringify(restantes));
  return { enviados, pendientes: restantes.length };
}

export async function forgotPassword(identifier) {
  return apiRequest('/auth/forgot-password', { method: 'POST', body: { identifier }, auth: false });
}

export async function verifyResetCode(identifier, codigo) {
  return apiRequest('/auth/verify-code', { method: 'POST', body: { identifier, codigo }, auth: false });
}

export async function resetPassword(identifier, codigo, password) {
  return apiRequest('/auth/reset-password', {
    method: 'POST',
    body: { identifier, codigo, password },
    auth: false,
  });
}
