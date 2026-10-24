// services/puntosService.js
// Puntos de comercialización (CU6: consulta; CU14: gestión admin).

import { apiRequest } from '../config/api';

export const listarPuntos = () => apiRequest('/puntos-comercializacion', { auth: false });
export const listarPuntosAdmin = () => apiRequest('/admin/puntos-comercializacion');
export const crearPunto = (payload) => apiRequest('/admin/puntos-comercializacion', { method: 'POST', body: payload });
export const editarPunto = (id, payload) => apiRequest(`/admin/puntos-comercializacion/${id}`, { method: 'PUT', body: payload });
export const cambiarEstadoPunto = (id, estado) =>
  apiRequest(`/admin/puntos-comercializacion/${id}/estado`, { method: 'PATCH', body: { estado } });
