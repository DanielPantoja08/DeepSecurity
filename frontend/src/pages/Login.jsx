import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { loginUser, registerUser } from "../api/auth";

export default function Login() {
  const { login } = useAuth();
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const switchMode = (newMode) => {
    setMode(newMode);
    setError("");
    setPassword("");
    setConfirmPassword("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (mode === "register" && password !== confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }

    setLoading(true);
    try {
      if (mode === "register") {
        await registerUser(email, password);
      }
      const data = await loginUser(email, password);
      login(data.access_token);
    } catch (err) {
      setError(err.message || (mode === "register" ? "Error al registrar usuario" : "Error al iniciar sesión"));
    } finally {
      setLoading(false);
    }
  };

  const isRegister = mode === "register";

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Brand */}
        <div className="login-brand">
          <span className="login-shield">🛡️</span>
          <h1 className="login-title">DeepSecurity</h1>
          <p className="login-subtitle">Sistema de Identificación AI</p>
        </div>

        {/* Mode tabs */}
        <div className="login-tabs">
          <button
            type="button"
            className={`login-tab${!isRegister ? " login-tab--active" : ""}`}
            onClick={() => switchMode("login")}
          >
            Iniciar Sesión
          </button>
          <button
            type="button"
            className={`login-tab${isRegister ? " login-tab--active" : ""}`}
            onClick={() => switchMode("register")}
          >
            Registrarse
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label htmlFor="email">Correo electrónico</label>
            <input
              id="email"
              className="input"
              type="email"
              placeholder="usuario@deepsecurity.ai"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="login-field">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              className="input"
              type="password"
              placeholder="••••••••"
              autoComplete={isRegister ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {isRegister && (
            <div className="login-field">
              <label htmlFor="confirmPassword">Confirmar contraseña</label>
              <input
                id="confirmPassword"
                className="input"
                type="password"
                placeholder="••••••••"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
          )}

          {error && (
            <div className="alert alert-danger" role="alert">
              <svg
                width="16"
                height="16"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                style={{ flexShrink: 0, marginTop: 1 }}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
                />
              </svg>
              {error}
            </div>
          )}

          <button
            className="btn btn-primary login-btn"
            type="submit"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="login-spinner" />
                {isRegister ? "Registrando…" : "Autenticando…"}
              </>
            ) : isRegister ? (
              <>
                <svg
                  width="16"
                  height="16"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
                  />
                </svg>
                Crear cuenta
              </>
            ) : (
              <>
                <svg
                  width="16"
                  height="16"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"
                  />
                </svg>
                Iniciar Sesión
              </>
            )}
          </button>
        </form>

        <p className="login-footer">
          {isRegister
            ? "El primer usuario registrado obtendrá privilegios de administrador"
            : "Acceso restringido — solo personal autorizado"}
        </p>
      </div>
    </div>
  );
}
