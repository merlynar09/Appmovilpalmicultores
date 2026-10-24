// services/adminService.js
// Panel de administrador: usuarios, validación de transportadores y reportes agregados.

import { apiRequest } from '../config/api';

export const listarUsuarios = (rol) => apiRequest(rol ? `/admin/usuarios?rol=${rol}` : '/admin/usuarios');
export const cambiarEstadoUsuario = (id, estado) =>
  apiRequest(`/admin/usuarios/${id}/estado`, { method: 'PATCH', body: { estado } });

export const transportadoresPendientes = () => apiRequest('/admin/transportadores/pendientes');
export const listarTransportadores = () => apiRequest('/admin/transportadores');
export const validarTransportador = (id, estado) =>
  apiRequest(`/admin/transportadores/${id}/validar`, { method: 'PATCH', body: { estado } });

export const reportesGenerales = () => apiRequest('/admin/reportes');

export const listarCompradoresAdmin = () => apiRequest('/admin/compradores');
export const crearCompradorAdmin = (payload) => apiRequest('/admin/compradores', { method: 'POST', body: payload });
export const editarCompradorAdmin = (id, payload) => apiRequest(`/admin/compradores/${id}`, { method: 'PUT', body: payload });
export const cambiarEstadoCompradorAdmin = (id, estado) =>
  apiRequest(`/admin/compradores/${id}/estado`, { method: 'PATCH', body: { estado } });
export const publicarPrecioAdmin = (compradorId, payload) =>
  apiRequest(`/admin/compradores/${compradorId}/precios`, { method: 'POST', body: payload });

export const listarContenidoSmsUssd = () => apiRequest('/admin/contenido-sms-ussd');
export const editarContenidoSmsUssd = (clave, texto) =>
  apiRequest(`/admin/contenido-sms-ussd/${clave}`, { method: 'PUT', body: { texto } });
export const restaurarContenidoSmsUssd = (clave) =>
  apiRequest(`/admin/contenido-sms-ussd/${clave}`, { method: 'DELETE' });
