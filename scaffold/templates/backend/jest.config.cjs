/**
 * jest.config.cjs — kept as CommonJS so Jest can read it without ts-node.
 * The ts-jest preset handles transpilation of *.spec.ts at run time.
 */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/*.spec.ts', '**/*.test.ts'],
  moduleNameMapper: {
    '^@/config/(.*)$': '<rootDir>/src/config/$1',
    '^@/lib/(.*)$': '<rootDir>/src/lib/$1',
    '^@/api/(.*)$': '<rootDir>/src/api/$1',
    '^@/middlewares/(.*)$': '<rootDir>/src/middlewares/$1',
    '^@/models/(.*)$': '<rootDir>/src/models/$1',
    '^@/types/(.*)$': '<rootDir>/src/types/$1',
  },
  clearMocks: true,
  collectCoverage: false,
};
