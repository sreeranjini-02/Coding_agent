import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

const API_URL = "http://localhost:8000";

export default function Login() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    if (!form.email.trim() || !form.password) {
      setError("Please enter your email and password.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username_or_email: form.email.trim(),
          password: form.password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Invalid login credentials."
        );
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("token", data.access_token);

      if (data.user) {
        localStorage.setItem("user", JSON.stringify(data.user));
      }

      navigate("/coding-agent");
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = `${API_URL}/auth/google/login`;
  };

  const handleMicrosoftLogin = () => {
    window.location.href = `${API_URL}/auth/microsoft/login`;
  };

  return (
    <div className="zenex-login-page">

      <style>{`

        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        * {
          box-sizing: border-box;
        }

        .zenex-login-page {
          width: 100%;
          height: 100vh;
          min-height: 600px;
          background: #000000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
          font-family: 'Inter', sans-serif;
          overflow: hidden;
        }

        .zenex-login-card {
          width: 100%;
          max-width: 1250px;
          height: min(680px, calc(100vh - 40px));
          min-height: 560px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          background: #050505;
          border-radius: 20px;
          overflow: hidden;
          border: 1px solid #171717;
        }

        /* LEFT SIDE */

        .zenex-login-left {
          padding: 35px 65px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          background: #050505;
          position: relative;
          z-index: 2;
        }

        .zenex-brand {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 30px;
        }

        .zenex-logo {
          width: 38px;
          height: 38px;
          border-radius: 11px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 20px;
          font-weight: 800;
          background: linear-gradient(135deg,#b5a0ff,#7356ed);
          box-shadow: 0 0 20px rgba(145,115,255,0.2);
        }

        .zenex-brand-name {
          color: white;
          font-size: 21px;
          font-weight: 800;
          letter-spacing: 2px;
        }

        .zenex-brand-name span {
          color: #a997ff;
        }

        .zenex-form-heading {
          font-size: 27px;
          color: white;
          font-weight: 600;
          margin: 0 0 10px;
          letter-spacing: -0.7px;
        }

        .zenex-form-subtitle {
          color: #9999ac;
          font-size: 13px;
          line-height: 1.6;
          margin-bottom: 25px;
        }

        .zenex-field {
          margin-bottom: 16px;
        }

        .zenex-field label {
          display: block;
          color: #d6d6e3;
          font-size: 12px;
          margin-bottom: 8px;
        }

        .zenex-input {
          width: 100%;
          height: 45px;
          padding: 0 13px;
          background: #101010;
          border: 1px solid #292929;
          border-radius: 8px;
          color: white;
          font-size: 13px;
          outline: none;
          transition: 0.2s;
        }

        .zenex-input::placeholder {
          color: #66667b;
        }

        .zenex-input:focus {
          border-color: #a493ff;
          box-shadow: 0 0 0 2px rgba(164,147,255,0.1);
        }

        .zenex-password-wrapper {
          position: relative;
        }

        .zenex-password-wrapper .zenex-input {
          padding-right: 60px;
        }

        .zenex-password-toggle {
          position: absolute;
          right: 12px;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          color: #aaaac0;
          cursor: pointer;
          font-size: 12px;
        }

        .zenex-forgot {
          display: flex;
          justify-content: flex-end;
          margin: -4px 0 18px;
        }

        .zenex-forgot a {
          color: #b4a3ff;
          font-size: 12px;
          text-decoration: none;
        }

        .zenex-forgot a:hover {
          color: white;
        }

        .zenex-submit {
          width: 100%;
          height: 45px;
          background: linear-gradient(135deg,#c3b4ff,#a18aff);
          border: none;
          border-radius: 8px;
          color: #141020;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: 0.2s;
        }

        .zenex-submit:hover {
          box-shadow: 0 5px 20px rgba(163,139,255,0.2);
        }

        .zenex-submit:disabled {
          opacity: 0.65;
          cursor: not-allowed;
        }

        .zenex-divider {
          display: flex;
          align-items: center;
          gap: 12px;
          color: #66667b;
          font-size: 10px;
          margin: 19px 0;
        }

        .zenex-divider::before,
        .zenex-divider::after {
          content: "";
          flex: 1;
          height: 1px;
          background: #252535;
        }

        .zenex-social-button {
          width: 100%;
          height: 41px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          background: #101010;
          border: 1px solid #292929;
          border-radius: 8px;
          color: #e4e4ef;
          font-size: 12px;
          cursor: pointer;
          transition: 0.2s;
          margin-bottom: 10px;
        }

        .zenex-social-button:hover {
          background: #191919;
          border-color: #45445c;
        }

        .zenex-social-button svg {
          width: 17px;
          height: 17px;
        }

        .zenex-register {
          text-align: center;
          margin-top: 16px;
          color: #9292a8;
          font-size: 12px;
        }

        .zenex-register a {
          color: #b7a6ff;
          text-decoration: none;
          font-weight: 600;
        }

        .zenex-register a:hover {
          color: white;
        }

        .zenex-terms {
          text-align: center;
          color: #66667b;
          font-size: 10px;
          margin-top: 20px;
          line-height: 1.6;
        }

        .zenex-terms a {
          color: #aaa0d7;
          text-decoration: underline;
        }

        .zenex-error {
          padding: 10px;
          background: rgba(255,75,100,0.08);
          border: 1px solid rgba(255,75,100,0.2);
          color: #ff8d9e;
          font-size: 12px;
          border-radius: 8px;
          margin-bottom: 15px;
        }

        /* RIGHT SIDE */

        .zenex-login-right {
          position: relative;
          padding: 35px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          overflow: hidden;
          background: #050505;
        }

        .zenex-glow {
          position: absolute;
          width: 350px;
          height: 350px;
          background: #7656e9;
          filter: blur(140px);
          opacity: 0.13;
          border-radius: 50%;
          bottom: -150px;
          right: -100px;
          pointer-events: none;
        }

        .zenex-visual-top {
          width: 100%;
          max-width: 430px;
          position: relative;
          z-index: 1;
        }

        .zenex-code-window {
          background: #0b0b12;
          border: 1px solid #252535;
          border-radius: 13px;
          overflow: hidden;
          box-shadow: 0 20px 50px rgba(0,0,0,0.35);
        }

        .zenex-window-header {
          display: flex;
          align-items: center;
          gap: 7px;
          padding: 12px 15px;
          border-bottom: 1px solid #252535;
        }

        .zenex-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #ff6b7a;
        }

        .zenex-dot:nth-child(2) {
          background: #ffc76b;
        }

        .zenex-dot:nth-child(3) {
          background: #76e5a7;
        }

        .zenex-window-title {
          margin-left: auto;
          color: #75758e;
          font-size: 10px;
        }

        .zenex-code {
          padding: 20px;
          font-family: Consolas, monospace;
          font-size: 12px;
          line-height: 1.9;
          color: #c4c4db;
        }

        .zenex-code .purple {
          color: #b8a2ff;
        }

        .zenex-code .green {
          color: #8fe6bb;
        }

        .zenex-code .blue {
          color: #8cbcff;
        }

        .zenex-code .muted {
          color: #707087;
        }

        .zenex-ai-card {
          width: 75%;
          margin: -20px 0 0 auto;
          position: relative;
          z-index: 2;
          padding: 18px;
          border-radius: 12px;
          background: #11111b;
          border: 1px solid #333044;
          box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }

        .zenex-ai-label {
          color: #a8a0c9;
          font-size: 10px;
          margin-bottom: 10px;
        }

        .zenex-ai-title {
          color: white;
          font-size: 14px;
          font-weight: 600;
          margin-bottom: 10px;
        }

        .zenex-ai-status {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          color: #91e6ba;
          font-size: 10px;
        }

        .zenex-status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #91e6ba;
          box-shadow: 0 0 8px #91e6ba;
        }

        .zenex-hero-content {
          text-align: center;
          max-width: 430px;
          margin-top: 35px;
          position: relative;
          z-index: 1;
        }

        .zenex-hero-title {
          color: #f4f1ff;
          font-size: 25px;
          font-weight: 600;
          line-height: 1.4;
          margin-bottom: 12px;
          letter-spacing: -0.7px;
        }

        .zenex-hero-title span {
          background: linear-gradient(90deg,#c7b8ff,#8d79ff);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
        }

        .zenex-hero-description {
          color: #9695ad;
          font-size: 12px;
          line-height: 1.8;
        }

        .zenex-feature-row {
          display: flex;
          justify-content: center;
          gap: 8px;
          flex-wrap: wrap;
          margin-top: 18px;
        }

        .zenex-feature-pill {
          border: 1px solid #29283c;
          color: #b6b2d1;
          background: #101010;
          padding: 7px 11px;
          border-radius: 25px;
          font-size: 10px;
        }

        /* RESPONSIVE */

        @media (max-width: 900px) {
          .zenex-login-left {
            padding: 30px;
          }

          .zenex-login-right {
            padding: 25px;
          }

          .zenex-code {
            font-size: 10px;
          }
        }

        @media (max-width: 700px) {
          .zenex-login-page {
            padding: 0;
            height: 100vh;
            min-height: 0;
            overflow-y: auto;
          }

          .zenex-login-card {
            grid-template-columns: 1fr;
            height: auto;
            min-height: 100vh;
            border-radius: 0;
            border: none;
          }

          .zenex-login-left {
            padding: 30px 24px;
          }

          .zenex-login-right {
            display: none;
          }
        }

        /* SHORT LAPTOP HEIGHT */

        @media (min-width: 701px) and (max-height: 720px) {
          .zenex-login-left {
            padding-top: 20px;
            padding-bottom: 20px;
          }

          .zenex-brand {
            margin-bottom: 20px;
          }

          .zenex-form-subtitle {
            margin-bottom: 18px;
          }

          .zenex-field {
            margin-bottom: 12px;
          }

          .zenex-divider {
            margin: 14px 0;
          }

          .zenex-register {
            margin-top: 10px;
          }

          .zenex-terms {
            margin-top: 12px;
          }

          .zenex-hero-content {
            margin-top: 22px;
          }

          .zenex-code {
            padding: 15px;
            line-height: 1.7;
          }
        }

      `}</style>

      <div className="zenex-login-card">

        {/* LEFT LOGIN SECTION */}

        <div className="zenex-login-left">

          <div className="zenex-brand">
            <div className="zenex-logo">Z</div>

            <div className="zenex-brand-name">
              ZEN<span>EX</span>
            </div>
          </div>

          <h1 className="zenex-form-heading">
            Welcome back
          </h1>

          <p className="zenex-form-subtitle">
            Continue your journey with ZENEX.
            <br />
            Sign in to your AI coding workspace.
          </p>

          {error && (
            <div className="zenex-error">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin}>

            <div className="zenex-field">
              <label>Email address or username</label>

              <input
                className="zenex-input"
                type="text"
                name="email"
                placeholder="Enter your email or username"
                value={form.email}
                onChange={handleChange}
                autoComplete="username"
                required
              />
            </div>

            <div className="zenex-field">
              <label>Password</label>

              <div className="zenex-password-wrapper">
                <input
                  className="zenex-input"
                  type={showPassword ? "text" : "password"}
                  name="password"
                  placeholder="Enter your password"
                  value={form.password}
                  onChange={handleChange}
                  autoComplete="current-password"
                  required
                />

                <button
                  type="button"
                  className="zenex-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <div className="zenex-forgot">
              <Link to="/forgot-password">
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              className="zenex-submit"
              disabled={loading}
            >
              {loading ? "Signing in..." : "Sign in to ZENEX"}
            </button>

          </form>

          <div className="zenex-divider">
            OR CONTINUE WITH
          </div>

          {/* GOOGLE LOGIN */}

          <button
            type="button"
            className="zenex-social-button"
            onClick={handleGoogleLogin}
          >
            <svg viewBox="0 0 48 48">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.47-4.78 7.17l7.73 6C44.4 37.18 46.98 31.37 46.98 24.55z"/>
              <path fill="#FBBC05" d="M10.54 28.59A14.5 14.5 0 0 1 9.77 24c0-1.59.27-3.13.77-4.59l-7.98-6.19A23.9 23.9 0 0 0 0 24c0 3.91.94 7.62 2.56 10.78l7.98-6.19z"/>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.9-5.81l-7.73-6C30.03 38.08 27.22 39 24 39c-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 43.62 14.62 48 24 48z"/>
            </svg>

            Continue with Google
          </button>

          {/* MICROSOFT LOGIN */}

          <button
            type="button"
            className="zenex-social-button"
            onClick={handleMicrosoftLogin}
          >
            <svg viewBox="0 0 24 24">
              <path fill="#F35325" d="M1 1h10v10H1z"/>
              <path fill="#81BC06" d="M13 1h10v10H13z"/>
              <path fill="#05A6F0" d="M1 13h10v10H1z"/>
              <path fill="#FFBA08" d="M13 13h10v10H13z"/>
            </svg>

            Continue with Microsoft
          </button>

          <div className="zenex-register">
            Don't have an account?{" "}
            <Link to="/register">
              Create account
            </Link>
          </div>

          <div className="zenex-terms">
            By continuing, you agree to ZENEX's
            <br />
            <a href="/privacy-policy">Privacy Policy</a>
            {" "}and{" "}
            <a href="/terms">Terms of Service</a>
          </div>

        </div>

        {/* RIGHT VISUAL SECTION */}

        <div className="zenex-login-right">

          <div className="zenex-glow"></div>

          <div className="zenex-visual-top">

            <div className="zenex-code-window">

              <div className="zenex-window-header">
                <div className="zenex-dot"></div>
                <div className="zenex-dot"></div>
                <div className="zenex-dot"></div>

                <div className="zenex-window-title">
                  zenex_ai.py
                </div>
              </div>

              <div className="zenex-code">
                <div>
                  <span className="purple">class</span>{" "}
                  <span className="blue">ZenexAI</span>:
                </div>

                <div>
                  &nbsp;&nbsp;<span className="purple">def</span>{" "}
                  <span className="green">generate_code</span>(self):
                </div>

                <div>
                  &nbsp;&nbsp;&nbsp;&nbsp;
                  <span className="muted"># Intelligent code generation</span>
                </div>

                <div>
                  &nbsp;&nbsp;&nbsp;&nbsp;
                  <span className="purple">return</span>{" "}
                  <span className="green">"Build something amazing"</span>
                </div>

                <br />

                <div>
                  <span className="purple">def</span>{" "}
                  <span className="blue">solve_problem</span>():
                </div>

                <div>
                  &nbsp;&nbsp;
                  <span className="purple">return</span>{" "}
                  <span className="green">zenex.optimize()</span>
                </div>
              </div>

            </div>

            <div className="zenex-ai-card">

              <div className="zenex-ai-label">
                ZENEX AI ENGINE
              </div>

              <div className="zenex-ai-title">
                Your intelligent coding partner.
              </div>

              <div className="zenex-ai-status">
                <span className="zenex-status-dot"></span>
                Ready to build
              </div>

            </div>

          </div>

          <div className="zenex-hero-content">

            <h2 className="zenex-hero-title">
              Build smarter.
              <br />
              Code with <span>ZENEX AI.</span>
            </h2>

            <p className="zenex-hero-description">
              Your intelligent workspace for code generation,
              debugging, document understanding, and AI-powered
              development.
            </p>

            <div className="zenex-feature-row">

              <div className="zenex-feature-pill">
                ✦ AI Code Generation
              </div>

              <div className="zenex-feature-pill">
                ◈ Smart Debugging
              </div>

              <div className="zenex-feature-pill">
                ✧ AI Assistant
              </div>

            </div>

          </div>

        </div>

      </div>

    </div>
  );
}
