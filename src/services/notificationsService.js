// services/notificationsService.js
// Notificaciones LOCALES (no push remoto): se programan/disparan desde el
// propio dispositivo cuando la app detecta alertas nuevas (cosecha próxima,
// cambios de estado de logística, etc.). El proyecto no usa ni ha usado
// nunca push remoto (no hay getExpoPushTokenAsync, FCM ni registro de token
// en el backend) — las alertas se generan en el backend y se entregan por
// polling + notificación local, así que no hace falta ningún token.
//
// IMPORTANTE (limitación real de la plataforma, no un bug de este archivo):
// desde el SDK 53 de Expo, Expo Go en ANDROID no incluye el módulo nativo de
// expo-notifications — Expo lo retiró del cliente de Expo Go por completo
// (no solo la parte de push remoto). Cualquier llamada ahí lanza
// "...was removed from Expo Go...". En iOS Expo Go y en cualquier
// development build o build de producción en Android, el módulo sí está
// presente y esta misma implementación funciona sin cambios.
//
// Por eso detectamos el entorno ANTES de tocar la librería (en vez de
// depender solo de try/catch, que no siempre alcanza a interceptar el error
// interno del propio paquete): si estamos en Expo Go + Android, las
// notificaciones simplemente quedan desactivadas con un aviso claro en
// consola, y el resto de la app sigue funcionando igual.

import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants, { ExecutionEnvironment } from 'expo-constants';

const NOTIFIED_IDS_KEY = '@notified_alert_ids';
const MAX_STORED_IDS = 300;

let Notifications = null;
let disponible = true;
let avisoMostrado = false;

function enExpoGoAndroid() {
  const enExpoGo =
    Constants.appOwnership === 'expo' ||
    Constants.executionEnvironment === ExecutionEnvironment.StoreClient;
  return Platform.OS === 'android' && enExpoGo;
}

function getNotificationsModule() {
  if (!disponible) return null;
  if (Notifications) return Notifications;

  if (enExpoGoAndroid()) {
    disponible = false;
    if (!avisoMostrado) {
      avisoMostrado = true;
      console.warn(
        '[notificaciones] Desactivadas en esta sesión: expo-notifications no está disponible en Expo Go para Android desde el SDK 53. ' +
          'Funcionan normal en un development build (npx expo run:android / EAS Build) o en iOS Expo Go. El resto de la app no se ve afectado.'
      );
    }
    return null;
  }

  try {
    Notifications = require('expo-notifications');
    return Notifications;
  } catch (_e) {
    disponible = false;
    return null;
  }
}

export async function initNotifications() {
  try {
    const N = getNotificationsModule();
    if (!N) return;

    N.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldShowBanner: true,
        shouldShowList: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
      }),
    });

    if (Platform.OS === 'android') {
      await N.setNotificationChannelAsync('alertas-palma-viva', {
        name: 'Alertas Palma Viva',
        importance: N.AndroidImportance.DEFAULT,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: '#1B4D3E',
      });
    }

    const { status } = await N.getPermissionsAsync();
    if (status !== 'granted') {
      await N.requestPermissionsAsync();
    }
  } catch (_e) {
    // No disponible en Expo Go (Android, SDK 53+), permiso denegado, o web.
    // La app sigue funcionando normalmente sin notificaciones.
    disponible = false;
  }
}

export function addNotificationTapListener(onTap) {
  try {
    const N = getNotificationsModule();
    if (!N) return { remove: () => {} };

    return N.addNotificationResponseReceivedListener((response) => {
      const data = response?.notification?.request?.content?.data;
      if (data) onTap(data);
    });
  } catch (_e) {
    return { remove: () => {} };
  }
}

export async function notificarAlertasNuevas(alertas) {
  const N = getNotificationsModule();
  if (!N || !alertas?.length) return;

  const yaNotificadas = await _leerNotificadas();
  const pendientes = alertas.filter((a) => !a.leida && !yaNotificadas.has(a.id));
  if (!pendientes.length) return;

  for (const alerta of pendientes) {
    try {
      await N.scheduleNotificationAsync({
        content: {
          title: alerta.titulo,
          body: alerta.mensaje,
          data: { enlace: alerta.enlace, alertaId: alerta.id },
        },
        trigger: null, // inmediata
      });
    } catch (_e) {
      // Sin permisos, módulo no disponible u otro error — no bloquea el resto de la app.
    }
    yaNotificadas.add(alerta.id);
  }

  const recortadas = Array.from(yaNotificadas).slice(-MAX_STORED_IDS);
  await AsyncStorage.setItem(NOTIFIED_IDS_KEY, JSON.stringify(recortadas));
}

async function _leerNotificadas() {
  const raw = await AsyncStorage.getItem(NOTIFIED_IDS_KEY);
  return new Set(raw ? JSON.parse(raw) : []);
}
