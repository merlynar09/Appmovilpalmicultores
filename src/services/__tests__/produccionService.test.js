// DEV-F3-03 / MOD-08: igual que authService, cubre la cola offline del censo
// de producción — error de red se encola, error real del servidor no.
import AsyncStorage from '@react-native-async-storage/async-storage';

jest.mock('../../config/api', () => ({ apiRequest: jest.fn() }));

const { apiRequest } = require('../../config/api');
const { crearRegistroProduccion, contarPendientes, sincronizarPendientes } = require('../produccionService');

const QUEUE_KEY = '@queue_produccion';

beforeEach(async () => {
  jest.clearAllMocks();
  await AsyncStorage.clear();
});

describe('crearRegistroProduccion', () => {
  it('encola el censo cuando es un error de red real', async () => {
    const error = new Error('fetch failed');
    error.isNetworkError = true;
    apiRequest.mockRejectedValueOnce(error);

    await expect(crearRegistroProduccion({ lote_id: 1, palmas_evaluadas: 10 })).rejects.toThrow(/Sin conexión/);

    expect(await contarPendientes()).toBe(1);
  });

  it('NO encola cuando el servidor rechazó la solicitud por un motivo real', async () => {
    const error = new Error('El lote indicado no existe o no te pertenece.');
    error.isNetworkError = false;
    apiRequest.mockRejectedValueOnce(error);

    await expect(crearRegistroProduccion({ lote_id: 999 })).rejects.toThrow(
      'El lote indicado no existe o no te pertenece.'
    );
    expect(await contarPendientes()).toBe(0);
  });
});

describe('sincronizarPendientes', () => {
  it('limpia la cola local únicamente de los items que el backend confirmó', async () => {
    await AsyncStorage.setItem(
      QUEUE_KEY,
      JSON.stringify([
        { lote_id: 1, _local_id: 'a' },
        { lote_id: 1, _local_id: 'b' },
      ])
    );
    apiRequest.mockResolvedValueOnce({
      resultados: [
        { _local_id: 'a', ok: true, id: 10 },
        { _local_id: 'b', ok: false, message: 'inválido' },
      ],
    });

    const resultado = await sincronizarPendientes();

    expect(resultado.enviados).toBe(1);
    expect(resultado.pendientes).toBe(1);
    const restante = JSON.parse(await AsyncStorage.getItem(QUEUE_KEY));
    expect(restante).toHaveLength(1);
    expect(restante[0]._local_id).toBe('b');
  });
});
