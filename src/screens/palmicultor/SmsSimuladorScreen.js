// screens/palmicultor/SmsSimuladorScreen.js
// Simulador SMS/USSD (MOCK): dos pestañas.
// 1) "Comando" — un solo mensaje de texto (REGISTRO/TRANSPORTE/AYUDA),
//    igual que como ya funcionaba, sin cambios de comportamiento.
// 2) "Sesión USSD" — menú interactivo con contexto real (el motor completo
//    de app/services/ussd_engine.py: navegación, submenús, confirmación),
//    para probar la experiencia de un teléfono básico marcando un código.
// Ninguna de las dos es una sesión real de un operador móvil — no hay
// proveedor USSD/SMS externo conectado para esto todavía (ver docs/USSD.md).

import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, typography, radius } from '../../theme/theme';
import { Field, PrimaryButton, Card, FormPicker, Badge } from '../../components/ui';
import { getStoredUser } from '../../services/authService';
import { enviarComandoSms } from '../../services/smsService';
import { simularUssd } from '../../services/ussdService';

const EJEMPLOS = {
  AYUDA: 'AYUDA',
  REGISTRO: 'REGISTRO Lote-A1 40 2 80 16',
  TRANSPORTE: 'TRANSPORTE Lote-A1 8 2026-10-05',
};

export default function SmsSimuladorScreen() {
  const [modo, setModo] = useState('comando');

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.background }} contentContainerStyle={styles.container}>
      <View style={styles.avisoBox}>
        <Ionicons name="flask-outline" size={16} color={colors.accentEarth} />
        <Text style={styles.avisoTexto}>
          SIMULACIÓN interna — no es una sesión real de un operador móvil. Útil para probar sin depender de un proveedor externo.
        </Text>
      </View>

      <FormPicker
        label="Modo"
        value={modo}
        onSelect={setModo}
        options={[
          { value: 'comando', label: 'Comando (SMS/USSD)' },
          { value: 'sesion', label: 'Sesión USSD (menú)' },
        ]}
      />

      {modo === 'comando' ? <ModoComando /> : <ModoSesion />}
    </ScrollView>
  );
}

