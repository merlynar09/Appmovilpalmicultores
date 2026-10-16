// screens/palmicultor/MisPublicacionesScreen.js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, PrimaryButton, EmptyState, Badge } from '../../components/ui';
import { misPublicaciones, cambiarEstadoPublicacion } from '../../services/marketService';

const ESTADO_TONE = { activa: 'success', vendida: 'primary', cancelada: 'danger' };

export default function MisPublicacionesScreen({ navigation }) {
  const [publicaciones, setPublicaciones] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const data = await misPublicaciones().catch(() => []);
    setPublicaciones(data);
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

  const cambiarEstado = (id, estado) => {
    Alert.alert('Confirmar', `¿Marcar esta publicación como "${estado}"?`, [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Confirmar', onPress: async () => { await cambiarEstadoPublicacion(id, estado); await load(); } },
    ]);
  };

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      data={publicaciones || []}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      ListHeaderComponent={
        <PrimaryButton
          title="Publicar nuevo producto"
          icon="add-circle-outline"
          onPress={() => navigation.navigate('PublicarProducto')}
          style={{ marginBottom: spacing.lg }}
        />
      }
      renderItem={({ item }) => (
        <Card>
          <View style={styles.rowHeader}>
            <Text style={styles.cantidad}>{item.cantidad_toneladas} ton</Text>
            <Badge text={item.estado} tone={ESTADO_TONE[item.estado] || 'neutral'} />
          </View>
          <Text style={styles.linea}>{item.municipio}</Text>
          {item.descripcion ? <Text style={styles.linea}>{item.descripcion}</Text> : null}
          {item.estado === 'activa' && (
            <View style={styles.actionsRow}>
              <PrimaryButton title="Vendida" variant="secondary" onPress={() => cambiarEstado(item.id, 'vendida')} style={{ flex: 1 }} />
              <PrimaryButton title="Cancelar" variant="danger" onPress={() => cambiarEstado(item.id, 'cancelada')} style={{ flex: 1 }} />
            </View>
          )}
        </Card>
      )}
      ListEmptyComponent={<EmptyState icon="storefront-outline" title="Sin publicaciones" subtitle="Publica tu cosecha para que los compradores la vean." />}
    />
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  rowHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cantidad: { ...typography.label, textTransform: 'none', fontSize: 17 },
  linea: { ...typography.subtitle, fontSize: 13, marginTop: 4 },
  actionsRow: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md },
});
