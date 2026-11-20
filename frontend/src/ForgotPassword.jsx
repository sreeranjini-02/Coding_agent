import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./auth.css";

export default function ForgotPassword() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleForgotPassword = async (e) => {
    e.preventDefault();

    setMessage("");
    setError("");
    setLoading(true);

    try {
      const response = await fetch(
        "http://localhost:8000/auth/forgot-password",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Unable to send reset email"
        );
      }

      setMessage(
        data.message ||
          "If your account exists, a password reset email has been sent."
      );

    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">

        {/* ZENEX BRAND */}
        <div className="auth-brand">
          <div className="auth-logo">Z</div>

          <div className="auth-brand-name">
            ZEN<span>EX</span>
          </div>
        </div>

        {/* TITLE */}
        <h1 className="auth-title">
          Forgot password?
        </h1>

        <p className="auth-subtitle">
          Enter your email to reset your password.
        </p>

        {/* SUCCESS MESSAGE */}
        {message && (
          <div className="auth-alert success">
            {message}
          </div>
        )}

        {/* ERROR MESSAGE */}
        {error && (
          <div className="auth-alert error">
            {error}
          </div>
        )}

        {/* EMAIL FORM */}
        <form onSubmit={handleForgotPassword}>

          <div className="auth-field">
            <label htmlFor="forgot-email">
              Email address
            </label>

            <input
              id="forgot-email"
              className="auth-input"
              type="email"
              placeholder="Enter your registered email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          {/* SEND RESET LINK */}
          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading ? "Sending..." : "Send Reset Link"}
          </button>

        </form>

        {/* BACK TO LOGIN */}
        <button
          type="button"
          className="auth-back-button"
          onClick={() => navigate("/login")}
        >
          ← Back to Login
        </button>

      </div>
    </div>
  );
}