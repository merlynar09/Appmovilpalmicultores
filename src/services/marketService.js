// services/marketService.js
// Precio vigente y compradores cercanos, con caché local para modo offline.

import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiRequest } from '../config/api';

const PRICE_CACHE_KEY = '@cache_precio_vigente';
const BUYERS_CACHE_KEY = '@cache_compradores';

export async function getPrecioVigente() {
  try {
    const data = await apiRequest('/precios/vigente');
    await AsyncStorage.setItem(PRICE_CACHE_KEY, JSON.stringify(data));
    return data;
  } catch (_err) {
    const cached = await AsyncStorage.getItem(PRICE_CACHE_KEY);
    return cached ? JSON.parse(cached) : null;
  }
}

export async function getCompradoresCercanos() {
  try {
    const data = await apiRequest('/compradores/cercanos');
    await AsyncStorage.setItem(BUYERS_CACHE_KEY, JSON.stringify(data));
    return data;
  } catch (_err) {
    const cached = await AsyncStorage.getItem(BUYERS_CACHE_KEY);
    return cached ? JSON.parse(cached) : [];
  }
}

export async function publicarProducto(payload) {
  return apiRequest('/mercado/publicaciones', { method: 'POST', body: payload });
}

export const misPublicaciones = () => apiRequest('/mercado/publicaciones');
export const editarPublicacion = (id, payload) =>
  apiRequest(`/mercado/publicaciones/${id}`, { method: 'PUT', body: payload });
export const cambiarEstadoPublicacion = (id, estado) =>
  apiRequest(`/mercado/publicaciones/${id}/estado`, { method: 'PATCH', body: { estado } });

export async function vitrinaPublica(filtros = {}) {
  const params = new URLSearchParams();
  if (filtros.municipio) params.set('municipio', filtros.municipio);
  const qs = params.toString();
  return apiRequest(`/mercado/vitrina${qs ? `?${qs}` : ''}`);
}

export const detallePublicacion = (id) => apiRequest(`/mercado/publicaciones/${id}/detalle`);
export const detalleComprador = (id) => apiRequest(`/compradores/${id}`);

// Precios: los fija siempre el comprador, nunca el palmicultor.
export const misPrecios = () => apiRequest('/precios/mios');
export const publicarPrecio = (payload) => apiRequest('/precios/mios', { method: 'POST', body: payload });
