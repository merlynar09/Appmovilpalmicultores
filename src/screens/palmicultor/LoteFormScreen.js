// screens/palmicultor/LoteFormScreen.js
// Crear/editar lote. RN02: el código admite cualquier nomenclatura
// (programa de siembra, bloque, sector o plano cartesiano) — no hay regex rígida.

import React, { useEffect, useState } from 'react';
import { ScrollView, Alert, Text } from 'react-native';
import { colors, spacing, typography } from '../../theme/theme';
import { Field, PrimaryButton } from '../../components/ui';
import { crearLote, editarLote, obtenerLote } from '../../services/fincasService';

export default function LoteFormScreen({ navigation, route }) {
  const { fincaId, loteId } = route.params || {};
  const [codigo, setCodigo] = useState('');
  const [nombre, setNombre] = useState('');
  const [areaHectareas, setAreaHectareas] = useState('');
  const [numeroPalmas, setNumeroPalmas] = useState('');
  const [anioSiembra, setAnioSiembra] = useState('');
  const [materialSembrado, setMaterialSembrado] = useState('');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [fincaIdEfectivo, setFincaIdEfectivo] = useState(fincaId);

  useEffect(() => {
    if (loteId) {
      obtenerLote(loteId).then((l) => {
        setCodigo(l.codigo || '');
        setNombre(l.nombre || '');
        setAreaHectareas(l.area_hectareas ? String(l.area_hectareas) : '');
        setNumeroPalmas(l.numero_palmas ? String(l.numero_palmas) : '');
        setAnioSiembra(l.anio_siembra ? String(l.anio_siembra) : '');
        setMaterialSembrado(l.material_sembrado || '');
        setFincaIdEfectivo(l.finca_id);
      });
    }
  }, [loteId]);

  const submit = async () => {
    if (!codigo.trim()) {
      setErrors({ codigo: 'El código del lote es obligatorio.' });
      return;
    }
    setErrors({});
    setLoading(true);
    const payload = {
      codigo: codigo.trim(),
      nombre: nombre.trim(),
      area_hectareas: areaHectareas ? Number(areaHectareas) : null,
      numero_palmas: numeroPalmas ? Number(numeroPalmas) : null,
      anio_siembra: anioSiembra ? Number(anioSiembra) : null,
      material_sembrado: materialSembrado.trim(),
    };
    try {
      if (loteId) {
        await editarLote(loteId, payload);
      } else {
        await crearLote(fincaIdEfectivo, payload);
      }
      navigation.goBack();
    } catch (err) {
      Alert.alert('No se pudo guardar', err?.message || 'Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.background }} contentContainerStyle={{ padding: spacing.lg }}>
      <Text style={styles.hint}>
        El código puede ser el que ya uses en campo: por programa de siembra, bloque, sector o plano cartesiano (ej. &quot;A1&quot;, &quot;Bloque-3&quot;, &quot;Plano-B7&quot;).
      </Text>
      <Field label="Código del lote" placeholder="Lote-A1" value={codigo} onChangeText={setCodigo} error={errors.codigo} />
      <Field label="Nombre / referencia" placeholder="Sector norte" value={nombre} onChangeText={setNombre} />
      <Field label="Número de palmas totales" keyboardType="numeric" value={numeroPalmas} onChangeText={setNumeroPalmas} />
      <Field label="Área (hectáreas)" keyboardType="numeric" value={areaHectareas} onChangeText={setAreaHectareas} />
      <Field label="Año de siembra" keyboardType="numeric" value={anioSiembra} onChangeText={setAnioSiembra} />
      <Field label="Material sembrado" placeholder="Híbrido OxG" value={materialSembrado} onChangeText={setMaterialSembrado} />
      <PrimaryButton title={loteId ? 'Guardar cambios' : 'Registrar lote'} onPress={submit} loading={loading} />
    </ScrollView>
  );
}

const styles = {
  hint: { ...typography.subtitle, fontSize: 13, marginBottom: spacing.lg },
};
