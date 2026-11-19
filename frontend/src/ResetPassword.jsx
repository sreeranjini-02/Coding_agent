import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import "./auth.css";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleResetPassword = async (e) => {
    e.preventDefault();

    setError("");
    setMessage("");

    if (!token) {
      setError("Password reset token is missing.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        "http://localhost:8000/auth/reset-password",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token,
            new_password: password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Password reset failed"
        );
      }

      setMessage(
        data.message || "Password reset successfully."
      );

      setTimeout(() => {
        navigate("/login");
      }, 2000);

    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">

        <div className="auth-brand">
          <div className="auth-logo">Z</div>
          <div className="auth-brand-name">
            ZEN<span>EX</span>
          </div>
        </div>

        <h1 className="auth-title">Reset password</h1>
        <p className="auth-subtitle">
          Create a new password for your account.
        </p>

        {message && <div className="auth-alert success">{message}</div>}

        {error && <div className="auth-alert error">{error}</div>}

        <form onSubmit={handleResetPassword}>

          <div className="auth-field">
            <label htmlFor="reset-password">New Password</label>
            <input
              id="reset-password"
              className="auth-input"
              type="password"
              placeholder="New password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="reset-confirm">Confirm Password</label>
            <input
              id="reset-confirm"
              className="auth-input"
              type="password"
              placeholder="Confirm password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading ? "Updating..." : "Reset Password"}
          </button>

        </form>

      </div>
    </div>
  );
}