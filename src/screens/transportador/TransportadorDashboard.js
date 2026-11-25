// screens/transportador/TransportadorDashboard.js
import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity, Switch } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography, radius } from '../../theme/theme';
import { getStoredUser } from '../../services/authService';
import { perfilTransportador, actualizarPerfilTransportador, listarSolicitudes } from '../../services/logisticsService';

export default function TransportadorDashboard({ navigation }) {
  const [usuario, setUsuario] = useState(null);
  const [perfil, setPerfil] = useState(null);
  const [pendientesCount, setPendientesCount] = useState(0);
  const [activasCount, setActivasCount] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [u, p] = await Promise.all([getStoredUser(), perfilTransportador().catch(() => null)]);
    setUsuario(u);
    setPerfil(p);
    if (p?.estado === 'aprobado') {
      const [pendientes, activas] = await Promise.all([
        listarSolicitudes({ pendientes: 'true' }).catch(() => []),
        listarSolicitudes({ estado: 'Aceptada' }).catch(() => []),
      ]);
      setPendientesCount(pendientes.length);
      setActivasCount(activas.length);
    }
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

  const toggleDisponible = async (valor) => {
    setPerfil((p) => ({ ...p, disponible: valor }));
    await actualizarPerfilTransportador({ disponible: valor }).catch(() => {});
  };

  const pendienteValidacion = perfil?.estado !== 'aprobado';

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <View style={styles.headerRow}>
        <Text style={styles.greeting}>¡Hola, {usuario?.nombre_completo?.split(' ')[0] || 'Transportador'}!</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Perfil')} hitSlop={12}>
          <Ionicons name="person-circle-outline" size={30} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {pendienteValidacion ? (
        <View style={styles.warningCard}>
          <Ionicons name="time-outline" size={22} color={colors.accentOrange} />
          <Text style={styles.warningText}>
            Tu perfil está pendiente de validación por un administrador. Podrás aceptar solicitudes cuando sea aprobado.
          </Text>
        </View>
      ) : (
        <View style={styles.availCard}>
          <View>
            <Text style={styles.availLabel}>DISPONIBLE PARA VIAJES</Text>
            <Text style={styles.availSub}>{perfil?.disponible ? 'Recibiendo solicitudes' : 'No disponible'}</Text>
          </View>
          <Switch value={!!perfil?.disponible} onValueChange={toggleDisponible} trackColor={{ true: colors.primaryLight }} thumbColor={colors.primary} />
        </View>
      )}

      <View style={styles.gridRow}>
        <ShortcutCard icon="notifications-outline" title="Solicitudes pendientes" subtitle={`${pendientesCount} disponibles`} onPress={() => navigation.navigate('SolicitudesPendientes')} disabled={pendienteValidacion} />
        <ShortcutCard icon="navigate-outline" title="Mis viajes activos" subtitle={`${activasCount} en curso`} onPress={() => navigation.navigate('MisSolicitudes')} disabled={pendienteValidacion} />
      </View>
      <View style={styles.gridRow}>
        <ShortcutCard icon="car-outline" title="Mis vehículos" onPress={() => navigation.navigate('Vehiculos')} />
        <ShortcutCard icon="time-outline" title="Historial" onPress={() => navigation.navigate('HistorialDespachosTransportador')} />
      </View>
      <ShortcutCard icon="trail-sign-outline" title="Estado de vías" onPress={() => navigation.navigate('EstadoVias')} wide />
    </ScrollView>
  );
}

function ShortcutCard({ icon, title, subtitle, onPress, wide, disabled }) {
  return (
    <TouchableOpacity
      style={[styles.shortcutCard, wide && { width: '100%' }, disabled && { opacity: 0.5 }]}
      onPress={disabled ? undefined : onPress}
      activeOpacity={0.85}
      disabled={disabled}
    >
      <Ionicons name={icon} size={26} color={colors.primary} />
      <Text style={styles.shortcutTitle}>{title}</Text>
      {subtitle ? <Text style={styles.shortcutSubtitle}>{subtitle}</Text> : null}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg },
  greeting: { ...typography.h1 },
  warningCard: {
    flexDirection: 'row', alignItems: 'center', gap: spacing.sm, backgroundColor: '#FBEAD9',
    borderRadius: radius.md, padding: spacing.md, marginBottom: spacing.xl,
  },
  warningText: { flex: 1, color: colors.accentEarth, fontSize: 14 },
  availCard: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.primary,
    borderRadius: radius.lg, padding: spacing.lg, marginBottom: spacing.xl,
  },
  availLabel: { color: colors.white, opacity: 0.8, fontWeight: '700', fontSize: 12, letterSpacing: 0.5 },
  availSub: { color: colors.white, fontSize: 17, fontWeight: '700', marginTop: 2 },
  gridRow: { flexDirection: 'row', gap: spacing.md, marginBottom: spacing.md },
  shortcutCard: { flex: 1, backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md, minHeight: 90 },
  shortcutTitle: { fontWeight: '700', fontSize: 15, color: colors.textPrimary, marginTop: spacing.sm },
  shortcutSubtitle: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },
});
