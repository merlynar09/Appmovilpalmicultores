// screens/palmicultor/BalanceIndustrialScreen.js
// Balance de extracción industrial (RN05): por cada 100 kg de fruto fresco.

import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert } from 'react-native';
import { colors, spacing, typography } from '../../theme/theme';
import { Field, PrimaryButton, Card } from '../../components/ui';
import { calcularBalance } from '../../services/balanceService';

export default function BalanceIndustrialScreen({ route }) {
  const { pronosticoId, produccionKg } = route.params || {};
  const [entradaKg, setEntradaKg] = useState(produccionKg ? String(Math.round(produccionKg)) : '100');
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(false);

  const calcular = async (usarPronostico) => {
    if (!usarPronostico && (!entradaKg || Number(entradaKg) <= 0)) {
      Alert.alert('Falta información', 'Ingresa la cantidad de fruto fresco en kg.');
      return;
    }
    setLoading(true);
    try {
      const body = usarPronostico ? { pronostico_id: pronosticoId } : { entrada_kg: Number(entradaKg) };
      const data = await calcularBalance(body);
      setResultado(data);
    } catch (err) {
      Alert.alert('No se pudo calcular', err?.message || 'Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.background }} contentContainerStyle={styles.container}>
      <Text style={styles.hint}>
        Por cada 100 kg de fruto fresco: 10 kg se pierden por humedad, 20 kg son tusas, 15 kg fibras, 21 kg aguas/impurezas, 7 kg cuesco, 5 kg palmiste y 22 kg se extraen como aceite crudo.
      </Text>

      <Field label="Fruto fresco de entrada (kg)" keyboardType="numeric" value={entradaKg} onChangeText={setEntradaKg} />
      <PrimaryButton title="Calcular balance" onPress={() => calcular(false)} loading={loading} />

      {pronosticoId ? (
        <PrimaryButton
          title={`Usar producción estimada del pronóstico (${Math.round(produccionKg).toLocaleString('es-CO')} kg)`}
          variant="secondary"
          onPress={() => calcular(true)}
          loading={loading}
          style={{ marginTop: spacing.md }}
        />
      ) : null}

      {resultado && (
        <>
          <Card style={styles.heroCard}>
            <Text style={styles.heroLabel}>ACEITE CRUDO EXTRAÍDO</Text>
            <Text style={styles.heroValue}>{resultado.aceite_crudo_kg.toLocaleString('es-CO')} kg</Text>
            <Text style={styles.heroSub}>{resultado.rendimiento_porcentaje}% de rendimiento sobre {resultado.entrada_kg.toLocaleString('es-CO')} kg de entrada</Text>
          </Card>

          <Text style={styles.sectionTitle}>Desglose por etapa</Text>
          <Card>
            {Object.values(resultado.desglose).map((etapa) => (
              <View key={etapa.etiqueta} style={styles.etapaRow}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.etapaLabel}>{etapa.etiqueta}</Text>
                  <Text style={styles.etapaPorcentaje}>{etapa.porcentaje}%</Text>
                </View>
                <Text style={styles.etapaKg}>{etapa.kg.toLocaleString('es-CO')} kg</Text>
              </View>
            ))}
          </Card>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  hint: { ...typography.subtitle, fontSize: 13, marginBottom: spacing.lg },
  heroCard: { backgroundColor: colors.primary, alignItems: 'center', paddingVertical: spacing.lg, marginTop: spacing.xl },
  heroLabel: { color: colors.white, opacity: 0.8, fontWeight: '700', fontSize: 12, letterSpacing: 0.5 },
  heroValue: { color: colors.white, fontSize: 30, fontWeight: '800', marginTop: 4 },
  heroSub: { color: colors.white, opacity: 0.85, marginTop: 4, fontSize: 12, textAlign: 'center', paddingHorizontal: spacing.md },
  sectionTitle: { ...typography.h2, fontSize: 18, marginTop: spacing.lg, marginBottom: spacing.sm },
  etapaRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: colors.border },
  etapaLabel: { ...typography.body, fontSize: 14 },
  etapaPorcentaje: { fontSize: 12, color: colors.textSecondary },
  etapaKg: { ...typography.label, textTransform: 'none', fontSize: 15 },
});
