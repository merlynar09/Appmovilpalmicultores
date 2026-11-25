// DEV-F3-03 / MOD-08: cobertura automatizada de la cola offline de registro —
// antes solo se había verificado a mano que un error de red se encola y uno
// del servidor (ej. teléfono duplicado) se muestra tal cual, sin encolar.
import AsyncStorage from '@react-native-async-storage/async-storage';

jest.mock('../../config/api', () => ({ apiRequest: jest.fn() }));
jest.mock('expo-secure-store', () => ({
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

const { apiRequest } = require('../../config/api');
const { registerUser, syncPendingRegistrations, logoutUser } = require('../authService');

const PENDING_KEY = '@pending_registrations';

beforeEach(async () => {
  jest.clearAllMocks();
  await AsyncStorage.clear();
});

describe('registerUser', () => {
  it('encola el registro cuando es un error de red real', async () => {
    const error = new Error('fetch failed');
    error.isNetworkError = true;
    apiRequest.mockRejectedValueOnce(error);

    const payload = { telefono: '3000000099', nombre_completo: 'Prueba', password: 'clave123' };
    await expect(registerUser(payload)).rejects.toThrow(/No hay conexión/);

    const pendingRaw = await AsyncStorage.getItem(PENDING_KEY);
    const pending = JSON.parse(pendingRaw);
    expect(pending).toHaveLength(1);
    expect(pending[0].telefono).toBe(payload.telefono);
  });

  it('NO encola cuando el servidor respondió con un error real (ej. duplicado)', async () => {
    const error = new Error('Ya existe una cuenta con ese teléfono.');
    error.isNetworkError = false;
    apiRequest.mockRejectedValueOnce(error);

    const payload = { telefono: '3001234567', nombre_completo: 'Prueba', password: 'clave123' };
    await expect(registerUser(payload)).rejects.toThrow('Ya existe una cuenta con ese teléfono.');

    const pendingRaw = await AsyncStorage.getItem(PENDING_KEY);
    expect(pendingRaw).toBeNull();
  });

  it('no encola nada si el registro fue exitoso', async () => {
    apiRequest.mockResolvedValueOnce({ token: 'abc', usuario: { id: 1 } });

    await registerUser({ telefono: '3000000098', nombre_completo: 'Prueba', password: 'clave123' });

    const pendingRaw = await AsyncStorage.getItem(PENDING_KEY);
    expect(pendingRaw).toBeNull();
  });
});

describe('logoutUser', () => {
  it('borra la sesión local aunque la revocación en el backend falle (sin red)', async () => {
    apiRequest.mockRejectedValueOnce(new Error('sin conexión'));
    const SecureStore = require('expo-secure-store');

    await AsyncStorage.setItem('@auth_user', JSON.stringify({ id: 1 }));
    await logoutUser();

    expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('auth_token');
    expect(await AsyncStorage.getItem('@auth_user')).toBeNull();
  });
});

describe('syncPendingRegistrations', () => {
  it('reintenta lo encolado y limpia solo lo que sí se envió', async () => {
    await AsyncStorage.setItem(
      PENDING_KEY,
      JSON.stringify([
        { telefono: '3000000097', nombre_completo: 'A', password: 'clave123', _queuedAt: 'x' },
        { telefono: '3000000096', nombre_completo: 'B', password: 'clave123', _queuedAt: 'x' },
      ])
    );
    apiRequest.mockResolvedValueOnce({}).mockRejectedValueOnce(new Error('aún sin conexión'));

    const resultado = await syncPendingRegistrations();

    expect(resultado.enviados).toBe(1);
    expect(resultado.pendientes).toBe(1);
    const restante = JSON.parse(await AsyncStorage.getItem(PENDING_KEY));
    expect(restante).toHaveLength(1);
    expect(restante[0].telefono).toBe('3000000096');
  });
});
