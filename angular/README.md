# Angular Oracle UI

Alternative Angular frontend for the oracle demo.

## Local development

```bash
cd angular
npm install
npm start
```

The dev server runs at `http://127.0.0.1:4200` and proxies `/api/*` to the orchestrator.

## Build

```bash
cd angular
npm run build
```

## Docker

The repo-level `docker compose up --build` command also starts this frontend on `http://127.0.0.1:8502`.
