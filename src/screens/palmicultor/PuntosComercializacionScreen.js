// screens/palmicultor/PuntosComercializacionScreen.js
// CU6: consulta de puntos de comercialización — solo lectura para palmicultor.

import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, EmptyState } from '../../components/ui';
import { listarPuntos } from '../../services/puntosService';

export default function PuntosComercializacionScreen() {
  const [puntos, setPuntos] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const data = await listarPuntos().catch(() => []);
    setPuntos(data);
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

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      data={puntos || []}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      renderItem={({ item }) => (
        <Card style={styles.row}>
          <View style={styles.iconCircle}>
            <Ionicons name="location-outline" size={22} color={colors.primary} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.nombre}>{item.nombre}</Text>
            {item.ubicacion ? <Text style={styles.linea}>{item.ubicacion}</Text> : null}
            {item.descripcion ? <Text style={styles.descripcion}>{item.descripcion}</Text> : null}
            {item.contacto ? (
              <View style={styles.contactoRow}>
                <Ionicons name="call-outline" size={14} color={colors.textSecondary} />
                <Text style={styles.contacto}>{item.contacto}</Text>
              </View>
            ) : null}
          </View>
        </Card>
      )}
      ListEmptyComponent={<EmptyState icon="location-outline" title="Sin puntos de comercialización" subtitle="Todavía no hay puntos registrados por el administrador." />}
    />
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  iconCircle: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.background, alignItems: 'center', justifyContent: 'center', marginRight: spacing.md },
  nombre: { ...typography.label, textTransform: 'none', fontSize: 16 },
  linea: { ...typography.subtitle, fontSize: 13, marginTop: 2 },
  descripcion: { ...typography.body, fontSize: 14, marginTop: 4, color: colors.textSecondary },
  contactoRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 6 },
  contacto: { fontSize: 13, color: colors.textSecondary },
});
