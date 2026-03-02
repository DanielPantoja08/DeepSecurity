import { useState, useEffect } from "react";
import { getSettings } from "../api/client";

const INFO_ROWS_BASE = [
    { label: "Detector de Rostros", value: "MTCNN", badge: "badge-accent" },
    { label: "Modelo de Reconocimiento", value: "VGG-Face (DeepFace)", badge: "badge-accent" },
    { label: "Backend", value: "FastAPI + Uvicorn", badge: "badge-accent" },
    { label: "Frontend", value: "React 19 + Vite 7", badge: "badge-accent" },
    { label: "Comunicación", value: "REST API / multipart/form-data", badge: "badge-success" },
];

const ENDPOINTS = [
    { method: "GET", path: "/api/faces", desc: "Lista todas las identidades registradas" },
    { method: "POST", path: "/api/faces/{name}", desc: "Registra o amplía una identidad con imágenes" },
    { method: "DELETE", path: "/api/faces/{name}", desc: "Elimina una identidad y sus imágenes" },
    { method: "POST", path: "/api/recognize", desc: "Recibe un frame JPEG y devuelve los rostros detectados" },
    { method: "GET", path: "/api/settings", desc: "Obtiene la ruta de la base de datos actual" },
    { method: "POST", path: "/api/settings", desc: "Actualiza la ruta de la base de datos" },
];

const METHOD_COLOR = {
    GET: { bg: "rgba(16,185,129,0.12)", color: "#10b981" },
    POST: { bg: "rgba(0,212,255,0.12)", color: "#00d4ff" },
    DELETE: { bg: "rgba(239,68,68,0.12)", color: "#ef4444" },
};

export default function SystemInfo() {
    const [dbPath, setDbPath] = useState("Cargando...");

    useEffect(() => {
        async function fetchDbPath() {
            try {
                const settings = await getSettings();
                setDbPath(settings.db_path);
            } catch (err) {
                setDbPath("Error al cargar");
            }
        }
        fetchDbPath();
    }, []);

    return (
        <div>
            <div className="page-header">
                <h2>⚙️ Información del Sistema</h2>
                <p>Modelos, arquitectura y endpoints de la API.</p>
            </div>

            {/* Stack info */}
            <div className="card" style={{ marginBottom: 24 }}>
                <h3 style={{ marginBottom: 16, fontSize: "1rem", fontWeight: 600 }}>Stack Tecnológico</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    <div style={{
                        display: "flex", alignItems: "center",
                        justifyContent: "space-between", gap: 12,
                        paddingBottom: 12,
                        borderBottom: "1px solid var(--border)",
                    }}>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>Base de Datos (Ruta)</span>
                        <span className="badge badge-success" style={{ fontFamily: "monospace", fontSize: "0.65rem" }}>{dbPath}</span>
                    </div>
                    {INFO_ROWS_BASE.map(({ label, value, badge }) => (
                        <div key={label} style={{
                            display: "flex", alignItems: "center",
                            justifyContent: "space-between", gap: 12,
                            paddingBottom: 12,
                            borderBottom: "1px solid var(--border)",
                        }}>
                            <span style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>{label}</span>
                            <span className={`badge ${badge}`}>{value}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* API Endpoints */}
            <div className="card" style={{ marginBottom: 24 }}>
                <h3 style={{ marginBottom: 16, fontSize: "1rem", fontWeight: 600 }}>REST API Endpoints</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {ENDPOINTS.map(({ method, path, desc }) => {
                        const mc = METHOD_COLOR[method];
                        return (
                            <div key={path} style={{
                                display: "flex", alignItems: "center", gap: 14,
                                padding: "12px 14px",
                                background: "var(--surface2)", borderRadius: "var(--radius-sm)",
                            }}>
                                <span style={{
                                    background: mc.bg, color: mc.color,
                                    fontWeight: 700, fontSize: "0.72rem",
                                    padding: "3px 8px", borderRadius: 4,
                                    fontFamily: "monospace", whiteSpace: "nowrap",
                                }}>{method}</span>
                                <code style={{ flex: "0 1 auto", fontSize: "0.82rem", color: "var(--accent)", whiteSpace: "nowrap" }}>{path}</code>
                                <span style={{ flex: 1, fontSize: "0.82rem", color: "var(--text-muted)" }}>{desc}</span>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Architecture note */}
            <div className="alert alert-info">
                <span>💡</span>
                <div>
                    <strong>Arquitectura modular</strong> — Para cambiar el modelo de reconocimiento (e.g., FaceNet, ArcFace) modifica
                    únicamente <code style={{ background: "rgba(0,212,255,0.12)", padding: "0 4px", borderRadius: 4 }}>backend/core/recognizer.py</code>.
                    La API REST y el frontend no requieren cambios.
                </div>
            </div>
        </div>
    );
}
