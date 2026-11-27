import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as XLSX from "xlsx";
import * as pdfjsLib from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import mammoth from "mammoth";
import "./CodingAgent.css";
import { FormattedMessage, extractCodeBlocks } from "./ChatFormatter";
import DiffView from "./DiffView";
import OnboardingTour, { TOUR_KEY } from "./OnboardingTour";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

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

// Languages and the frameworks offered for each one
const FRAMEWORKS = {
  Python: ["None", "Django", "Flask", "FastAPI", "pandas"],
  JavaScript: ["None", "React", "Node.js / Express", "Vue"],
  TypeScript: ["None", "React", "Node.js / Express"],
  Java: ["None", "Spring Boot"],
  "C#": ["None", "ASP.NET Core"],
  SQL: ["None", "PostgreSQL", "MySQL"],
};

const LANGUAGE_OPTIONS = ["Auto", ...Object.keys(FRAMEWORKS)];

// Plain text file types that are read directly in the browser
const TEXT_PREVIEW_EXTENSIONS = [
  "txt", "py", "java", "js", "jsx", "ts", "tsx",
  "html", "css", "json", "sql", "md", "csv",
];

const PREVIEW_LINES = 20;
const PREVIEW_ROWS = 8;

// Words that can come before the tool word at the start of a line
const POLITE = "^\\s*(please\\s+|kindly\\s+|can you\\s+|could you\\s+)?";

// Order matters: the most specific patterns come first
const TOOL_PATTERNS = [
  { id: "tests", re: new RegExp(POLITE + "(generate|write|create|add)\\b.*\\btests?\\b", "i") },
  { id: "optimize", re: new RegExp(POLITE + "(optimi[sz]e|make (this|it|the code) (faster|more efficient))\\b", "i") },
  { id: "debug", re: new RegExp(POLITE + "(debug|fix (this|the|my) (bug|error|code))\\b", "i") },
  { id: "explain", re: new RegExp(POLITE + "explain\\b", "i") },
  { id: "review", re: new RegExp(POLITE + "review\\b", "i") },
  { id: "convert", re: new RegExp(POLITE + "convert\\b", "i") },
  { id: "generate", re: new RegExp(POLITE + "generate\\b", "i") },
];

// Checks every prose line, ignoring fenced code blocks
const findIntendedTool = (text) => {
  const prose = text.replace(/```[\s\S]*?```/g, "\n");
  const lines = prose
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  for (const line of lines) {
    const found = TOOL_PATTERNS.find((p) => p.re.test(line));
    if (found) return found.id;
  }

  return null;
};

// Original code: the first code block in the user's request,
// or the whole message if it has several lines but no code block
const extractOriginalCode = (text) => {
  if (!text) return null;

  const blocks = extractCodeBlocks(text);
  if (blocks.length > 0) return blocks[0].code;

  const trimmed = text.trim();
  return trimmed.includes("\n") ? trimmed : null;
};

