import { useEffect, useRef, useState, useCallback } from "react";
import { recognizeFrame, startRecording, stopRecording, getRecordingStatus } from "../api/client";

const COLORS = { known: "#10b981", unknown: "#ef4444", spoof: "#f59e0b" };
const LERP = 0.35;

function lerp(a, b, t) { return a + (b - a) * t; }
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

/**
 * A single camera tile that captures frames from a specific webcam device,
 * sends them to the backend tagged with camera_id, and displays the overlay.
 */
export default function CameraTile({ camera, tileCount = 1 }) {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const overlayRef = useRef(null);
    const cancelledRef = useRef(false);
    const animFrameRef = useRef(null);
    const interpRef = useRef([]);
    const isRecordingRef = useRef(false);
    const fpsCounterRef = useRef({ count: 0, last: Date.now() });

    const [running, setRunning] = useState(false);
    const [faces, setFaces] = useState([]);
    const [error, setError] = useState(null);
    const [fps, setFps] = useState(0);
    const [isRecording, _setIsRecording] = useState(false);
    const [recordingLoading, setRecordingLoading] = useState(false);

    const setIsRecording = (val) => {
        isRecordingRef.current = val;
        _setIsRecording(val);
    };

    // Reduce quality when many tiles share bandwidth
    const frameQuality = tileCount > 2 ? 0.55 : 0.75;

    const startCamera = useCallback(async () => {
        setError(null);
        cancelledRef.current = false;
        try {
            const statusData = await getRecordingStatus();
            const camStatus = statusData.cameras?.[camera.id];
            if (camStatus?.is_recording) setIsRecording(true);

            const constraints = { video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false };
            // If the camera has a known device label, try to match it
            if (camera.device_label) {
                constraints.video.facingMode = undefined;
                // Use deviceId if we stored the hash and can find a matching device
            }
            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            videoRef.current.srcObject = stream;
            await videoRef.current.play();
            setRunning(true);
        } catch (err) {
            setError("Sin acceso: " + err.message);
        }
    }, [camera]);

    const handleToggleRecording = useCallback(async () => {
        if (!running) return;
        setRecordingLoading(true);
        try {
            if (isRecordingRef.current) {
                await stopRecording(camera.id);
                setIsRecording(false);
            } else {
                await startRecording(camera.id);
                setIsRecording(true);
            }
        } catch (err) {
            setError("Error grabación: " + err.message);
        } finally {
            setRecordingLoading(false);
        }
    }, [running, camera.id]);

    const stopCamera = useCallback(() => {
        if (isRecordingRef.current) handleToggleRecording();
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
    }, [handleToggleRecording]);

    // Response-gated capture loop
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
                        canvas.toBlob((b) => res(b), "image/jpeg", frameQuality)
                    );
                    if (!blob || cancelledRef.current) break;

                    const data = await recognizeFrame(blob, camera.id);
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
    }, [running, camera.id, frameQuality]);

    // Smooth overlay animation
    useEffect(() => {
        if (!running) return;
        function animate() {
            const overlay = overlayRef.current;
            if (overlay && overlay.width && overlay.height) {
                drawOverlay(overlay, interpRef.current, overlay.width, overlay.height);
            }
            animFrameRef.current = requestAnimationFrame(animate);
        }
        animFrameRef.current = requestAnimationFrame(animate);
        return () => { if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current); };
    }, [running]);

    useEffect(() => {
        const video = videoRef.current;
        return () => {
            cancelledRef.current = true;
            if (video?.srcObject) video.srcObject.getTracks().forEach((t) => t.stop());
        };
    }, []);

    function updateInterp(newFaces) {
        const prev = interpRef.current;
        const used = new Set();
        interpRef.current = newFaces.map((face) => {
            const cx = face.box.x + face.box.w / 2;
            const cy = face.box.y + face.box.h / 2;
            let bestMatch = null, bestDist = Infinity;
            prev.forEach((p, idx) => {
                if (used.has(idx)) return;
                const pcx = p.interp.x + p.interp.w / 2;
                const pcy = p.interp.y + p.interp.h / 2;
                const dist = Math.hypot(cx - pcx, cy - pcy);
                if (dist < bestDist) { bestDist = dist; bestMatch = idx; }
            });
            if (bestMatch !== null && bestDist < 300) {
                used.add(bestMatch);
                return { ...face, interp: { ...prev[bestMatch].interp }, target: { ...face.box } };
            }
            return { ...face, interp: { ...face.box }, target: { ...face.box } };
        });
    }

    function drawOverlay(overlay, faces, W, H) {
        const ctx = overlay.getContext("2d");
        ctx.clearRect(0, 0, W, H);
        faces.forEach((face) => {
            if (face.target) {
                face.interp.x = lerp(face.interp.x, face.target.x, LERP);
                face.interp.y = lerp(face.interp.y, face.target.y, LERP);
                face.interp.w = lerp(face.interp.w, face.target.w, LERP);
                face.interp.h = lerp(face.interp.h, face.target.h, LERP);
            }
            const { x, y, w, h } = face.interp || face.box;
            const isSpoof = face.is_real === false;
            const isKnown = face.name !== "Unknown";
            const color = !isKnown ? COLORS.unknown : (isSpoof ? COLORS.spoof : COLORS.known);
            const label = isKnown ? `${face.name}  ${Math.round(face.similarity * 100)}%` : "Desconocido";

            ctx.shadowColor = color;
            ctx.shadowBlur = 14;
            ctx.strokeStyle = color;
            ctx.lineWidth = 2.5;
            ctx.strokeRect(x, y, w, h);
            ctx.shadowBlur = 0;

            ctx.font = "bold 13px Inter, sans-serif";
            const textW = ctx.measureText(label).width + 14;
            const labelH = 22;
            const lx = x;
            const ly = y > labelH + 4 ? y - labelH - 4 : y + h;
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.roundRect(lx, ly, textW, labelH, 4);
            ctx.fill();
            ctx.fillStyle = !isKnown ? "#fff" : "#000";
            ctx.fillText(label, lx + 7, ly + 15);
        });
    }

    return (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            {/* Tile header */}
            <div style={{
                padding: "10px 14px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                borderBottom: "1px solid var(--border)",
                background: "var(--surface)",
            }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{camera.name}</span>
                    {running && (
                        <span className="badge badge-accent" style={{ fontSize: "0.72rem" }}>
                            <span className="dot dot-green" style={{ width: 5, height: 5, marginRight: 5, display: "inline-block" }} />
                            {fps} fps
                        </span>
                    )}
                    {isRecording && (
                        <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: "0.75rem", color: "#ef4444", fontWeight: 600 }}>
                            <span className="rec-dot animate-pulse" />
                            REC
                        </span>
                    )}
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                    {!running ? (
                        <button className="btn btn-primary" onClick={startCamera} style={{ padding: "5px 12px", fontSize: "0.78rem" }}>
                            Iniciar
                        </button>
                    ) : (
                        <>
                            <button
                                className="btn"
                                onClick={handleToggleRecording}
                                disabled={recordingLoading}
                                style={{
                                    padding: "5px 12px", fontSize: "0.78rem",
                                    background: isRecording ? "linear-gradient(135deg,#dc2626,#b91c1c)" : undefined,
                                    color: isRecording ? "#fff" : undefined,
                                    border: isRecording ? "1px solid #b91c1c" : "1px solid var(--border)",
                                }}
                            >
                                {isRecording ? "⏹ Parar" : "⏺ Grabar"}
                            </button>
                            <button className="btn btn-danger" onClick={stopCamera} style={{ padding: "5px 12px", fontSize: "0.78rem" }}>
                                Detener
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Video area */}
            <div style={{ position: "relative", background: "var(--surface)", aspectRatio: "16/9" }}>
                <video
                    ref={videoRef}
                    style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
                    playsInline
                    muted
                />
                <canvas
                    ref={overlayRef}
                    style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none", objectFit: "contain" }}
                />
                {!running && (
                    <div style={{
                        position: "absolute", inset: 0,
                        display: "flex", flexDirection: "column",
                        alignItems: "center", justifyContent: "center",
                        gap: 8, color: "var(--text-muted)",
                    }}>
                        <svg width="36" height="36" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.069A1 1 0 0121 8.882V15.118a1 1 0 01-1.447.906L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                        </svg>
                        <p style={{ fontSize: "0.8rem" }}>Pulsa <strong>Iniciar</strong></p>
                    </div>
                )}
                {error && (
                    <div style={{
                        position: "absolute", inset: 0,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        background: "rgba(0,0,0,0.6)",
                    }}>
                        <span style={{ color: "#ef4444", fontSize: "0.8rem", padding: "0 16px", textAlign: "center" }}>{error}</span>
                    </div>
                )}
            </div>

            {/* Face badges */}
            {faces.length > 0 && (
                <div style={{ padding: "10px 14px", display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {faces.map((f, i) => {
                        const isSpoof = f.is_real === false;
                        const isKnown = f.name !== "Unknown";
                        const dotClass = !isKnown ? "dot-red" : (isSpoof ? "dot-orange" : "dot-green");
                        return (
                            <div key={i} className="card" style={{ padding: "6px 12px", display: "flex", alignItems: "center", gap: 8, background: "var(--bg)" }}>
                                <span className={`dot ${dotClass}`} style={isKnown && isSpoof ? { backgroundColor: "#f59e0b" } : {}} />
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: "0.82rem" }}>{isKnown ? f.name : "Desconocido"}</div>
                                    <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>{Math.round(f.similarity * 100)}%</div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            <canvas ref={canvasRef} style={{ display: "none" }} />
        </div>
    );
}
