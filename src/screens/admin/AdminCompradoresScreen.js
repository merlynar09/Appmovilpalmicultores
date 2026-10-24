// screens/admin/AdminCompradoresScreen.js
// CU13: admin gestiona compradores. CU12 ampliado: el admin también puede
// publicar/editar el precio de cualquier comprador (el comprador sigue
// pudiendo hacerlo por su cuenta en "Mi precio" — esto no se lo quita).

import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, PrimaryButton, EmptyState, Badge, Field } from '../../components/ui';
import {
  listarCompradoresAdmin,
  editarCompradorAdmin,
  cambiarEstadoCompradorAdmin,
  publicarPrecioAdmin,
} from '../../services/adminService';

export default function AdminCompradoresScreen() {
  const [compradores, setCompradores] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [editandoId, setEditandoId] = useState(null);
  const [form, setForm] = useState({});
  const [nuevoPrecio, setNuevoPrecio] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const data = await listarCompradoresAdmin().catch(() => []);
    setCompradores(data);
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

  const iniciarEdicion = (c) => {
    setEditandoId(c.id);
    setForm({ empresa: c.empresa || '', descripcion: c.descripcion || '', telefono: c.telefono || '', correo: c.correo || '', ubicacion: c.ubicacion || '' });
    setNuevoPrecio('');
    setError('');
  };

  const guardarDatos = async (id) => {
    if (!form.empresa.trim()) {
      setError('La empresa es obligatoria.');
      return;
    }
    setGuardando(true);
    setError('');
    try {
      await editarCompradorAdmin(id, form);
      setEditandoId(null);
      await load();
    } catch (err) {
      setError(err?.message || 'No se pudo guardar.');
    } finally {
      setGuardando(false);
    }
  };

  const publicarPrecio = async (id) => {
    const valor = Number(nuevoPrecio);
    if (!valor || valor <= 0) {
      setError('Ingresa un precio válido.');
      return;
    }
    setGuardando(true);
    setError('');
    try {
      await publicarPrecioAdmin(id, { valor_moneda: valor });
      setNuevoPrecio('');
      await load();
    } catch (err) {
      setError(err?.message || 'No se pudo publicar el precio.');
    } finally {
      setGuardando(false);
    }
  };

  const toggleEstado = (c) => {
    const nuevo = c.estado === 'activo' ? 'inactivo' : 'activo';
    Alert.alert('Confirmar', `¿${nuevo === 'activo' ? 'Activar' : 'Desactivar'} a ${c.empresa}?`, [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Confirmar', onPress: async () => { await cambiarEstadoCompradorAdmin(c.id, nuevo); await load(); } },
    ]);
  };

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      data={compradores || []}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      renderItem={({ item }) => (
        <Card>
          <View style={styles.rowHeader}>
            <View style={{ flex: 1 }}>
              <Text style={styles.nombre}>{item.empresa}</Text>
              <Text style={styles.linea}>{item.nombre_usuario} · {item.telefono || 'sin teléfono'}</Text>
              <Text style={styles.linea}>
                {item.precio_vigente ? `Precio: $${Number(item.precio_vigente).toLocaleString('es-CO')} / ${item.precio_unidad}` : 'Sin precio publicado'}
              </Text>
            </View>
            <Badge text={item.estado} tone={item.estado === 'activo' ? 'success' : 'danger'} />
          </View>

          {editandoId === item.id ? (
            <View style={{ marginTop: spacing.md }}>
              <Field label="Empresa" value={form.empresa} onChangeText={(v) => setForm((f) => ({ ...f, empresa: v }))} />
              <Field label="Descripción" value={form.descripcion} onChangeText={(v) => setForm((f) => ({ ...f, descripcion: v }))} multiline />
              <Field label="Teléfono" value={form.telefono} onChangeText={(v) => setForm((f) => ({ ...f, telefono: v }))} keyboardType="phone-pad" />
              <Field label="Correo" value={form.correo} onChangeText={(v) => setForm((f) => ({ ...f, correo: v }))} autoCapitalize="none" />
              <Field label="Ubicación" value={form.ubicacion} onChangeText={(v) => setForm((f) => ({ ...f, ubicacion: v }))} />

              <Field label="Publicar nuevo precio ($/tonelada)" value={nuevoPrecio} onChangeText={setNuevoPrecio} keyboardType="numeric" error={error} />

              <View style={{ flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.sm }}>
                <PrimaryButton title="Cancelar" variant="secondary" onPress={() => setEditandoId(null)} style={{ flex: 1 }} />
                <PrimaryButton title="Guardar datos" onPress={() => guardarDatos(item.id)} loading={guardando} style={{ flex: 1 }} />
              </View>
              <PrimaryButton title="Publicar precio" icon="pricetag-outline" onPress={() => publicarPrecio(item.id)} loading={guardando} />
            </View>
          ) : (
            <View style={{ flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md }}>
              <PrimaryButton title="Editar" variant="secondary" onPress={() => iniciarEdicion(item)} style={{ flex: 1, minHeight: 40 }} />
              <PrimaryButton
                title={item.estado === 'activo' ? 'Desactivar' : 'Activar'}
                variant={item.estado === 'activo' ? 'danger' : 'secondary'}
                onPress={() => toggleEstado(item)}
                style={{ flex: 1, minHeight: 40 }}
              />
            </View>
          )}
        </Card>
      )}
      ListEmptyComponent={<EmptyState icon="business-outline" title="Sin compradores" />}
    />
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  rowHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  nombre: { ...typography.label, textTransform: 'none', fontSize: 15 },
  linea: { ...typography.subtitle, fontSize: 12, marginTop: 2 },
});
