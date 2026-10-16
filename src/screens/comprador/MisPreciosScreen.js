// screens/comprador/MisPreciosScreen.js
// El precio SIEMPRE lo fija el comprador — el palmicultor nunca pone precio
// en sus publicaciones, solo revisa el precio vigente de cada comprador
// (aquí) y decide a quién venderle.

import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, Field, PrimaryButton, EmptyState, Badge } from '../../components/ui';
import { misPrecios, publicarPrecio } from '../../services/marketService';

export default function MisPreciosScreen() {
  const [precios, setPrecios] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [valor, setValor] = useState('');
  const [unidad, setUnidad] = useState('Tonelada');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const data = await misPrecios().catch(() => []);
    setPrecios(data);
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

  const precioActivo = (precios || []).find((p) => p.estado === 'activo');

  const submit = () => {
    if (!valor || Number(valor) <= 0) {
      setError('Ingresa el valor del precio.');
      return;
    }
    setError('');
    Alert.alert(
      'Actualizar precio',
      precioActivo
        ? `Esto reemplaza tu precio actual de $${Number(precioActivo.valor_moneda).toLocaleString('es-CO')} / ${precioActivo.unidad}. ¿Continuar?`
        : '¿Publicar este precio?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Confirmar',
          onPress: async () => {
            setLoading(true);
            try {
              await publicarPrecio({ valor_moneda: Number(valor), unidad });
              setValor('');
              await load();
            } catch (err) {
              Alert.alert('No se pudo publicar', err?.message || 'Intenta de nuevo.');
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      data={(precios || []).filter((p) => p.estado !== 'activo')}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      ListHeaderComponent={
        <>
          <Card style={styles.heroCard}>
            <Text style={styles.heroLabel}>TU PRECIO VIGENTE</Text>
            <Text style={styles.heroValue}>
              {precioActivo ? `$${Number(precioActivo.valor_moneda).toLocaleString('es-CO')}` : 'Sin definir'}
            </Text>
            <Text style={styles.heroSub}>{precioActivo ? `por ${precioActivo.unidad}` : 'Publica un precio para que los palmicultores lo vean'}</Text>
          </Card>

          <Text style={styles.sectionTitle}>Actualizar precio</Text>
          <Card>
            <Field label="Valor por tonelada (COP)" keyboardType="numeric" value={valor} onChangeText={setValor} error={error} />
            <Field label="Unidad" value={unidad} onChangeText={setUnidad} />
            <PrimaryButton title="Publicar nuevo precio" onPress={submit} loading={loading} />
          </Card>

          <Text style={styles.sectionTitle}>Historial</Text>
        </>
      }
      renderItem={({ item }) => (
        <Card style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text style={styles.valor}>${Number(item.valor_moneda).toLocaleString('es-CO')} / {item.unidad}</Text>
            <Text style={styles.fecha}>{item.fecha_publicacion ? new Date(item.fecha_publicacion).toLocaleDateString('es-CO') : ''}</Text>
          </View>
          <Badge text="Anterior" tone="neutral" />
        </Card>
      )}
      ListEmptyComponent={<EmptyState icon="pricetag-outline" title="Sin historial" subtitle="Tus precios anteriores aparecerán aquí." />}
    />
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  heroCard: { backgroundColor: colors.primary, alignItems: 'center', paddingVertical: spacing.lg, marginBottom: spacing.lg },
  heroLabel: { color: colors.white, opacity: 0.8, fontWeight: '700', fontSize: 12, letterSpacing: 0.5 },
  heroValue: { color: colors.white, fontSize: 30, fontWeight: '800', marginTop: 4 },
  heroSub: { color: colors.white, opacity: 0.85, marginTop: 4, fontSize: 12 },
  sectionTitle: { ...typography.h2, fontSize: 18, marginTop: spacing.lg, marginBottom: spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center' },
  valor: { ...typography.label, textTransform: 'none', fontSize: 15 },
  fecha: { ...typography.subtitle, fontSize: 12, marginTop: 2 },
});
