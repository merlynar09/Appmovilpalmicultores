// App.js
import 'react-native-gesture-handler';
import React, { useEffect, useRef, useState } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer, createNavigationContainerRef } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import ForgotPasswordScreen from './src/screens/ForgotPasswordScreen';

import PalmicultorDashboard from './src/screens/PalmicultorDashboard';
import FincasListScreen from './src/screens/palmicultor/FincasListScreen';
import FincaFormScreen from './src/screens/palmicultor/FincaFormScreen';
import FincaDetailScreen from './src/screens/palmicultor/FincaDetailScreen';
import LoteFormScreen from './src/screens/palmicultor/LoteFormScreen';
import LoteDetailScreen from './src/screens/palmicultor/LoteDetailScreen';
import CicloFormScreen from './src/screens/palmicultor/CicloFormScreen';
import ProduccionFormScreen from './src/screens/palmicultor/ProduccionFormScreen';
import ProduccionHistoryScreen from './src/screens/palmicultor/ProduccionHistoryScreen';
import PronosticosScreen from './src/screens/palmicultor/PronosticosScreen';
import PronosticoDetailScreen from './src/screens/palmicultor/PronosticoDetailScreen';
import AlertasScreen from './src/screens/palmicultor/AlertasScreen';
import PublicarProductoScreen from './src/screens/palmicultor/PublicarProductoScreen';
import MisPublicacionesScreen from './src/screens/palmicultor/MisPublicacionesScreen';
import TransporteRequestScreen from './src/screens/palmicultor/TransporteRequestScreen';
import HistorialDespachosScreen from './src/screens/palmicultor/HistorialDespachosScreen';
import BalanceIndustrialScreen from './src/screens/palmicultor/BalanceIndustrialScreen';
import SmsSimuladorScreen from './src/screens/palmicultor/SmsSimuladorScreen';
import CompradoresListScreen from './src/screens/palmicultor/CompradoresListScreen';
import CompradorDetalleScreen from './src/screens/palmicultor/CompradorDetalleScreen';

import CompradorDashboard from './src/screens/comprador/CompradorDashboard';
import MercadoVitrinaScreen from './src/screens/comprador/MercadoVitrinaScreen';
import PublicacionDetalleScreen from './src/screens/comprador/PublicacionDetalleScreen';
import MisPreciosScreen from './src/screens/comprador/MisPreciosScreen';

import TransportadorDashboard from './src/screens/transportador/TransportadorDashboard';
import SolicitudesPendientesScreen from './src/screens/transportador/SolicitudesPendientesScreen';
import MisSolicitudesScreen from './src/screens/transportador/MisSolicitudesScreen';
import VehiculosScreen from './src/screens/transportador/VehiculosScreen';
import HistorialTransportadorScreen from './src/screens/transportador/HistorialTransportadorScreen';

import AdminDashboard from './src/screens/admin/AdminDashboard';
import AdminUsuariosScreen from './src/screens/admin/AdminUsuariosScreen';
import AdminTransportadoresScreen from './src/screens/admin/AdminTransportadoresScreen';
import AdminReportesScreen from './src/screens/admin/AdminReportesScreen';

import EstadoViasScreen from './src/screens/common/EstadoViasScreen';
import PerfilScreen from './src/screens/common/PerfilScreen';
import RutaMapScreen from './src/screens/common/RutaMapScreen';

import { colors } from './src/theme/theme';
import { getStoredUser } from './src/services/authService';
import { sincronizarTodo } from './src/services/offlineSync';
import { initNotifications, addNotificationTapListener } from './src/services/notificationsService';

const Stack = createNativeStackNavigator();
const navigationRef = createNavigationContainerRef();

const DASHBOARD_BY_ROLE = {
  palmicultor: 'PalmicultorDashboard',
  comprador: 'CompradorDashboard',
  transportador: 'TransportadorDashboard',
  administrador: 'AdminDashboard',
};

