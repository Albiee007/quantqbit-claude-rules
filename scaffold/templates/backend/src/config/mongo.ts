// src/config/mongo.ts
// Mongoose connection stub. Call `connectMongo()` from server.ts when the
// application needs Mongo. The stub is a no-op when MONGO_URI is empty so
// the buildable starter works without Mongo running.

import mongoose from 'mongoose';
import { env } from './env';
import { logger } from './logger';

let connected = false;

export async function connectMongo(): Promise<void> {
  if (connected) return;
  if (!env.MONGO_URI) {
    logger.info('MONGO_URI empty — skipping Mongo connect');
    return;
  }
  await mongoose.connect(env.MONGO_URI);
  connected = true;
  logger.info('Mongo connected');
}

export async function disconnectMongo(): Promise<void> {
  if (!connected) return;
  await mongoose.disconnect();
  connected = false;
}
