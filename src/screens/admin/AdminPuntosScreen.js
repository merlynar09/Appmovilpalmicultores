// screens/admin/AdminPuntosScreen.js
// CU14: admin gestiona puntos de comercialización.

import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, FlatList, RefreshControl, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, PrimaryButton, EmptyState, Badge, Field } from '../../components/ui';
import { listarPuntosAdmin, crearPunto, editarPunto, cambiarEstadoPunto } from '../../services/puntosService';

const FORM_VACIO = { nombre: '', descripcion: '', ubicacion: '', contacto: '' };

export default function AdminPuntosScreen() {
  const [puntos, setPuntos] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [editandoId, setEditandoId] = useState(null); // null = cerrado, 'nuevo' = creando
  const [form, setForm] = useState(FORM_VACIO);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const data = await listarPuntosAdmin().catch(() => []);
    setPuntos(data);
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

  const iniciarCreacion = () => {
    setEditandoId('nuevo');
    setForm(FORM_VACIO);
    setError('');
  };

  const iniciarEdicion = (p) => {
    setEditandoId(p.id);
    setForm({ nombre: p.nombre || '', descripcion: p.descripcion || '', ubicacion: p.ubicacion || '', contacto: p.contacto || '' });
    setError('');
  };

  const guardar = async () => {
    if (!form.nombre.trim()) {
      setError('El nombre es obligatorio.');
      return;
    }
    setGuardando(true);
    setError('');
    try {
      if (editandoId === 'nuevo') {
        await crearPunto(form);
      } else {
        await editarPunto(editandoId, form);
      }
      setEditandoId(null);
      await load();
    } catch (err) {
      setError(err?.message || 'No se pudo guardar.');
    } finally {
      setGuardando(false);
    }
  };

  const toggleEstado = (p) => {
    const nuevo = p.estado === 'activo' ? 'inactivo' : 'activo';
    Alert.alert('Confirmar', `¿${nuevo === 'activo' ? 'Activar' : 'Desactivar'} "${p.nombre}"?`, [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Confirmar', onPress: async () => { await cambiarEstadoPunto(p.id, nuevo); await load(); } },
    ]);
  };

  return (
    <FlatList
      style={{ flex: 1, backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      data={puntos || []}
      keyExtractor={(item) => String(item.id)}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      ListHeaderComponent={
        <>
          {editandoId !== 'nuevo' && (
            <PrimaryButton title="Nuevo punto de comercialización" icon="add-circle-outline" onPress={iniciarCreacion} style={{ marginBottom: spacing.lg }} />
          )}
          {editandoId === 'nuevo' && (
            <Card>
              <Field label="Nombre" value={form.nombre} onChangeText={(v) => setForm((f) => ({ ...f, nombre: v }))} error={error} />
              <Field label="Ubicación" value={form.ubicacion} onChangeText={(v) => setForm((f) => ({ ...f, ubicacion: v }))} />
              <Field label="Contacto" value={form.contacto} onChangeText={(v) => setForm((f) => ({ ...f, contacto: v }))} />
              <Field label="Descripción" value={form.descripcion} onChangeText={(v) => setForm((f) => ({ ...f, descripcion: v }))} multiline />
              <View style={{ flexDirection: 'row', gap: spacing.sm }}>
                <PrimaryButton title="Cancelar" variant="secondary" onPress={() => setEditandoId(null)} style={{ flex: 1 }} />
                <PrimaryButton title="Guardar" onPress={guardar} loading={guardando} style={{ flex: 1 }} />
              </View>
            </Card>
          )}
        </>
      }
      renderItem={({ item }) => (
        <Card>
          <View style={styles.rowHeader}>
            <Text style={styles.nombre}>{item.nombre}</Text>
            <Badge text={item.estado} tone={item.estado === 'activo' ? 'success' : 'danger'} />
          </View>
          {item.ubicacion ? <Text style={styles.linea}>{item.ubicacion}</Text> : null}
          {item.descripcion ? <Text style={styles.descripcion}>{item.descripcion}</Text> : null}

          {editandoId === item.id ? (
            <View style={{ marginTop: spacing.md }}>
              <Field label="Nombre" value={form.nombre} onChangeText={(v) => setForm((f) => ({ ...f, nombre: v }))} error={error} />
              <Field label="Ubicación" value={form.ubicacion} onChangeText={(v) => setForm((f) => ({ ...f, ubicacion: v }))} />
              <Field label="Contacto" value={form.contacto} onChangeText={(v) => setForm((f) => ({ ...f, contacto: v }))} />
              <Field label="Descripción" value={form.descripcion} onChangeText={(v) => setForm((f) => ({ ...f, descripcion: v }))} multiline />
              <View style={{ flexDirection: 'row', gap: spacing.sm }}>
                <PrimaryButton title="Cancelar" variant="secondary" onPress={() => setEditandoId(null)} style={{ flex: 1 }} />
                <PrimaryButton title="Guardar" onPress={guardar} loading={guardando} style={{ flex: 1 }} />
              </View>
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
      ListEmptyComponent={<EmptyState icon="location-outline" title="Sin puntos de comercialización" />}
    />
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  rowHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  nombre: { ...typography.label, textTransform: 'none', fontSize: 16, flexShrink: 1 },
  linea: { ...typography.subtitle, fontSize: 13, marginTop: 4 },
  descripcion: { ...typography.body, fontSize: 14, marginTop: 4, color: colors.textSecondary },
});
