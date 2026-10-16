// screens/palmicultor/PronosticoDetailScreen.js
// Detalle del pronóstico: desglose completo de la fórmula RN04 y distribución
// mensual histórica del Pacífico nariñense.

import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { colors, spacing, typography, radius } from '../../theme/theme';
import { Card, LoadingView, PrimaryButton, IconRow } from '../../components/ui';
import { obtenerPronostico } from '../../services/pronosticosService';

export default function PronosticoDetailScreen({ navigation, route }) {
  const { pronosticoId } = route.params;
  const [p, setP] = useState(null);

  useEffect(() => {
    obtenerPronostico(pronosticoId).then(setP).catch(() => {});
  }, [pronosticoId]);

  if (!p) return <LoadingView label="Cargando pronóstico..." />;

  const maxKg = Math.max(...(p.distribucion_mensual || []).map((m) => m.produccion_kg), 1);

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.background }} contentContainerStyle={styles.container}>
      <Card style={styles.heroCard}>
        <Text style={styles.heroLabel}>PRODUCCIÓN ESTIMADA (6 MESES)</Text>
        <Text style={styles.heroValue}>{p.produccion_estimada_ton?.toFixed(2)} ton</Text>
        <Text style={styles.heroSub}>{Math.round(p.produccion_estimada_kg).toLocaleString('es-CO')} kg</Text>
      </Card>

      <Text style={styles.sectionTitle}>Distribución mensual</Text>
      <Card>
        {(p.distribucion_mensual || []).map((m) => (
          <View key={m.mes} style={styles.barRow}>
            <Text style={styles.barLabel}>{m.mes}</Text>
            <View style={styles.barTrack}>
              <View style={[styles.barFill, { width: `${(m.produccion_kg / maxKg) * 100}%` }]} />
            </View>
            <Text style={styles.barValue}>{m.porcentaje}%</Text>
          </View>
        ))}
      </Card>

      <Text style={styles.sectionTitle}>Cómo se calculó (RN04)</Text>
      <Card>
        <IconRow icon="leaf-outline" label="Palmas totales" value={p.palmas_totales} />
        <IconRow icon="close-circle-outline" label="Improductivas (muestra)" value={p.palmas_improductivas_muestra} />
        <IconRow icon="checkmark-circle-outline" label="Palmas productivas" value={p.palmas_productivas} />
        <IconRow icon="stats-chart-outline" label="Promedio de estructuras" value={p.promedio_estructuras?.toFixed(3)} />
        <IconRow icon="albums-outline" label="Racimos estimados" value={Math.round(p.racimos_estimados)} />
        <IconRow icon="scale-outline" label="Peso promedio racimo" value={`${p.peso_promedio} kg`} />

        <View style={styles.formula}>
          <Text style={styles.formulaText}>1. Palmas Productivas = Palmas Totales − Palmas Improductivas en muestra</Text>
          <Text style={styles.formulaText}>2. Promedio de Estructuras = Racimos en muestra / Palmas Productivas Muestreadas</Text>
          <Text style={styles.formulaText}>3. Total de Racimos = Palmas Productivas × Promedio de Estructuras</Text>
          <Text style={styles.formulaText}>4. Producción Estimada = Total Racimos × Peso Promedio del Racimo</Text>
          <Text style={styles.formulaText}>5. Distribución mensual histórica del Pacífico nariñense (jul-dic)</Text>
        </View>
      </Card>

      <PrimaryButton
        title="Calcular balance industrial con esta producción"
        icon="flask-outline"
        variant="secondary"
        onPress={() => navigation.navigate('BalanceIndustrial', { pronosticoId: p.id, produccionKg: p.produccion_estimada_kg })}
        style={{ marginTop: spacing.lg }}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  heroCard: { backgroundColor: colors.primary, alignItems: 'center', paddingVertical: spacing.lg },
  heroLabel: { color: colors.white, opacity: 0.8, fontWeight: '700', fontSize: 12, letterSpacing: 0.5 },
  heroValue: { color: colors.white, fontSize: 32, fontWeight: '800', marginTop: 4 },
  heroSub: { color: colors.white, opacity: 0.85, marginTop: 2 },
  sectionTitle: { ...typography.h2, fontSize: 18, marginTop: spacing.lg, marginBottom: spacing.sm },
  barRow: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing.sm },
  barLabel: { width: 80, fontSize: 13, color: colors.textSecondary },
  barTrack: { flex: 1, height: 14, backgroundColor: colors.background, borderRadius: radius.pill, marginHorizontal: spacing.sm, overflow: 'hidden' },
  barFill: { height: '100%', backgroundColor: colors.accentOrange, borderRadius: radius.pill },
  barValue: { width: 40, fontSize: 13, fontWeight: '700', color: colors.textPrimary, textAlign: 'right' },
  formula: { marginTop: spacing.md, borderTopWidth: 1, borderTopColor: colors.border, paddingTop: spacing.md },
  formulaText: { fontSize: 13, color: colors.textSecondary, marginBottom: 6 },
});
