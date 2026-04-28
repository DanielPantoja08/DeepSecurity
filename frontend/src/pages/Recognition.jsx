import { useEffect, useState } from "react";
import { listCameras } from "../api/cameras";
import CameraTile from "../components/CameraTile";

export default function Recognition() {
    const [cameras, setCameras] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        listCameras()
            .then((data) => setCameras(data.filter((c) => c.is_active)))
            .catch((err) => setError("Error al cargar cámaras: " + err.message))
            .finally(() => setLoading(false));
    }, []);

    const cols = cameras.length <= 1 ? 1 : cameras.length <= 4 ? 2 : 3;

    if (loading) return <div className="skeleton" style={{ height: 400, width: "100%" }} />;

    return (
        <div>
            <div className="page-header">
                <h2>📹 Reconocimiento en Tiempo Real</h2>
                <p>Todas las cámaras activas capturan y analizan frames de forma simultánea e independiente.</p>
            </div>

            {error && <div className="alert alert-danger" style={{ marginBottom: 16 }}>{error}</div>}

            {cameras.length === 0 ? (
                <div className="card" style={{ padding: "40px 24px", textAlign: "center", color: "var(--text-muted)" }}>
                    <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1} style={{ margin: "0 auto 16px" }}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.069A1 1 0 0121 8.882V15.118a1 1 0 01-1.447.906L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                    </svg>
                    <p style={{ fontSize: "0.9rem" }}>No hay cámaras activas registradas.</p>
                    <p style={{ fontSize: "0.82rem", marginTop: 8 }}>
                        Ve a <strong>Cámaras</strong> para agregar y activar al menos una.
                    </p>
                </div>
            ) : (
                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns: `repeat(${cols}, 1fr)`,
                        gap: 16,
                    }}
                >
                    {cameras.map((cam) => (
                        <CameraTile key={cam.id} camera={cam} tileCount={cameras.length} />
                    ))}
                </div>
            )}
        </div>
    );
}
