// screens/admin/AdminReportesScreen.js
// Reportes agregados: nunca expone información personal ni ubicaciones exactas.

import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, LoadingView } from '../../components/ui';
import { reportesGenerales } from '../../services/adminService';

export default function AdminReportesScreen() {
  const [r, setR] = useState(null);

  useEffect(() => {
    reportesGenerales().then(setR).catch(() => {});
  }, []);

  if (!r) return <LoadingView label="Cargando reportes..." />;

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.background }} contentContainerStyle={styles.container}>
      <Text style={styles.sectionTitle}>Usuarios</Text>
      <Card>
        <Row label="Total" value={r.usuarios.total} />
        {Object.entries(r.usuarios.por_rol).map(([rol, count]) => (
          <Row key={rol} label={rol} value={count} />
        ))}
      </Card>

      <Text style={styles.sectionTitle}>Producción</Text>
      <Card>
        <Row label="Fincas activas" value={r.produccion.total_fincas} />
        <Row label="Lotes activos" value={r.produccion.total_lotes} />
        <Row label="Hectáreas totales" value={r.produccion.total_hectareas?.toFixed(1)} />
      </Card>

      <Text style={styles.sectionTitle}>Mercado</Text>
      <Card>
        <Row label="Publicaciones activas" value={r.mercado.publicaciones_activas} />
        <Row label="Publicaciones vendidas" value={r.mercado.publicaciones_vendidas} />
        <Row label="Toneladas publicadas" value={r.mercado.toneladas_publicadas?.toFixed(1)} />
      </Card>

      <Text style={styles.sectionTitle}>Logística</Text>
      <Card>
        {Object.entries(r.logistica.solicitudes_por_estado).map(([estado, count]) => (
          <Row key={estado} label={estado} value={count} />
        ))}
        <Row label="Transportadores pendientes" value={r.logistica.transportadores_pendientes} />
      </Card>
    </ScrollView>
  );
}

function Row({ label, value }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value ?? '—'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  sectionTitle: { ...typography.h2, fontSize: 18, marginTop: spacing.lg, marginBottom: spacing.sm },
  row: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: colors.border },
  label: { ...typography.body, fontSize: 14, textTransform: 'capitalize' },
  value: { ...typography.label, textTransform: 'none', fontSize: 15 },
});
