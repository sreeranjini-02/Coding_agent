import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Register() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e) => {
    e.preventDefault();

    setError("");
    setSuccess("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must contain at least 8 characters");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        "http://localhost:8000/auth/register",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username,
            email,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Registration failed"
        );
      }

      setSuccess("Account created successfully!");

      setTimeout(() => {
        navigate("/login");
      }, 1500);

    } catch (err) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: "100%",
    padding: "12px",
    background: "#2f2f2f",
    border: "1px solid #454545",
    borderRadius: "9px",
    color: "#ffffff",
    boxSizing: "border-box",
    marginBottom: "18px",
    outline: "none",
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
        maxWidth: "400px",
        padding: "30px",
        border: "1px solid #383838",
        borderRadius: "18px",
        boxSizing: "border-box",
      }}>

        <h1 style={{
          textAlign: "center",
          fontSize: "28px",
          marginBottom: "8px",
        }}>
          Create account
        </h1>

        <p style={{
          textAlign: "center",
          color: "#a1a1aa",
          fontSize: "14px",
          marginBottom: "25px",
        }}>
          Get started with ZENEX
        </p>

        {error && (
          <div style={{
            background: "#3b2020",
            color: "#ffaaaa",
            padding: "12px",
            borderRadius: "8px",
            fontSize: "13px",
            marginBottom: "18px",
          }}>
            {error}
          </div>
        )}

        {success && (
          <div style={{
            background: "#16351f",
            color: "#86efac",
            padding: "12px",
            borderRadius: "8px",
            fontSize: "13px",
            marginBottom: "18px",
          }}>
            {success}
          </div>
        )}

        <form onSubmit={handleRegister}>

          <label>Username</label>

          <input
            type="text"
            placeholder="Choose a username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={inputStyle}
            minLength={3}
            maxLength={50}
            required
          />

          <label>Email</label>

          <input
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={inputStyle}
            required
          />

          <label>Password</label>

          <input
            type="password"
            placeholder="Create a password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={inputStyle}
            minLength={8}
            maxLength={72}
            required
          />

          <label>Confirm Password</label>

          <input
            type="password"
            placeholder="Confirm your password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            style={inputStyle}
            required
          />

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "12px",
              background: "#ffffff",
              color: "#000000",
              border: "none",
              borderRadius: "9px",
              fontWeight: "600",
              cursor: "pointer",
              opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "Creating account..." : "Create Account"}
          </button>

        </form>

        <p style={{
          textAlign: "center",
          color: "#a1a1aa",
          fontSize: "13px",
          marginTop: "22px",
        }}>
          Already have an account?{" "}
          <span
            onClick={() => navigate("/login")}
            style={{
              color: "white",
              cursor: "pointer",
              fontWeight: "600",
            }}
          >
            Sign in
          </span>
        </p>

      </div>
    </div>
  );
}
