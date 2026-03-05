import { useEffect, useState } from "react";
import { getRecognitionLogs, getVideoRecordings } from "../api/client";

export default function Logs() {
    const [activeTab, setActiveTab] = useState("logs");
    const [logs, setLogs] = useState([]);
    const [recordings, setRecordings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const [logsData, recsData] = await Promise.all([
                    getRecognitionLogs(),
                    getVideoRecordings()
                ]);
                setLogs(logsData);
                setRecordings(recsData);
            } catch (err) {
                setError("Error al cargar datos históricos: " + err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const formatDate = (isoStr) => {
        if (!isoStr) return "-";
        const d = new Date(isoStr);
        return d.toLocaleDateString() + " " + d.toLocaleTimeString();
    };

    if (loading) return <div className="skeleton" style={{ height: 300, width: "100%" }} />;

    return (
        <div className="logs-page">
            <div className="page-header">
                <h2>📜 Historial y Registros</h2>
                <p>Consulta los eventos de reconocimiento y las grabaciones almacenadas.</p>
            </div>

            <div className="tabs">
                <button
                    className={`tab-btn ${activeTab === "logs" ? "active" : ""}`}
                    onClick={() => setActiveTab("logs")}
                >
                    Reconocimientos
                </button>
                <button
                    className={`tab-btn ${activeTab === "recordings" ? "active" : ""}`}
                    onClick={() => setActiveTab("recordings")}
                >
                    Grabaciones
                </button>
            </div>

            {error && <div className="alert alert-danger" style={{ marginBottom: 20 }}>{error}</div>}

            <div className="card">
                {activeTab === "logs" ? (
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Fecha y Hora</th>
                                    <th>Persona</th>
                                    <th>Confianza</th>
                                </tr>
                            </thead>
                            <tbody>
                                {logs.length === 0 ? (
                                    <tr><td colSpan="3" style={{ textAlign: "center", py: 20 }}>No hay registros disponibles.</td></tr>
                                ) : (
                                    logs.map((log) => (
                                        <tr key={log.id}>
                                            <td>{formatDate(log.timestamp)}</td>
                                            <td>
                                                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                                    <span className={`dot ${log.person_name !== "Unknown" ? "dot-green" : "dot-red"}`} />
                                                    {log.person_name}
                                                </div>
                                            </td>
                                            <td>{Math.round(log.confidence * 100)}%</td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Inicio</th>
                                    <th>Fin</th>
                                    <th>Archivo</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recordings.length === 0 ? (
                                    <tr><td colSpan="3" style={{ textAlign: "center", py: 20 }}>No hay grabaciones disponibles.</td></tr>
                                ) : (
                                    recordings.map((rec) => (
                                        <tr key={rec.id}>
                                            <td>{formatDate(rec.start_time)}</td>
                                            <td>{formatDate(rec.end_time)}</td>
                                            <td style={{ fontSize: "0.8rem", fontFamily: "monospace", color: "var(--text-muted)" }}>
                                                {rec.file_path.split(/[\\/]/).pop()}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
