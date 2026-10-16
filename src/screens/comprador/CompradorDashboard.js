// screens/comprador/CompradorDashboard.js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography, radius, MIN_TOUCH_TARGET } from '../../theme/theme';
import { getStoredUser } from '../../services/authService';
import { misPrecios, vitrinaPublica } from '../../services/marketService';

export default function CompradorDashboard({ navigation }) {
  const [usuario, setUsuario] = useState(null);
  const [precioActivo, setPrecioActivo] = useState(null);
  const [publicaciones, setPublicaciones] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [u, precios, pub] = await Promise.all([
      getStoredUser(),
      misPrecios().catch(() => []),
      vitrinaPublica().catch(() => []),
    ]);
    setUsuario(u);
    setPrecioActivo(precios.find((p) => p.estado === 'activo') || null);
    setPublicaciones(pub.slice(0, 5));
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
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <View style={styles.headerRow}>
        <Text style={styles.greeting}>¡Hola, {usuario?.nombre_completo?.split(' ')[0] || 'Comprador'}!</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Perfil')} hitSlop={12}>
          <Ionicons name="person-circle-outline" size={30} color={colors.primary} />
        </TouchableOpacity>
      </View>

      <View style={styles.priceCard}>
        <Text style={styles.priceLabel}>MI PRECIO VIGENTE</Text>
        <Text style={styles.priceValue}>{precioActivo ? `$${Number(precioActivo.valor_moneda).toLocaleString('es-CO')}` : 'Sin definir'}</Text>
        <Text style={styles.priceUnit}>{precioActivo ? `por ${precioActivo.unidad}` : 'Publica tu precio para que los palmicultores lo vean'}</Text>
        <TouchableOpacity style={styles.publishButton} onPress={() => navigation.navigate('MisPrecios')} activeOpacity={0.85}>
          <Text style={styles.publishButtonText}>{precioActivo ? 'Actualizar precio' : 'Publicar mi precio'}</Text>
          <Ionicons name="arrow-forward" size={18} color={colors.white} />
        </TouchableOpacity>
      </View>

      <TouchableOpacity style={styles.bigButton} onPress={() => navigation.navigate('MercadoVitrina')} activeOpacity={0.85}>
        <Ionicons name="storefront-outline" size={22} color={colors.white} />
        <Text style={styles.bigButtonText}>Explorar cosechas disponibles</Text>
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>Publicaciones recientes</Text>
      {publicaciones.map((p) => (
        <TouchableOpacity key={p.id} onPress={() => navigation.navigate('PublicacionDetalle', { id: p.id })} activeOpacity={0.85}>
          <View style={styles.pubCard}>
            <View style={{ flex: 1 }}>
              <Text style={styles.pubCantidad}>{p.cantidad_toneladas} ton — {p.municipio}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} />
          </View>
        </TouchableOpacity>
      ))}
      {publicaciones.length === 0 ? <Text style={styles.emptyText}>Aún no hay publicaciones activas.</Text> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg },
  greeting: { ...typography.h1 },
  priceCard: { backgroundColor: colors.primary, borderRadius: radius.lg, padding: spacing.lg, marginBottom: spacing.lg },
  priceLabel: { color: colors.white, opacity: 0.8, fontWeight: '700', fontSize: 13, letterSpacing: 0.5 },
  priceValue: { color: colors.white, fontSize: 34, fontWeight: '800', marginTop: 4 },
  priceUnit: { color: colors.white, opacity: 0.9, fontSize: 15, marginTop: 2 },
  publishButton: {
    marginTop: spacing.lg,
    backgroundColor: colors.primaryDark,
    borderRadius: radius.pill,
    minHeight: MIN_TOUCH_TARGET - 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  publishButtonText: { color: colors.white, fontWeight: '700', fontSize: 16 },
  bigButton: {
    backgroundColor: colors.accentOrange, borderRadius: radius.pill, minHeight: MIN_TOUCH_TARGET,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: spacing.xl,
  },
  bigButtonText: { color: colors.white, fontWeight: '700', fontSize: 17 },
  sectionTitle: { ...typography.h2, fontSize: 19, marginBottom: spacing.sm },
  pubCard: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: colors.surface,
    borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.sm,
  },
  pubCantidad: { ...typography.label, textTransform: 'none', fontSize: 15 },
  emptyText: { color: colors.textSecondary, paddingVertical: spacing.md },
});
