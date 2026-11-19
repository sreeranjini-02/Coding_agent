import {
  Routes,
  Route,
  Navigate,
  BrowserRouter
} from "react-router-dom";

import Login from "./login";
import Register from "./Register";
import CodingAgent from "./CodingAgent";
import OAuthCallback from "./OAuthCallback";
import ForgotPassword from "./ForgotPassword";
import ResetPassword from "./ResetPassword";

// ===============================
// PROTECTED ROUTE
// ===============================
function ProtectedRoute({ children }) {
  const token =
    localStorage.getItem("access_token") ||
    localStorage.getItem("token");

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

// ===============================
// APP
// ===============================
function App() {

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("token");
    localStorage.removeItem("user");

    window.location.href = "/login";
  };

  return (
    <BrowserRouter>
      <Routes>

        {/* HOME */}
        <Route
          path="/"
          element={<Navigate to="/login" replace />}
        />

        {/* LOGIN */}
        <Route
          path="/login"
          element={<Login />}
        />

        {/* REGISTER */}
        <Route
          path="/register"
          element={<Register />}
        />

        {/* FORGOT PASSWORD */}
        <Route
          path="/forgot-password"
          element={<ForgotPassword />}
        />

        {/* RESET PASSWORD */}
        <Route
          path="/reset-password"
          element={<ResetPassword />}
        />

        {/* GOOGLE OAUTH CALLBACK */}
        <Route
          path="/oauth/callback"
          element={<OAuthCallback />}
        />

        {/* CODING AGENT */}
        <Route
          path="/coding-agent"
          element={
            <ProtectedRoute>
              <CodingAgent
                token={
                  localStorage.getItem("access_token") ||
                  localStorage.getItem("token")
                }
                onLogout={handleLogout}
              />
            </ProtectedRoute>
          }
        />

        {/* OLD CHAT ROUTE */}
        <Route
          path="/chat"
          element={<Navigate to="/coding-agent" replace />}
        />

        {/* INVALID ROUTES */}
        <Route
          path="*"
          element={<Navigate to="/login" replace />}
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;