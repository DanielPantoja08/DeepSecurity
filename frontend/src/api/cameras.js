const BASE_URL = "";
const TOKEN_KEY = "ds_token";

function getAuthHeaders() {
  const token = sessionStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch(url, options = {}) {
  const headers = { ...getAuthHeaders(), ...(options.headers || {}) };
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    sessionStorage.removeItem(TOKEN_KEY);
    window.location.reload();
    return res;
  }
  return res;
}

export async function listCameras() {
  const res = await apiFetch(`${BASE_URL}/api/cameras`);
  if (!res.ok) throw new Error(`listCameras: ${res.status}`);
  return res.json();
}

export async function createCamera({ name, device_label, device_id_hash }) {
  const res = await apiFetch(`${BASE_URL}/api/cameras`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, device_label, device_id_hash }),
  });
  if (!res.ok) throw new Error(`createCamera: ${res.status}`);
  return res.json();
}

export async function updateCamera(id, patch) {
  const res = await apiFetch(`${BASE_URL}/api/cameras/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) throw new Error(`updateCamera: ${res.status}`);
  return res.json();
}

export async function deleteCamera(id) {
  const res = await apiFetch(`${BASE_URL}/api/cameras/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) throw new Error(`deleteCamera: ${res.status}`);
}
