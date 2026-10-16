// screens/palmicultor/SmsSimuladorScreen.js
// Simulador SMS/USSD (MOCK): permite probar, dentro de la misma app, los
// comandos que un palmicultor SIN datos móviles enviaría por SMS/USSD real
// a través de un operador. No hay proveedor externo (Twilio, etc.) conectado
// todavía porque requiere credenciales que no están disponibles en este
// entorno; este simulador llama al mismo endpoint que atendería ese gateway.

import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { colors, spacing, typography, radius } from '../../theme/theme';
import { Field, PrimaryButton, Card, FormPicker } from '../../components/ui';
import { getStoredUser } from '../../services/authService';
import { enviarComandoSms } from '../../services/smsService';

const EJEMPLOS = {
  AYUDA: 'AYUDA',
  REGISTRO: 'REGISTRO Lote-A1 40 2 80 16',
  TRANSPORTE: 'TRANSPORTE Lote-A1 8 2026-10-05',
};

export default function SmsSimuladorScreen() {
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
    <ScrollView style={{ flex: 1, backgroundColor: colors.background }} contentContainerStyle={styles.container}>
      <Text style={styles.hint}>
        Simula lo que recibiría un operador móvil (SMS o USSD) cuando un palmicultor sin datos envía un comando de texto. Se usa tu propio número registrado.
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
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  hint: { ...typography.subtitle, fontSize: 13, marginBottom: spacing.lg },
  chipsRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md, flexWrap: 'wrap' },
  chip: { paddingHorizontal: spacing.md, minHeight: 40 },
  respuestaLabel: { fontSize: 11, fontWeight: '700', color: colors.textSecondary, marginBottom: 6, letterSpacing: 0.5 },
  respuestaTexto: { ...typography.body, fontSize: 14 },
});
