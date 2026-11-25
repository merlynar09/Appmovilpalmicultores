// AsyncStorage no funciona con su módulo nativo real bajo Jest — se usa el
// mock oficial que la propia librería distribuye para pruebas.
jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);
