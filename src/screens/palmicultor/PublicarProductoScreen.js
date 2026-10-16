// screens/palmicultor/PublicarProductoScreen.js
// RN01: la publicación solo expone cantidad, unidad, municipio, descripción
// y fecha — nunca ubicación exacta de la finca. El precio NO lo pone el
// palmicultor: cada comprador fija su propio precio (ver "Compradores en tu
// zona") y el palmicultor decide a quién vender según esos precios.

import React, { useEffect, useState } from 'react';
import { ScrollView, Text, Alert } from 'react-native';
import { colors, spacing, typography } from '../../theme/theme';
import { Field, PrimaryButton, FormPicker } from '../../components/ui';
import { listarTodosLosLotes } from '../../services/fincasService';
import { publicarProducto } from '../../services/marketService';

export default function PublicarProductoScreen({ navigation }) {
  const [lotes, setLotes] = useState([]);
  const [loteId, setLoteId] = useState(null);
  const [cantidad, setCantidad] = useState('');
  const [municipio, setMunicipio] = useState('Tumaco');
  const [descripcion, setDescripcion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    listarTodosLosLotes().then(setLotes).catch(() => setLotes([]));
  }, []);

  const submit = async () => {
    if (!cantidad || Number(cantidad) <= 0) {
      setError('Indica la cantidad en toneladas.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await publicarProducto({
        lote_id: loteId,
        cantidad_toneladas: Number(cantidad),
        municipio,
        descripcion: descripcion.trim(),
      });
      Alert.alert('¡Publicado!', 'Tu producto ya está visible para los compradores.', [
        { text: 'Ver mis publicaciones', onPress: () => navigation.replace('MisPublicaciones') },
      ]);
    } catch (err) {
      Alert.alert('No se pudo publicar', err?.message || 'Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.background }} contentContainerStyle={{ padding: spacing.lg }}>
      <Text style={styles.hint}>
        Solo se mostrará al comprador la cantidad, el municipio y la descripción — nunca la ubicación exacta de tu finca. El precio no se define aquí: revisa el precio vigente de cada comprador en "Compradores en tu zona" y decide a quién venderle.
      </Text>

      {lotes.length > 0 && (
        <FormPicker
          label="Lote de origen (opcional)"
          value={loteId}
          onSelect={setLoteId}
          options={lotes.map((l) => ({ value: l.id, label: l.codigo }))}
        />
      )}

      <Field label="Cantidad (toneladas)" keyboardType="numeric" value={cantidad} onChangeText={setCantidad} error={error} />
      <Field label="Municipio" value={municipio} onChangeText={setMunicipio} />
      <Field label="Descripción" placeholder="Fruto fresco, cosecha reciente..." value={descripcion} onChangeText={setDescripcion} multiline />

      <PrimaryButton title="Publicar producto" onPress={submit} loading={loading} />
    </ScrollView>
  );
}

const styles = {
  hint: { ...typography.subtitle, fontSize: 13, marginBottom: spacing.lg },
};
