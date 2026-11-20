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

    setMessage("");
    setError("");

    // Check reset token
    if (!token) {
      setError("Password reset token is missing or invalid.");
      return;
    }

    // Password validation
    if (password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
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
            token: token,
            new_password: password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Password reset failed."
        );
      }

      setMessage(
        data.message || "Password reset successfully!"
      );

      setPassword("");
      setConfirmPassword("");

      // Redirect to login after successful reset
      setTimeout(() => {
        navigate("/login");
      }, 2000);

    } catch (err) {
      setError(err.message || "Something went wrong.");
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
          Reset Password
        </h1>

        <p className="auth-subtitle">
          Create a new password for your account.
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

        {/* RESET PASSWORD FORM */}
        <form onSubmit={handleResetPassword}>

          {/* NEW PASSWORD */}
          <div className="auth-field">
            <label htmlFor="reset-password">
              New Password
            </label>

            <input
              id="reset-password"
              className="auth-input"
              type="password"
              placeholder="Enter new password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          {/* CONFIRM PASSWORD */}
          <div className="auth-field">
            <label htmlFor="reset-confirm-password">
              Confirm Password
            </label>

            <input
              id="reset-confirm-password"
              className="auth-input"
              type="password"
              placeholder="Confirm new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          {/* RESET BUTTON */}
          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading
              ? "Updating Password..."
              : "Reset Password"}
          </button>

        </form>

        {/* BACK TO LOGIN */}
        <div className="auth-footer">
          <button
            type="button"
            className="auth-link"
            onClick={() => navigate("/login")}
          >
            Back to Login
          </button>
        </div>

      </div>
    </div>
  );
}