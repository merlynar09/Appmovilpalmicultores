// screens/admin/AdminContenidoSmsUssdScreen.js
// CU17: admin edita los textos de menú/ayuda de SMS/USSD. Cambia de inmediato
// (sin reiniciar el backend) y se puede restaurar al texto original en
// cualquier momento.

import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, PrimaryButton, Field, Badge, LoadingView } from '../../components/ui';
import { listarContenidoSmsUssd, editarContenidoSmsUssd, restaurarContenidoSmsUssd } from '../../services/adminService';

const CLAVE_LABEL = {
  ussd_menu_principal: 'Menú principal (USSD)',
  ussd_ayuda: 'Ayuda (USSD)',
  sms_ayuda: 'Ayuda (SMS)',
};

export default function AdminContenidoSmsUssdScreen() {
  const [items, setItems] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [textos, setTextos] = useState({});
  const [guardandoClave, setGuardandoClave] = useState(null);

  const load = useCallback(async () => {
    const data = await listarContenidoSmsUssd().catch(() => []);
    setItems(data);
    setTextos(Object.fromEntries(data.map((i) => [i.clave, i.texto])));
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

  const guardar = async (clave) => {
    setGuardandoClave(clave);
    try {
      await editarContenidoSmsUssd(clave, textos[clave]);
      await load();
    } catch (err) {
      Alert.alert('No se pudo guardar', err?.message || 'Intenta de nuevo.');
    } finally {
      setGuardandoClave(null);
    }
  };

  const restaurar = (clave) => {
    Alert.alert('Restaurar texto original', '¿Descartar la personalización y volver al texto por defecto?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Restaurar',
        style: 'destructive',
        onPress: async () => {
          setGuardandoClave(clave);
          try {
            await restaurarContenidoSmsUssd(clave);
            await load();
          } finally {
            setGuardandoClave(null);
          }
        },
      },
    ]);
  };

  if (!items) return <LoadingView label="Cargando contenido..." />;

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
    >
      {items.map((item) => (
        <Card key={item.clave}>
          <View style={styles.header}>
            <Text style={styles.titulo}>{CLAVE_LABEL[item.clave] || item.clave}</Text>
            {item.personalizado ? <Badge text="Personalizado" tone="primary" /> : <Badge text="Por defecto" tone="neutral" />}
          </View>
          <Field
            value={textos[item.clave] ?? ''}
            onChangeText={(v) => setTextos((t) => ({ ...t, [item.clave]: v }))}
            multiline
            containerStyle={{ marginBottom: spacing.sm }}
          />
          <View style={{ flexDirection: 'row', gap: spacing.sm }}>
            <PrimaryButton
              title="Guardar"
              onPress={() => guardar(item.clave)}
              loading={guardandoClave === item.clave}
              style={{ flex: 1, minHeight: 44 }}
            />
            {item.personalizado && (
              <PrimaryButton
                title="Restaurar"
                variant="secondary"
                onPress={() => restaurar(item.clave)}
                loading={guardandoClave === item.clave}
                style={{ flex: 1, minHeight: 44 }}
              />
            )}
          </View>
        </Card>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm },
  titulo: { ...typography.label, textTransform: 'none', fontSize: 15 },
});
