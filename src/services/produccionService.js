// services/produccionService.js
// Censo de producción con cola de reintentos offline (AsyncStorage).

import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiRequest } from '../config/api';

const QUEUE_KEY = '@queue_produccion';
const CACHE_KEY_PREFIX = '@cache_produccion_';

export async function listarProduccion(loteId) {
  const path = loteId ? `/produccion?lote_id=${loteId}` : '/produccion';
  const cacheKey = CACHE_KEY_PREFIX + (loteId || 'todos');
  try {
    const data = await apiRequest(path);
    await AsyncStorage.setItem(cacheKey, JSON.stringify(data));
    return data;
  } catch (err) {
    const cached = await AsyncStorage.getItem(cacheKey);
    return cached ? JSON.parse(cached) : [];
  }
}

export async function crearRegistroProduccion(payload) {
  try {
    return await apiRequest('/produccion', { method: 'POST', body: payload });
  } catch (err) {
    if (!err.isNetworkError) {
      // El servidor respondió con un error real (validación, etc.) —
      // no es algo que se resuelva reintentando sin conexión.
      throw err;
    }
    await _encolar(payload);
    throw new Error(
      'Sin conexión: el censo se guardó en este dispositivo y se enviará automáticamente cuando haya señal.'
    );
  }
}

export async function contarPendientes() {
  const cola = await _leerCola();
  return cola.length;
}

export async function sincronizarPendientes() {
  const cola = await _leerCola();
  if (!cola.length) return { enviados: 0, pendientes: 0, errores: [] };

  let data;
  try {
    data = await apiRequest('/produccion/sync', { method: 'POST', body: { items: cola } });
  } catch (_e) {
    return { enviados: 0, pendientes: cola.length, errores: [] };
  }

  const resultados = data.resultados || [];
  const idsOk = new Set(resultados.filter((r) => r.ok).map((r) => r._local_id));
  const errores = resultados.filter((r) => !r.ok);
  const restantes = cola.filter((item) => !idsOk.has(item._local_id));

  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(restantes));
  return { enviados: idsOk.size, pendientes: restantes.length, errores };
}

async function _encolar(payload) {
  const cola = await _leerCola();
  cola.push({ ...payload, _local_id: `${Date.now()}_${Math.random().toString(36).slice(2)}` });
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(cola));
}

async function _leerCola() {
  const raw = await AsyncStorage.getItem(QUEUE_KEY);
  return raw ? JSON.parse(raw) : [];
}
