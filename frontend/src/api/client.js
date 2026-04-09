// Use relative URLs so requests go to the same host/IP that served the page.
// Nginx proxies /api/* → backend:8000/api/* internally.
// This works from any PC on the network without hardcoding an IP.
const BASE_URL = "";
const TOKEN_KEY = "ds_token";

function getAuthHeaders() {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Fetch wrapper that injects the JWT Authorization header on every request.
 * On 401, clears the stored token and reloads the page to force re-login.
 */
async function apiFetch(url, options = {}) {
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    window.location.reload();
    return res;
  }
  return res;
}

export const getRecordingFileUrl = (id, download = false) => {
  const token = localStorage.getItem(TOKEN_KEY);
  const base = `${BASE_URL}/api/history/recordings/${id}/file${download ? "?download=true" : ""}`;
  // Append token as query param for direct file/video URLs (browser can't set headers)
  return token ? `${base}${download ? "&" : "?"}token=${token}` : base;
};

/**
 * Sends a video frame blob to the recognition endpoint.
 * @param {Blob} blob - JPEG image blob from canvas.toBlob()
 * @returns {Promise<{faces: Array}>}
 */
export async function recognizeFrame(blob) {
  const form = new FormData();
  form.append("file", blob, "frame.jpg");
  const res = await apiFetch(`${BASE_URL}/api/recognize`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`recognize: ${res.status}`);
  return res.json();
}

/**
 * Lists all registered identities.
 * @returns {Promise<{faces: string[]}>}
 */
export async function listFaces() {
  const res = await apiFetch(`${BASE_URL}/api/faces`);
  if (!res.ok) throw new Error(`listFaces: ${res.status}`);
  return res.json();
}

/**
 * Registers or extends an identity with one or more image files.
 * @param {string} name
 * @param {File[]} files
 */
export async function registerFace(name, files) {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await apiFetch(`${BASE_URL}/api/faces/${encodeURIComponent(name)}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`registerFace: ${res.status}`);
  return res.json();
}

/**
 * Deletes an identity and all its stored images.
 * @param {string} name
 */
export async function deleteFace(name) {
  const res = await apiFetch(`${BASE_URL}/api/faces/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 204) throw new Error(`deleteFace: ${res.status}`);
}

/**
 * Gets current system settings.
 * @returns {Promise<{db_path: string}>}
 */
export async function getSettings() {
  const res = await apiFetch(`${BASE_URL}/api/settings`);
  if (!res.ok) throw new Error(`getSettings: ${res.status}`);
  return res.json();
}

/**
 * Updates system settings.
 * @param {{db_path: string}} settings
 * @returns {Promise<{message: string, db_path: string}>}
 */
export async function updateSettings(settings) {
  const res = await apiFetch(`${BASE_URL}/api/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || `updateSettings: ${res.status}`);
  }
  return res.json();
}

/**
 * Opens a native OS folder picker on the server and returns the selected path.
 * @returns {Promise<{path: string|null, cancelled: boolean}>}
 */
export async function browseFolder() {
  const res = await apiFetch(`${BASE_URL}/api/settings/browse`, {
    method: "POST",
  });
  if (!res.ok) {
    let msg = `browseFolder: ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) msg = data.detail;
    } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

/**
 * Commands the server to start recording the current stream.
 */
export async function startRecording() {
  const res = await apiFetch(`${BASE_URL}/api/recognize/start_recording`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`startRecording: ${res.status}`);
  return res.json();
}

/**
 * Commands the server to stop recording and returns recording info.
 */
export async function stopRecording() {
  const res = await apiFetch(`${BASE_URL}/api/recognize/stop_recording`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`stopRecording: ${res.status}`);
  return res.json();
}

/**
 * Fetches the current recording status.
 * @returns {Promise<{is_recording: boolean}>}
 */
export const getRecordingStatus = async () => {
  const res = await apiFetch(`${BASE_URL}/api/recognize/status`);
  if (!res.ok) throw new Error("Error fetching recording status");
  return res.json();
};

/**
 * Fetches the recognition logs.
 * @returns {Promise<Array>}
 */
export const getRecognitionLogs = async () => {
  const res = await apiFetch(`${BASE_URL}/api/history/logs`);
  if (!res.ok) throw new Error("Error fetching history");
  return res.json();
};

/**
 * Fetches the video recordings metadata.
 * @returns {Promise<Array>}
 */
export async function getVideoRecordings() {
  const res = await apiFetch(`${BASE_URL}/api/history/recordings`);
  if (!res.ok) throw new Error(`getVideoRecordings: ${res.status}`);
  return res.json();
}
