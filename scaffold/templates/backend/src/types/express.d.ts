// src/types/express.d.ts
// Augment Express's Request so `req.id` is typed across the codebase.

declare global {
  namespace Express {
    interface Request {
      id: string;
    }
  }
}

export {};
