/**
 * Minimal ESLint config. We deliberately don't pull in @typescript-eslint to
 * keep the buildable-starter dependency surface tight — users can add it
 * themselves. The config registers .ts files so `eslint . --ext .ts` doesn't
 * complain about the absence of a parser; it just won't lint TS deeply.
 */
module.exports = {
  root: true,
  env: {
    node: true,
    es2022: true,
    jest: true,
  },
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
  },
  ignorePatterns: ['dist/', 'node_modules/', 'coverage/'],
  rules: {},
};
