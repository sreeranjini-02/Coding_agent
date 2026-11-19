import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./auth.css";

const API_URL = "http://localhost:8000";

export default function OAuthCallback() {
  const navigate = useNavigate();

  const [message, setMessage] = useState(
    "Completing your ZENEX login..."
  );

  useEffect(() => {
    let isMounted = true;

    const verifyOAuthToken = async () => {
      console.log("========== OAUTH CALLBACK ==========");

      // ============================================
      // STEP 1: READ TOKEN FROM CALLBACK URL
      // ============================================

      const params = new URLSearchParams(
        window.location.search
      );

      const token =
        params.get("token") ||
        params.get("access_token");

      console.log("OAuth callback loaded");
      console.log("Token received:", Boolean(token));

      // ============================================
      // STEP 2: REMOVE TOKEN FROM URL
      // ============================================

      window.history.replaceState(
        {},
        document.title,
        window.location.pathname
      );

      // ============================================
      // STEP 3: CHECK TOKEN
      // ============================================

      if (!token) {
        console.error("OAuth token missing");

        if (isMounted) {
          setMessage(
            "Authentication token was not received."
          );
        }

        localStorage.removeItem("access_token");
        localStorage.removeItem("token");
        localStorage.removeItem("user");

        navigate(
          "/login?error=token_missing",
          { replace: true }
        );

        return;
      }

      // ============================================
      // STEP 4: CHECK JWT STRUCTURE
      // ============================================

      const jwtParts = token.split(".");

      if (jwtParts.length !== 3) {
        console.error("Invalid JWT structure");

        localStorage.removeItem("access_token");
        localStorage.removeItem("token");
        localStorage.removeItem("user");

        navigate(
          "/login?error=invalid_token",
          { replace: true }
        );

        return;
      }

      console.log("JWT structure appears valid");

      // ============================================
      // STEP 5: VERIFY TOKEN WITH BACKEND
      // ============================================

      try {
        if (isMounted) {
          setMessage(
            "Verifying your authentication..."
          );
        }

        const response = await fetch(
          `${API_URL}/auth/me`,
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
              Accept: "application/json",
            },
          }
        );

        console.log(
          "Backend verification status:",
          response.status
        );

        if (!response.ok) {
          throw new Error(
            `Token verification failed: ${response.status}`
          );
        }

        // ============================================
        // STEP 6: GET USER DETAILS
        // ============================================

        const user = await response.json();

        if (!user || !user.id || !user.email) {
          throw new Error(
            "Invalid user information returned by backend"
          );
        }

        console.log(
          "OAuth authentication verified successfully"
        );

        // ============================================
        // STEP 7: STORE AUTHENTICATION
        // ============================================

        localStorage.setItem(
          "access_token",
          token
        );

        localStorage.setItem(
          "token",
          token
        );

        localStorage.setItem(
          "user",
          JSON.stringify(user)
        );

        console.log(
          "Authentication data stored successfully"
        );

        // ============================================
        // STEP 8: REDIRECT
        // ============================================

        if (isMounted) {
          setMessage(
            "Login successful! Opening ZENEX..."
          );
        }

        setTimeout(() => {
          if (isMounted) {
            navigate(
              "/coding-agent",
              { replace: true }
            );
          }
        }, 700);

      } catch (error) {
        console.error(
          "OAuth verification failed:",
          error.message
        );

        // ============================================
        // STEP 9: CLEAR INVALID AUTHENTICATION
        // ============================================

        localStorage.removeItem("access_token");
        localStorage.removeItem("token");
        localStorage.removeItem("user");

        if (isMounted) {
          setMessage(
            "Authentication failed. Redirecting to login..."
          );
        }

        setTimeout(() => {
          if (isMounted) {
            navigate(
              "/login?error=oauth_verification_failed",
              { replace: true }
            );
          }
        }, 1500);
      }

      console.log("========== CALLBACK FINISHED ==========");
    };

    verifyOAuthToken();

    return () => {
      isMounted = false;
    };
  }, [navigate]);

  // ============================================
  // UI
  // ============================================

  return (
    <div className="auth-page">
      <div className="auth-card auth-status-card">
        <div className="auth-spinner" />
        <p className="auth-status">{message}</p>
      </div>
    </div>
  );
}