function ModoComando() {
  const [canal, setCanal] = useState('sms');
  const [mensaje, setMensaje] = useState(EJEMPLOS.AYUDA);
  const [respuesta, setRespuesta] = useState(null);
  const [loading, setLoading] = useState(false);

  const enviar = async () => {
    setLoading(true);
    setRespuesta(null);
    try {
      const usuario = await getStoredUser();
      const data = await enviarComandoSms(usuario?.telefono, mensaje, canal);
      setRespuesta(data.respuesta);
    } catch (err) {
      setRespuesta(`Error: ${err?.message || 'no se pudo enviar el comando'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      <Text style={styles.hint}>
        Simula un solo mensaje de texto, como lo escribiría un palmicultor sin datos móviles. Se usa tu propio número registrado.
      </Text>

      <FormPicker label="Canal" value={canal} onSelect={setCanal} options={[{ value: 'sms', label: 'SMS' }, { value: 'ussd', label: 'USSD' }]} />

      <View style={styles.chipsRow}>
        {Object.entries(EJEMPLOS).map(([key, val]) => (
          <PrimaryButton key={key} title={key} variant="secondary" onPress={() => setMensaje(val)} style={styles.chip} />
        ))}
      </View>

      <Field label="Mensaje" value={mensaje} onChangeText={setMensaje} multiline />
      <PrimaryButton title="Enviar" icon="send-outline" onPress={enviar} loading={loading} />

      {respuesta ? (
        <Card style={{ marginTop: spacing.lg }}>
          <Text style={styles.respuestaLabel}>RESPUESTA DEL SISTEMA</Text>
          <Text style={styles.respuestaTexto}>{respuesta}</Text>
        </Card>
      ) : null}
    </View>
  );
}

function nuevoSessionId() {
  return `app-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function ModoSesion() {
  const [sessionId, setSessionId] = useState(nuevoSessionId());
  const [historial, setHistorial] = useState([]); // [{de: 'sistema'|'yo', texto}]
  const [entrada, setEntrada] = useState('');
  const [activa, setActiva] = useState(false);
  const [loading, setLoading] = useState(false);

  const iniciar = async () => {
    setLoading(true);
    const sid = nuevoSessionId();
    setSessionId(sid);
    setHistorial([]);
    try {
      const usuario = await getStoredUser();
      const data = await simularUssd(usuario?.telefono, sid, '');
      setHistorial([{ de: 'sistema', texto: data.respuesta }]);
      setActiva(data.continuar);
    } catch (err) {
      setHistorial([{ de: 'sistema', texto: `Error: ${err?.message || 'no se pudo iniciar'}` }]);
      setActiva(false);
    } finally {
      setLoading(false);
    }
  };

  const enviar = async () => {
    if (!entrada.trim()) return;
    setLoading(true);
    const miEntrada = entrada.trim();
    setHistorial((h) => [...h, { de: 'yo', texto: miEntrada }]);
    setEntrada('');
    try {
      const usuario = await getStoredUser();
      const data = await simularUssd(usuario?.telefono, sessionId, miEntrada);
      setHistorial((h) => [...h, { de: 'sistema', texto: data.respuesta }]);
      setActiva(data.continuar);
    } catch (err) {
      setHistorial((h) => [...h, { de: 'sistema', texto: `Error: ${err?.message || 'no se pudo continuar'}` }]);
      setActiva(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      <Text style={styles.hint}>
        Marca como lo haría un teléfono básico: pulsa "Iniciar sesión" para ver el menú principal, luego escribe un número y "Enviar" para navegar.
      </Text>

      <View style={styles.sesionHeader}>
        <Badge text={activa ? 'Sesión activa' : 'Sin sesión'} tone={activa ? 'success' : 'neutral'} />
        <PrimaryButton title="Iniciar sesión" variant="secondary" icon="refresh-outline" onPress={iniciar} loading={loading && historial.length === 0} style={{ minHeight: 40, paddingHorizontal: spacing.md }} />
      </View>

      {historial.length > 0 && (
        <Card style={{ marginBottom: spacing.md }}>
          {historial.map((h, i) => (
            <View key={i} style={[styles.burbuja, h.de === 'yo' ? styles.burbujaYo : styles.burbujaSistema]}>
              <Text style={styles.burbujaEtiqueta}>{h.de === 'yo' ? 'Tú' : 'Palma Viva'}</Text>
              <Text style={styles.burbujaTexto}>{h.texto}</Text>
            </View>
          ))}
        </Card>
      )}

      {activa && (
        <View style={styles.entradaRow}>
          <View style={{ flex: 1 }}>
            <Field placeholder="Escribe una opción (ej. 1)" value={entrada} onChangeText={setEntrada} />
          </View>
          <PrimaryButton title="Enviar" icon="send-outline" onPress={enviar} loading={loading} style={styles.botonEnviar} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  avisoBox: {
    flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#FBEAD9',
    borderRadius: radius.md, padding: spacing.sm, marginBottom: spacing.lg,
  },
  avisoTexto: { flex: 1, fontSize: 12, color: colors.accentEarth },
  hint: { ...typography.subtitle, fontSize: 13, marginBottom: spacing.lg },
  chipsRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md, flexWrap: 'wrap' },
  chip: { paddingHorizontal: spacing.md, minHeight: 40 },
  respuestaLabel: { fontSize: 11, fontWeight: '700', color: colors.textSecondary, marginBottom: 6, letterSpacing: 0.5 },
  respuestaTexto: { ...typography.body, fontSize: 14 },
  sesionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.md },
  burbuja: { marginBottom: spacing.sm, padding: spacing.sm, borderRadius: radius.sm },
  burbujaSistema: { backgroundColor: colors.background },
  burbujaYo: { backgroundColor: '#E1EAE6', alignItems: 'flex-end' },
  burbujaEtiqueta: { fontSize: 10, fontWeight: '700', color: colors.textSecondary, marginBottom: 2 },
  burbujaTexto: { fontSize: 14, color: colors.textPrimary },
  entradaRow: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start' },
  botonEnviar: { minHeight: 56, paddingHorizontal: spacing.lg },
});
