import { useEffect, useRef, useState, useCallback } from "react";
import { recognizeFrame, startRecording, stopRecording, getRecordingStatus } from "../api/client";

const COLORS = {
    known: "#10b981",
    unknown: "#ef4444",
};

const LERP = 0.35;

export default function Recognition() {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const overlayRef = useRef(null);

    const [running, setRunning] = useState(false);
    const [faces, setFaces] = useState([]);
    const [error, setError] = useState(null);
    const [fps, setFps] = useState(0);

    const isRecordingRef = useRef(false);
    const [isRecording, _setIsRecording] = useState(false);
    const setIsRecording = (val) => {
        isRecordingRef.current = val;
        _setIsRecording(val);
    };

    const [recordingLoading, setRecordingLoading] = useState(false);
    const fpsCounterRef = useRef({ count: 0, last: Date.now() });
    const cancelledRef = useRef(false);
    const animFrameRef = useRef(null);
    const interpRef = useRef([]);


    // ── Start / stop camera ─────────────────────────────────────
    const startCamera = useCallback(async () => {
        setError(null);
        cancelledRef.current = false;
        try {
            // Synchronize recording state with backend on start
            const status = await getRecordingStatus();
            setIsRecording(status.is_recording);

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
        if (isRecordingRef.current) handleToggleRecording(); // Stop recording if camera stops
        cancelledRef.current = true;
        if (videoRef.current?.srcObject) {
            videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
            videoRef.current.srcObject = null;
        }
        if (animFrameRef.current) {
            cancelAnimationFrame(animFrameRef.current);
            animFrameRef.current = null;
        }
        setRunning(false);
        setFaces([]);
        interpRef.current = [];
        const ctx = overlayRef.current?.getContext("2d");
        if (ctx) ctx.clearRect(0, 0, overlayRef.current.width, overlayRef.current.height);
    }, []);

    // ── Recording toggle ────────────────────────────────────────
    const handleToggleRecording = useCallback(async () => {
        if (!running) return;
        setRecordingLoading(true);
        try {
            if (isRecordingRef.current) {
                await stopRecording();
                setIsRecording(false);
            } else {
                await startRecording();
                setIsRecording(true);
            }
        } catch (err) {
            setError("Error con la grabación: " + err.message);
        } finally {
            setRecordingLoading(false);
        }
    }, [running]);

    // ── Response-gated capture loop ─────────────────────────────
    useEffect(() => {
        if (!running) return;
        let active = true;

        async function loop() {
            while (active && !cancelledRef.current) {
                const video = videoRef.current;
                const canvas = canvasRef.current;
                const overlay = overlayRef.current;
                if (!video || video.readyState < 2 || !canvas || !overlay) {
                    await sleep(100);
                    continue;
                }

                const W = video.videoWidth;
                const H = video.videoHeight;
                if (!W || !H) { await sleep(100); continue; }

                canvas.width = W;
                canvas.height = H;
                overlay.width = W;
                overlay.height = H;

                const ctx = canvas.getContext("2d");
                ctx.drawImage(video, 0, 0, W, H);

                try {
                    const blob = await new Promise((res) =>
                        canvas.toBlob((b) => res(b), "image/jpeg", 0.75)
                    );
                    if (!blob || cancelledRef.current) break;

                    const data = await recognizeFrame(blob);
                    if (cancelledRef.current) break;

                    const detectedFaces = data.faces || [];
                    setFaces(detectedFaces);
                    updateInterp(detectedFaces);

                    const now = Date.now();
                    fpsCounterRef.current.count += 1;
                    if (now - fpsCounterRef.current.last >= 1000) {
                        setFps(fpsCounterRef.current.count);
                        fpsCounterRef.current = { count: 0, last: now };
                    }
                } catch (err) {
                    console.error("recognize error", err);
                    await sleep(500);
                }
            }
        }

        loop();
        return () => { active = false; };
    }, [running]);

    // ── Smooth overlay animation ────────────────────────────────
    useEffect(() => {
        if (!running) return;
        function animate() {
            const overlay = overlayRef.current;
            if (overlay) {
                const W = overlay.width;
                const H = overlay.height;
                if (W && H) drawOverlay(overlay, interpRef.current, W, H);
            }
            animFrameRef.current = requestAnimationFrame(animate);
        }
        animFrameRef.current = requestAnimationFrame(animate);
        return () => { if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current); };
    }, [running]);

    /**
     * Match each new detection to the closest previous box by centroid distance.
     * Only updates `target` — `interp` is advanced toward target in drawOverlay
     * at 60fps so the animation remains smooth without double-LERPing.
     */
    function updateInterp(newFaces) {
        const prev = interpRef.current;
        const used = new Set();

        interpRef.current = newFaces.map((face) => {
            const cx = face.box.x + face.box.w / 2;
            const cy = face.box.y + face.box.h / 2;

            let bestMatch = null;
            let bestDist = Infinity;

            prev.forEach((p, idx) => {
                if (used.has(idx)) return;
                const pcx = p.interp.x + p.interp.w / 2;
                const pcy = p.interp.y + p.interp.h / 2;
                const dist = Math.hypot(cx - pcx, cy - pcy);
                if (dist < bestDist) { bestDist = dist; bestMatch = idx; }
            });

            if (bestMatch !== null && bestDist < 300) {
                used.add(bestMatch);
                // Keep the current interpolated position — drawOverlay will advance it
                return {
                    ...face,
                    interp: { ...prev[bestMatch].interp },
                    target: { ...face.box },
                };
            }
            // New face — snap immediately so it doesn't fly in from (0,0)
            return { ...face, interp: { ...face.box }, target: { ...face.box } };
        });
    }

    function drawOverlay(overlay, faces, W, H) {
        const ctx = overlay.getContext("2d");
        ctx.clearRect(0, 0, W, H);
        faces.forEach((face) => {
            // Advance interp → target each animation frame (60fps) for smooth movement.
            // updateInterp() only sets the target on API responses, so there's no double-LERP.
            if (face.target) {
                face.interp.x = lerp(face.interp.x, face.target.x, LERP);
                face.interp.y = lerp(face.interp.y, face.target.y, LERP);
                face.interp.w = lerp(face.interp.w, face.target.w, LERP);
                face.interp.h = lerp(face.interp.h, face.target.h, LERP);
            }
            const { x, y, w, h } = face.interp || face.box;
            const isKnown = face.name !== "Unknown";
            const color = isKnown ? COLORS.known : COLORS.unknown;
            const label = isKnown ? `${face.name}  ${Math.round(face.similarity * 100)}%` : "Desconocido";

            ctx.shadowColor = color;
            ctx.shadowBlur = 14;
            ctx.strokeStyle = color;
            ctx.lineWidth = 2.5;
            ctx.strokeRect(x, y, w, h);
            ctx.shadowBlur = 0;

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

    useEffect(() => {
        return () => {
            cancelledRef.current = true;
            if (videoRef.current?.srcObject) {
                videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
            }
        };
    }, []);

    // ── RENDER ──────────────────────────────────────────────────


    // Step 2: Recognition view (DB is set)
    return (
        <div>
            <div className="page-header">
                <h2>📹 Reconocimiento en Tiempo Real</h2>
                <p>La cámara captura frames continuamente y los envía al API para su análisis.</p>
            </div>

            {/* DB indicator + controls */}
            <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center", flexWrap: "wrap" }}>
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
                    <button
                        className={`btn ${isRecording ? "btn-danger" : ""}`}
                        onClick={handleToggleRecording}
                        disabled={recordingLoading}
                        style={{ border: "1px solid var(--border)" }}
                    >
                        {isRecording ? (
                            <>
                                <span className="rec-dot" />
                                Detener Grabación
                            </>
                        ) : (
                            <>
                                <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <circle cx="12" cy="12" r="6" fill="#ef4444" />
                                    <circle cx="12" cy="12" r="9" stroke="#ef4444" />
                                </svg>
                                Grabar Video
                            </>
                        )}
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
                {isRecording && (
                    <div className="rec-overlay">
                        <span className="rec-dot animate-pulse" />
                        REC
                    </div>
                )}
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

            <canvas ref={canvasRef} style={{ display: "none" }} />

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

function lerp(a, b, t) { return a + (b - a) * t; }
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
