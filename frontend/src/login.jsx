import React, { useState, useEffect } from "react";
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

  // GOOGLE AND MICROSOFT OAUTH ERROR HANDLING
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    const oauthError = params.get("error");
    const stage = params.get("stage");

    if (oauthError === "microsoft_auth_failed") {
      setError(
        stage
          ? `Microsoft login failed during: ${stage}. Please check the backend terminal.`
          : "Microsoft authentication failed. Please try again."
      );
    } else if (oauthError === "google_auth_failed") {
      setError("Google authentication failed. Please try again.");
    } else if (oauthError) {
      setError(`Authentication failed: ${oauthError}`);
    }

    // Remove OAuth error parameters from the browser URL
    if (oauthError) {
      window.history.replaceState(
        {},
        document.title,
        window.location.pathname
      );
    }
  }, []);

  // FORM INPUT
  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  // EMAIL LOGIN
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

      if (!data.access_token) {
        throw new Error("Access token was not received from the server.");
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("token", data.access_token);

      if (data.user) {
        localStorage.setItem("user", JSON.stringify(data.user));
      }

      navigate("/coding-agent", { replace: true });

    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  // CLEAR OLD LOGIN DATA BEFORE OAUTH
  const clearOldLoginData = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  };

  // GOOGLE LOGIN
  const handleGoogleLogin = () => {
    setError("");
    clearOldLoginData();

    window.location.href = `${API_URL}/auth/google/login`;
  };

  // MICROSOFT LOGIN
  const handleMicrosoftLogin = () => {
    setError("");
    clearOldLoginData();

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
          background: #050505;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 16px;
          font-family: 'Inter', sans-serif;
          overflow: hidden;
        }

        .zenex-login-card {
          width: 100%;
          max-width: 1250px;
          height: calc(100vh - 32px);
          max-height: 720px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          background: #050505;
          border-radius: 20px;
          overflow: hidden;
          border: 1px solid #292436;
        }

        /* LEFT SIDE */

        .zenex-login-left {
          padding: 28px 56px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          background: #050505;
          overflow: hidden;
        }

        .zenex-brand {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 30px;
        }

        .zenex-logo {
          width: 40px;
          height: 40px;
          border-radius: 11px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 21px;
          font-weight: 800;
          background: linear-gradient(135deg,#c4b5fd,#8b5cf6);
          box-shadow: 0 0 20px rgba(167,139,250,0.3);
        }

        .zenex-brand-name {
          color: white;
          font-size: 22px;
          font-weight: 800;
          letter-spacing: 2px;
        }

        .zenex-brand-name span {
          color: #a78bfa;
        }

        .zenex-form-heading {
          font-size: 29px;
          color: white;
          font-weight: 600;
          margin: 0 0 10px;
        }

        .zenex-form-subtitle {
          color: #a1a1aa;
          font-size: 13px;
          line-height: 1.7;
          margin-bottom: 25px;
        }

        .zenex-field {
          margin-bottom: 16px;
        }

        .zenex-field label {
          display: block;
          color: #d4d4d8;
          font-size: 12px;
          margin-bottom: 8px;
        }

        .zenex-input {
          width: 100%;
          height: 45px;
          padding: 0 13px;
          background: #111019;
          border: 1px solid #292436;
          border-radius: 8px;
          color: white;
          font-size: 13px;
          outline: none;
          transition: 0.2s;
        }

        .zenex-input::placeholder {
          color: #71717a;
        }

        .zenex-input:focus {
          border-color: #a78bfa;
          box-shadow: 0 0 0 2px rgba(167,139,250,0.12);
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
          color: #c4b5fd;
          cursor: pointer;
          font-size: 12px;
        }

        .zenex-forgot {
          display: flex;
          justify-content: flex-end;
          margin: -4px 0 18px;
        }

        .zenex-forgot a {
          color: #c4b5fd;
          font-size: 12px;
          text-decoration: none;
        }

        .zenex-forgot a:hover {
          color: white;
        }

        /* SIGN IN BUTTON */

        .zenex-submit {
          display: block;
          width: 75%;
          height: 40px;
          margin: 0 auto;
          background: linear-gradient(135deg,#c4b5fd,#a78bfa);
          border: none;
          border-radius: 8px;
          color: #100b1c;
          font-size: 13px;
          font-weight: 700;
          cursor: pointer;
          transition: 0.2s;
        }

        .zenex-submit:hover {
          background: #c4b5fd;
          box-shadow: 0 5px 20px rgba(167,139,250,0.25);
          transform: translateY(-1px);
        }

        .zenex-submit:disabled {
          opacity: 0.65;
          cursor: not-allowed;
        }

        /* DIVIDER */

        .zenex-divider {
          display: flex;
          align-items: center;
          gap: 12px;
          color: #71717a;
          font-size: 10px;
          margin: 20px 0;
        }

        .zenex-divider::before,
        .zenex-divider::after {
          content: "";
          flex: 1;
          height: 1px;
          background: #292436;
        }

        /* SOCIAL LOGIN */

        .zenex-social-row {
          display: flex;
          gap: 12px;
          width: 100%;
        }

        .zenex-social-button {
          flex: 1;
          min-width: 0;
          height: 43px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          background: #111019;
          border: 1px solid #292436;
          border-radius: 8px;
          color: #e4e4ef;
          font-size: 12px;
          cursor: pointer;
          transition: 0.2s;
          white-space: nowrap;
        }

        .zenex-social-button:hover {
          background: #191522;
          border-color: #a78bfa;
        }

        .zenex-social-button svg {
          width: 17px;
          height: 17px;
          flex-shrink: 0;
        }

        /* REGISTER */

        .zenex-register {
          text-align: center;
          margin-top: 22px;
          color: #a1a1aa;
          font-size: 12px;
        }

        .zenex-register a {
          color: #c4b5fd;
          text-decoration: none;
          font-weight: 600;
        }

        .zenex-register a:hover {
          color: white;
        }

        .zenex-terms {
          text-align: center;
          color: #71717a;
          font-size: 10px;
          margin-top: 20px;
          line-height: 1.7;
        }

        .zenex-terms a {
          color: #c4b5fd;
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
          line-height: 1.6;
          overflow-wrap: anywhere;
        }

        /* RIGHT ROBOT SECTION */

        .zenex-login-right {
          position: relative;
          padding: 35px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          overflow: hidden;
          background: radial-gradient(
            circle at center,
            #171024 0%,
            #0b0811 55%,
            #050505 100%
          );
        }

        .zenex-glow {
          position: absolute;
          width: 350px;
          height: 350px;
          background: #8b5cf6;
          filter: blur(140px);
          opacity: 0.20;
          border-radius: 50%;
          pointer-events: none;
        }

        /* ROBOT */

        .zenex-robot-container {
          position: relative;
          z-index: 2;
          display: flex;
          justify-content: center;
          align-items: center;
          width: 100%;
          max-width: 400px;
          height: 340px;
        }

        .zenex-robot-orbit {
          position: absolute;
          width: 290px;
          height: 290px;
          border: 1px solid rgba(167,139,250,0.25);
          border-radius: 50%;
          box-shadow: 0 0 35px rgba(139,92,246,0.12);
        }

        .zenex-robot-orbit::before {
          content: "";
          position: absolute;
          width: 9px;
          height: 9px;
          background: #c4b5fd;
          border-radius: 50%;
          top: 30px;
          right: 30px;
          box-shadow: 0 0 15px #a78bfa;
        }

        .zenex-robot {
          position: relative;
          width: 185px;
          height: 205px;
          animation: zenexFloat 3s ease-in-out infinite;
          filter: drop-shadow(0 0 25px rgba(167,139,250,0.35));
        }

        .zenex-robot-head {
          position: absolute;
          top: 15px;
          left: 25px;
          width: 135px;
          height: 115px;
          background: linear-gradient(145deg,#e9e2ff,#a78bfa 60%,#7651d5);
          border: 4px solid #d8c9ff;
          border-radius: 40px;
          box-shadow: inset -8px -8px 15px rgba(50,20,100,0.2);
        }

        .zenex-robot-ear {
          position: absolute;
          width: 17px;
          height: 40px;
          top: 55px;
          background: #a78bfa;
          border-radius: 10px;
          border: 2px solid #d8c9ff;
        }

        .zenex-robot-ear.left {
          left: 10px;
        }

        .zenex-robot-ear.right {
          right: 10px;
        }

        .zenex-robot-face {
          position: absolute;
          top: 30px;
          left: 19px;
          width: 90px;
          height: 58px;
          background: #17102b;
          border-radius: 22px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 20px;
        }

        .zenex-robot-eye {
          width: 12px;
          height: 16px;
          background: #c4b5fd;
          border-radius: 50%;
          box-shadow: 0 0 12px #c4b5fd;
        }

        .zenex-robot-mouth {
          position: absolute;
          bottom: 12px;
          left: 36px;
          width: 18px;
          height: 7px;
          border-bottom: 3px solid #c4b5fd;
          border-radius: 50%;
        }

        .zenex-robot-antenna {
          position: absolute;
          top: -10px;
          left: 87px;
          width: 4px;
          height: 24px;
          background: #c4b5fd;
        }

        .zenex-robot-antenna::after {
          content: "";
          position: absolute;
          width: 12px;
          height: 12px;
          background: #c4b5fd;
          border-radius: 50%;
          top: -9px;
          left: -4px;
          box-shadow: 0 0 15px #a78bfa;
        }

        .zenex-robot-body {
          position: absolute;
          bottom: 0;
          left: 45px;
          width: 95px;
          height: 75px;
          background: linear-gradient(145deg,#c4b5fd,#8055e8);
          border: 3px solid #d8c9ff;
          border-radius: 25px 25px 30px 30px;
        }

        .zenex-robot-body::after {
          content: "Z";
          position: absolute;
          top: 15px;
          left: 30px;
          font-size: 27px;
          font-weight: 800;
          color: white;
        }

        @keyframes zenexFloat {
          0%,100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-12px);
          }
        }

        .zenex-robot-spark {
          position: absolute;
          color: #c4b5fd;
          font-size: 25px;
          animation: zenexPulse 2s infinite alternate;
        }

        .zenex-robot-spark.one {
          top: 40px;
          left: 45px;
        }

        .zenex-robot-spark.two {
          bottom: 45px;
          right: 45px;
        }

        @keyframes zenexPulse {
          from {
            opacity: 0.3;
            transform: scale(0.8);
          }
          to {
            opacity: 1;
            transform: scale(1.2);
          }
        }

        /* HERO CONTENT */

        .zenex-hero-content {
          text-align: center;
          max-width: 430px;
          margin-top: 15px;
          position: relative;
          z-index: 1;
        }

        .zenex-hero-title {
          color: #f4f1ff;
          font-size: 27px;
          font-weight: 600;
          line-height: 1.4;
          margin-bottom: 12px;
        }

        .zenex-hero-title span {
          background: linear-gradient(90deg,#c4b5fd,#8b5cf6);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
        }

        .zenex-hero-description {
          color: #a1a1aa;
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
          border: 1px solid #39304e;
          color: #c4b5fd;
          background: #111019;
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
        }

        @media (max-width: 700px) {
          .zenex-login-page {
            padding: 0;
          }

          .zenex-login-card {
            grid-template-columns: 1fr;
            height: 100vh;
            max-height: none;
            border-radius: 0;
            border: none;
          }

          .zenex-login-left {
            padding: 35px 24px;
            overflow-y: auto;
          }

          .zenex-login-right {
            display: none;
          }
        }

        @media (max-width: 420px) {
          .zenex-social-row {
            gap: 7px;
          }

          .zenex-social-button {
            font-size: 10px;
            gap: 5px;
          }

          .zenex-submit {
            width: 85%;
          }
        }

        /* Fit the login page on shorter screens without scrolling */
        @media (max-height: 820px) {
          .zenex-brand {
            margin-bottom: 18px;
          }

          .zenex-form-heading {
            font-size: 26px;
            margin-bottom: 6px;
          }

          .zenex-form-subtitle {
            margin-bottom: 16px;
            line-height: 1.5;
          }

          .zenex-field {
            margin-bottom: 10px;
          }

          .zenex-field label {
            margin-bottom: 6px;
          }

          .zenex-input {
            height: 40px;
          }

          .zenex-forgot {
            margin: -2px 0 12px;
          }

          .zenex-submit {
            height: 38px;
          }

          .zenex-divider {
            margin: 14px 0;
          }

          .zenex-social-button {
            height: 40px;
          }

          .zenex-register {
            margin-top: 14px;
          }

          .zenex-terms {
            margin-top: 12px;
          }

          .zenex-robot-container {
            transform: scale(0.85);
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
            <div className="zenex-error" role="alert">
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
              {loading ? "Signing in..." : "Sign In"}
            </button>

          </form>

          <div className="zenex-divider">
            OR CONTINUE WITH
          </div>

          {/* GOOGLE AND MICROSOFT SAME ROW */}

          <div className="zenex-social-row">

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

              Google

            </button>

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

              Microsoft

            </button>

          </div>

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

        {/* RIGHT ROBOT SECTION */}

        <div className="zenex-login-right">

          <div className="zenex-glow"></div>

          <div className="zenex-robot-container">

            <div className="zenex-robot-orbit"></div>

            <span className="zenex-robot-spark one">✦</span>
            <span className="zenex-robot-spark two">✧</span>

            <div className="zenex-robot">

              <div className="zenex-robot-ear left"></div>
              <div className="zenex-robot-ear right"></div>

              <div className="zenex-robot-antenna"></div>

              <div className="zenex-robot-head">

                <div className="zenex-robot-face">

                  <div className="zenex-robot-eye"></div>
                  <div className="zenex-robot-eye"></div>

                  <div className="zenex-robot-mouth"></div>

                </div>

              </div>

              <div className="zenex-robot-body"></div>

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