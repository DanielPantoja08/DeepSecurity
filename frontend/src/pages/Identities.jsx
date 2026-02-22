import { useState, useEffect, useRef, useCallback } from "react";
import { listFaces, registerFace, deleteFace } from "../api/client";

export default function Identities() {
    const [tab, setTab] = useState("list");
    const [faces, setFaces] = useState([]);
    const [loading, setLoading] = useState(false);

    // Register form state
    const [name, setName] = useState("");
    const [files, setFiles] = useState([]);
    const [cameraOpen, setCameraOpen] = useState(false);
    const [snapshot, setSnapshot] = useState(null); // Blob
    const [snapshotURL, setSnapshotURL] = useState(null);
    const [registering, setRegistering] = useState(false);
    const [feedback, setFeedback] = useState(null); // {type, msg}

    const videoRef = useRef(null);
    const snapCanvasRef = useRef(null);
    const streamRef = useRef(null);

    // ── Load identities ─────────────────────────────────────────
    const loadFaces = useCallback(async () => {
        setLoading(true);
        try {
            const data = await listFaces();
            setFaces(data.faces || []);
        } catch {
            setFaces([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (tab === "list") loadFaces();
    }, [tab, loadFaces]);

    // ── Delete identity ──────────────────────────────────────────
    const handleDelete = async (faceName) => {
        if (!confirm(`¿Eliminar la identidad "${faceName}"?`)) return;
        try {
            await deleteFace(faceName);
            setFaces((prev) => prev.filter((f) => f !== faceName));
        } catch (err) {
            alert("Error al eliminar: " + err.message);
        }
    };

    // ── Camera snapshot ──────────────────────────────────────────
    const openCamera = async () => {
        setSnapshot(null);
        setSnapshotURL(null);
        setCameraOpen(true);
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                await videoRef.current.play();
            }
        } catch (err) {
            setFeedback({ type: "danger", msg: "No se pudo acceder a la cámara: " + err.message });
            setCameraOpen(false);
        }
    };

    const closeCamera = () => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        setCameraOpen(false);
    };

    const takeSnapshot = () => {
        const video = videoRef.current;
        const canvas = snapCanvasRef.current;
        if (!video || !canvas) return;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        canvas.toBlob((blob) => {
            setSnapshot(blob);
            setSnapshotURL(canvas.toDataURL("image/jpeg"));
        }, "image/jpeg", 0.9);
        closeCamera();
    };

    // ── Register ─────────────────────────────────────────────────
    const handleRegister = async () => {
        setFeedback(null);
        if (!name.trim()) return setFeedback({ type: "danger", msg: "Ingresa un nombre." });
        const allFiles = [
            ...files,
            ...(snapshot ? [new File([snapshot], "snapshot.jpg", { type: "image/jpeg" })] : []),
        ];
        if (allFiles.length === 0)
            return setFeedback({ type: "danger", msg: "Agrega al menos una imagen." });

        setRegistering(true);
        try {
            const res = await registerFace(name.trim(), allFiles);
            setFeedback({ type: "success", msg: `${res.message} (${res.saved} imagen${res.saved > 1 ? "es" : ""} guardadas)` });
            setName("");
            setFiles([]);
            setSnapshot(null);
            setSnapshotURL(null);
        } catch (err) {
            setFeedback({ type: "danger", msg: "Error al registrar: " + err.message });
        } finally {
            setRegistering(false);
        }
    };

    // ── UI ────────────────────────────────────────────────────────
    return (
        <div>
            <div className="page-header">
                <h2>👥 Gestión de Identidades</h2>
                <p>Lista, registra y elimina personas en la base de datos de reconocimiento.</p>
            </div>

            <div className="tabs">
                <button className={`tab-btn ${tab === "list" ? "active" : ""}`} onClick={() => setTab("list")}>
                    Listar
                </button>
                <button className={`tab-btn ${tab === "register" ? "active" : ""}`} onClick={() => setTab("register")}>
                    Registrar
                </button>
            </div>

            {/* ── LIST TAB ── */}
            {tab === "list" && (
                <div>
                    {loading ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                            {[1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 58 }} />)}
                        </div>
                    ) : faces.length === 0 ? (
                        <div className="alert alert-info">
                            No hay identidades registradas. Ve a <strong>Registrar</strong> para agregar una.
                        </div>
                    ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                            {faces.map((f) => (
                                <div
                                    key={f}
                                    className="card"
                                    style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 20px" }}
                                >
                                    <div style={{
                                        width: 42, height: 42, borderRadius: "50%",
                                        background: "linear-gradient(135deg,var(--accent),var(--accent2))",
                                        display: "flex", alignItems: "center", justifyContent: "center",
                                        fontWeight: 700, fontSize: "1rem", color: "#000", flexShrink: 0,
                                    }}>
                                        {f[0].toUpperCase()}
                                    </div>
                                    <span style={{ flex: 1, fontWeight: 500 }}>{f}</span>
                                    <button className="btn btn-danger" style={{ padding: "6px 14px" }} onClick={() => handleDelete(f)}>
                                        Eliminar
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                    <button className="btn btn-ghost" style={{ marginTop: 16 }} onClick={loadFaces}>
                        ↻ Actualizar
                    </button>
                </div>
            )}

            {/* ── REGISTER TAB ── */}
            {tab === "register" && (
                <div style={{ maxWidth: 580 }}>
                    {feedback && (
                        <div className={`alert alert-${feedback.type}`} style={{ marginBottom: 20 }}>
                            {feedback.msg}
                        </div>
                    )}

                    <div style={{ marginBottom: 16 }}>
                        <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: "0.875rem" }}>
                            Nombre de la persona
                        </label>
                        <input
                            className="input"
                            placeholder="Ej: Daniel Pantoja"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                        />
                    </div>

                    {/* File upload */}
                    <div style={{ marginBottom: 20 }}>
                        <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: "0.875rem" }}>
                            Subir foto(s)
                        </label>
                        <label
                            style={{
                                display: "flex", alignItems: "center", justifyContent: "center",
                                gap: 8, padding: "20px", borderRadius: "var(--radius)",
                                border: "2px dashed var(--border)", cursor: "pointer",
                                color: "var(--text-muted)", transition: "border-color 0.2s",
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
                            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                        >
                            <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                            </svg>
                            {files.length > 0 ? `${files.length} archivo(s) seleccionados` : "Haz clic para seleccionar imágenes"}
                            <input
                                type="file"
                                accept="image/*"
                                multiple
                                style={{ display: "none" }}
                                onChange={(e) => setFiles(Array.from(e.target.files))}
                            />
                        </label>
                    </div>

                    {/* Camera snapshot */}
                    <div style={{ marginBottom: 24 }}>
                        <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: "0.875rem" }}>
                            O tomar foto con cámara
                        </label>
                        {!cameraOpen && !snapshotURL && (
                            <button className="btn btn-ghost" onClick={openCamera}>
                                📷 Abrir cámara
                            </button>
                        )}
                        {cameraOpen && (
                            <div className="card" style={{ padding: 16 }}>
                                <video
                                    ref={videoRef}
                                    style={{ width: "100%", borderRadius: 8, background: "#000", display: "block" }}
                                    autoPlay playsInline muted
                                />
                                <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
                                    <button className="btn btn-primary" onClick={takeSnapshot}>📸 Capturar</button>
                                    <button className="btn btn-ghost" onClick={closeCamera}>Cancelar</button>
                                </div>
                            </div>
                        )}
                        {snapshotURL && (
                            <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8 }}>
                                <img src={snapshotURL} alt="snapshot" style={{ width: 80, height: 60, objectFit: "cover", borderRadius: 8, border: "1px solid var(--border)" }} />
                                <button className="btn btn-ghost" style={{ padding: "6px 12px" }} onClick={() => { setSnapshot(null); setSnapshotURL(null); }}>
                                    ✕ Quitar
                                </button>
                            </div>
                        )}
                    </div>

                    <canvas ref={snapCanvasRef} style={{ display: "none" }} />

                    <button
                        className="btn btn-primary"
                        onClick={handleRegister}
                        disabled={registering}
                        style={{ width: "100%", justifyContent: "center" }}
                    >
                        {registering ? (
                            <><span className="animate-pulse">⏳</span> Registrando…</>
                        ) : (
                            "✅ Registrar Identidad"
                        )}
                    </button>
                </div>
            )}
        </div>
    );
}
