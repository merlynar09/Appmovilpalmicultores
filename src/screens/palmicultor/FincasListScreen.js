// screens/palmicultor/FincasListScreen.js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, PrimaryButton, EmptyState, LoadingView } from '../../components/ui';
import { listarFincas } from '../../services/fincasService';

export default function FincasListScreen({ navigation }) {
  const [fincas, setFincas] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const data = await listarFincas().catch(() => []);
    setFincas(data);
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

  if (fincas === null) return <LoadingView label="Cargando tus fincas..." />;

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      data={fincas}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      ListHeaderComponent={
        <PrimaryButton
          title="Registrar nueva finca"
          icon="add-circle-outline"
          onPress={() => navigation.navigate('FincaForm')}
          style={{ marginBottom: spacing.lg }}
        />
      }
      renderItem={({ item }) => (
        <TouchableOpacity onPress={() => navigation.navigate('FincaDetail', { fincaId: item.id })} activeOpacity={0.85}>
          <Card style={styles.row}>
            <View style={styles.iconCircle}>
              <Ionicons name="leaf-outline" size={22} color={colors.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.nombre}>{item.nombre}</Text>
              <Text style={styles.sub}>{item.municipio}{item.vereda ? `, ${item.vereda}` : ''}</Text>
              <Text style={styles.sub}>{item.total_lotes ?? '—'} lotes · {item.area_hectareas || '—'} ha</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} />
          </Card>
        </TouchableOpacity>
      )}
      ListEmptyComponent={
        <EmptyState icon="leaf-outline" title="Aún no tienes fincas" subtitle="Registra tu primera finca para empezar a llevar el control de tus lotes." />
      }
    />
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  row: { flexDirection: 'row', alignItems: 'center' },
  iconCircle: {
    width: 44, height: 44, borderRadius: 22, backgroundColor: colors.background,
    alignItems: 'center', justifyContent: 'center', marginRight: spacing.md,
  },
  nombre: { ...typography.label, textTransform: 'none', fontSize: 17 },
  sub: { ...typography.subtitle, fontSize: 13, marginTop: 2 },
});
