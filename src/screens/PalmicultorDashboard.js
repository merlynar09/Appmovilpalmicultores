// screens/PalmicultorDashboard.js
// Dashboard del Palmicultor — precio vigente, compradores en la zona,
// logística/transporte y accesos directos de alto contraste.

import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  FlatList,
  RefreshControl,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, typography, radius, MIN_TOUCH_TARGET } from '../theme/theme';
import { getPrecioVigente, getCompradoresCercanos } from '../services/marketService';
import { getEstadoLogistica } from '../services/logisticsService';
import { listarAlertas } from '../services/alertasService';
import { notificarAlertasNuevas } from '../services/notificationsService';

export default function PalmicultorDashboard({ navigation }) {
  const [precio, setPrecio] = useState(null);
  const [compradores, setCompradores] = useState([]);
  const [logistica, setLogistica] = useState(null);
  const [alertasNoLeidas, setAlertasNoLeidas] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [p, c, l] = await Promise.all([
        getPrecioVigente(),
        getCompradoresCercanos(),
        getEstadoLogistica(),
      ]);
      setPrecio(p);
      setCompradores(c);
      setLogistica(l);
    } catch (e) {
      // En modo offline se usan los últimos valores en caché local.
      console.warn('No se pudo actualizar desde el servidor, usando caché local.', e?.message);
    }

    // Revisa alertas de cosecha/logística y dispara notificaciones locales de las nuevas.
    listarAlertas()
      .then((alertas) => {
        setAlertasNoLeidas(alertas.filter((a) => !a.leida).length);
        return notificarAlertasNuevas(alertas);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      <Text style={styles.greeting}>¡Hola, Cultivador!</Text>

      {/* Precio vigente */}
      <View style={styles.priceCard}>
        <Text style={styles.priceLabel}>PRECIO DE MERCADO</Text>
        <Text style={styles.priceValue}>
          {precio ? formatCOP(precio.valor) : '$ ----'}
        </Text>
        <Text style={styles.priceUnit}>
          {precio?.unidad || 'Tonelada de Aceite de Palma'}
        </Text>
        <Text style={styles.priceDate}>
          <Ionicons name="calendar-outline" size={13} /> {precio?.fecha || 'Actualizando...'}
        </Text>
        <TouchableOpacity
          style={styles.publishButton}
          onPress={() => navigation.navigate('PublicarProducto')}
          activeOpacity={0.85}
        >
          <Text style={styles.publishButtonText}>Publicar mi producto</Text>
          <Ionicons name="arrow-forward" size={18} color={colors.white} />
        </TouchableOpacity>
      </View>

      {/* Compradores en la zona */}
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.sectionTitle}>Compradores en tu zona</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Compradores')}>
          <Text style={styles.seeAll}>Ver todos</Text>
        </TouchableOpacity>
      </View>
      <FlatList
        data={compradores}
        horizontal
        showsHorizontalScrollIndicator={false}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={{ gap: spacing.md, paddingRight: spacing.md }}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.buyerCard}
            activeOpacity={0.85}
            onPress={() => navigation.navigate('CompradorDetalle', { id: item.id })}
          >
            <View style={styles.buyerLogo}>
              {item.logoUrl ? (
                <Image source={{ uri: item.logoUrl }} style={styles.buyerLogoImg} />
              ) : (
                <Ionicons name="business-outline" size={22} color={colors.primary} />
              )}
            </View>
            <Text style={styles.buyerName} numberOfLines={1}>{item.nombre}</Text>
            <Text style={styles.buyerDistance}>A {item.distanciaKm} km de distancia</Text>
            {item.verificado ? (
              <View style={styles.verifiedBadge}>
                <Ionicons name="checkmark-circle" size={14} color={colors.success} />
                <Text style={styles.verifiedText}>Verificado</Text>
              </View>
            ) : null}
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <Text style={styles.emptyText}>Cargando compradores cercanos...</Text>
        }
      />

      {/* Logística y transporte */}
      <Text style={styles.sectionTitle}>Logística y Transporte</Text>
      <View style={styles.gridRow}>
        <ShortcutCard
          icon="navigate-outline"
          title="Rutas de Transporte"
          subtitle={`${logistica?.vehiculosDisponibles ?? 0} disponibles hoy`}
          onPress={() => navigation.navigate('Transporte')}
        />
        <ShortcutCard
          icon="alert-circle-outline"
          title="Estado de Vías"
          subtitle={logistica?.estadoVias || 'Sin novedades'}
          onPress={() => navigation.navigate('EstadoVias')}
        />
      </View>
      <ShortcutCard
        icon="time-outline"
        title="Historial de despachos"
        subtitle={logistica?.ultimoDespacho || 'Último hace 2 días'}
        onPress={() => navigation.navigate('HistorialDespachos')}
        wide
      />

      {/* Accesos directos agronómicos */}
      <Text style={styles.sectionTitle}>Mi Finca</Text>
      <View style={styles.gridRow}>
        <ShortcutCard icon="leaf-outline" title="Mis Fincas y Lotes" onPress={() => navigation.navigate('Fincas')} />
        <ShortcutCard icon="bar-chart-outline" title="Producción" onPress={() => navigation.navigate('Produccion')} />
      </View>
      <View style={styles.gridRow}>
        <ShortcutCard icon="trending-up-outline" title="Pronósticos" onPress={() => navigation.navigate('Pronosticos')} />
        <ShortcutCard
          icon="notifications-outline"
          title="Alertas de Cosecha"
          subtitle={alertasNoLeidas > 0 ? `${alertasNoLeidas} nueva(s)` : undefined}
          onPress={() => navigation.navigate('Alertas')}
        />
      </View>

      {/* Mercado */}
      <Text style={styles.sectionTitle}>Mercado</Text>
      <View style={styles.gridRow}>
        <ShortcutCard icon="storefront-outline" title="Mis Publicaciones" onPress={() => navigation.navigate('MisPublicaciones')} />
        <ShortcutCard icon="flask-outline" title="Balance Industrial" onPress={() => navigation.navigate('BalanceIndustrial')} />
      </View>
      <ShortcutCard icon="location-outline" title="Puntos de Comercialización" onPress={() => navigation.navigate('PuntosComercializacion')} wide />

      {/* Herramientas */}
      <Text style={styles.sectionTitle}>Herramientas</Text>
      <View style={styles.gridRow}>
        <ShortcutCard icon="chatbubble-ellipses-outline" title="Simulador SMS/USSD" onPress={() => navigation.navigate('SmsSimulador')} />
        <ShortcutCard icon="person-outline" title="Mi Perfil" onPress={() => navigation.navigate('Perfil')} />
      </View>
    </ScrollView>
  );
}

