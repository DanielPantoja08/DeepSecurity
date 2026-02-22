const BASE_URL = "http://localhost:8000";

/**
 * Sends a video frame blob to the recognition endpoint.
 * @param {Blob} blob - JPEG image blob from canvas.toBlob()
 * @returns {Promise<{faces: Array}>}
 */
export async function recognizeFrame(blob) {
    const form = new FormData();
    form.append("file", blob, "frame.jpg");
    const res = await fetch(`${BASE_URL}/api/recognize`, {
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
    const res = await fetch(`${BASE_URL}/api/faces`);
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
    const res = await fetch(`${BASE_URL}/api/faces/${encodeURIComponent(name)}`, {
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
    const res = await fetch(`${BASE_URL}/api/faces/${encodeURIComponent(name)}`, {
        method: "DELETE",
    });
    // 204 No Content is success
    if (!res.ok && res.status !== 204) throw new Error(`deleteFace: ${res.status}`);
}
