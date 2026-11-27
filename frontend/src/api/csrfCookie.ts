/** Name of the readable CSRF cookie. The session JWT stays in a different HttpOnly cookie. */
const configured = import.meta.env.VITE_CSRF_COOKIE

export const CSRF_COOKIE =
  typeof configured === 'string' && configured.trim() ? configured.trim() : 'parkify_csrf'
