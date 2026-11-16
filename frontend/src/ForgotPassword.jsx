import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

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

  const styles = {
    page: {
      minHeight: "100vh",
      background: "#212121",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px",
      color: "white",
      fontFamily: "Arial, sans-serif",
    },
    card: {
      width: "100%",
      maxWidth: "390px",
      padding: "28px",
      background: "#212121",
      border: "1px solid #383838",
      borderRadius: "18px",
      boxSizing: "border-box",
    },
    input: {
      width: "100%",
      padding: "12px",
      background: "#2f2f2f",
      border: "1px solid #454545",
      borderRadius: "9px",
      color: "white",
      boxSizing: "border-box",
      marginBottom: "18px",
    },
    button: {
      width: "100%",
      padding: "12px",
      background: "white",
      color: "black",
      border: "none",
      borderRadius: "9px",
      fontWeight: "600",
      cursor: "pointer",
    },
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>

        <h2 style={{ textAlign: "center" }}>
          Forgot password?
        </h2>

        <p style={{
          textAlign: "center",
          color: "#a1a1aa",
          fontSize: "14px",
          marginBottom: "25px",
        }}>
          Enter your email to reset your password.
        </p>

        {message && (
          <div style={{
            color: "#86efac",
            background: "#16351f",
            padding: "12px",
            borderRadius: "8px",
            fontSize: "13px",
            marginBottom: "18px",
          }}>
            {message}
          </div>
        )}

        {error && (
          <div style={{
            color: "#ffaaaa",
            background: "#3b2020",
            padding: "12px",
            borderRadius: "8px",
            fontSize: "13px",
            marginBottom: "18px",
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleForgotPassword}>
          <label style={{
            display: "block",
            marginBottom: "8px",
            fontSize: "13px",
          }}>
            Email address
          </label>

          <input
            type="email"
            placeholder="Enter your registered email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={styles.input}
            required
          />

          <button
            type="submit"
            disabled={loading}
            style={{
              ...styles.button,
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "Sending..." : "Send Reset Link"}
          </button>
        </form>

        <p
          onClick={() => navigate("/login")}
          style={{
            textAlign: "center",
            color: "#a1a1aa",
            cursor: "pointer",
            fontSize: "13px",
            marginTop: "22px",
          }}
        >
          ← Back to Login
        </p>

      </div>
    </div>
  );
}