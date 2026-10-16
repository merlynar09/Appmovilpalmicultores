// screens/palmicultor/ProduccionHistoryScreen.js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, PrimaryButton, EmptyState, Badge, OfflineBanner } from '../../components/ui';
import { listarProduccion, sincronizarPendientes, contarPendientes } from '../../services/produccionService';

const FUENTE_LABEL = { app: 'App', sms: 'SMS', ussd: 'USSD' };

export default function ProduccionHistoryScreen({ navigation, route }) {
  const loteId = route.params?.loteId;
  const [registros, setRegistros] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [pendientes, setPendientes] = useState(0);

  const load = useCallback(async () => {
    await sincronizarPendientes().catch(() => {});
    const [data, p] = await Promise.all([listarProduccion(loteId), contarPendientes()]);
    setRegistros(data);
    setPendientes(p);
  }, [loteId]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      data={registros || []}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      ListHeaderComponent={
        <>
          <OfflineBanner visible={pendientes > 0} text={`${pendientes} censo(s) pendientes de sincronizar.`} />
          <PrimaryButton
            title="Nuevo censo de producción"
            icon="add-circle-outline"
            onPress={() => navigation.navigate('ProduccionForm', { loteId })}
            style={{ marginBottom: spacing.lg, marginTop: spacing.md }}
          />
        </>
      }
      renderItem={({ item }) => (
        <Card>
          <View style={styles.rowHeader}>
            <Text style={styles.fecha}>{item.fecha}</Text>
            <Badge text={FUENTE_LABEL[item.fuente] || item.fuente} tone={item.fuente === 'app' ? 'neutral' : 'primary'} />
          </View>
          <Text style={styles.linea}>Muestra: {item.palmas_evaluadas} palmas ({item.porcentaje_muestra ? `${item.porcentaje_muestra.toFixed(1)}%` : '—'}) · {item.palmas_improductivas} improductivas</Text>
          <Text style={styles.linea}>Racimos: {item.racimos_totales}</Text>
          {item.peso_promedio_racimo ? <Text style={styles.linea}>Peso promedio racimo: {item.peso_promedio_racimo} kg</Text> : null}
        </Card>
      )}
      ListEmptyComponent={<EmptyState icon="bar-chart-outline" title="Sin censos registrados" subtitle="Registra tu primer censo de producción." />}
    />
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  rowHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  fecha: { ...typography.label, textTransform: 'none', fontSize: 15 },
  linea: { ...typography.subtitle, fontSize: 13, marginTop: 4 },
});
