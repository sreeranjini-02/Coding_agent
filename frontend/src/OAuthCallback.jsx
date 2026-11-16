import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function OAuthCallback() {
  const navigate = useNavigate();
  const [message, setMessage] = useState("Completing your ZENEX login...");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    const token =
      params.get("token") ||
      params.get("access_token");

    if (token) {
      localStorage.setItem("access_token", token);
      localStorage.setItem("token", token);

      setMessage("Login successful! Opening ZENEX...");

      setTimeout(() => {
        navigate("/coding-agent", { replace: true });
      }, 500);
    } else {
      setMessage("Authentication failed. Please try again.");

      setTimeout(() => {
        navigate("/login", { replace: true });
      }, 2000);
    }
  }, [navigate]);

  return (
    <div
      style={{
        height: "100vh",
        background: "#000",
        color: "#b7a6ff",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "Arial",
        fontSize: "16px",
      }}
    >
      {message}
    </div>
  );
}
