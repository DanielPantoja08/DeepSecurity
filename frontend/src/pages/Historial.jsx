import React, { useEffect, useState } from "react";
import { getVideoRecordings, getRecognitionLogs } from "../api/client";

export default function Historial() {
    const [recordings, setRecordings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [nextCursor, setNextCursor] = useState(null);
    const [error, setError] = useState(null);
    const [expandedId, setExpandedId] = useState(null);
    const [logsMap, setLogsMap] = useState({});
    const [loadingLogsId, setLoadingLogsId] = useState(null);

    const fetchPage = async (cursor = null) => {
        const isFirstPage = cursor === null;
        if (isFirstPage) setLoading(true);
        else setLoadingMore(true);
        try {
            const data = await getVideoRecordings({ cursor, includeDeleted: true });
            const items = Array.isArray(data) ? data : (data?.items ?? []);
            const next_cursor = Array.isArray(data) ? null : (data?.next_cursor ?? null);
            setRecordings((prev) => isFirstPage ? items : [...prev, ...items]);
            setNextCursor(next_cursor);
        } catch (err) {
            setError("Error al cargar grabaciones: " + err.message);
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    };

    useEffect(() => { fetchPage(); }, []);

    const formatDate = (isoStr) => {
        if (!isoStr) return "-";
        const d = new Date(isoStr);
        return d.toLocaleDateString() + " " + d.toLocaleTimeString();
    };

    const handleViewLogs = async (e, id) => {
        e.stopPropagation();
        if (expandedId === id) { setExpandedId(null); return; }
        setExpandedId(id);
        if (logsMap[id]) return;
        setLoadingLogsId(id);
        try {
            const data = await getRecognitionLogs({ videoId: id, limit: 200 });
            const items = data?.items ?? [];
            setLogsMap((prev) => ({ ...prev, [id]: items }));
        } catch (err) {
            setError("Error al cargar logs: " + err.message);
        } finally {
            setLoadingLogsId(null);
        }
    };

    const handleDownloadLogs = async (e, id, rec) => {
        e.stopPropagation();
        try {
            let items = logsMap[id];
            if (!items) {
                const data = await getRecognitionLogs({ videoId: id, limit: 200 });
                items = data?.items ?? [];
                setLogsMap((prev) => ({ ...prev, [id]: items }));
            }
            const filename = rec.file_path.split(/[\\/]/).pop().replace(/\.[^.]+$/, "") + "_logs.json";
            const blob = new Blob([JSON.stringify(items, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            setError("Error al descargar logs: " + err.message);
        }
    };

    if (loading) return <div className="skeleton" style={{ height: 300, width: "100%" }} />;

    return (
        <div className="logs-page">
            <div className="page-header">
                <h2>📋 Historial de Reconocimiento</h2>
                <p>Consulta los eventos de reconocimiento facial registrados por grabación.</p>
            </div>

            {error && <div className="alert alert-danger" style={{ marginBottom: 20 }}>{error}</div>}

            <div className="card">
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th style={{ width: 40 }}></th>
                                <th>Grabación</th>
                                <th>Fecha y Hora</th>
                                <th>Duración</th>
                                <th>Estado</th>
                                <th style={{ textAlign: "right" }}>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recordings.length === 0 ? (
                                <tr><td colSpan="6" style={{ textAlign: "center", padding: "40px 20px" }}>No hay grabaciones registradas.</td></tr>
                            ) : recordings.map((rec) => (
                                <React.Fragment key={rec.id}>
                                    <tr
                                        onClick={(e) => handleViewLogs(e, rec.id)}
                                        style={{ cursor: "pointer" }}
                                        className={expandedId === rec.id ? "row-selected" : ""}
                                    >
                                        <td>
                                            <svg
                                                width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                                                style={{ transform: expandedId === rec.id ? "rotate(90deg)" : "none", transition: "0.2s" }}
                                            >
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                                            </svg>
                                        </td>
                                        <td>
                                            <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>
                                                {rec.file_path.split(/[\\/]/).pop()}
                                            </div>
                                        </td>
                                        <td>{formatDate(rec.start_time)}</td>
                                        <td>
                                            {rec.end_time ? (
                                                <span>{Math.round((new Date(rec.end_time) - new Date(rec.start_time)) / 1000)}s</span>
                                            ) : (
                                                <span className="badge badge-accent">En curso…</span>
                                            )}
                                        </td>
                                        <td>
                                            {rec.is_deleted ? (
                                                <span className="badge" style={{ background: "rgba(220,38,38,0.15)", color: "#dc2626" }}>Eliminada</span>
                                            ) : (
                                                <span className="badge badge-accent">Activa</span>
                                            )}
                                        </td>
                                        <td style={{ textAlign: "right" }}>
                                            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                                                <button
                                                    className="btn btn-primary"
                                                    onClick={(e) => handleViewLogs(e, rec.id)}
                                                    style={{ padding: "6px 12px", fontSize: "0.8rem" }}
                                                >
                                                    {loadingLogsId === rec.id ? (
                                                        <span style={{ display: "inline-block", width: 14, height: 14, border: "2px solid #fff", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.6s linear infinite" }} />
                                                    ) : (
                                                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                                        </svg>
                                                    )}
                                                    Ver Logs
                                                </button>
                                                <button
                                                    className="btn"
                                                    onClick={(e) => handleDownloadLogs(e, rec.id, rec)}
                                                    style={{ padding: "6px 12px", fontSize: "0.8rem", background: "linear-gradient(135deg, #16a34a, #15803d)", color: "#fff", border: "1px solid #15803d", boxShadow: "0 0 12px rgba(22,163,74,0.25)" }}
                                                >
                                                    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                                    </svg>
                                                    Descargar
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                    {expandedId === rec.id && (
                                        <tr style={{ background: "var(--surface)" }}>
                                            <td></td>
                                            <td colSpan="5" style={{ padding: "20px 24px" }}>
                                                <h5 style={{ marginBottom: 12, fontSize: "0.95rem", fontWeight: 600 }}>Eventos de Reconocimiento:</h5>
                                                {loadingLogsId === rec.id ? (
                                                    <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Cargando logs…</div>
                                                ) : !logsMap[rec.id] || logsMap[rec.id].length === 0 ? (
                                                    <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No hay eventos registrados para esta grabación.</div>
                                                ) : (
                                                    <div style={{ maxHeight: 320, overflowY: "auto" }}>
                                                        <table className="table" style={{ fontSize: "0.8rem" }}>
                                                            <thead>
                                                                <tr>
                                                                    <th>ID</th>
                                                                    <th>Timestamp</th>
                                                                    <th>Identidad</th>
                                                                    <th>Confianza</th>
                                                                    <th>¿Spoof?</th>
                                                                    <th>Score Anti-Spoof</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {logsMap[rec.id].map((log) => (
                                                                    <tr key={log.id}>
                                                                        <td style={{ color: "var(--text-muted)" }}>{log.id}</td>
                                                                        <td style={{ whiteSpace: "nowrap" }}>{formatDate(log.timestamp)}</td>
                                                                        <td>
                                                                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                                                                <span className={`dot ${log.person_name !== "Unknown" ? "dot-green" : "dot-red"}`} style={{ width: 7, height: 7, flexShrink: 0 }} />
                                                                                <span style={{ fontWeight: 500 }}>{log.person_name}</span>
                                                                            </div>
                                                                        </td>
                                                                        <td>
                                                                            {log.confidence != null
                                                                                ? `${(log.confidence * 100).toFixed(1)}%`
                                                                                : "-"}
                                                                        </td>
                                                                        <td>
                                                                            <span
                                                                                className="badge"
                                                                                style={log.is_spoof
                                                                                    ? { background: "rgba(220,38,38,0.15)", color: "#dc2626" }
                                                                                    : { background: "rgba(22,163,74,0.15)", color: "#16a34a" }}
                                                                            >
                                                                                {log.is_spoof ? "Sí" : "No"}
                                                                            </span>
                                                                        </td>
                                                                        <td>
                                                                            {log.antispoof_score != null
                                                                                ? log.antispoof_score.toFixed(3)
                                                                                : "-"}
                                                                        </td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            ))}
                        </tbody>
                    </table>
                </div>

                {nextCursor !== null && (
                    <div style={{ padding: "16px 24px", borderTop: "1px solid var(--border)", textAlign: "center" }}>
                        <button
                            className="btn"
                            onClick={() => fetchPage(nextCursor)}
                            disabled={loadingMore}
                            style={{ minWidth: 140, border: "1px solid var(--border)" }}
                        >
                            {loadingMore ? "Cargando…" : "Cargar más"}
                        </button>
                    </div>
                )}
            </div>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
    );
}
