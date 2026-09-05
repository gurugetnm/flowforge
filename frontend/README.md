# FlowForge web client

Next.js application: workflow dashboard, visual editor and execution inspector.

## Development

```bash
cp .env.example .env.local
npm install
npm run dev
```

The app expects the FlowForge API to be running (see `../backend/README.md`).

## Scripts

| Command             | Description                                 |
| ------------------- | ------------------------------------------- |
| `npm run dev`       | Development server on http://localhost:3000 |
| `npm run build`     | Production build                            |
| `npm run lint`      | ESLint                                      |
| `npm run typecheck` | Route type generation and `tsc --noEmit`    |
| `npm run test`      | Vitest unit and component tests             |
| `npm run format`    | Prettier                                    |
