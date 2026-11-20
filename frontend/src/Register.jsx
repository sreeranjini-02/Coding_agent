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

    if (!token) {
      setError("Invalid or missing reset link.");
      return;
    }

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
            : "Unable to reset password."
        );
      }

      setMessage(
        data.message || "Password reset successfully!"
      );

      setPassword("");
      setConfirmPassword("");

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
    <div className="reset-page">

      <div className="reset-card">

        {/* BRAND */}
        <div className="reset-brand">
          <h1>ZENEX</h1>
          <span>AI CODING AGENT</span>
        </div>

        {/* TITLE */}
        <h2>Reset Password</h2>

        <p className="reset-subtitle">
          Create a new password for your account.
        </p>

        {/* SUCCESS MESSAGE */}
        {message && (
          <div className="reset-success">
            {message}
          </div>
        )}

        {/* ERROR MESSAGE */}
        {error && (
          <div className="reset-error">
            {error}
          </div>
        )}

        {/* PASSWORD FORM */}
        <form onSubmit={handleResetPassword}>

          <div className="reset-input-group">
            <label>New Password</label>

            <input
              type="password"
              placeholder="Enter new password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <div className="reset-input-group">
            <label>Confirm Password</label>

            <input
              type="password"
              placeholder="Confirm new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
            className="reset-button"
            disabled={loading}
          >
            {loading
              ? "Resetting Password..."
              : "Reset Password"}
          </button>

        </form>

        {/* BACK TO LOGIN */}
        <button
          type="button"
          className="reset-back-button"
          onClick={() => navigate("/login")}
        >
          Back to Login
        </button>

      </div>
    </div>
  );
}