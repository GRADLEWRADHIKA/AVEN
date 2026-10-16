# aven-web

AVEN frontend: Next.js (App Router), React, TypeScript, Tailwind.

See the main [README](../README.md) for how to run everything.

```
app/
  login/, register/, dashboard/   pages
  actions.ts                      server actions: sign in, sign up, sign out, add practice/user
components/forms.tsx              form components
lib/
  api.ts                          server-side client for the AVEN API
  session.ts                      sign-in cookie and "require a signed-in user"
  types.ts                        shared types and role ranks
```

How sign-in works: the browser never sees the API token. The login form calls a server action, which gets a token from the API and stores it in an HttpOnly cookie. Pages and actions read that cookie on the server and call the API. Every protected page starts with `requireSession()`.

Quick start without Docker for the web app (the API must be running on port 8000):

```
npm install
cp .env.example .env.local
npm run dev
```
