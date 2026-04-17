import React, { useEffect, useState } from "react";
import { getVideoRecordings, getDownloadToken, getRecordingFileUrl, deleteRecording } from "../api/client";

export default function Logs() {
    const [recordings, setRecordings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [nextCursor, setNextCursor] = useState(null);
    const [error, setError] = useState(null);
    const [expandedId, setExpandedId] = useState(null);
    const [playingId, setPlayingId] = useState(null);
    const [videoUrls, setVideoUrls] = useState({});
    const [deletingId, setDeletingId] = useState(null);
    const [confirmDeleteId, setConfirmDeleteId] = useState(null);

    const fetchPage = async (cursor = null) => {
        const isFirstPage = cursor === null;
        if (isFirstPage) setLoading(true);
        else setLoadingMore(true);
        try {
            const data = await getVideoRecordings({ cursor });
            // Defensive: backend may return old array format during rolling deploys
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

    useEffect(() => {
        fetchPage();
    }, []);

    const formatDate = (isoStr) => {
        if (!isoStr) return "-";
        const d = new Date(isoStr);
        return d.toLocaleDateString() + " " + d.toLocaleTimeString();
    };

    const toggleExpand = (id) => {
        setExpandedId(expandedId === id ? null : id);
        // Stop playing if we collapse the row
        if (expandedId === id) setPlayingId(null);
    };

    const handleWatch = async (e, id) => {
        e.stopPropagation();
        setExpandedId(id);
        setPlayingId(id);
        try {
            const { token } = await getDownloadToken(id);
            setVideoUrls((prev) => ({ ...prev, [id]: getRecordingFileUrl(id, token) }));
        } catch (err) {
            setError("No se pudo obtener el token de reproducción: " + err.message);
        }
    };

    const handleDeleteClick = (e, id) => {
        e.stopPropagation();
        setConfirmDeleteId(id);
    };

    const handleDeleteConfirm = async (id) => {
        setConfirmDeleteId(null);
        setDeletingId(id);
        try {
            await deleteRecording(id);
            setRecordings((prev) => prev.filter((r) => r.id !== id));
            if (expandedId === id) setExpandedId(null);
            if (playingId === id) setPlayingId(null);
        } catch (err) {
            setError("No se pudo eliminar la grabación: " + err.message);
        } finally {
            setDeletingId(null);
        }
    };

    const handleDownload = async (e, id) => {
        e.stopPropagation();
        try {
            const { token } = await getDownloadToken(id);
            window.open(getRecordingFileUrl(id, token, true), "_blank");
        } catch (err) {
            setError("No se pudo descargar la grabación: " + err.message);
        }
    };

    if (loading) return <div className="skeleton" style={{ height: 300, width: "100%" }} />;

    const confirmRec = confirmDeleteId !== null && recordings.find((r) => r.id === confirmDeleteId);

    return (
        <>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

            {confirmRec && (
                <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
                    <div className="card" style={{ padding: "28px 32px", maxWidth: 400, width: "90%", textAlign: "center" }}>
                        <div style={{ marginBottom: 12 }}>
                            <svg width="40" height="40" fill="none" viewBox="0 0 24 24" stroke="#dc2626" strokeWidth={1.5} style={{ display: "block", margin: "0 auto 12px" }}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                            </svg>
                            <h4 style={{ marginBottom: 8 }}>¿Eliminar grabación?</h4>
                            <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
                                Esta acción eliminará permanentemente el archivo de video y no se puede deshacer.
                            </p>
                            <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", marginTop: 6 }}>
                                {confirmRec.file_path.split(/[\\/]/).pop()}
                            </p>
                        </div>
                        <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 20 }}>
                            <button className="btn" onClick={() => setConfirmDeleteId(null)} style={{ minWidth: 100, border: "1px solid var(--border)" }}>
                                Cancelar
                            </button>
                            <button
                                className="btn"
                                onClick={() => handleDeleteConfirm(confirmDeleteId)}
                                style={{ minWidth: 100, background: "linear-gradient(135deg, #dc2626, #b91c1c)", color: "#fff", border: "1px solid #b91c1c" }}
                            >
                                Eliminar
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div className="logs-page">
            <div className="page-header">
                <h2>📜 Registro de Grabaciones e Historial</h2>
                <p>Visualiza las grabaciones realizadas y las personas identificadas en cada sesión.</p>
            </div>

            {error && <div className="alert alert-danger" style={{ marginBottom: 20 }}>{error}</div>}

            <div className="card">
                <div className="table-container">
                    <table className="table">
                        <thead>
                            <tr>
                                <th style={{ width: 40 }}></th>
                                <th>Fecha y Hora</th>
                                <th>Duración</th>
                                <th style={{ textAlign: "right" }}>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recordings.length === 0 ? (
                                <tr><td colSpan="4" style={{ textAlign: "center", padding: "40px 20px" }}>No hay grabaciones registradas.</td></tr>
                            ) : (recordings.map((rec) => (
                                    <React.Fragment key={rec.id}>
                                        <tr
                                            onClick={() => toggleExpand(rec.id)}
                                            style={{ cursor: "pointer" }}
                                            className={expandedId === rec.id ? "row-selected" : ""}
                                        >
                                            <td>
                                                <svg
                                                    width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                                                    style={{ transform: expandedId === rec.id ? 'rotate(90deg)' : 'none', transition: '0.2s' }}
                                                >
                                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                                                </svg>
                                            </td>
                                            <td>
                                                <div style={{ fontWeight: 600 }}>{formatDate(rec.start_time)}</div>
                                                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{rec.file_path.split(/[\\/]/).pop()}</div>
                                            </td>
                                            <td>
                                                {rec.end_time ? (
                                                    <span>{Math.round((new Date(rec.end_time) - new Date(rec.start_time)) / 1000)}s</span>
                                                ) : (
                                                    <span className="badge badge-accent">En curso...</span>
                                                )}
                                            </td>
                                            <td style={{ textAlign: "right" }}>
                                                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                                                    <button
                                                        className="btn btn-primary"
                                                        onClick={(e) => handleWatch(e, rec.id)}
                                                        style={{ padding: "6px 12px", fontSize: "0.8rem" }}
                                                    >
                                                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                                            <circle cx="12" cy="12" r="9" />
                                                        </svg>
                                                        Mirar
                                                    </button>
                                                    <button
                                                        className="btn"
                                                        onClick={(e) => handleDownload(e, rec.id)}
                                                        style={{ padding: "6px 12px", fontSize: "0.8rem", background: "linear-gradient(135deg, #16a34a, #15803d)", color: "#fff", border: "1px solid #15803d", boxShadow: "0 0 12px rgba(22,163,74,0.25)" }}
                                                    >
                                                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                                        </svg>
                                                        Descargar
                                                    </button>
                                                    <button
                                                        className="btn"
                                                        onClick={(e) => handleDeleteClick(e, rec.id)}
                                                        disabled={deletingId === rec.id}
                                                        style={{ padding: "6px 12px", fontSize: "0.8rem", background: "linear-gradient(135deg, #dc2626, #b91c1c)", color: "#fff", border: "1px solid #b91c1c", boxShadow: "0 0 12px rgba(220,38,38,0.25)" }}
                                                    >
                                                        {deletingId === rec.id ? (
                                                            <span style={{ display: "inline-block", width: 14, height: 14, border: "2px solid #fff", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.6s linear infinite" }} />
                                                        ) : (
                                                            <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                            </svg>
                                                        )}
                                                        Eliminar
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                        {expandedId === rec.id && (
                                            <tr style={{ background: "var(--surface)" }}>
                                                <td></td>
                                                <td colSpan="3" style={{ padding: "20px 24px" }}>
                                                    <div style={{ display: "grid", gridTemplateColumns: playingId === rec.id ? "1fr 1fr" : "1fr", gap: 24, alignItems: "start" }}>
                                                        {/* Info Panel */}
                                                        <div>
                                                            <h5 style={{ marginBottom: 12, fontSize: "0.95rem", fontWeight: 600 }}>Personas Identificadas (Consolidado):</h5>
                                                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                                                                {rec.detected_people && rec.detected_people.length > 0 ? (
                                                                    rec.detected_people.map((p, i) => (
                                                                        <div key={i} className="card" style={{ padding: "8px 12px", background: "var(--bg)", display: "flex", alignItems: "center", gap: 8 }}>
                                                                            <span className={`dot ${p !== "Unknown" ? "dot-green" : "dot-red"}`} style={{ width: 8, height: 8 }} />
                                                                            <span style={{ fontWeight: 500, fontSize: "0.85rem" }}>{p}</span>
                                                                        </div>
                                                                    ))
                                                                ) : (
                                                                    <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No se identificó a nadie en esta grabación.</div>
                                                                )}
                                                            </div>
                                                        </div>

                                                        {/* Video Player Panel */}
                                                        {playingId === rec.id && (
                                                            <div style={{ borderRadius: "var(--radius)", overflow: "hidden", border: "1px solid var(--border)", background: "#000" }}>
                                                                {videoUrls[rec.id] ? (
                                                                    <video
                                                                        key={videoUrls[rec.id]}
                                                                        controls
                                                                        autoPlay
                                                                        style={{ width: "100%", display: "block" }}
                                                                    >
                                                                        <source src={videoUrls[rec.id]} type="video/mp4" />
                                                                        Tu navegador no soporta la reproducción de este video.
                                                                    </video>
                                                                ) : (
                                                                    <div style={{ padding: 20, color: "#aaa", textAlign: "center" }}>Cargando video…</div>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                ))
                            )}
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
        </div>
        </>
    );
}
