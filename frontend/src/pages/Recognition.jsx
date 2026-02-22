import { useEffect, useRef, useState, useCallback } from "react";
import { recognizeFrame } from "../api/client";

const FRAME_INTERVAL_MS = 600;

const COLORS = {
    known: "#10b981",
    unknown: "#ef4444",
};

export default function Recognition() {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);   // hidden canvas for frame capture
    const overlayRef = useRef(null);  // visible overlay for bounding boxes
    const intervalRef = useRef(null);

    const [running, setRunning] = useState(false);
    const [faces, setFaces] = useState([]);
    const [error, setError] = useState(null);
    const [fps, setFps] = useState(0);
    const fpsCounterRef = useRef({ count: 0, last: Date.now() });

    // ── Start / stop camera ─────────────────────────────────────
    const startCamera = useCallback(async () => {
        setError(null);
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } },
                audio: false,
            });
            videoRef.current.srcObject = stream;
            await videoRef.current.play();
            setRunning(true);
        } catch (err) {
            setError("No se pudo acceder a la cámara: " + err.message);
        }
    }, []);

    const stopCamera = useCallback(() => {
        if (videoRef.current?.srcObject) {
            videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
            videoRef.current.srcObject = null;
        }
        clearInterval(intervalRef.current);
        setRunning(false);
        setFaces([]);
        // Clear overlay
        const ctx = overlayRef.current?.getContext("2d");
        if (ctx) ctx.clearRect(0, 0, overlayRef.current.width, overlayRef.current.height);
    }, []);

    // ── Capture loop ────────────────────────────────────────────
    useEffect(() => {
        if (!running) return;

        intervalRef.current = setInterval(async () => {
            const video = videoRef.current;
            const canvas = canvasRef.current;
            const overlay = overlayRef.current;
            if (!video || video.readyState < 2 || !canvas || !overlay) return;

            const W = video.videoWidth;
            const H = video.videoHeight;
            if (!W || !H) return;

            // Sync canvas sizes
            canvas.width = W;
            canvas.height = H;
            overlay.width = W;
            overlay.height = H;

            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0, W, H);

            canvas.toBlob(async (blob) => {
                if (!blob) return;
                try {
                    const data = await recognizeFrame(blob);
                    const detectedFaces = data.faces || [];
                    setFaces(detectedFaces);
                    drawOverlay(overlay, detectedFaces, W, H);

                    // FPS counter
                    const now = Date.now();
                    fpsCounterRef.current.count += 1;
                    if (now - fpsCounterRef.current.last >= 1000) {
                        setFps(fpsCounterRef.current.count);
                        fpsCounterRef.current = { count: 0, last: now };
                    }
                } catch (err) {
                    console.error("recognize error", err);
                }
            }, "image/jpeg", 0.85);
        }, FRAME_INTERVAL_MS);

        return () => clearInterval(intervalRef.current);
    }, [running]);

    // ── Draw bounding boxes ──────────────────────────────────────
    function drawOverlay(overlay, faces, W, H) {
        const ctx = overlay.getContext("2d");
        ctx.clearRect(0, 0, W, H);

        faces.forEach(({ name, similarity, box }) => {
            const { x, y, w, h } = box;
            const isKnown = name !== "Unknown";
            const color = isKnown ? COLORS.known : COLORS.unknown;
            const label = isKnown ? `${name}  ${Math.round(similarity * 100)}%` : "Desconocido";

            // Glow effect
            ctx.shadowColor = color;
            ctx.shadowBlur = 14;

            // Rectangle
            ctx.strokeStyle = color;
            ctx.lineWidth = 2.5;
            ctx.strokeRect(x, y, w, h);

            ctx.shadowBlur = 0;

            // Label background
            ctx.font = "bold 14px Inter, sans-serif";
            const textW = ctx.measureText(label).width + 16;
            const labelH = 24;
            const lx = x;
            const ly = y > labelH + 4 ? y - labelH - 4 : y + h;

            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.roundRect(lx, ly, textW, labelH, 4);
            ctx.fill();

            ctx.fillStyle = isKnown ? "#000" : "#fff";
            ctx.fillText(label, lx + 8, ly + 16);
        });
    }

    // ── Cleanup on unmount ───────────────────────────────────────
    useEffect(() => () => stopCamera(), [stopCamera]);

    return (
        <div>
            <div className="page-header">
                <h2>📹 Reconocimiento en Tiempo Real</h2>
                <p>La cámara captura frames continuamente y los envía al API de FastAPI para su análisis.</p>
            </div>

            {/* Controls */}
            <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center" }}>
                {!running ? (
                    <button className="btn btn-primary" onClick={startCamera}>
                        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                            <circle cx="12" cy="12" r="9" />
                        </svg>
                        Iniciar Cámara
                    </button>
                ) : (
                    <button className="btn btn-danger" onClick={stopCamera}>
                        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                        </svg>
                        Detener
                    </button>
                )}
                {running && (
                    <span className="badge badge-accent" style={{ fontSize: "0.78rem" }}>
                        <span className="dot dot-green" style={{ width: 6, height: 6, marginRight: 6, display: "inline-block" }} />
                        {fps} fps
                    </span>
                )}
            </div>

            {error && <div className="alert alert-danger" style={{ marginBottom: 16 }}>{error}</div>}

            {/* Video + Overlay */}
            <div
                style={{
                    position: "relative",
                    borderRadius: "var(--radius)",
                    overflow: "hidden",
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    aspectRatio: "16/9",
                    maxWidth: 900,
                }}
            >
                <video
                    ref={videoRef}
                    style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
                    playsInline
                    muted
                />
                <canvas
                    ref={overlayRef}
                    style={{
                        position: "absolute", inset: 0,
                        width: "100%", height: "100%",
                        pointerEvents: "none",
                        objectFit: "contain",
                    }}
                />
                {!running && (
                    <div style={{
                        position: "absolute", inset: 0,
                        display: "flex", flexDirection: "column",
                        alignItems: "center", justifyContent: "center",
                        gap: 12, color: "var(--text-muted)",
                    }}>
                        <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.069A1 1 0 0121 8.882V15.118a1 1 0 01-1.447.906L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                        </svg>
                        <p style={{ fontSize: "0.875rem" }}>Pulsa <strong>Iniciar Cámara</strong> para comenzar</p>
                    </div>
                )}
            </div>

            {/* Hidden capture canvas */}
            <canvas ref={canvasRef} style={{ display: "none" }} />

            {/* Face list */}
            {faces.length > 0 && (
                <div style={{ marginTop: 20, display: "flex", flexWrap: "wrap", gap: 10 }}>
                    {faces.map((f, i) => (
                        <div key={i} className="card" style={{ padding: "14px 18px", display: "flex", alignItems: "center", gap: 12 }}>
                            <span className={`dot ${f.name !== "Unknown" ? "dot-green" : "dot-red"}`} />
                            <div>
                                <div style={{ fontWeight: 600 }}>{f.name !== "Unknown" ? f.name : "Desconocido"}</div>
                                <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                                    Similitud: {Math.round(f.similarity * 100)}%
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
