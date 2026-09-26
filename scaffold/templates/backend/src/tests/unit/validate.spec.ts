import express from 'express';
import request from 'supertest';
import { z } from 'zod';
import { errorHandler } from '../../middlewares/errorHandler';
import { validate } from '../../middlewares/validate';

jest.mock('../../config/logger', () => ({ logger: { error: jest.fn() } }));

function appWith(): express.Express {
  const app = express();
  app.use(express.json());
  app.post(
    '/items',
    validate({ query: z.object({ limit: z.coerce.number().int().positive() }), body: z.object({ name: z.string() }) }),
    (req, res) => {
      res.json({ limit: req.query.limit, limitType: typeof req.query.limit, name: req.body.name });
    },
  );
  app.use(errorHandler);
  return app;
}

it('replaces query and body with the parsed values', async () => {
  const response = await request(appWith()).post('/items?limit=5').send({ name: 'pen' });
  expect(response.status).toBe(200);
  expect(response.body).toEqual({ limit: 5, limitType: 'number', name: 'pen' });
});

it('rejects invalid input with 400', async () => {
  const response = await request(appWith()).post('/items?limit=zero').send({ name: 'pen' });
  expect(response.status).toBe(400);
});
