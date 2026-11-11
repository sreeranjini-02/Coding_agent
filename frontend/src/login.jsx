
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./Login.css";

export default function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/auth/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username_or_email: email.trim(),
            password: password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        let message = "Login failed";

        if (typeof data.detail === "string") {
          message = data.detail;
        } else if (Array.isArray(data.detail)) {
          message = data.detail
            .map((item) => item.msg)
            .join(", ");
        } else if (data.message) {
          message = data.message;
        }

        throw new Error(message);
      }

      if (!data.access_token) {
        throw new Error("Login succeeded but token was not received.");
      }

      // Save authentication token
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("access_token", data.access_token);

      // Save user information
      if (data.user) {
        localStorage.setItem("user", JSON.stringify(data.user));
      }

      // Redirect to Coding Agent
      navigate("/coding-agent", { replace: true });

    } catch (err) {
      console.error("Login error:", err);

      if (err.name === "TypeError") {
        setError(
          "Cannot connect to backend. Check whether FastAPI is running on port 8000."
        );
      } else {
        setError(err.message || "Something went wrong.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    setError(
      "Google authentication is not configured yet. Please use email and password."
    );
  };

  return (
    <div className="login-page">
      <div className="login-glow glow-one"></div>
      <div className="login-glow glow-two"></div>

      <div className="login-brand">
        <div className="brand-icon">✦</div>
        <span>AI Coding Agent</span>
      </div>

      <div className="login-container">
        <div className="login-heading">
          <h1>Welcome back</h1>
          <p>Sign in to continue building something amazing.</p>
        </div>

        <form onSubmit={handleLogin}>
          <div className="login-field">
            <label>Email address or username</label>

            <input
              type="text"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </div>

          <div className="login-field">
            <div className="password-label">
              <label>Password</label>

              <Link to="/forgot-password">
                Forgot password?
              </Link>
            </div>

            <div className="password-input">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />

              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="login-submit"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Continue"}
          </button>
        </form>

        <div className="login-divider">
          <span>OR</span>
        </div>

        <button
          type="button"
          className="google-login"
          onClick={handleGoogleLogin}
        >
          <img
            src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg"
            alt="Google"
          />
          Continue with Google
        </button>

        <div className="login-register">
          Don't have an account?

          <Link to="/register">
            Create account
          </Link>
        </div>

        <div className="login-footer">
          Secure authentication · AI Coding Agent
        </div>
      </div>
    </div>
  );
}
