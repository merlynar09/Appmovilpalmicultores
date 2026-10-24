// screens/common/PerfilScreen.js
// Perfil básico compartido por los 4 roles + cierre de sesión.

import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, typography, radius } from '../../theme/theme';
import { PrimaryButton, Card, Badge, Field } from '../../components/ui';
import { getStoredUser, logoutUser, actualizarPerfil } from '../../services/authService';

const ROL_LABEL = {
  palmicultor: 'Palmicultor',
  comprador: 'Comprador',
  transportador: 'Transportador',
  administrador: 'Administrador',
};

export default function PerfilScreen({ navigation }) {
  const [usuario, setUsuario] = useState(null);
  const [editando, setEditando] = useState(false);
  const [nombre, setNombre] = useState('');
  const [telefono, setTelefono] = useState('');
  const [correo, setCorreo] = useState('');
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    getStoredUser().then(setUsuario);
  }, []);

  const iniciarEdicion = () => {
    setNombre(usuario?.nombre_completo || '');
    setTelefono(usuario?.telefono || '');
    setCorreo(usuario?.correo || '');
    setError('');
    setEditando(true);
  };

  const guardar = async () => {
    if (!nombre.trim() || !telefono.trim()) {
      setError('Nombre y teléfono son obligatorios.');
      return;
    }
    setError('');
    setGuardando(true);
    try {
      const actualizado = await actualizarPerfil({
        nombre_completo: nombre.trim(),
        telefono: telefono.trim(),
        correo: correo.trim(),
      });
      setUsuario(actualizado);
      setEditando(false);
    } catch (err) {
      setError(err?.message || 'No se pudo guardar. Intenta de nuevo.');
    } finally {
      setGuardando(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Cerrar sesión', '¿Seguro que deseas salir?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Salir',
        style: 'destructive',
        onPress: async () => {
          await logoutUser();
          navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
        },
      },
    ]);
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.background }} contentContainerStyle={styles.container}>
      <View style={styles.avatar}>
        <Ionicons name="person" size={36} color={colors.white} />
      </View>
      <Text style={styles.name}>{usuario?.nombre_completo || '—'}</Text>
      <Badge text={ROL_LABEL[usuario?.rol] || usuario?.rol || ''} tone="primary" />

      {editando ? (
        <Card style={{ marginTop: spacing.xl, width: '100%' }}>
          <Field label="Nombre completo" value={nombre} onChangeText={setNombre} />
          <Field label="Teléfono" value={telefono} onChangeText={setTelefono} keyboardType="phone-pad" />
          <Field label="Correo" value={correo} onChangeText={setCorreo} keyboardType="email-address" autoCapitalize="none" error={error} />
          <View style={{ flexDirection: 'row', gap: spacing.sm, marginTop: spacing.sm }}>
            <PrimaryButton title="Cancelar" variant="secondary" onPress={() => setEditando(false)} style={{ flex: 1 }} />
            <PrimaryButton title="Guardar" onPress={guardar} loading={guardando} style={{ flex: 1 }} />
          </View>
        </Card>
      ) : (
        <>
          <Card style={{ marginTop: spacing.xl, width: '100%' }}>
            <Row icon="call-outline" label="Teléfono" value={usuario?.telefono} />
            <Row icon="mail-outline" label="Correo" value={usuario?.correo || 'No registrado'} />
            <Row icon="checkmark-circle-outline" label="Estado" value={usuario?.estado} />
          </Card>
          <PrimaryButton title="Editar perfil" variant="secondary" icon="create-outline" onPress={iniciarEdicion} style={{ marginTop: spacing.lg, width: '100%' }} />
        </>
      )}

      <PrimaryButton title="Cerrar sesión" variant="danger" icon="log-out-outline" onPress={handleLogout} style={{ marginTop: spacing.lg, width: '100%' }} />
    </ScrollView>
  );
}

function Row({ icon, label, value }) {
  return (
    <View style={styles.row}>
      <Ionicons name={icon} size={18} color={colors.textSecondary} style={{ marginRight: 8 }} />
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue} numberOfLines={1}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingTop: spacing.xl, alignItems: 'center' },
  avatar: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  name: { ...typography.h1, fontSize: 24, marginBottom: spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8 },
  rowLabel: { ...typography.subtitle, width: 90 },
  rowValue: { ...typography.body, fontWeight: '600', flex: 1 },
});
