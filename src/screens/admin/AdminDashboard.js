// screens/admin/AdminDashboard.js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography, radius } from '../../theme/theme';
import { getStoredUser } from '../../services/authService';
import { reportesGenerales, transportadoresPendientes } from '../../services/adminService';

export default function AdminDashboard({ navigation }) {
  const [usuario, setUsuario] = useState(null);
  const [reportes, setReportes] = useState(null);
  const [pendientes, setPendientes] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [u, r, p] = await Promise.all([
      getStoredUser(),
      reportesGenerales().catch(() => null),
      transportadoresPendientes().catch(() => []),
    ]);
    setUsuario(u);
    setReportes(r);
    setPendientes(p.length);
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
        <Text style={styles.greeting}>¡Hola, {usuario?.nombre_completo?.split(' ')[0] || 'Administrador'}!</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Perfil')} hitSlop={12}>
          <Ionicons name="person-circle-outline" size={30} color={colors.primary} />
        </TouchableOpacity>
      </View>

      <View style={styles.statsRow}>
        <StatCard label="Usuarios" value={reportes?.usuarios?.total ?? '—'} icon="people-outline" />
        <StatCard label="Fincas activas" value={reportes?.produccion?.total_fincas ?? '—'} icon="leaf-outline" />
      </View>
      <View style={styles.statsRow}>
        <StatCard label="Publicaciones activas" value={reportes?.mercado?.publicaciones_activas ?? '—'} icon="storefront-outline" />
        <StatCard label="Ton. publicadas" value={reportes?.mercado?.toneladas_publicadas?.toFixed?.(1) ?? '—'} icon="cube-outline" />
      </View>

      <TouchableOpacity onPress={() => navigation.navigate('AdminTransportadores')} activeOpacity={0.85}>
        <View style={styles.pendingCard}>
          <Ionicons name="car-outline" size={22} color={colors.white} />
          <Text style={styles.pendingText}>{pendientes} transportador(es) pendiente(s) de validar</Text>
          <Ionicons name="chevron-forward" size={20} color={colors.white} />
        </View>
      </TouchableOpacity>

      <View style={styles.gridRow}>
        <ShortcutCard icon="people-outline" title="Usuarios" onPress={() => navigation.navigate('AdminUsuarios')} />
        <ShortcutCard icon="bar-chart-outline" title="Reportes" onPress={() => navigation.navigate('AdminReportes')} />
      </View>
      <View style={styles.gridRow}>
        <ShortcutCard icon="business-outline" title="Compradores" onPress={() => navigation.navigate('AdminCompradores')} />
        <ShortcutCard icon="location-outline" title="Puntos de comercialización" onPress={() => navigation.navigate('AdminPuntos')} />
      </View>
      <ShortcutCard icon="trail-sign-outline" title="Estado de vías" onPress={() => navigation.navigate('EstadoVias')} wide />
      <ShortcutCard icon="chatbubble-ellipses-outline" title="Contenido SMS/USSD" onPress={() => navigation.navigate('AdminContenidoSmsUssd')} wide />
    </ScrollView>
  );
}

function StatCard({ label, value, icon }) {
  return (
    <View style={styles.statCard}>
      <Ionicons name={icon} size={20} color={colors.primary} />
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function ShortcutCard({ icon, title, onPress, wide }) {
  return (
    <TouchableOpacity style={[styles.shortcutCard, wide && { width: '100%' }]} onPress={onPress} activeOpacity={0.85}>
      <Ionicons name={icon} size={26} color={colors.primary} />
      <Text style={styles.shortcutTitle}>{title}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg },
  greeting: { ...typography.h1 },
  statsRow: { flexDirection: 'row', gap: spacing.md, marginBottom: spacing.md },
  statCard: { flex: 1, backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md },
  statValue: { fontSize: 24, fontWeight: '800', color: colors.textPrimary, marginTop: spacing.sm },
  statLabel: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  pendingCard: {
    flexDirection: 'row', alignItems: 'center', gap: spacing.sm, backgroundColor: colors.accentOrange,
    borderRadius: radius.md, padding: spacing.md, marginVertical: spacing.lg,
  },
  pendingText: { flex: 1, color: colors.white, fontWeight: '700' },
  gridRow: { flexDirection: 'row', gap: spacing.md, marginBottom: spacing.md },
  shortcutCard: { flex: 1, backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md, minHeight: 90 },
  shortcutTitle: { fontWeight: '700', fontSize: 15, color: colors.textPrimary, marginTop: spacing.sm },
});
