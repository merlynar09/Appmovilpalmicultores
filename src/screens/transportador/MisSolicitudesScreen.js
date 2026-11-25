// screens/transportador/MisSolicitudesScreen.js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, PrimaryButton, EmptyState, Badge } from '../../components/ui';
import { listarSolicitudes, actualizarEstadoSolicitud } from '../../services/logisticsService';

const SIGUIENTE_ESTADO = {
  Aceptada: 'En preparación',
  'En preparación': 'En tránsito',
  'En tránsito': 'Entregada',
};

const ESTADO_TONE = { Aceptada: 'primary', 'En preparación': 'warning', 'En tránsito': 'warning', Entregada: 'success' };

export default function MisSolicitudesScreen({ navigation }) {
  const [solicitudes, setSolicitudes] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const activas = await listarSolicitudes({}).catch(() => []);
    setSolicitudes((activas || []).filter((s) => !['Rechazada', 'Cancelada', 'Entregada'].includes(s.estado)));
  }, []);

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

  const avanzar = async (item) => {
    const siguiente = SIGUIENTE_ESTADO[item.estado];
    if (!siguiente) return;
    await actualizarEstadoSolicitud(item.id, siguiente);
    await load();
  };

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      data={solicitudes || []}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      renderItem={({ item }) => (
        <Card>
          <View style={styles.rowHeader}>
            <Text style={styles.id}>Solicitud #{item.id}</Text>
            <Badge text={item.estado} tone={ESTADO_TONE[item.estado] || 'neutral'} />
          </View>
          <Text style={styles.linea}>{item.cantidad_estimada} ton · {item.destino || 'Destino por confirmar'}</Text>
          {item.ubicacion_exacta ? (
            <View style={styles.ubicacionBox}>
              <Text style={styles.ubicacionLabel}>UBICACIÓN EXACTA (revelada al aceptar)</Text>
              <Text style={styles.linea}>{item.ubicacion_exacta.direccion || `${item.ubicacion_exacta.lat}, ${item.ubicacion_exacta.long}`}</Text>
            </View>
          ) : null}
          <PrimaryButton
            title="Ver mapa de la ruta"
            variant="secondary"
            icon="map-outline"
            onPress={() => navigation.navigate('RutaMap', { solicitudId: item.id })}
            style={{ marginTop: spacing.md }}
          />
          {SIGUIENTE_ESTADO[item.estado] && (
            <PrimaryButton title={`Marcar: ${SIGUIENTE_ESTADO[item.estado]}`} onPress={() => avanzar(item)} style={{ marginTop: spacing.sm }} />
          )}
        </Card>
      )}
      ListEmptyComponent={<EmptyState icon="navigate-outline" title="Sin viajes activos" subtitle="Acepta una solicitud pendiente para empezar." />}
    />
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  rowHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  id: { ...typography.label, textTransform: 'none', fontSize: 15 },
  linea: { ...typography.subtitle, fontSize: 13, marginTop: 4 },
  ubicacionBox: { marginTop: spacing.sm, backgroundColor: colors.background, borderRadius: 10, padding: spacing.sm },
  ubicacionLabel: { fontSize: 10, fontWeight: '700', color: colors.primary, letterSpacing: 0.4 },
});
