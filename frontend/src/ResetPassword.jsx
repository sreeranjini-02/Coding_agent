import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

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
    <div style={{
      minHeight: "100vh",
      background: "#212121",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px",
      color: "white",
      fontFamily: "Arial, sans-serif",
    }}>
      <div style={{
        width: "100%",
        maxWidth: "390px",
        padding: "28px",
        border: "1px solid #383838",
        borderRadius: "18px",
        boxSizing: "border-box",
      }}>

        <h2 style={{ textAlign: "center" }}>
          Reset Password
        </h2>

        <p style={{
          textAlign: "center",
          color: "#a1a1aa",
          fontSize: "14px",
          marginBottom: "25px",
        }}>
          Create a new password for your account.
        </p>

        {message && (
          <p style={{ color: "#86efac" }}>
            {message}
          </p>
        )}

        {error && (
          <p style={{ color: "#ffaaaa" }}>
            {error}
          </p>
        )}

        <form onSubmit={handleResetPassword}>

          <label style={{
            display: "block",
            marginBottom: "8px",
            fontSize: "13px",
          }}>
            New Password
          </label>

          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="New password"
            minLength={8}
            required
            style={{
              width: "100%",
              padding: "12px",
              background: "#2f2f2f",
              border: "1px solid #454545",
              borderRadius: "9px",
              color: "white",
              boxSizing: "border-box",
              marginBottom: "18px",
            }}
          />

          <label style={{
            display: "block",
            marginBottom: "8px",
            fontSize: "13px",
          }}>
            Confirm Password
          </label>

          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm password"
            required
            style={{
              width: "100%",
              padding: "12px",
              background: "#2f2f2f",
              border: "1px solid #454545",
              borderRadius: "9px",
              color: "white",
              boxSizing: "border-box",
              marginBottom: "18px",
            }}
          />

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px",
              background: "white",
              color: "black",
              border: "none",
              borderRadius: "9px",
              fontWeight: "600",
              cursor: "pointer",
            }}
          >
            {loading ? "Updating..." : "Reset Password"}
          </button>

        </form>

      </div>
    </div>
  );
}