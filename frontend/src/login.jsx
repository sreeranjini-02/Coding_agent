import React, { useState } from "react";
import "./Login.css";

const API_URL = "http://localhost:8000";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  // GOOGLE OAUTH
  const handleGoogleLogin = () => {
    window.location.href = `${API_URL}/auth/google/login`;
  };

  // MICROSOFT OAUTH
  const handleMicrosoftLogin = () => {
    window.location.href = `${API_URL}/auth/microsoft/login`;
  };

  // NORMAL LOGIN
  const handleLogin = async (e) => {
    e.preventDefault();

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        alert(data.detail || "Login failed");
        return;
      }

      // SAVE JWT TOKEN
      localStorage.setItem("access_token", data.access_token);

      // SAVE USER DATA
      if (data.user) {
        localStorage.setItem("user", JSON.stringify(data.user));
      }

      // REDIRECT AFTER LOGIN
      window.location.href = "/";

    } catch (error) {
      console.error("Login error:", error);
      alert("Unable to connect to the server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">

      <div className="login-card">

        {/* BRAND */}
        <div className="login-brand">
          <div className="brand-icon">Z</div>

          <span className="brand-name">
            ZENEX<span className="brand-ai"> AI</span>
          </span>
        </div>

        {/* HEADING */}
        <div className="login-heading">
          <h1>Welcome back</h1>
          <p>Sign in to continue to your workspace.</p>
        </div>

        {/* LOGIN FORM */}
        <form className="login-form" onSubmit={handleLogin}>

          {/* EMAIL */}
          <div className="form-group">
            <label htmlFor="email">Email address</label>

            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          {/* PASSWORD */}
          <div className="form-group">

            <div className="password-label">
              <label htmlFor="password">Password</label>

              <a href="/forgot-password">
                Forgot password?
              </a>
            </div>

            <div className="password-input">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />

              <button
                type="button"
                className="show-password"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>

          </div>

          {/* SIGN IN */}
          <button
            type="submit"
            className="login-submit"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>

        </form>

        {/* DIVIDER */}
        <div className="login-divider">
          <span>OR CONTINUE WITH</span>
        </div>

        {/* GOOGLE AND MICROSOFT LOGIN */}
        <div className="social-login">

          {/* GOOGLE */}
          <button
            type="button"
            className="social-button"
            onClick={handleGoogleLogin}
          >
            <span className="google-icon">G</span>
            Google
          </button>

          {/* MICROSOFT */}
          <button
            type="button"
            className="social-button"
            onClick={handleMicrosoftLogin}
          >
            <span className="microsoft-icon">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </span>

            Microsoft
          </button>

        </div>

        {/* REGISTER */}
        <div className="register-link">
          Don't have an account?
          <a href="/register"> Create account</a>
        </div>

        {/* FOOTER */}
        <div className="login-footer">
          Secure access to your AI coding workspace.
        </div>

      </div>

    </div>
  );
}