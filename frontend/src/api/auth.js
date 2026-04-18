const BASE_URL = "";

/**
 * Logs in a user and returns { access_token, token_type }.
 * FastAPI Users expects form-encoded body with "username" (= email) and "password".
 */
export async function loginUser(email, password) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const res = await fetch(`${BASE_URL}/api/auth/jwt/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Credenciales inválidas");
  }

  return res.json(); // { access_token, token_type }
}

/**
 * Registers a new user. Returns the created user object.
 */
export async function registerUser(email, password) {
  const res = await fetch(`${BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Error al registrar usuario");
  }

  return res.json();
}

/**
 * Fetches the currently authenticated user profile.
 */
export async function getMe(token) {
  const res = await fetch(`${BASE_URL}/api/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) throw new Error("Token inválido o expirado");
  return res.json();
}