// Optimized code: the block under the "Optimized Code" heading if there is one,
// otherwise the largest code block in the reply
const extractOptimizedCode = (content) => {
  const blocks = extractCodeBlocks(content || "");
  if (blocks.length === 0) return null;

  const headingMatch = content.match(/^\s*#*\s*optimized code\s*$/im);
  if (headingMatch) {
    const after = extractCodeBlocks(content.slice(headingMatch.index));
    if (after.length > 0) return after[0].code;
  }

  return blocks.reduce((best, block) =>
    block.code.length > best.code.length ? block : best
  ).code;
};

// Builds the comparison for an assistant reply at a given position
const getDiffPair = (list, index) => {
  const message = list[index];

  if (!message || message.role !== "assistant" || message.loading) return null;

  const optimized = extractOptimizedCode(message.content);
  if (!optimized) return null;

  let previousUser = null;
  for (let i = index - 1; i >= 0; i--) {
    if (list[i].role === "user") {
      previousUser = list[i];
      break;
    }
  }

  return {
    original: extractOriginalCode(previousUser?.content),
    fromFile: Boolean(previousUser?.fileName),
    optimized,
  };
};

const formatSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default function CodingAgent() {
  const navigate = useNavigate();

  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("generate");
  const [model, setModel] = useState("gemini-3.5-flash-lite");
  const [autoFallback, setAutoFallback] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(true);
  const [language, setLanguage] = useState("Auto");
  const [framework, setFramework] = useState("None");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [openDiffs, setOpenDiffs] = useState({});
  const [theme, setTheme] = useState(
    () => localStorage.getItem("zenex_theme") || "light"
  );

  // Show the tour on the first visit only
  const [tourOpen, setTourOpen] = useState(
    () => !localStorage.getItem(TOUR_KEY)
  );

  // Chats loaded from MySQL
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);

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

  // Dark mode: sets data-theme on <html>, which theme.css reads
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("zenex_theme", theme);
  }, [theme]);

  // File preview: text, PDF, and DOCX show their first lines; Excel shows its first rows
  useEffect(() => {
    if (!selectedFile) {
      setFilePreview(null);
      return;
    }

    const extension = selectedFile.name.split(".").pop().toLowerCase();
    let cancelled = false;

    const showText = (text) => {
      if (cancelled) return;
      const lines = text.split("\n");
      setFilePreview({
        kind: "text",
        lineCount: lines.length,
        text: lines.slice(0, PREVIEW_LINES).join("\n"),
      });
    };

    const load = async () => {
      if (extension === "xlsx") {
        const buffer = await selectedFile.arrayBuffer();
        const workbook = XLSX.read(buffer, { type: "array" });
        const sheetName = workbook.SheetNames[0];
        const rows = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], {
          header: 1,
          defval: "",
        });

        if (!cancelled) {
          setFilePreview({
            kind: "table",
            sheetName,
            sheetCount: workbook.SheetNames.length,
            rowCount: rows.length,
            rows: rows.slice(0, PREVIEW_ROWS),
          });
        }
        return;
      }

      if (extension === "pdf") {
        const buffer = await selectedFile.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({
          data: new Uint8Array(buffer),
        }).promise;

        let text = "";
        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber++) {
          const page = await pdf.getPage(pageNumber);
          const content = await page.getTextContent();
          text += `--- Page ${pageNumber} ---\n`;
          text += content.items.map((item) => item.str).join(" ") + "\n";
        }

        showText(text.trim() || "No selectable text found in this PDF.");
        return;
      }

      if (extension === "docx") {
        const buffer = await selectedFile.arrayBuffer();
        const result = await mammoth.extractRawText({ arrayBuffer: buffer });
        showText(result.value.trim() || "No text found in this document.");
        return;
      }

      if (TEXT_PREVIEW_EXTENSIONS.includes(extension)) {
        showText(await selectedFile.text());
        return;
      }

      if (!cancelled) setFilePreview({ kind: "none" });
    };

    setFilePreview({ kind: "loading" });

    load().catch((err) => {
      console.error("File preview failed:", err);
      if (!cancelled) setFilePreview({ kind: "error", message: err.message });
    });

    return () => {
      cancelled = true;
    };
  }, [selectedFile]);

  const getToken = () =>
    localStorage.getItem("token") || localStorage.getItem("access_token");

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  // --------------------------------------------------
  // API HELPER
  // --------------------------------------------------

  const apiFetch = async (path, options = {}) => {
    const token = getToken();

    if (!token) {
      logout();
      throw new Error("Please login again.");
    }

    const headers = { Authorization: `Bearer ${token}` };

    if (options.json !== undefined) {
      headers["Content-Type"] = "application/json";
    }

    const response = await fetch(`${API_URL}${path}`, {
      method: options.method || "GET",
      headers,
      body:
        options.json !== undefined
          ? JSON.stringify(options.json)
          : options.body,
      signal: options.signal,
    });

    if (response.status === 401) {
      logout();
      throw new Error("Session expired. Login again.");
    }

    if (!response.ok) {
      let message = `Request failed: ${response.status}`;
      try {
        const data = await response.json();
        if (typeof data.detail === "string") message = data.detail;
      } catch {
        // Response was not JSON
      }
      throw new Error(message);
    }

    return response;
  };

  const updateAssistantMessage = (id, content, extra = {}) => {
    setMessages((previous) =>
      previous.map((message) =>
        message.id === id ? { ...message, content, ...extra } : message
      )
    );
  };

  // --------------------------------------------------
  // CHAT STORAGE (MySQL through FastAPI)
  // --------------------------------------------------

  const loadConversations = async () => {
    const response = await apiFetch("/chat/conversations");
    const data = await response.json();
    setConversations(data.conversations || []);
  };

  useEffect(() => {
    loadConversations().catch((err) => setError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchMessages = async (id) => {
    const response = await apiFetch(`/chat/conversations/${id}/messages`);
    const data = await response.json();
    return (data.messages || []).map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      answeredBy: m.model_name,
      fallbackUsed: false,
    }));
  };

  const createConversation = async () => {
    const response = await apiFetch("/chat/conversations", {
      method: "POST",
      json: { title: "New Chat", mode },
    });
    const data = await response.json();

    if (!data.conversation_id) {
      throw new Error("Conversation ID was not returned from the backend.");
    }

    setConversationId(data.conversation_id);
    return data.conversation_id;
  };

  // Saves user messages only. The backend saves assistant replies.
  const saveUserMessage = (convId, content) =>
    apiFetch(`/chat/conversations/${convId}/messages`, {
      method: "POST",
      json: { role: "user", content, model_name: null },
    }).catch((err) => console.error("Could not save message:", err));

  // --------------------------------------------------
  // LANGUAGE AND FRAMEWORK
  // --------------------------------------------------

  // Adds the language choice to the prompt sent to the model.
  // The chat shows and saves only what the user typed.
  const buildModelPrompt = (text) => {
    if (mode !== "generate" && mode !== "convert") return text;
    if (language === "Auto") return text;

    const using = framework !== "None" ? ` using ${framework}` : "";
    const instruction =
      mode === "convert"
        ? `Convert the code to ${language}${using}.`
        : `Write the code in ${language}${using}.`;

    return `${text}\n\n${instruction}`;
  };

  // --------------------------------------------------
  // SEND MESSAGE
  // --------------------------------------------------

  const sendMessage = async () => {
    const question = prompt.trim();

    if ((!question && !selectedFile) || loading) return;

    // Block requests that belong to another tool.
    // The notice is shown in the chat and the text stays in the box.
    if (question) {
      const intended = findIntendedTool(question);
      if (intended && intended !== mode) {
        const label = MODES.find((m) => m.id === intended)?.label || intended;
        setMessages((previous) => [
          ...previous,
          {
            id: Date.now(),
            role: "assistant",
            content: `I don't work here. Please use the **${label}** option for this request. Your message is still in the box, so you can switch tabs and send it there.`,
          },
        ]);
        return;
      }
    }

    setError("");
    setLoading(true);

    const fileToUpload = selectedFile;
    const userText = question || `Analyze ${fileToUpload.name}`;
    const userId = Date.now();
    const assistantId = userId + 1;

    setMessages((previous) => [
      ...previous,
      {
        id: userId,
        role: "user",
        content: userText,
        fileName: fileToUpload?.name || null,
      },
      { id: assistantId, role: "assistant", content: "", loading: true },
    ]);
    setPrompt("");

    abortControllerRef.current = new AbortController();

    try {
      // Create the chat in MySQL on the first message
      let activeId = conversationId;
      if (!activeId) {
        activeId = await createConversation();
      }

      await saveUserMessage(activeId, userText);

      const formData = new FormData();
      formData.append(
        "prompt",
        buildModelPrompt(question || "Analyze uploaded file.")
      );
      formData.append("mode", mode);
      formData.append("model", model);
      formData.append("auto_fallback", String(autoFallback));
      formData.append("conversation_id", String(activeId));

      if (fileToUpload) {
        formData.append("file", fileToUpload);
      }

      const response = await apiFetch("/coding-agent", {
        method: "POST",
        body: formData,
        signal: abortControllerRef.current.signal,
      });

      // Backend sends the model that actually answered.
      const activeModel = response.headers.get("X-Active-Model") || model;
      const fallbackUsed = response.headers.get("X-Fallback-Used") === "true";

      setSelectedFile(null);

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
        throw new Error("Empty response. Check Gemini backend logs.");
      }

      // The backend saves this reply to MySQL, so no save happens here.
      updateAssistantMessage(assistantId, output, {
        loading: false,
        answeredBy: activeModel,
        fallbackUsed,
      });
    } catch (err) {
      if (err.name === "AbortError") {
        updateAssistantMessage(assistantId, "", {
          loading: false,
          stopped: true,
        });
        return;
      }

      console.error("Coding Agent Error:", err);
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
      loadConversations().catch(() => {});
    }
  };

  // --------------------------------------------------
  // CHAT HISTORY AND TOOL TABS
  // --------------------------------------------------

  const newChat = () => {
    if (loading) return;

    setMessages([]);
    setError("");
    setPrompt("");
    setSelectedFile(null);
    setConversationId(null);
  };

  const openConversation = async (conv) => {
    if (loading) return;

    setError("");
    setPrompt("");
    setSelectedFile(null);
    setConversationId(conv.id);
    setMode(conv.mode || "generate");
    setMessages([]);
    setOpenDiffs({});

    try {
      setMessages(await fetchMessages(conv.id));
    } catch (err) {
      setError(err.message || "Could not load this chat.");
    }
  };

  // Each tool has its own tab: open its latest chat, or a blank one
  const selectTool = (id) => {
    if (loading) return;

    const latest = conversations.find((c) => (c.mode || "generate") === id);

    if (latest) {
      openConversation(latest);
    } else {
      newChat();
      setMode(id);
    }
  };

  const deleteConversation = async (id, event) => {
    event.stopPropagation();
    if (loading) return;

    if (!window.confirm("Delete this chat?")) return;

    try {
      await apiFetch(`/chat/conversations/${id}`, { method: "DELETE" });

      if (conversationId === id) {
        newChat();
      }

      await loadConversations();
    } catch (err) {
      setError(err.message || "Could not delete chat.");
    }
  };

  const toggleDiff = (id) => {
    setOpenDiffs((previous) => ({ ...previous, [id]: !previous[id] }));
  };

  const visibleConversations = conversations.filter(
    (c) => (c.mode || "generate") === mode
  );

  // --------------------------------------------------
  // KEYBOARD
  // --------------------------------------------------

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  const showLanguagePicker = mode === "generate" || mode === "convert";

  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (
    <div className="chatgpt-app">
      {/* SIDEBAR */}

      <aside className={`chat-sidebar ${sidebarOpen ? "" : "collapsed"}`}>
        <div className="sidebar-top">
          <div className="sidebar-brand">
            <div className="sidebar-logo">✦</div>
            {sidebarOpen && <span>ZENEX</span>}
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
          <div className="sidebar-middle">
            <div className="sidebar-section-title">CODING TOOLS</div>

            <div className="sidebar-tools">
              {MODES.map((item) => (
                <button
                  key={item.id}
                  className={`sidebar-tool ${mode === item.id ? "selected" : ""}`}
                  onClick={() => selectTool(item.id)}
                >
                  <span>{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </div>

            <button
              className="sidebar-section-toggle"
              onClick={() => setHistoryOpen(!historyOpen)}
              aria-expanded={historyOpen}
            >
              <span>CHAT HISTORY</span>
              <span className="toggle-caret">{historyOpen ? "▾" : "▸"}</span>
            </button>

            {historyOpen && (
              <div className="chat-history">
                <div className="history-list">
                  {visibleConversations.length === 0 && (
                    <div className="history-empty">
                      {`No ${MODES.find((m) => m.id === mode)?.label} chats yet`}
                    </div>
                  )}

                  {visibleConversations.map((chat) => (
                    <div
                      key={chat.id}
                      className={`history-row ${chat.id === conversationId ? "active" : ""}`}
                    >
                      <button
                        className="history-item"
                        onClick={() => openConversation(chat)}
                        title={chat.title}
                      >
                        {chat.title || "Untitled chat"}
                      </button>

                      <button
                        className="history-delete"
                        title="Delete chat"
                        onClick={(event) => deleteConversation(chat.id, event)}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="sidebar-bottom">
          <button className="sidebar-profile" onClick={logout} title="Logout">
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
        <header className="chat-header">
          <div className="chat-header-left">
            {!sidebarOpen && (
              <button className="header-menu" onClick={() => setSidebarOpen(true)}>
                ☰
              </button>
            )}

            <span className="header-title">ZENEX AI</span>

            <span className="header-mode">
              {MODES.find((item) => item.id === mode)?.label}
            </span>
          </div>

          <div className="chat-header-right">
            <button
              className="header-tour"
              title="Show the tour"
              onClick={() => setTourOpen(true)}
            >
              ?
            </button>

            <button
              className="header-theme"
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? "☀" : "☾"}
            </button>

            <button
              className="header-model"
              onClick={() => setSettingsOpen(!settingsOpen)}
            >
              {model}
              <span>⌄</span>
            </button>
          </div>
        </header>

        <section className="chat-scroll">
          {messages.length === 0 ? (
            <div className="chat-welcome">
              <h1>Welcome to ZENEX</h1>
              <p>Generate, debug, explain, review and optimize code.</p>

              <div className="welcome-tools">
                {MODES.slice(0, 4).map((item) => (
                  <button key={item.id} onClick={() => selectTool(item.id)}>
                    <span>{item.icon}</span>
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="chat-conversation">
              {messages.map((message, index) => {
                const pair =
                  mode === "optimize" || mode === "convert"
                    ? getDiffPair(messages, index)
                    : null;

                return (
                  <div
                    key={message.id}
                    className={`chat-message ${
                      message.role === "user" ? "user-message" : "assistant-message"
                    }`}
                  >
                    {message.role === "user" ? (
                      <div className="user-bubble">
                        {message.fileName && (
                          <div className="user-file">📎 {message.fileName}</div>
                        )}
                        {message.content}
                      </div>
                    ) : (
                      <div className="assistant-content">
                        {message.content ? (
                          <FormattedMessage content={message.content} />
                        ) : message.loading ? (
                          <div className="chat-thinking">
                            <span></span>
                            <span></span>
                            <span></span>
                          </div>
                        ) : null}

                        {message.answeredBy && (
                          <small className="answered-by">
                            Answered by {message.answeredBy}
                            {message.fallbackUsed ? " (fallback)" : ""}
                          </small>
                        )}

                        {pair && (
                          <div>
                            <button
                              type="button"
                              onClick={() => toggleDiff(message.id)}
                              className="diff-toggle"
                            >
                              {openDiffs[message.id] ? "Hide diff" : "Show diff"}
                            </button>

                            {openDiffs[message.id] && (
                              <DiffView
                                original={pair.original}
                                optimized={pair.optimized}
                              />
                            )}

                            {openDiffs[message.id] && pair.fromFile && !pair.original && (
                              <small className="diff-note">
                                This request used an uploaded file, so the original code can't be compared.
                              </small>
                            )}
                          </div>
                        )}

                        {message.stopped && (
                          <small className="stopped-label">Generation stopped.</small>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              <div ref={messagesEndRef} />
            </div>
          )}
        </section>

        {error && (
          <div className="chat-error">
            {error}
            <button onClick={() => setError("")}>×</button>
          </div>
        )}

        <footer className="chat-composer-wrapper">
          {selectedFile && (
            <div className="file-preview">
              <div className="file-preview-head">
                <span>
                  📎 {selectedFile.name} · {formatSize(selectedFile.size)}
                  {filePreview?.kind === "text" && filePreview.lineCount
                    ? ` · ${filePreview.lineCount} lines`
                    : ""}
                </span>

                <div className="file-preview-actions">
                  <button onClick={() => setPreviewOpen(!previewOpen)}>
                    {previewOpen ? "Hide preview" : "Show preview"}
                  </button>
                  <button onClick={() => setSelectedFile(null)} title="Remove file">
                    ×
                  </button>
                </div>
              </div>

              {previewOpen && filePreview?.kind === "loading" && (
                <div className="file-preview-note">Reading file...</div>
              )}

              {previewOpen && filePreview?.kind === "error" && (
                <div className="file-preview-note">
                  Preview failed: {filePreview.message}
                </div>
              )}

              {previewOpen && filePreview?.kind === "text" && (
                <pre className="file-preview-code">
                  {filePreview.text}
                  {filePreview.lineCount > PREVIEW_LINES ? "\n…" : ""}
                </pre>
              )}

              {previewOpen && filePreview?.kind === "table" && (
                <div className="file-preview-table-wrap">
                  <div className="file-preview-note">
                    Sheet "{filePreview.sheetName}" · {filePreview.rowCount} rows
                    {filePreview.sheetCount > 1 ? ` · ${filePreview.sheetCount} sheets` : ""}
                  </div>
                  <table className="file-preview-table">
                    <tbody>
                      {filePreview.rows.map((row, r) => (
                        <tr key={r}>
                          {row.map((cell, c) => (
                            <td key={c}>{String(cell)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {previewOpen && filePreview?.kind === "none" && (
                <div className="file-preview-note">
                  No text preview for this file type. It will be read when you send.
                </div>
              )}
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
                  onChange={(event) => setAutoFallback(event.target.checked)}
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
              placeholder="Start coding with ZENEX..."
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

                <span className="composer-mode">{mode.toUpperCase()}</span>

                {showLanguagePicker && (
                  <>
                    <select
                      className="composer-select"
                      value={language}
                      onChange={(event) => {
                        setLanguage(event.target.value);
                        setFramework("None");
                      }}
                      title={mode === "convert" ? "Convert to" : "Language"}
                    >
                      {LANGUAGE_OPTIONS.map((item) => (
                        <option key={item} value={item}>
                          {mode === "convert" && item !== "Auto"
                            ? `To ${item}`
                            : item}
                        </option>
                      ))}
                    </select>

                    {FRAMEWORKS[language] && (
                      <select
                        className="composer-select"
                        value={framework}
                        onChange={(event) => setFramework(event.target.value)}
                        title="Framework"
                      >
                        {FRAMEWORKS[language].map((item) => (
                          <option key={item} value={item}>
                            {item}
                          </option>
                        ))}
                      </select>
                    )}
                  </>
                )}
              </div>

              <button
                className={`composer-send ${loading ? "stop-generation" : ""}`}
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

      {tourOpen && <OnboardingTour onClose={() => setTourOpen(false)} />}
    </div>
  );
}