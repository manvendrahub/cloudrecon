# CloudRecon AI Frontend

Professional React + TypeScript frontend for:

**Generative AI-Based Cloud Removal and Reconstruction for LISS-IV Satellite Imagery**

## Stack

- React 19
- TypeScript
- Vite
- React Router
- Axios
- Recharts
- Lucide React
- CSS (custom responsive design)

## Run

```bash
npm install
npm run dev
```

Open the URL shown by Vite, normally:

```text
http://localhost:5173
```

## Build

```bash
npm run build
```

## Spring Boot integration

Set the backend URL in a `.env` file:

```env
VITE_API_URL=http://localhost:8080/api
```

The Axios client is in:

`src/services/api.ts`

Expected backend endpoints can be added around:

- `POST /api/auth/login`
- `POST /api/images/upload`
- `POST /api/analysis/start`
- `GET /api/analysis/{id}`
- `GET /api/results/{id}`
- `GET /api/history`

The current login and dashboard use demo/local data so the UI works immediately without a backend.

## Backend connection (updated)

Login, upload, analysis, results and history now call the Java backend at `http://localhost:8080/api`.
Demo login: `researcher@cloudrecon.ai` / `demo123`. Start the backend first, then `npm run dev`.
The dashboard page still shows demo numbers; use `GET /api/dashboard/stats` to wire it.