export default function App() {
  const [initialRoute, setInitialRoute] = useState(null);

  useEffect(() => {
    (async () => {
      const usuario = await getStoredUser().catch(() => null);
      setInitialRoute(usuario ? DASHBOARD_BY_ROLE[usuario.rol] || 'Login' : 'Login');
      // Intenta vaciar las colas offline (censos y registros pendientes) al abrir la app.
      sincronizarTodo().catch(() => {});
    })();

    initNotifications();
    const sub = addNotificationTapListener((data) => {
      if (data?.enlace && navigationRef.isReady()) {
        navigationRef.navigate(data.enlace);
      }
    });
    return () => sub.remove();
  }, []);

  if (!initialRoute) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.background }}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigationRef}>
      <StatusBar style="dark" />
      <Stack.Navigator
        initialRouteName={initialRoute}
        screenOptions={{
          headerStyle: { backgroundColor: colors.background },
          headerTintColor: colors.primary,
          headerShadowVisible: false,
          headerTitleStyle: { fontWeight: '700' },
        }}
      >
        {/* --- Autenticación --- */}
        <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
        <Stack.Screen name="Register" component={RegisterScreen} options={{ headerShown: false }} />
        <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} options={{ headerShown: false }} />

        {/* --- Palmicultor --- */}
        <Stack.Screen name="PalmicultorDashboard" component={PalmicultorDashboard} options={{ headerShown: false }} />
        <Stack.Screen name="Fincas" component={FincasListScreen} options={{ title: 'Mis fincas' }} />
        <Stack.Screen name="FincaForm" component={FincaFormScreen} options={{ title: 'Finca' }} />
        <Stack.Screen name="FincaDetail" component={FincaDetailScreen} options={{ title: 'Finca' }} />
        <Stack.Screen name="LoteForm" component={LoteFormScreen} options={{ title: 'Lote' }} />
        <Stack.Screen name="LoteDetail" component={LoteDetailScreen} options={{ title: 'Lote' }} />
        <Stack.Screen name="CicloForm" component={CicloFormScreen} options={{ title: 'Ciclo de cosecha' }} />
        <Stack.Screen name="ProduccionForm" component={ProduccionFormScreen} options={{ title: 'Censo de producción' }} />
        <Stack.Screen name="Produccion" component={ProduccionHistoryScreen} options={{ title: 'Producción' }} />
        <Stack.Screen name="Pronosticos" component={PronosticosScreen} options={{ title: 'Pronósticos' }} />
        <Stack.Screen name="PronosticoDetail" component={PronosticoDetailScreen} options={{ title: 'Detalle del pronóstico' }} />
        <Stack.Screen name="Alertas" component={AlertasScreen} options={{ title: 'Alertas de cosecha' }} />
        <Stack.Screen name="PublicarProducto" component={PublicarProductoScreen} options={{ title: 'Publicar mi producto' }} />
        <Stack.Screen name="MisPublicaciones" component={MisPublicacionesScreen} options={{ title: 'Mis publicaciones' }} />
        <Stack.Screen name="Transporte" component={TransporteRequestScreen} options={{ title: 'Solicitar transporte' }} />
        <Stack.Screen name="HistorialDespachos" component={HistorialDespachosScreen} options={{ title: 'Historial de despachos' }} />
        <Stack.Screen name="BalanceIndustrial" component={BalanceIndustrialScreen} options={{ title: 'Balance industrial' }} />
        <Stack.Screen name="SmsSimulador" component={SmsSimuladorScreen} options={{ title: 'Simulador SMS/USSD' }} />
        <Stack.Screen name="Compradores" component={CompradoresListScreen} options={{ title: 'Compradores en tu zona' }} />
        <Stack.Screen name="CompradorDetalle" component={CompradorDetalleScreen} options={{ title: 'Comprador' }} />

        {/* --- Comprador --- */}
        <Stack.Screen name="CompradorDashboard" component={CompradorDashboard} options={{ headerShown: false }} />
        <Stack.Screen name="MercadoVitrina" component={MercadoVitrinaScreen} options={{ title: 'Cosechas disponibles' }} />
        <Stack.Screen name="PublicacionDetalle" component={PublicacionDetalleScreen} options={{ title: 'Publicación' }} />
        <Stack.Screen name="MisPrecios" component={MisPreciosScreen} options={{ title: 'Mi precio' }} />

        {/* --- Transportador --- */}
        <Stack.Screen name="TransportadorDashboard" component={TransportadorDashboard} options={{ headerShown: false }} />
        <Stack.Screen name="SolicitudesPendientes" component={SolicitudesPendientesScreen} options={{ title: 'Solicitudes pendientes' }} />
        <Stack.Screen name="MisSolicitudes" component={MisSolicitudesScreen} options={{ title: 'Mis viajes activos' }} />
        <Stack.Screen name="Vehiculos" component={VehiculosScreen} options={{ title: 'Mis vehículos' }} />
        <Stack.Screen name="HistorialDespachosTransportador" component={HistorialTransportadorScreen} options={{ title: 'Historial' }} />

        {/* --- Administrador --- */}
        <Stack.Screen name="AdminDashboard" component={AdminDashboard} options={{ headerShown: false }} />
        <Stack.Screen name="AdminUsuarios" component={AdminUsuariosScreen} options={{ title: 'Usuarios' }} />
        <Stack.Screen name="AdminTransportadores" component={AdminTransportadoresScreen} options={{ title: 'Transportadores' }} />
        <Stack.Screen name="AdminReportes" component={AdminReportesScreen} options={{ title: 'Reportes' }} />

        {/* --- Compartidas --- */}
        <Stack.Screen name="EstadoVias" component={EstadoViasScreen} options={{ title: 'Estado de vías' }} />
        <Stack.Screen name="Perfil" component={PerfilScreen} options={{ title: 'Mi perfil' }} />
        <Stack.Screen name="RutaMap" component={RutaMapScreen} options={{ title: 'Mapa de la ruta' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
