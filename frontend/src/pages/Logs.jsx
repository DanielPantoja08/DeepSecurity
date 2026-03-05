import React, { useEffect, useState } from "react";
import { getRecordingStatus, getVideoRecordings } from "../api/client";

export default function Logs() {
    const [recordings, setRecordings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedId, setExpandedId] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const recsData = await getVideoRecordings();
                setRecordings(recsData);
            } catch (err) {
                setError("Error al cargar grabaciones: " + err.message);
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

    const toggleExpand = (id) => {
        setExpandedId(expandedId === id ? null : id);
    };

    if (loading) return <div className="skeleton" style={{ height: 300, width: "100%" }} />;

    return (
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
                                <th>Personas Detectadas</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recordings.length === 0 ? (
                                <tr><td colSpan="4" style={{ textAlign: "center", padding: "40px 20px" }}>No hay grabaciones registradas.</td></tr>
                            ) : (
                                recordings.map((rec) => (
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
                                            <td>
                                                {rec.detected_people && rec.detected_people.length > 0 ? (
                                                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                                                        {rec.detected_people.slice(0, 3).map((p, i) => (
                                                            <span key={i} className="badge" style={{ fontSize: "0.7rem" }}>{p}</span>
                                                        ))}
                                                        {rec.detected_people.length > 3 && (
                                                            <span className="badge" style={{ fontSize: "0.7rem" }}>+{rec.detected_people.length - 3}</span>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Nadie detectado</span>
                                                )}
                                            </td>
                                        </tr>
                                        {expandedId === rec.id && (
                                            <tr style={{ background: "var(--surface)" }}>
                                                <td></td>
                                                <td colSpan="3" style={{ padding: "16px 24px" }}>
                                                    <h5 style={{ marginBottom: 10, fontSize: "0.9rem", color: "var(--text-muted)" }}>Personas Identificadas (Consolidado):</h5>
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
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
