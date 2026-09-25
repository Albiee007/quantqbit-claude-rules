import express from 'express';
import request from 'supertest';
import { errorHandler } from '../../middlewares/errorHandler';
import { requestId } from '../../middlewares/requestId';

jest.mock('../../config/logger', () => ({ logger: { error: jest.fn() } }));

it.each([undefined, 200, 999, 500])('sanitizes internal errors with status %s', async (status) => {
  const app = express();
  app.use(requestId);
  app.get('/', (_req, _res, next) => next(Object.assign(new Error('private database details'), { status })));
  app.use(errorHandler);
  const response = await request(app).get('/');
  expect(response.status).toBe(500);
  expect(response.body.message).toBe('Internal server error');
  expect(response.body.requestId).toBeDefined();
});

it('keeps actionable client errors', async () => {
  const app = express();
  app.get('/', (_req, _res, next) => next(Object.assign(new Error('Invalid input'), { status: 400 })));
  app.use(errorHandler);
  const response = await request(app).get('/');
  expect(response.status).toBe(400);
  expect(response.body.message).toBe('Invalid input');
});
