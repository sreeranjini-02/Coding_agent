import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./CodingAgent.css";

const API_URL = "http://127.0.0.1:8000";

const MODES = [
  { id: "generate", label: "Generate", icon: "✦" },
  { id: "debug", label: "Debug", icon: "⌘" },
  { id: "explain", label: "Explain", icon: "◎" },
  { id: "review", label: "Review", icon: "✓" },
  { id: "optimize", label: "Optimize", icon: "⚡" },
  { id: "tests", label: "Tests", icon: "⊞" },
  { id: "convert", label: "Convert", icon: "⇄" },
];

const MODELS = [
  "gemini-3.5-flash-lite",
  "gemini-3.5-flash",
  "gemini-3.6-flash",
  "gemini-3.7-flash",
  "gemini-3.8-flash",
];

export default function CodingAgent() {
  const navigate = useNavigate();

  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("generate");
  const [model, setModel] = useState("gemini-3.5-flash-lite");
  const [autoFallback, setAutoFallback] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const abortControllerRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: loading ? "auto" : "smooth",
    });
  }, [messages, loading]);

  useEffect(() => {
    return () => abortControllerRef.current?.abort();
  }, []);

  const getToken = () =>
    localStorage.getItem("token") ||
    localStorage.getItem("access_token");

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  const updateAssistantMessage = (id, content, extra = {}) => {
    setMessages((previous) =>
      previous.map((message) =>
        message.id === id
          ? { ...message, content, ...extra }
          : message
      )
    );
  };

  const sendMessage = async () => {
    const question = prompt.trim();

    if ((!question && !selectedFile) || loading) return;

    const token = getToken();

    if (!token) {
      logout();
      return;
    }

    setError("");
    setLoading(true);

    const userId = Date.now();
    const assistantId = userId + 1;

    const userMessage = {
      id: userId,
      role: "user",
      content: question || `Analyze ${selectedFile.name}`,
      fileName: selectedFile?.name || null,
    };

    const assistantMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      loading: true,
    };

    setMessages((previous) => [
      ...previous,
      userMessage,
      assistantMessage,
    ]);

    setPrompt("");
    abortControllerRef.current = new AbortController();

    try {
      const formData = new FormData();

      formData.append("prompt", question || "Analyze uploaded file.");
      formData.append("mode", mode);
      formData.append("model", model);
      formData.append("auto_fallback", String(autoFallback));

      if (selectedFile) {
        formData.append("file", selectedFile);
      }

      setSelectedFile(null);

      const response = await fetch(`${API_URL}/coding-agent`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
        signal: abortControllerRef.current.signal,
      });

      if (response.status === 401) {
        logout();
        throw new Error("Session expired. Login again.");
      }

      if (!response.ok) {
        let message = `Backend error: ${response.status}`;

        try {
          const data = await response.json();
          message =
            typeof data.detail === "string"
              ? data.detail
              : JSON.stringify(data.detail || data);
        } catch {
          // Response was not JSON.
        }

        throw new Error(message);
      }

      if (!response.body) {
        throw new Error("Streaming response unavailable.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let output = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        output += decoder.decode(value, { stream: true });

        updateAssistantMessage(assistantId, output);
      }

      output += decoder.decode();

      if (!output.trim()) {
        throw new Error(
          "Empty response. Check Gemini backend logs."
        );
      }

      updateAssistantMessage(assistantId, output, {
        loading: false,
      });

    } catch (err) {
      if (err.name === "AbortError") {
        updateAssistantMessage(assistantId, "", {
          loading: false,
          stopped: true,
        });
        return;
      }

      console.error(err);

      setError(err.message || "Unable to connect to backend.");

      updateAssistantMessage(
        assistantId,
        `⚠️ ${err.message || "Response failed."}`,
        { loading: false }
      );

    } finally {
      setLoading(false);
      abortControllerRef.current = null;
      textareaRef.current?.focus();
    }
  };

  const newChat = () => {
    if (loading) return;
    setMessages([]);
    setError("");
    setPrompt("");
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chatgpt-app">

      {/* SIDEBAR */}

      <aside className={`chat-sidebar ${sidebarOpen ? "" : "collapsed"}`}>

        <div className="sidebar-top">

          <div className="sidebar-brand">
            <div className="sidebar-logo">✦</div>
            {sidebarOpen && <span>AI Coding Agent</span>}
          </div>

          <button
            className="sidebar-icon-button"
            title="Collapse sidebar"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            ☰
          </button>

        </div>

        <button className="sidebar-new-chat" onClick={newChat}>
          <span>＋</span>
          {sidebarOpen && <span>New chat</span>}
        </button>

        {sidebarOpen && (
          <>
            <div className="sidebar-section-title">CODING TOOLS</div>

            <div className="sidebar-tools">
              {MODES.map((item) => (
                <button
                  key={item.id}
                  className={`sidebar-tool ${
                    mode === item.id ? "selected" : ""
                  }`}
                  onClick={() => setMode(item.id)}
                >
                  <span>{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </div>
          </>
        )}

        <div className="sidebar-bottom">
          <button
            className="sidebar-profile"
            onClick={logout}
            title="Logout"
          >
            <div className="profile-avatar">S</div>
            {sidebarOpen && (
              <div className="profile-info">
                <strong>My Account</strong>
                <small>Logout</small>
              </div>
            )}
          </button>
        </div>

      </aside>

      {/* MAIN */}

      <main className="chat-main">

        {/* HEADER */}

        <header className="chat-header">

          <div className="chat-header-left">
            {!sidebarOpen && (
              <button
                className="header-menu"
                onClick={() => setSidebarOpen(true)}
              >
                ☰
              </button>
            )}

            <span className="header-title">Coding Agent</span>

            <span className="header-mode">
              {MODES.find((item) => item.id === mode)?.label}
            </span>
          </div>

          <button
            className="header-model"
            onClick={() => setSettingsOpen(!settingsOpen)}
          >
            {model}
            <span>⌄</span>
          </button>

        </header>

        {/* CHAT */}

        <section className="chat-scroll">

          {messages.length === 0 ? (

            <div className="chat-welcome">
              <h1>What can I help you code?</h1>

              <p>
                Generate, debug, explain, review and optimize code.
              </p>

              <div className="welcome-tools">
                {MODES.slice(0, 4).map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      setMode(item.id);
                      textareaRef.current?.focus();
                    }}
                  >
                    <span>{item.icon}</span>
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

          ) : (

            <div className="chat-conversation">

              {messages.map((message) => (

                <div
                  key={message.id}
                  className={`chat-message ${
                    message.role === "user"
                      ? "user-message"
                      : "assistant-message"
                  }`}
                >

                  {message.role === "user" ? (

                    <div className="user-bubble">
                      {message.fileName && (
                        <div className="user-file">
                          📎 {message.fileName}
                        </div>
                      )}
                      {message.content}
                    </div>

                  ) : (

                    <div className="assistant-content">

                      {message.content ? (
                        <pre>{message.content}</pre>
                      ) : message.loading ? (
                        <div className="chat-thinking">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      ) : null}

                      {message.stopped && (
                        <small className="stopped-label">
                          Generation stopped.
                        </small>
                      )}

                    </div>

                  )}

                </div>

              ))}

              <div ref={messagesEndRef} />

            </div>

          )}

        </section>

        {/* ERROR */}

        {error && (
          <div className="chat-error">
            {error}
            <button onClick={() => setError("")}>×</button>
          </div>
        )}

        {/* COMPOSER */}

        <footer className="chat-composer-wrapper">

          {selectedFile && (
            <div className="composer-file">
              📎 {selectedFile.name}
              <button onClick={() => setSelectedFile(null)}>×</button>
            </div>
          )}

          {settingsOpen && (
            <div className="model-popup">

              <strong>Choose Gemini Model</strong>

              {MODELS.map((item) => (
                <button
                  key={item}
                  className={model === item ? "active" : ""}
                  onClick={() => {
                    setModel(item);
                    setSettingsOpen(false);
                  }}
                >
                  {item}
                  {model === item && <span>✓</span>}
                </button>
              ))}

              <label>
                <input
                  type="checkbox"
                  checked={autoFallback}
                  onChange={(event) =>
                    setAutoFallback(event.target.checked)
                  }
                />
                Auto fallback
              </label>

            </div>
          )}

          <div className="chat-composer">

            <textarea
              ref={textareaRef}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message AI Coding Agent..."
              rows={1}
              disabled={loading}
            />

            <div className="composer-bottom">

              <div className="composer-actions">

                <input
                  ref={fileInputRef}
                  type="file"
                  hidden
                  accept=".txt,.py,.java,.js,.jsx,.ts,.tsx,.html,.css,.json,.sql,.md,.csv,.pdf,.docx,.xlsx"
                  onChange={(event) =>
                    setSelectedFile(event.target.files?.[0] || null)
                  }
                />

                <button
                  title="Attach file"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading}
                >
                  ＋
                </button>

                <button
                  title="Model settings"
                  onClick={() => setSettingsOpen(!settingsOpen)}
                >
                  ⚙
                </button>

                <span className="composer-mode">
                  {mode.toUpperCase()}
                </span>

              </div>

              <button
                className={`composer-send ${
                  loading ? "stop-generation" : ""
                }`}
                onClick={() => {
                  if (loading) {
                    abortControllerRef.current?.abort();
                  } else {
                    sendMessage();
                  }
                }}
                title={loading ? "Stop" : "Send"}
              >
                {loading ? "■" : "↑"}
              </button>

            </div>

          </div>

          <div className="composer-footer">
            AI-generated code may contain errors. Review before using.
          </div>

        </footer>

      </main>

    </div>
  );
}
