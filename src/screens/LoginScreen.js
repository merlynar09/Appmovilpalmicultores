// screens/LoginScreen.js
// Pantalla de Inicio de Sesión — alto contraste, campos grandes.

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
import { colors, spacing, typography, radius, MIN_TOUCH_TARGET } from '../theme/theme';
import { loginUser } from '../services/authService';

export default function LoginScreen({ navigation }) {
  const [identifier, setIdentifier] = useState(''); // teléfono o correo
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    if (!identifier.trim() || !password) {
      setError('Ingresa tu teléfono/correo y tu contraseña.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const { rol } = await loginUser({ identifier: identifier.trim(), password, remember });
      if (rol === 'palmicultor') {
        navigation.replace('PalmicultorDashboard');
      } else if (rol === 'comprador') {
        navigation.replace('CompradorDashboard');
      } else if (rol === 'transportador') {
        navigation.replace('TransportadorDashboard');
      } else {
        navigation.replace('AdminDashboard');
      }
    } catch (err) {
      Alert.alert(
        'No pudimos iniciar sesión',
        err?.message || 'Verifica tus datos o tu conexión e inténtalo de nuevo.'
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
        <View style={styles.brandRow}>
          <Text style={styles.brandLeaf}>🌴</Text>
          <Text style={styles.brandName}>Palma Viva</Text>
        </View>

        <Text style={styles.title}>Bienvenido de nuevo</Text>
        <Text style={styles.subtitle}>
          Ingrese sus credenciales para acceder a su panel de control.
        </Text>

        <Text style={styles.label}>TELÉFONO O CORREO</Text>
        <TextInput
          style={styles.input}
          placeholder="nombre@ejemplo.com"
          placeholderTextColor={colors.placeholder}
          autoCapitalize="none"
          keyboardType="email-address"
          value={identifier}
          onChangeText={setIdentifier}
        />

        <View style={styles.passwordHeaderRow}>
          <Text style={styles.label}>CONTRASEÑA</Text>
          <TouchableOpacity onPress={() => navigation.navigate('ForgotPassword')}>
            <Text style={styles.forgotText}>¿Olvidó su contraseña?</Text>
          </TouchableOpacity>
        </View>
        <TextInput
          style={styles.input}
          placeholder="••••••••"
          placeholderTextColor={colors.placeholder}
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />
        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <TouchableOpacity
          style={styles.rememberRow}
          onPress={() => setRemember((r) => !r)}
          activeOpacity={0.7}
        >
          <View style={[styles.checkbox, remember && styles.checkboxChecked]} />
          <Text style={styles.rememberText}>Mantener sesión iniciada</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.submitButton}
          onPress={handleLogin}
          disabled={loading}
          activeOpacity={0.85}
        >
          {loading ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={typography.button}>Iniciar sesión  →</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.registerLink}
          onPress={() => navigation.navigate('Register')}
        >
          <Text style={styles.registerLinkText}>
            ¿No tienes cuenta? <Text style={styles.registerLinkBold}>Regístrate ahora</Text>
          </Text>
        </TouchableOpacity>

        <View style={styles.footer}>
          <Text style={styles.footerText}>© 2026 Palma Viva Colombia</Text>
          <View style={styles.footerLinksRow}>
            <Text style={styles.footerLink}>Términos</Text>
            <Text style={styles.footerDot}> · </Text>
            <Text style={styles.footerLink}>Privacidad</Text>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: spacing.lg,
    paddingTop: spacing.xl,
    paddingBottom: spacing.xl,
  },
  brandRow: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing.xl },
  brandLeaf: { fontSize: 22, marginRight: 8 },
  brandName: { ...typography.h2 },
  title: { ...typography.h1, marginBottom: spacing.xs },
  subtitle: { ...typography.subtitle, marginBottom: spacing.xl },
  label: { ...typography.label, marginBottom: spacing.sm, textTransform: 'uppercase' },
  input: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    minHeight: MIN_TOUCH_TARGET,
    ...typography.body,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    marginBottom: spacing.lg,
  },
  passwordHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  forgotText: { color: colors.primary, fontWeight: '600', fontSize: 14 },
  rememberRow: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing.lg },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: colors.border,
    marginRight: spacing.sm,
  },
  checkboxChecked: { backgroundColor: colors.primary, borderColor: colors.primary },
  rememberText: { ...typography.body, fontSize: 15 },
  submitButton: {
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    minHeight: MIN_TOUCH_TARGET,
    alignItems: 'center',
    justifyContent: 'center',
  },
  registerLink: { marginTop: spacing.lg, alignItems: 'center' },
  registerLinkText: { ...typography.subtitle },
  registerLinkBold: { color: colors.primary, fontWeight: '700' },
  errorText: { color: colors.danger, marginTop: -8, marginBottom: spacing.md, fontSize: 14 },
  footer: { marginTop: spacing.xl * 1.5, alignItems: 'center' },
  footerText: { fontSize: 12, color: colors.textSecondary },
  footerLinksRow: { flexDirection: 'row', marginTop: 4 },
  footerLink: { fontSize: 12, color: colors.primary, fontWeight: '600' },
  footerDot: { fontSize: 12, color: colors.textSecondary },
});
