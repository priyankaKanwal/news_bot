# Frontend

The news chat interface is built with React, Vite, and Tailwind CSS 4. Styling uses Tailwind utility classes, with CSS custom properties in `src/index.css` for the light and dark themes.

From this directory:

```powershell
npm ci
npm run dev
```

The welcome screen shows the six latest ingested stories from `GET /api/articles/recent`. The API address defaults to `http://localhost:8000`; set `VITE_API_URL` to use another backend address.

Run `npm run build` and `npm run lint` to validate frontend changes.
