import { useState } from "react";
import "./login.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

async function readJson(res) {
  try {
    return await res.json();
  } catch {
    return {};
  }
}

function getErrorMessage(data, fallback) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
}

async function postJson(path, body, fallback) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Can't reach the server. Check your connection and try again.");
  }

  const data = await readJson(response);
  if (!response.ok) {
    throw new Error(getErrorMessage(data, fallback));
  }
  return data;
}

export default function Login() {
  const [activeTab, setActiveTab] = useState("login");
  const [identifier, setIdentifier] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState({ type: "", text: "" });

  const isLogin = activeTab === "login";

  function switchTab(tab) {
    setActiveTab(tab);
    setNotice({ type: "", text: "" });
    setPassword("");
    setConfirm("");
    setShowPassword(false);
  }

  function showError(text) {
    setNotice({ type: "error", text });
  }

  /* ================= LOGIN ================= */

  const handleLogin = async (e) => {
    e.preventDefault();
    setNotice({ type: "", text: "" });

    const id = identifier.trim();
    if (!id) return showError("Enter your email or username.");
    if (id.includes("@") && !EMAIL_RE.test(id)) {
      return showError("Enter a valid email address.");
    }
    if (!password) return showError("Enter your password.");

    setLoading(true);
    try {
      const data = await postJson(
        "/auth/login",
        { email: id, password },
        "Invalid email or password"
      );

      const token = data.access_token || data.token;
      const store = rememberMe ? localStorage : sessionStorage;

      if (token) store.setItem("access_token", token);
      if (data.user) store.setItem("user", JSON.stringify(data.user));
      localStorage.setItem("remember_me", String(rememberMe));

      window.location.href = "/";
    } catch (err) {
      showError(err.message || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  /* ================= REGISTER ================= */

  const handleRegister = async (e) => {
    e.preventDefault();
    setNotice({ type: "", text: "" });

    if (username.trim().length < 3) {
      return showError("Username must be at least 3 characters.");
    }
    if (!EMAIL_RE.test(email.trim())) {
      return showError("Enter a valid email address.");
    }
    if (password.length < 8) {
      return showError("Password must be at least 8 characters.");
    }
    if (password !== confirm) {
      return showError("Passwords do not match.");
    }

    setLoading(true);
    try {
      await postJson(
        "/auth/register",
        {
          username: username.trim(),
          email: email.trim(),
          password,
        },
        "Registration failed. Please try again."
      );

      setIdentifier(email.trim());
      setUsername("");
      setPassword("");
      setConfirm("");
      setActiveTab("login");
      setNotice({
        type: "success",
        text: "Account created. Please sign in.",
      });
    } catch (err) {
      showError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  /* ================= SOCIAL / FORGOT ================= */

  const handleGoogleLogin = () => {
    window.location.href = `${API_URL}/auth/google/login`;
  };

  const handleMicrosoftLogin = () => {
    window.location.href = `${API_URL}/auth/microsoft/login`;
  };

  const handleForgotPassword = () => {
    window.location.href = "/forgot-password";
  };

  return (
    <div className="zenex-login-page">
      <div className="zenex-login-container">
        {/* ================= LEFT SIDE ================= */}
        <section className="zenex-left-panel">
          <div className="left-circle circle-one" aria-hidden="true" />
          <div className="left-circle circle-two" aria-hidden="true" />
          <div className="left-glow" aria-hidden="true" />

          <div className="left-company-logo">
            <img src="/softworks-logo.png" alt="SoftWorks Technologies" />
          </div>

          <div className="zenex-brand-content">
            <div className="zenex-main-title">
              <span className="zenex-title-dark">ZENE</span>
              <span className="zenex-title-arrow">&gt;</span>
              <span className="zenex-title-blue">X</span>
            </div>

            <div className="zenex-agent-title">
              <span className="title-line" aria-hidden="true" />
              <span>AI Coding Agent</span>
              <span className="title-line" aria-hidden="true" />
            </div>
          </div>

          <div className="zenex-description-section">
            <h2 className="zenex-tagline">Code Smarter. Build Better.</h2>
            <p className="zenex-description">
              Your intelligent AI assistant for coding, debugging and development.
            </p>
          </div>

          <div className="zenex-feature-list">
            <div className="zenex-feature-item">
              <div className="feature-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M13 2L4 14h7l-1 8 10-13h-7l1-7z" />
                </svg>
              </div>
              <div className="feature-text">
                <h4>Generate &amp; Debug</h4>
                <p>Code Instantly</p>
              </div>
            </div>

            <div className="zenex-feature-item">
              <div className="feature-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M8 8l-5 4 5 4" />
                  <path d="M16 8l5 4-5 4" />
                  <path d="M14 5l-4 14" />
                </svg>
              </div>
              <div className="feature-text">
                <h4>Get Smart Explanations</h4>
                <p>Suggestions and solutions</p>
              </div>
            </div>

            <div className="zenex-feature-item">
              <div className="feature-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3 17h4v4H3z" />
                  <path d="M10 11h4v10h-4z" />
                  <path d="M17 4h4v17h-4z" />
                  <path d="M3 12l7-6 7-3" />
                </svg>
              </div>
              <div className="feature-text">
                <h4>Boost Productivity</h4>
                <p>Work faster with AI</p>
              </div>
            </div>
          </div>

          <div className="coding-visual" aria-hidden="true">
            <div className="floating-code-icon">
              <span>&lt;/&gt;</span>
              <div className="floating-icon-glow" />
            </div>

            <div className="coding-laptop">
              <div className="laptop-screen">
                <div className="laptop-toolbar">
                  <span />
                  <span />
                  <span />
                  <div className="toolbar-title">zenex-ai.jsx</div>
                </div>

                <div className="laptop-code">
                  <div>
                    <span className="code-purple">import</span> React{" "}
                    <span className="code-blue">from</span>{" "}
                    <span className="code-green">"react";</span>
                  </div>
                  <div>
                    <span className="code-purple">function</span>{" "}
                    <span className="code-yellow">AI_Assistant</span>()
                  </div>
                  <div>{"{"}</div>
                  <div className="indent">
                    <span className="code-blue">const</span> result =
                  </div>
                  <div className="indent">
                    <span className="code-purple">await</span> AI.generate();
                  </div>
                  <div>{"}"}</div>
                  <div className="code-green">// Build smarter with AI</div>
                  <div className="code-blue">// ZENEX AI</div>
                </div>
              </div>

              <div className="laptop-base">
                <div className="laptop-trackpad" />
              </div>
            </div>

            <div className="visual-plant">
              <div className="plant-leaf leaf-one" />
              <div className="plant-leaf leaf-two" />
              <div className="plant-leaf leaf-three" />
              <div className="plant-leaf leaf-four" />
              <div className="plant-leaf leaf-five" />
              <div className="plant-pot">
                <div className="pot-top" />
              </div>
            </div>

            <div className="floating-ai-card">
              <span className="floating-ai-star">✦</span>
              <div>
                <strong>AI Assistant</strong>
                <small>Ready to build</small>
              </div>
            </div>
          </div>

          <div className="zenex-left-footer">
            <span>Powered by SoftWorks Technologies</span>
            <div className="footer-wave" />
          </div>
        </section>

        {/* ================= RIGHT SIDE ================= */}
        <section className="zenex-right-panel">
          <div className="right-blue-circle" aria-hidden="true" />
          <div className="right-blue-glow" aria-hidden="true" />

          <div className="right-top-text">
            <span>Innovate</span>
            <i aria-hidden="true" />
            <span>Develop</span>
            <i aria-hidden="true" />
            <span>Grow</span>
          </div>

          <div className="login-card">
            <div className="login-company-logo">
              <img src="/softworks-logo.png" alt="SoftWorks Technologies" />
            </div>

            <h1 className="login-heading">
              {isLogin ? "Welcome Back" : "Create Account"}
            </h1>
            <p className="login-subheading">
              {isLogin
                ? "Sign in to your Zenex account"
                : "Create your Zenex account"}
            </p>

            <div className="login-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={isLogin}
                className={`login-tab ${isLogin ? "active" : ""}`}
                onClick={() => switchTab("login")}
                disabled={loading}
              >
                Login
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={!isLogin}
                className={`login-tab ${!isLogin ? "active" : ""}`}
                onClick={() => switchTab("register")}
                disabled={loading}
              >
                Register
              </button>
            </div>

            <form
              className="login-form"
              onSubmit={isLogin ? handleLogin : handleRegister}
              noValidate
            >
              {notice.text && (
                <div
                  className={notice.type === "success" ? "login-success" : "login-error"}
                  role={notice.type === "success" ? "status" : "alert"}
                >
                  {notice.text}
                </div>
              )}

              {isLogin ? (
                <div className="login-input-group">
                  <div className="input-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24">
                      <rect x="3" y="5" width="18" height="14" rx="2" />
                      <path d="M3 7l9 6 9-6" />
                    </svg>
                  </div>
                  <input
                    type="text"
                    name="identifier"
                    placeholder="Email or Username"
                    aria-label="Email or username"
                    autoComplete="username"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    disabled={loading}
                  />
                </div>
              ) : (
                <>
                  <div className="login-input-group">
                    <div className="input-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24">
                        <circle cx="12" cy="8" r="4" />
                        <path d="M4 21c0-4 3.5-7 8-7s8 3 8 7" />
                      </svg>
                    </div>
                    <input
                      type="text"
                      name="username"
                      placeholder="Username"
                      aria-label="Username"
                      autoComplete="username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      disabled={loading}
                    />
                  </div>

                  <div className="login-input-group">
                    <div className="input-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24">
                        <rect x="3" y="5" width="18" height="14" rx="2" />
                        <path d="M3 7l9 6 9-6" />
                      </svg>
                    </div>
                    <input
                      type="email"
                      name="email"
                      placeholder="Email"
                      aria-label="Email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                </>
              )}

              <div className="login-input-group">
                <div className="input-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <rect x="4" y="10" width="16" height="11" rx="2" />
                    <path d="M8 10V7a4 4 0 018 0v3" />
                  </svg>
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  placeholder="Password"
                  aria-label="Password"
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword((s) => !s)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  disabled={loading}
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z" />
                    <circle cx="12" cy="12" r="3" />
                    {showPassword && <path d="M3 3l18 18" />}
                  </svg>
                </button>
              </div>

              {!isLogin && (
                <div className="login-input-group">
                  <div className="input-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24">
                      <rect x="4" y="10" width="16" height="11" rx="2" />
                      <path d="M8 10V7a4 4 0 018 0v3" />
                    </svg>
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    name="confirm"
                    placeholder="Confirm password"
                    aria-label="Confirm password"
                    autoComplete="new-password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    disabled={loading}
                  />
                </div>
              )}

              {isLogin && (
                <div className="login-options">
                  <label className="remember-option">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      disabled={loading}
                    />
                    <span>Remember me</span>
                  </label>

                  <button
                    type="button"
                    className="forgot-password"
                    onClick={handleForgotPassword}
                    disabled={loading}
                  >
                    Forgot Password?
                  </button>
                </div>
              )}

              <button
                type="submit"
                className="login-submit-button"
                disabled={loading}
              >
                {loading
                  ? "Please wait..."
                  : isLogin
                  ? "Sign In"
                  : "Create Account"}
              </button>
            </form>

            <div className="login-divider">
              <span />
              <p>or continue with</p>
              <span />
            </div>

            <div className="social-login">
              <button
                type="button"
                className="social-button"
                onClick={handleGoogleLogin}
                disabled={loading}
              >
                <svg viewBox="0 0 48 48" aria-hidden="true" focusable="false">
                  <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 8 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
                  <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 8 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
                  <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z" />
                  <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
                </svg>
                <span>Continue with Google</span>
              </button>

              <button
                type="button"
                className="social-button"
                onClick={handleMicrosoftLogin}
                disabled={loading}
              >
                <div className="microsoft-icon" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
                <span>Continue with Microsoft</span>
              </button>
            </div>

            <div className="login-register-footer">
              {isLogin ? (
                <>
                  Don&apos;t have an account?
                  <button type="button" onClick={() => switchTab("register")} disabled={loading}>
                    Register here
                  </button>
                </>
              ) : (
                <>
                  Already have an account?
                  <button type="button" onClick={() => switchTab("login")} disabled={loading}>
                    Login here
                  </button>
                </>
              )}
            </div>
          </div>
        </section>
      </div>

      <div className="zenex-copyright">
        &copy; {new Date().getFullYear()} SoftWorks Technologies. All rights reserved.
      </div>

      <div className="bottom-blue-decoration" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}