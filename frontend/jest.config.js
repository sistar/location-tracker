export default {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: [
    '**/e2e/**/*.test.ts',
    '**/tests/**/*.test.ts'
  ],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/'
  ],
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  testTimeout: 30000,
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/vite-env.d.ts'
  ],
  transform: {
    '^.+\\.ts$': ['ts-jest', {
      tsconfig: 'tsconfig.json'
    }]
  }
};