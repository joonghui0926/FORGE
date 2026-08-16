import { Pool } from 'pg'

const globalForAuthDb = globalThis as unknown as { forgeAuthPool?: Pool }

export const authPool = globalForAuthDb.forgeAuthPool ?? new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 5,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 10_000,
  ssl: process.env.FORGE_ENV === 'production' ? { rejectUnauthorized: false } : undefined,
})

if (process.env.NODE_ENV !== 'production') globalForAuthDb.forgeAuthPool = authPool

