import { useEffect, useState } from "react";
import { listCameras, createCamera, updateCamera, deleteCamera } from "../api/cameras";

export default function Cameras() {
    const [cameras, setCameras] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [newName, setNewName] = useState("");
    const [creating, setCreating] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [editName, setEditName] = useState("");
    const [deletingId, setDeletingId] = useState(null);
    const [devices, setDevices] = useState([]);
    const [detectingDevices, setDetectingDevices] = useState(false);

    const load = async () => {
        try {
            const data = await listCameras();
            setCameras(data);
        } catch (err) {
            setError("Error al cargar cámaras: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    const handleDetectDevices = async () => {
        setDetectingDevices(true);
        setError(null);
        try {
            // Request camera permission first so labels are visible
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            stream.getTracks().forEach((t) => t.stop());

            const all = await navigator.mediaDevices.enumerateDevices();
            setDevices(all.filter((d) => d.kind === "videoinput"));
        } catch (err) {
            setError("No se pudo acceder a los dispositivos de video: " + err.message);
        } finally {
            setDetectingDevices(false);
        }
    };

    const handleRegisterDevice = async (device) => {
        const name = device.label || `Cámara ${cameras.length + 1}`;
        setCreating(true);
        try {
            const cam = await createCamera({
                name,
                device_label: device.label || null,
                device_id_hash: device.deviceId ? await hashDeviceId(device.deviceId) : null,
            });
            setCameras((prev) => [...prev, cam]);
        } catch (err) {
            setError("Error al registrar cámara: " + err.message);
        } finally {
            setCreating(false);
        }
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!newName.trim()) return;
        setCreating(true);
        try {
            const cam = await createCamera({ name: newName.trim() });
            setCameras((prev) => [...prev, cam]);
            setNewName("");
        } catch (err) {
            setError("Error al crear cámara: " + err.message);
        } finally {
            setCreating(false);
        }
    };

    const handleEditSave = async (id) => {
        if (!editName.trim()) return;
        try {
            const updated = await updateCamera(id, { name: editName.trim() });
            setCameras((prev) => prev.map((c) => c.id === id ? updated : c));
            setEditingId(null);
        } catch (err) {
            setError("Error al actualizar cámara: " + err.message);
        }
    };

    const handleDelete = async (id) => {
        setDeletingId(id);
        try {
            await deleteCamera(id);
            setCameras((prev) => prev.filter((c) => c.id !== id));
        } catch (err) {
            setError("Error al eliminar cámara: " + err.message);
        } finally {
            setDeletingId(null);
        }
    };

    const handleToggleActive = async (cam) => {
        try {
            const updated = await updateCamera(cam.id, { is_active: !cam.is_active });
            setCameras((prev) => prev.map((c) => c.id === cam.id ? updated : c));
        } catch (err) {
            setError("Error al actualizar estado: " + err.message);
        }
    };

    if (loading) return <div className="skeleton" style={{ height: 300, width: "100%" }} />;

    return (
        <div>
            <div className="page-header">
                <h2>📷 Cámaras</h2>
                <p>Registra y gestiona las cámaras disponibles para el reconocimiento facial.</p>
            </div>

            {error && <div className="alert alert-danger" style={{ marginBottom: 16 }}>{error}</div>}

            {/* Detect devices */}
            <div className="card" style={{ marginBottom: 20, padding: "20px 24px" }}>
                <h4 style={{ marginBottom: 12, fontSize: "0.95rem" }}>Detectar dispositivos conectados</h4>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: 16 }}>
                    Pulsa el botón para detectar las cámaras disponibles en este equipo. Se pedirá permiso de acceso la primera vez.
                </p>
                <button
                    className="btn btn-primary"
                    onClick={handleDetectDevices}
                    disabled={detectingDevices}
                    style={{ marginBottom: devices.length > 0 ? 16 : 0 }}
                >
                    {detectingDevices ? "Detectando…" : "Detectar dispositivos"}
                </button>

                {devices.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                        {devices.map((d) => (
                            <div
                                key={d.deviceId}
                                className="card"
                                style={{
                                    padding: "12px 16px",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "space-between",
                                    background: "var(--bg)",
                                }}
                            >
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                                        {d.label || "Cámara desconocida"}
                                    </div>
                                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                                        {d.deviceId.slice(0, 20)}…
                                    </div>
                                </div>
                                <button
                                    className="btn btn-primary"
                                    onClick={() => handleRegisterDevice(d)}
                                    disabled={creating}
                                    style={{ padding: "6px 14px", fontSize: "0.8rem" }}
                                >
                                    + Registrar
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Manual create */}
            <div className="card" style={{ marginBottom: 20, padding: "20px 24px" }}>
                <h4 style={{ marginBottom: 12, fontSize: "0.95rem" }}>Agregar cámara manualmente</h4>
                <form onSubmit={handleCreate} style={{ display: "flex", gap: 12, alignItems: "center" }}>
                    <input
                        className="input"
                        placeholder="Nombre de la cámara…"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        style={{ flex: 1 }}
                    />
                    <button className="btn btn-primary" type="submit" disabled={creating || !newName.trim()}>
                        {creating ? "Creando…" : "Agregar"}
                    </button>
                </form>
            </div>

            {/* Camera list */}
            <div className="card">
                {cameras.length === 0 ? (
                    <div style={{ padding: "40px 24px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.875rem" }}>
                        No hay cámaras registradas. Usa los botones de arriba para agregar una.
                    </div>
                ) : (
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Nombre</th>
                                    <th>Dispositivo</th>
                                    <th>Estado</th>
                                    <th style={{ textAlign: "right" }}>Acciones</th>
                                </tr>
                            </thead>
                            <tbody>
                                {cameras.map((cam) => (
                                    <tr key={cam.id}>
                                        <td>
                                            {editingId === cam.id ? (
                                                <input
                                                    className="input"
                                                    value={editName}
                                                    onChange={(e) => setEditName(e.target.value)}
                                                    style={{ width: "100%", maxWidth: 200 }}
                                                    autoFocus
                                                />
                                            ) : (
                                                <span style={{ fontWeight: 600 }}>{cam.name}</span>
                                            )}
                                        </td>
                                        <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                                            {cam.device_label || "—"}
                                        </td>
                                        <td>
                                            <span
                                                className={`badge ${cam.is_active ? "badge-accent" : ""}`}
                                                style={{ cursor: "pointer" }}
                                                onClick={() => handleToggleActive(cam)}
                                                title="Clic para activar/desactivar"
                                            >
                                                {cam.is_active ? "Activa" : "Inactiva"}
                                            </span>
                                        </td>
                                        <td style={{ textAlign: "right" }}>
                                            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                                                {editingId === cam.id ? (
                                                    <>
                                                        <button
                                                            className="btn btn-primary"
                                                            onClick={() => handleEditSave(cam.id)}
                                                            style={{ padding: "6px 12px", fontSize: "0.8rem" }}
                                                        >
                                                            Guardar
                                                        </button>
                                                        <button
                                                            className="btn"
                                                            onClick={() => setEditingId(null)}
                                                            style={{ padding: "6px 12px", fontSize: "0.8rem", border: "1px solid var(--border)" }}
                                                        >
                                                            Cancelar
                                                        </button>
                                                    </>
                                                ) : (
                                                    <button
                                                        className="btn"
                                                        onClick={() => { setEditingId(cam.id); setEditName(cam.name); }}
                                                        style={{ padding: "6px 12px", fontSize: "0.8rem", border: "1px solid var(--border)" }}
                                                    >
                                                        Editar
                                                    </button>
                                                )}
                                                <button
                                                    className="btn"
                                                    onClick={() => handleDelete(cam.id)}
                                                    disabled={deletingId === cam.id}
                                                    style={{ padding: "6px 12px", fontSize: "0.8rem", background: "linear-gradient(135deg, #dc2626, #b91c1c)", color: "#fff", border: "1px solid #b91c1c" }}
                                                >
                                                    {deletingId === cam.id ? "…" : "Eliminar"}
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}

async function hashDeviceId(deviceId) {
    const enc = new TextEncoder().encode(deviceId);
    const buf = await crypto.subtle.digest("SHA-256", enc);
    return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 64);
}
