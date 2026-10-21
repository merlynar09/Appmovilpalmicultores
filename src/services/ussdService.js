// services/ussdService.js
// Simulador de SESIÓN USSD (menú interactivo con contexto), distinto del
// comando de una sola línea de smsService.js. Llama al motor real de
// menús del backend (app/services/ussd_engine.py) a través del endpoint
// de simulación — la misma lógica que usaría un proveedor USSD real,
// solo que aquí sin firma ni teléfono/operador real de por medio.

import { apiRequest } from '../config/api';

export const simularUssd = (telefono, sessionId, texto) =>
  apiRequest('/ussd/simular', { method: 'POST', body: { telefono, session_id: sessionId, texto }, auth: false });
