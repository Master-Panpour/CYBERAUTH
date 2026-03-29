import { useState, useEffect, useRef } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ─── Auth API (tokens stored in memory, NOT localStorage) ────────────────────
// Access token lives only in module-level memory. It is lost on page reload,
// which is intentional: on reload we use the refresh token (HttpOnly cookie,
// set server-side) to silently obtain a new access token.
// This prevents XSS from stealing tokens via localStorage.

let _accessToken = null;

const authApi = {
  getToken: () => _accessToken,
  setToken: (t) => { _accessToken = t; },
  clearToken: () => { _accessToken = null; },

  login: async (email, password) => {
    const form = new URLSearchParams({ username: email, password });
    const res = await fetch(`${API}/auth/login`, {
      method: "POST",
      credentials: "include",   // sends/receives HttpOnly cookies
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Login failed");
    }
    const data = await res.json();
    _accessToken = data.access_token;  // keep only in memory
    return data;
  },

  register: async (email, username, password) => {
    const res = await fetch(`${API}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Registration failed");
    }
    return res.json();
  },

  refresh: async () => {
    // Uses HttpOnly refresh-token cookie automatically
    const res = await fetch(`${API}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: "" }), // server reads cookie
    });
    if (!res.ok) return null;
    const data = await res.json();
    _accessToken = data.access_token;
    return data;
  },

  me: async () => {
    if (!_accessToken) return null;
    const res = await fetch(`${API}/auth/me`, {
      headers: { Authorization: `Bearer ${_accessToken}` },
      credentials: "include",
    });
    if (!res.ok) return null;
    return res.json();
  },

  logout: async () => {
    if (_accessToken) {
      await fetch(`${API}/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: { Authorization: `Bearer ${_accessToken}` },
      }).catch(() => {});
    }
    _accessToken = null;
  },

  // FIX: exchange short-lived code from OAuth redirect (not token-in-URL)
  exchangeOAuthCode: async (code) => {
    const res = await fetch(`${API}/auth/oauth/exchange`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (!res.ok) throw new Error("OAuth exchange failed");
    const data = await res.json();
    _accessToken = data.access_token;
    return data;
  },

  googleLogin: () => { window.location.href = `${API}/auth/google`; },
  githubLogin: () => { window.location.href = `${API}/auth/github`; },
};

// ─── Password strength meter ──────────────────────────────────────────────────
function passwordStrength(pw) {
  let score = 0;
  if (pw.length >= 12) score++;
  if (pw.length >= 16) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[a-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 2) return { label: "Weak", color: "#E24B4A", width: "25%" };
  if (score <= 4) return { label: "Fair", color: "#EF9F27", width: "55%" };
  return { label: "Strong", color: "#00ffb4", width: "100%" };
}

// ─── Neural Canvas ─────────────────────────────────────────────────────────────
function NeuralCanvas() {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const nodes = useRef([]);
  const mouse = useRef({ x: -9999, y: -9999 });

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let W, H;
    const resize = () => {
      W = canvas.width = canvas.offsetWidth;
      H = canvas.height = canvas.offsetHeight;
      nodes.current = Array.from({ length: 70 }, () => ({
        x: Math.random() * W, y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.4, vy: (Math.random() - 0.5) * 0.4,
        r: Math.random() * 1.8 + 0.8, pulse: Math.random() * Math.PI * 2,
      }));
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    canvas.addEventListener("mousemove", (e) => {
      const r = canvas.getBoundingClientRect();
      mouse.current = { x: e.clientX - r.left, y: e.clientY - r.top };
    });
    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      nodes.current.forEach((n) => {
        n.x += n.vx; n.y += n.vy; n.pulse += 0.018;
        if (n.x < 0 || n.x > W) n.vx *= -1;
        if (n.y < 0 || n.y > H) n.vy *= -1;
        const dx = n.x - mouse.current.x, dy = n.y - mouse.current.y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < 100) { n.x += (dx / d) * 1.2; n.y += (dy / d) * 1.2; }
      });
      for (let i = 0; i < nodes.current.length; i++)
        for (let j = i + 1; j < nodes.current.length; j++) {
          const a = nodes.current[i], b = nodes.current[j];
          const dx = a.x - b.x, dy = a.y - b.y, d = Math.sqrt(dx * dx + dy * dy);
          if (d < 110) {
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(0,255,180,${(1 - d / 110) * 0.4})`; ctx.lineWidth = 0.5; ctx.stroke();
          }
        }
      nodes.current.forEach((n) => {
        const g = 0.5 + Math.sin(n.pulse) * 0.5;
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0,255,180,${g})`; ctx.fill();
      });
      animRef.current = requestAnimationFrame(draw);
    };
    animRef.current = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(animRef.current); ro.disconnect(); };
  }, []);

  return (
    <canvas ref={canvasRef} style={{
      position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.5,
    }} />
  );
}

// ─── Glitch Text ──────────────────────────────────────────────────────────────
function GlitchText({ text }) {
  const [glitch, setGlitch] = useState(false);
  useEffect(() => {
    const id = setInterval(() => { setGlitch(true); setTimeout(() => setGlitch(false), 110); }, 3500);
    return () => clearInterval(id);
  }, []);
  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      {text}
      {glitch && (
        <>
          <span style={{ position: "absolute", top: 0, left: "2px", color: "#ff003c", opacity: 0.8, clipPath: "inset(30% 0 40% 0)" }}>{text}</span>
          <span style={{ position: "absolute", top: 0, left: "-2px", color: "#00ffea", opacity: 0.8, clipPath: "inset(60% 0 10% 0)" }}>{text}</span>
        </>
      )}
    </span>
  );
}

// ─── Cyber Input ──────────────────────────────────────────────────────────────
function CyberInput({ label, type = "text", value, onChange, icon, maxLength }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ marginBottom: "18px" }}>
      <label style={{ display: "block", fontSize: "10px", letterSpacing: "3px", color: "#00ffb4", textTransform: "uppercase", marginBottom: "7px", fontFamily: "'Share Tech Mono', monospace" }}>
        {icon} {label}
      </label>
      <input
        type={type} value={value} onChange={onChange} maxLength={maxLength}
        onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
        style={{
          width: "100%", boxSizing: "border-box",
          background: "rgba(0,255,180,0.04)",
          border: `1px solid ${focused ? "#00ffb4" : "rgba(0,255,180,0.2)"}`,
          borderRadius: "4px", color: "#e0fff5", padding: "11px 14px",
          fontSize: "14px", fontFamily: "'Share Tech Mono', monospace",
          outline: "none", transition: "all 0.2s",
          boxShadow: focused ? "0 0 18px rgba(0,255,180,0.12)" : "none",
        }}
      />
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [user, setUser] = useState(null);

  const strength = mode === "register" ? passwordStrength(password) : null;

  const styles = `
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #020d0a; }
    @keyframes fadeIn { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
    @keyframes borderGlow { 0%,100%{border-color:rgba(0,255,180,0.22)} 50%{border-color:rgba(0,255,180,0.55)} }
  `;

  // Try silent refresh on mount (uses HttpOnly cookie automatically)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (code) {
      window.history.replaceState({}, "", window.location.pathname);
      authApi.exchangeOAuthCode(code)
        .then((data) => { setUser(data.user); setSuccess("OAuth login successful!"); })
        .catch((e) => setError(e.message));
      return;
    }
    authApi.me().then((u) => { if (u) setUser(u); });
  }, []);

  const handleSubmit = async () => {
    setError(""); setSuccess(""); setLoading(true);
    try {
      if (mode === "login") {
        const data = await authApi.login(email, password);
        setUser(data.user);
        setSuccess("ACCESS GRANTED");
      } else {
        await authApi.register(email, username, password);
        setSuccess("ACCOUNT CREATED — you may now log in");
        setMode("login");
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await authApi.logout();
    setUser(null); setSuccess(""); setError("");
  };

  if (user) {
    return (
      <>
        <style>{styles}</style>
        <div style={{ minHeight: "100vh", background: "#020d0a", display: "flex", alignItems: "center", justifyContent: "center", position: "relative", overflow: "hidden", fontFamily: "'Share Tech Mono', monospace" }}>
          <NeuralCanvas />
          <div style={{ position: "relative", zIndex: 1, textAlign: "center", background: "rgba(2,20,14,0.92)", border: "1px solid rgba(0,255,180,0.3)", borderRadius: "8px", padding: "48px 52px", maxWidth: "420px", width: "90%", animation: "fadeIn 0.5s ease" }}>
            <div style={{ fontSize: "48px", marginBottom: "14px" }}>
              {user.avatar_url ? <img src={user.avatar_url} alt="" style={{ width: 68, height: 68, borderRadius: "50%", border: "2px solid #00ffb4" }} /> : "🛡️"}
            </div>
            <div style={{ color: "#00ffb4", fontSize: "10px", letterSpacing: "4px", marginBottom: "8px" }}>ACCESS GRANTED</div>
            <h2 style={{ color: "#e0fff5", fontSize: "20px", fontFamily: "'Orbitron', monospace", marginBottom: "6px" }}>{user.username}</h2>
            <div style={{ color: "rgba(0,255,180,0.5)", fontSize: "12px", marginBottom: "28px" }}>{user.email} · via {user.auth_provider.toUpperCase()}</div>
            <button onClick={handleLogout} style={{ background: "transparent", border: "1px solid rgba(255,60,60,0.4)", color: "#ff6060", padding: "10px 26px", borderRadius: "4px", fontFamily: "'Share Tech Mono', monospace", fontSize: "11px", letterSpacing: "2px", cursor: "pointer" }}>
              DISCONNECT SESSION
            </button>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <style>{styles}</style>
      <div style={{ minHeight: "100vh", background: "#020d0a", display: "flex", alignItems: "center", justifyContent: "center", position: "relative", overflow: "hidden", fontFamily: "'Share Tech Mono', monospace" }}>
        <NeuralCanvas />
        <div style={{ position: "absolute", inset: 0, backgroundImage: "linear-gradient(rgba(0,255,180,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,180,0.025) 1px, transparent 1px)", backgroundSize: "38px 38px", pointerEvents: "none" }} />

        <div style={{ position: "relative", zIndex: 1, width: "100%", maxWidth: "420px", margin: "20px", background: "rgba(2,16,11,0.96)", border: "1px solid rgba(0,255,180,0.22)", borderRadius: "7px", padding: "36px 36px 30px", animation: "fadeIn 0.6s ease, borderGlow 4s ease infinite" }}>
          {/* Corner accents */}
          {["tl","tr","bl","br"].map(c => (
            <div key={c} style={{ position: "absolute", width: 12, height: 12,
              top: c[0]==="t" ? -1 : "auto", bottom: c[0]==="b" ? -1 : "auto",
              left: c[1]==="l" ? -1 : "auto", right: c[1]==="r" ? -1 : "auto",
              borderTop: c[0]==="t" ? "2px solid #00ffb4" : "none",
              borderBottom: c[0]==="b" ? "2px solid #00ffb4" : "none",
              borderLeft: c[1]==="l" ? "2px solid #00ffb4" : "none",
              borderRight: c[1]==="r" ? "2px solid #00ffb4" : "none",
            }} />
          ))}

          <div style={{ textAlign: "center", marginBottom: "26px" }}>
            <svg width="40" height="40" viewBox="0 0 42 42" style={{ marginBottom: 10 }}>
              <polygon points="21,3 38,12 38,30 21,39 4,30 4,12" stroke="#00ffb4" strokeWidth="1.5" fill="rgba(0,255,180,0.07)"/>
              <polygon points="21,10 31,16 31,26 21,32 11,26 11,16" stroke="#00ffb4" strokeWidth="0.8" fill="rgba(0,255,180,0.04)" strokeDasharray="2,2"/>
              <circle cx="21" cy="21" r="4" fill="#00ffb4" opacity="0.9"/>
            </svg>
            <h1 style={{ fontFamily: "'Orbitron', monospace", fontWeight: 900, fontSize: "20px", letterSpacing: "4px", color: "#e0fff5", marginBottom: "5px" }}>
              <GlitchText text="CYBERAUTH" />
            </h1>
            <div style={{ color: "rgba(0,255,180,0.45)", fontSize: "9px", letterSpacing: "3px" }}>SECURE AUTHENTICATION PROTOCOL v2.4</div>
          </div>

          <div style={{ display: "flex", marginBottom: "22px", border: "1px solid rgba(0,255,180,0.15)", borderRadius: "4px", overflow: "hidden" }}>
            {["login","register"].map((m) => (
              <button key={m} onClick={() => { setMode(m); setError(""); setSuccess(""); }}
                style={{ flex: 1, padding: "9px", border: "none", cursor: "pointer", background: mode === m ? "rgba(0,255,180,0.1)" : "transparent", color: mode === m ? "#00ffb4" : "rgba(0,255,180,0.35)", fontFamily: "'Share Tech Mono', monospace", fontSize: "10px", letterSpacing: "2px", textTransform: "uppercase", transition: "all .2s", borderRight: m === "login" ? "1px solid rgba(0,255,180,0.15)" : "none" }}>
                {m === "login" ? "⌨ LOGIN" : "⊕ REGISTER"}
              </button>
            ))}
          </div>

          <CyberInput label="Email Address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} icon="◈" maxLength={254} />
          {mode === "register" && <CyberInput label="Username" value={username} onChange={(e) => setUsername(e.target.value)} icon="◉" maxLength={64} />}
          <CyberInput label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} icon="⬡" maxLength={128} />

          {/* Password strength indicator */}
          {mode === "register" && password.length > 0 && (
            <div style={{ marginBottom: "16px", marginTop: "-10px" }}>
              <div style={{ height: "3px", background: "rgba(0,255,180,0.1)", borderRadius: "99px", overflow: "hidden" }}>
                <div style={{ height: "100%", width: strength.width, background: strength.color, transition: "width 0.3s, background 0.3s", borderRadius: "99px" }} />
              </div>
              <div style={{ fontSize: "10px", color: strength.color, marginTop: "4px", letterSpacing: "1px" }}>{strength.label}</div>
            </div>
          )}

          {error && <div style={{ background: "rgba(255,0,60,0.08)", border: "1px solid rgba(255,0,60,0.3)", borderRadius: "4px", padding: "9px 13px", marginBottom: "14px", color: "#ff6080", fontSize: "12px" }}>⚠ {error}</div>}
          {success && <div style={{ background: "rgba(0,255,180,0.06)", border: "1px solid rgba(0,255,180,0.3)", borderRadius: "4px", padding: "9px 13px", marginBottom: "14px", color: "#00ffb4", fontSize: "12px" }}>✓ {success}</div>}

          <button onClick={handleSubmit} disabled={loading} style={{ width: "100%", padding: "12px", background: "rgba(0,255,180,0.08)", border: "1px solid rgba(0,255,180,0.4)", borderRadius: "4px", color: "#00ffb4", fontFamily: "'Orbitron', monospace", fontWeight: 700, fontSize: "11px", letterSpacing: "3px", cursor: loading ? "wait" : "pointer", marginBottom: "18px" }}>
            {loading ? "AUTHENTICATING..." : mode === "login" ? "INITIATE LOGIN" : "CREATE ACCOUNT"}
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
            <div style={{ flex: 1, height: "1px", background: "rgba(0,255,180,0.1)" }} />
            <span style={{ color: "rgba(0,255,180,0.3)", fontSize: "9px", letterSpacing: "2px" }}>OR</span>
            <div style={{ flex: 1, height: "1px", background: "rgba(0,255,180,0.1)" }} />
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            {[{ label: "GOOGLE", icon: "G", fn: authApi.googleLogin, color: "#ea4335" }, { label: "GITHUB", icon: "⌥", fn: authApi.githubLogin, color: "#e0fff5" }].map(({ label, icon, fn, color }) => (
              <button key={label} onClick={fn} style={{ flex: 1, padding: "10px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "4px", color: "rgba(224,255,245,0.55)", fontFamily: "'Share Tech Mono', monospace", fontSize: "10px", letterSpacing: "2px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "7px" }}>
                <span style={{ color }}>{icon}</span>{label}
              </button>
            ))}
          </div>
          <div style={{ marginTop: "24px", textAlign: "center", color: "rgba(0,255,180,0.18)", fontSize: "9px", letterSpacing: "2px" }}>
            ██ END-TO-END ENCRYPTED · JWT · OAUTH2 ██
          </div>
        </div>
      </div>
    </>
  );
}