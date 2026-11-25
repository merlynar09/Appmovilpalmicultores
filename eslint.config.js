// DEV-F3-03 / MOD-08: antes no existía ningún lint configurado en el frontend.
const expoConfig = require("eslint-config-expo/flat");

module.exports = [
  {
    // Antes que cualquier otra cosa: nunca lintear el backend (Python) ni
    // ningún entorno virtual/empaquetado (venv, node_modules) — son código
    // de terceros o de otro lenguaje, no del frontend.
    ignores: [
      "android/**",
      ".expo/**",
      "node_modules/**",
      "backend/**",
      ".venv/**",
      "venv/**",
    ],
  },
  ...expoConfig,
  {
    // `eslint-config-expo` (SDK 58) activó esta regla nueva de
    // react-hooks como error. Señala el patrón "cargar datos al montar la
    // pantalla llamando una función dentro de useEffect" — el estándar en
    // toda la app (ver PalmicultorDashboard.js, EstadoViasScreen.js,
    // TransporteRequestScreen.js) y no un bug real. Se deja como aviso en
    // vez de bloquear el lint por un patrón ya usado en todo el proyecto.
    rules: {
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  {
    files: ["**/__tests__/**/*.js", "jest.setup.js"],
    languageOptions: {
      globals: {
        jest: "readonly",
        describe: "readonly",
        it: "readonly",
        test: "readonly",
        expect: "readonly",
        beforeEach: "readonly",
        afterEach: "readonly",
        beforeAll: "readonly",
        afterAll: "readonly",
      },
    },
  },
];
