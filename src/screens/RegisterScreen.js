// screens/RegisterScreen.js
// Pantalla de Registro — alto contraste, campos grandes, selección de rol.
// Roles soportados en el registro público: Palmicultor, Comprador y
// Transportador. El Transportador queda "pendiente" hasta que un
// administrador lo valide (ver AdminTransportadoresScreen). El rol
// Administrador no se autorregistra, se gestiona aparte.

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, typography, radius, MIN_TOUCH_TARGET } from '../theme/theme';
import { registerUser } from '../services/authService';

const ROLES = [
  { key: 'palmicultor', label: 'Palmicultor', icon: 'leaf-outline' },
  { key: 'comprador', label: 'Comprador', icon: 'basket-outline' },
  { key: 'transportador', label: 'Transportador', icon: 'car-outline' },
];

export default function RegisterScreen({ navigation }) {
  const [nombreCompleto, setNombreCompleto] = useState('');
  const [telefono, setTelefono] = useState('');
  const [ubicacion, setUbicacion] = useState('');
  const [password, setPassword] = useState('');
  const [rol, setRol] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const validate = () => {
    const e = {};
    if (!nombreCompleto.trim()) e.nombreCompleto = 'Ingresa tu nombre completo';
    if (!telefono.trim()) {
      e.telefono = 'Ingresa tu teléfono';
    } else if (!/^\+?\d{7,15}$/.test(telefono.replace(/\s/g, ''))) {
      e.telefono = 'Formato de teléfono inválido';
    }
    if (!ubicacion.trim()) e.ubicacion = 'Ingresa tu ubicación';
    if (!rol) e.rol = 'Selecciona tu rol';
    if (!password || password.length < 6) e.password = 'Mínimo 6 caracteres';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      await registerUser({
        nombre_completo: nombreCompleto.trim(),
        telefono: telefono.trim(),
        ubicacion: ubicacion.trim(),
        password,
        rol,
      });
      Alert.alert('¡Cuenta creada!', 'Tu cuenta se creó correctamente.', [
        { text: 'Continuar', onPress: () => navigation.replace('Login') },
      ]);
    } catch (err) {
      Alert.alert(
        'No se pudo crear la cuenta',
        err?.message || 'Verifica tu conexión e inténtalo de nuevo. Tus datos quedaron guardados localmente.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.background }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>¡Hola, Cultivador!</Text>
            <Text style={styles.subtitle}>
              Estamos listos para empezar. Cuéntanos quién eres.
            </Text>
          </View>
          <View style={styles.avatarCircle}>
            <Ionicons name="person" size={26} color={colors.white} />
          </View>
        </View>

        <Field
          label="NOMBRE COMPLETO"
          placeholder="Ej. Juan Pérez"
          value={nombreCompleto}
          onChangeText={setNombreCompleto}
          error={errors.nombreCompleto}
        />

        <Field
          label="TELÉFONO DE CONTACTO"
          placeholder="+57 300 000 0000"
          value={telefono}
          onChangeText={setTelefono}
          keyboardType="phone-pad"
          error={errors.telefono}
        />

        <Field
          label="UBICACIÓN"
          placeholder="Tumaco, Nariño..."
          value={ubicacion}
          onChangeText={setUbicacion}
          icon="location-outline"
          error={errors.ubicacion}
        />

        <Text style={styles.label}>¿CUÁL ES TU ROL?</Text>
        <View style={styles.roleRow}>
          {ROLES.map((r) => {
            const selected = rol === r.key;
            return (
              <TouchableOpacity
                key={r.key}
                style={[styles.roleCard, selected && styles.roleCardSelected]}
                onPress={() => setRol(r.key)}
                activeOpacity={0.8}
              >
                <Ionicons
                  name={r.icon}
                  size={24}
                  color={selected ? colors.white : colors.primary}
                />
                <Text style={[styles.roleLabel, selected && { color: colors.white }]}>
                  {r.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
        {errors.rol ? <Text style={styles.errorText}>{errors.rol}</Text> : null}

        <Text style={styles.label}>CONTRASEÑA</Text>
        <View style={styles.passwordRow}>
          <TextInput
            style={styles.passwordInput}
            placeholder="••••••••"
            placeholderTextColor={colors.placeholder}
            secureTextEntry={!showPassword}
            value={password}
            onChangeText={setPassword}
          />
          <TouchableOpacity onPress={() => setShowPassword((s) => !s)} hitSlop={10}>
            <Ionicons
              name={showPassword ? 'eye-off-outline' : 'eye-outline'}
              size={24}
              color={colors.textSecondary}
            />
          </TouchableOpacity>
        </View>
        {errors.password ? <Text style={styles.errorText}>{errors.password}</Text> : null}

        <TouchableOpacity
          style={styles.submitButton}
          onPress={handleSubmit}
          disabled={loading}
          activeOpacity={0.85}
        >
          {loading ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={typography.button}>Crear mi cuenta</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.loginLink}
          onPress={() => navigation.navigate('Login')}
        >
          <Text style={styles.loginLinkText}>
            ¿Ya tienes una cuenta? <Text style={styles.loginLinkBold}>Inicia sesión aquí</Text>
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Field({ label, error, icon, ...inputProps }) {
  return (
    <View style={{ marginBottom: spacing.lg }}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.inputWrapper}>
        {icon ? (
          <Ionicons name={icon} size={20} color={colors.textSecondary} style={{ marginRight: 8 }} />
        ) : null}
        <TextInput
          style={styles.input}
          placeholderTextColor={colors.placeholder}
          {...inputProps}
        />
      </View>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: spacing.lg,
    paddingTop: spacing.xl,
    paddingBottom: spacing.xl * 2,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: spacing.xl,
  },
  title: { ...typography.h1 },
  subtitle: { ...typography.subtitle, marginTop: 4 },
  avatarCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: spacing.md,
  },
  label: { ...typography.label, marginBottom: spacing.sm, textTransform: 'uppercase' },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    minHeight: MIN_TOUCH_TARGET,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  input: { flex: 1, ...typography.body, paddingVertical: spacing.md },
  roleRow: { flexDirection: 'row', gap: spacing.md, marginBottom: spacing.sm },
  roleCard: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xs,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
    minHeight: MIN_TOUCH_TARGET + 20,
  },
  roleCardSelected: {
    backgroundColor: colors.primary,
    borderColor: colors.primaryDark,
  },
  roleLabel: { ...typography.label, marginTop: spacing.sm, textTransform: 'none', fontSize: 13, textAlign: 'center' },
  passwordRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    minHeight: MIN_TOUCH_TARGET,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    marginBottom: spacing.xs,
  },
  passwordInput: { flex: 1, ...typography.body, paddingVertical: spacing.md },
  submitButton: {
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    minHeight: MIN_TOUCH_TARGET,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing.lg,
  },
  loginLink: { marginTop: spacing.lg, alignItems: 'center' },
  loginLinkText: { ...typography.subtitle },
  loginLinkBold: { color: colors.primary, fontWeight: '700' },
  errorText: { color: colors.danger, marginTop: 4, fontSize: 14 },
});
