// screens/comprador/MercadoVitrinaScreen.js
// Vitrina pública (RN01): solo cantidad, unidad, municipio, descripción y
// fecha. Nunca ubicación exacta ni datos privados de producción. El precio
// no está aquí: lo fija cada comprador (pantalla "Mi Precio"), no la
// publicación del palmicultor.

import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, Field, PrimaryButton, EmptyState } from '../../components/ui';
import { vitrinaPublica } from '../../services/marketService';

export default function MercadoVitrinaScreen({ navigation }) {
  const [publicaciones, setPublicaciones] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [municipio, setMunicipio] = useState('');

  const load = useCallback(async (filtroMunicipio) => {
    const data = await vitrinaPublica({ municipio: filtroMunicipio }).catch(() => []);
    setPublicaciones(data);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(municipio);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await load(municipio);
    setRefreshing(false);
  };

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      data={publicaciones || []}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      ListHeaderComponent={
        <View style={styles.filterRow}>
          <View style={{ flex: 1 }}>
            <Field placeholder="Filtrar por municipio" value={municipio} onChangeText={setMunicipio} icon="location-outline" />
          </View>
          <PrimaryButton title="Buscar" onPress={() => load(municipio)} style={styles.searchButton} />
        </View>
      }
      renderItem={({ item }) => (
        <TouchableOpacity onPress={() => navigation.navigate('PublicacionDetalle', { id: item.id })} activeOpacity={0.85}>
          <Card style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.cantidad}>{item.cantidad_toneladas} ton</Text>
              <Text style={styles.municipio}>{item.municipio}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} />
          </Card>
        </TouchableOpacity>
      )}
      ListEmptyComponent={<EmptyState icon="storefront-outline" title="Sin cosechas publicadas" subtitle="Vuelve pronto o ajusta el filtro de municipio." />}
    />
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  filterRow: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start', marginBottom: spacing.md },
  searchButton: { minHeight: 56, paddingHorizontal: spacing.lg },
  row: { flexDirection: 'row', alignItems: 'center' },
  cantidad: { ...typography.label, textTransform: 'none', fontSize: 17 },
  municipio: { ...typography.subtitle, fontSize: 13, marginTop: 2 },
});
