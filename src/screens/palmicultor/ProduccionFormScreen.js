// screens/palmicultor/ProduccionFormScreen.js
// Formulario de censo de producción — muestra del 4-5% (RN04). Funciona sin
// conexión: si falla el envío, el registro se guarda en el dispositivo y se
// sincroniza automáticamente más adelante (offlineSync).

import React, { useEffect, useState } from 'react';
import { ScrollView, Text, Alert } from 'react-native';
import { colors, spacing, typography } from '../../theme/theme';
import { Field, PrimaryButton, FormPicker } from '../../components/ui';
import { listarTodosLosLotes, obtenerLote } from '../../services/fincasService';
import { crearRegistroProduccion } from '../../services/produccionService';

export default function ProduccionFormScreen({ navigation, route }) {
  const loteIdParam = route.params?.loteId;
  const [lotes, setLotes] = useState([]);
  const [loteId, setLoteId] = useState(loteIdParam || null);
  const [loteSeleccionado, setLoteSeleccionado] = useState(null);

  const [palmasEvaluadas, setPalmasEvaluadas] = useState('');
  const [palmasImproductivas, setPalmasImproductivas] = useState('');
  const [racimosTotales, setRacimosTotales] = useState('');
  const [pesoPromedio, setPesoPromedio] = useState('');
  const [frutoSuelto, setFrutoSuelto] = useState('');
  const [observaciones, setObservaciones] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!loteIdParam) {
      listarTodosLosLotes().then(setLotes).catch(() => setLotes([]));
    } else {
      obtenerLote(loteIdParam).then(setLoteSeleccionado).catch(() => {});
    }
  }, [loteIdParam]);

  const porcentajeMuestra =
    loteSeleccionado?.numero_palmas && palmasEvaluadas
      ? ((Number(palmasEvaluadas) / loteSeleccionado.numero_palmas) * 100).toFixed(1)
      : null;

  const submit = async () => {
    if (!loteId) {
      setError('Selecciona el lote que vas a censar.');
      return;
    }
    if (!palmasEvaluadas || Number(palmasEvaluadas) <= 0) {
      setError('Ingresa cuántas palmas evaluaste en la muestra.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await crearRegistroProduccion({
        lote_id: loteId,
        palmas_evaluadas: Number(palmasEvaluadas),
        palmas_improductivas: Number(palmasImproductivas || 0),
        racimos_totales: Number(racimosTotales || 0),
        peso_promedio_racimo: pesoPromedio ? Number(pesoPromedio) : null,
        fruto_suelto: frutoSuelto ? Number(frutoSuelto) : null,
        observaciones: observaciones.trim(),
      });
      Alert.alert('Censo guardado', 'El registro de producción se guardó correctamente.', [
        { text: 'Listo', onPress: () => navigation.goBack() },
      ]);
    } catch (err) {
      // Offline: el service ya encoló el registro; avisamos y volvemos.
      Alert.alert('Guardado localmente', err?.message || 'Se sincronizará cuando haya conexión.', [
        { text: 'Entendido', onPress: () => navigation.goBack() },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.background }} contentContainerStyle={{ padding: spacing.lg }}>
      {!loteIdParam && (
        <FormPicker
          label="Lote"
          value={loteId}
          onSelect={(v) => {
            setLoteId(v);
            setLoteSeleccionado(lotes.find((l) => l.id === v));
          }}
          options={lotes.map((l) => ({ value: l.id, label: l.codigo }))}
        />
      )}

      <Text style={styles.hint}>
        Recomendado: censa entre el 4% y el 5% de las palmas del lote{loteSeleccionado?.numero_palmas ? ` (${loteSeleccionado.numero_palmas} palmas totales)` : ''}.
      </Text>

      <Field label="Palmas evaluadas en la muestra" keyboardType="numeric" value={palmasEvaluadas} onChangeText={setPalmasEvaluadas} error={error} />
      {porcentajeMuestra ? <Text style={styles.porcentaje}>Eso equivale al {porcentajeMuestra}% del lote.</Text> : null}

      <Field label="Palmas improductivas en la muestra" keyboardType="numeric" value={palmasImproductivas} onChangeText={setPalmasImproductivas} />
      <Field label="Racimos contados (muestra)" keyboardType="numeric" value={racimosTotales} onChangeText={setRacimosTotales} />
      <Field label="Peso promedio histórico del racimo (kg)" keyboardType="numeric" value={pesoPromedio} onChangeText={setPesoPromedio} />
      <Field label="Fruto suelto (kg, opcional)" keyboardType="numeric" value={frutoSuelto} onChangeText={setFrutoSuelto} />
      <Field label="Observaciones" value={observaciones} onChangeText={setObservaciones} multiline />

      <PrimaryButton title="Guardar censo" onPress={submit} loading={loading} />
    </ScrollView>
  );
}

const styles = {
  hint: { ...typography.subtitle, fontSize: 13, marginBottom: spacing.md },
  porcentaje: { ...typography.subtitle, fontSize: 13, marginTop: -12, marginBottom: spacing.md, color: colors.primary },
};
