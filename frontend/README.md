# Plan Helper Frontend

A Vite + React + TypeScript dashboard for interacting with the Flask planning tools backend.

## Getting started

1. Install dependencies:

   ```bash
   npm install
   ```

2. Configure environment variables by copying the example file:

   ```bash
   cp .env.example .env
   ```

   Set `VITE_API_BASE_URL` to the Flask backend URL (for example `http://localhost:5000`). Optionally define
   `VITE_API_PROXY` to let Vite proxy API requests during development.

3. Start the development server:

   ```bash
   npm run dev
   ```

   The app opens on [http://localhost:5173](http://localhost:5173). When `VITE_API_PROXY` is configured the browser will
   call the backend via the Vite dev server proxy. Alternatively, ensure CORS is enabled on the Flask backend.

## Available scripts

- `npm run dev` – start the Vite development server
- `npm run build` – type-check the project and output a production build to `dist/`
- `npm run preview` – preview the production build locally
- `npm run lint` – run ESLint on the `src/` directory
- `npm run format` – format source files with Prettier

## Building for production

The build script runs TypeScript in project reference mode followed by `vite build`, generating a tree-shaken, hashed
bundle in `dist/`. Deploy the static assets behind your preferred CDN or web server. Configure environment variables at
build time via `.env` or system environment to ensure `VITE_API_BASE_URL` points at the live Flask service.

## Backend integration

The frontend assumes the Flask app (see `api/app.py`) exposes the REST namespaces under `/tools/*`. During development
set `VITE_API_PROXY` to the Flask server URL to avoid CORS. In production you can host the static assets behind the same
origin as the Flask API or configure CORS headers on the backend.

The React Query client caches responses from each feature module:

- Tickets – manual uploads and filtered search
- Subtasks – generation and list view with filters
- Affinity – recompute controls and grouped output
- Planner – constraint form, generated plan timeline, and persisted plan view
- Reports – morning and evening report interactions

Tailwind CSS powers the styling layer via `tailwind.config.ts` and `postcss.config.cjs`. Customize the palette or add
utility plugins as needed.
