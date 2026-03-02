import { useState, useEffect } from "react";
import { getSettings, updateSettings } from "../api/client";

export default function Settings() {
    const [dbPath, setDbPath] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [feedback, setFeedback] = useState(null);

    useEffect(() => {
        async function fetchSettings() {
            try {
                const data = await getSettings();
                setDbPath(data.db_path);
            } catch (err) {
                setFeedback({ type: "danger", msg: "Error al cargar configuración: " + err.message });
            } finally {
                setLoading(false);
            }
        }
        fetchSettings();
    }, []);

    const handleSave = async () => {
        setFeedback(null);
        if (!dbPath.trim()) return setFeedback({ type: "danger", msg: "La ruta no puede estar vacía." });

        setSaving(true);
        try {
            const res = await updateSettings({ db_path: dbPath.trim() });
            setDbPath(res.db_path);
            setFeedback({ type: "success", msg: "Configuración guardada correctamente." });
        } catch (err) {
            setFeedback({ type: "danger", msg: "Error al guardar: " + err.message });
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div>
                <div className="page-header">
                    <h2>⚙️ Configuración</h2>
                    <p>Cargando ajustes del sistema...</p>
                </div>
                <div className="skeleton" style={{ height: 100 }} />
            </div>
        );
    }

    return (
        <div>
            <div className="page-header">
                <h2>⚙️ Configuración</h2>
                <p>Ajusta los parámetros del sistema de reconocimiento.</p>
            </div>

            <div className="card" style={{ maxWidth: 600 }}>
                {feedback && (
                    <div className={`alert alert-${feedback.type}`} style={{ marginBottom: 20 }}>
                        {feedback.msg}
                    </div>
                )}

                <div style={{ marginBottom: 24 }}>
                    <label style={{ display: "block", marginBottom: 8, fontWeight: 600, fontSize: "0.9rem" }}>
                        Directorio de Base de Datos de Rostros
                    </label>
                    <div style={{ color: "var(--text-muted)", fontSize: "0.8rem", marginBottom: 12 }}>
                        Esta carpeta debe contener subcarpetas, donde cada subcarpeta es el nombre de una persona y contiene sus fotos.
                    </div>
                    <input
                        className="input"
                        value={dbPath}
                        onChange={(e) => setDbPath(e.target.value)}
                        placeholder="Ej: C:\Ruta\A\Fotos"
                        style={{ fontFamily: "monospace" }}
                    />
                </div>

                <button
                    className="btn btn-primary"
                    onClick={handleSave}
                    disabled={saving}
                    style={{ width: "100%", justifyContent: "center" }}
                >
                    {saving ? <><span className="animate-pulse">⏳</span> Guardando…</> : "Guardar Configuración"}
                </button>
            </div>

            <div className="alert alert-info" style={{ marginTop: 24, maxWidth: 600 }}>
                <span>💡</span>
                <div>
                    <strong>Rutas Absolutas</strong> — Se recomienda usar rutas absolutas para evitar confusiones con la ubicación del servidor.
                </div>
            </div>
        </div>
    );
}