function ShortcutCard({ icon, title, subtitle, onPress, wide }) {
  return (
    <TouchableOpacity
      style={[styles.shortcutCard, wide && { flex: undefined, width: '100%' }]}
      onPress={onPress}
      activeOpacity={0.85}
    >
      <Ionicons name={icon} size={26} color={colors.primary} />
      <Text style={styles.shortcutTitle}>{title}</Text>
      {subtitle ? <Text style={styles.shortcutSubtitle}>{subtitle}</Text> : null}
    </TouchableOpacity>
  );
}

function formatCOP(value) {
  if (value == null) return '$ ----';
  return '$' + Number(value).toLocaleString('es-CO');
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  greeting: { ...typography.h1, marginBottom: spacing.lg },

  priceCard: {
    backgroundColor: colors.primary,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.xl,
  },
  priceLabel: { color: colors.white, opacity: 0.8, fontWeight: '700', fontSize: 13, letterSpacing: 0.5 },
  priceValue: { color: colors.white, fontSize: 34, fontWeight: '800', marginTop: 4 },
  priceUnit: { color: colors.white, opacity: 0.9, fontSize: 15, marginTop: 2 },
  priceDate: { color: colors.white, opacity: 0.75, fontSize: 13, marginTop: spacing.sm },
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
  publishButtonText: { color: colors.white, fontWeight: '700', fontSize: 17 },

  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  sectionTitle: { ...typography.h2, fontSize: 19, marginTop: spacing.lg, marginBottom: spacing.sm },
  seeAll: { color: colors.primary, fontWeight: '700' },

  buyerCard: {
    width: 170,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  buyerLogo: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
    overflow: 'hidden',
  },
  buyerLogoImg: { width: '100%', height: '100%' },
  buyerName: { fontWeight: '700', fontSize: 15, color: colors.textPrimary },
  buyerDistance: { fontSize: 13, color: colors.textSecondary, marginTop: 2 },
  verifiedBadge: { flexDirection: 'row', alignItems: 'center', marginTop: spacing.sm, gap: 4 },
  verifiedText: { fontSize: 12, color: colors.success, fontWeight: '600' },
  emptyText: { color: colors.textSecondary, paddingVertical: spacing.md },

  gridRow: { flexDirection: 'row', gap: spacing.md, marginBottom: spacing.md },
  shortcutCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    padding: spacing.md,
    minHeight: 90,
  },
  shortcutTitle: { fontWeight: '700', fontSize: 15, color: colors.textPrimary, marginTop: spacing.sm },
  shortcutSubtitle: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },
});
