// screens/comprador/PublicacionDetalleScreen.js
import React, { useEffect, useState } from 'react';
import { ScrollView, Text } from 'react-native';
import { colors, spacing, typography } from '../../theme/theme';
import { Card, LoadingView, IconRow, Badge } from '../../components/ui';
import { detallePublicacion } from '../../services/marketService';

export default function PublicacionDetalleScreen({ route }) {
  const { id } = route.params;
  const [p, setP] = useState(null);

  useEffect(() => {
    detallePublicacion(id).then(setP).catch(() => {});
  }, [id]);

  if (!p) return <LoadingView label="Cargando publicación..." />;

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.background }} contentContainerStyle={{ padding: spacing.lg }}>
      <Card>
        <Text style={styles.title}>{p.cantidad_toneladas} toneladas de fruto de palma</Text>
        <Badge text={p.estado} tone="success" />
        <IconRow icon="location-outline" label="Municipio" value={p.municipio} />
        <IconRow icon="calendar-outline" label="Publicado" value={p.fecha_publicacion ? new Date(p.fecha_publicacion).toLocaleDateString('es-CO') : '—'} />
      </Card>
      {p.descripcion ? (
        <Card>
          <Text style={styles.descripcion}>{p.descripcion}</Text>
        </Card>
      ) : null}
      <Text style={styles.privacidad}>
        Por privacidad, la ubicación exacta de la finca no se comparte en el mercado. Coordina el transporte con el palmicultor a través de la plataforma.
      </Text>
    </ScrollView>
  );
}

const styles = {
  title: { ...typography.label, textTransform: 'none', fontSize: 19, marginBottom: spacing.sm },
  descripcion: { ...typography.body },
  privacidad: { ...typography.subtitle, fontSize: 12, marginTop: spacing.md, textAlign: 'center' },
};
