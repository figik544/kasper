import { Hono } from 'hono';

const app = new Hono();

app.get('/', (c) => {
  return c.text('Galactic Empire Bot API');
});

export default app;