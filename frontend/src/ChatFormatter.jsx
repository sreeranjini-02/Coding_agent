// ChatFormatter.jsx
import { useState } from "react";

const API_URL = "http://127.0.0.1:8000";

const TOKEN_RE =
  /(#.*$|\/\/.*$)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`[^`]*`)|\b(def|class|return|if|elif|else|for|while|in|import|from|as|try|except|finally|with|lambda|yield|and|or|not|is|True|False|None|const|let|var|function|new|async|await|export|default|struct|public|private|static|void|int|str)\b|\b(\d+(?:\.\d+)?)\b/gm;

// Maps a code block's language label to a file extension
const EXTENSIONS = {
  python: "py",
  py: "py",
  javascript: "js",
  js: "js",
  jsx: "jsx",
  typescript: "ts",
  ts: "ts",
  tsx: "tsx",
  java: "java",
  c: "c",
  cpp: "cpp",
  "c++": "cpp",
  csharp: "cs",
  cs: "cs",
  go: "go",
  rust: "rs",
  rs: "rs",
  html: "html",
  css: "css",
  json: "json",
  sql: "sql",
  bash: "sh",
  sh: "sh",
  shell: "sh",
  markdown: "md",
  md: "md",
  xml: "xml",
  yaml: "yaml",
  yml: "yml",
};

const getExtension = (language) =>
  EXTENSIONS[(language || "").toLowerCase()] || "txt";

function highlight(src) {
  const out = [];
  const re = new RegExp(TOKEN_RE.source, "gm");
  let last = 0;
  let key = 0;
  let m;
  while ((m = re.exec(src))) {
    if (m.index > last) out.push(src.slice(last, m.index));
    const [tok, comment, str, kw] = m;
    const color = comment ? "#6a9955" : str ? "#ce9178" : kw ? "#c586c0" : "#b5cea8";
    out.push(
      <span
        key={key++}
        style={{
          color,
          fontWeight: kw ? 700 : 400,
          fontStyle: comment ? "italic" : "normal",
        }}
      >
        {tok}
      </span>
    );
    last = m.index + tok.length;
  }
  out.push(src.slice(last));
  return out;
}

// Result line shown under a code block after "Check syntax"
function SyntaxResult({ result }) {
  if (!result) return null;

  if (result.status === "loading") {
    return <div style={{ ...styles.result, color: "#94a3b8" }}>Checking syntax...</div>;
  }

  if (result.status === "error") {
    return <div style={{ ...styles.result, color: "#f87171" }}>{result.text}</div>;
  }

  const color =
    result.valid === true ? "#4ade80" : result.valid === false ? "#f87171" : "#94a3b8";
  const icon = result.valid === true ? "✓" : result.valid === false ? "✗" : "ⓘ";

  return (
    <div style={{ ...styles.result, color }}>
      {icon} {result.line ? `Line ${result.line}: ` : ""}
      {result.message}
    </div>
  );
}

export function CodeBlock({ code, language = "text" }) {
  const [copied, setCopied] = useState(false);
  const [syntax, setSyntax] = useState(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
    } catch {
      // Fallback for browsers or contexts without the Clipboard API
      const area = document.createElement("textarea");
      area.value = code;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      document.body.removeChild(area);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `code-${Date.now()}.${getExtension(language)}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCheckSyntax = async () => {
    setSyntax({ status: "loading" });

    const token = localStorage.getItem("token") || localStorage.getItem("access_token");

    try {
      const response = await fetch(`${API_URL}/code/check-syntax`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ code, language }),
      });

      const data = await response.json();

      if (!response.ok) {
        setSyntax({
          status: "error",
          text: typeof data.detail === "string" ? data.detail : "Syntax check failed.",
        });
        return;
      }

      setSyntax({
        status: "done",
        valid: data.valid,
        line: data.line,
        message: data.message,
      });
    } catch {
      setSyntax({ status: "error", text: "Could not reach the backend." });
    }
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.header}>
        <span style={styles.lang}>{language}</span>
        <div style={styles.actions}>
          <button
            type="button"
            onClick={handleCheckSyntax}
            style={styles.button}
            disabled={syntax?.status === "loading"}
          >
            Check syntax
          </button>
          <button type="button" onClick={handleCopy} style={styles.button}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button type="button" onClick={handleDownload} style={styles.button}>
            Download
          </button>
        </div>
      </div>
      <pre style={styles.pre}>
        <code>{highlight(code)}</code>
      </pre>
      <SyntaxResult result={syntax} />
    </div>
  );
}

export function ComparisonBox({ title, rows }) {
  return (
    <div style={styles.box}>
      {title && <div style={styles.boxTitle}>{title}</div>}
      {rows.map((row, i) => (
        <div key={i} style={styles.row}>
          <span style={styles.label}>{row.label}</span>
          <span style={styles.value}>{row.value}</span>
        </div>
      ))}
    </div>
  );
}
// Guesses the language of a code block that has no label
export function detectLanguage(code) {
  const c = code || "";

  if (/^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE|ALTER TABLE)\b/im.test(c)) return "sql";
  if (/public\s+(static\s+)?(class|void|interface)|System\.out\.print/.test(c)) return "java";
  if (/^\s*<(!DOCTYPE|html|div|body|head)\b/im.test(c)) return "html";
  if (/^\s*(import\s+React|export\s+(default|const|function)|const\s+\w+\s*=|let\s+\w+|function\s+\w+\s*\(|console\.log)/m.test(c)) {
    return /:\s*(string|number|boolean)\b|interface\s+\w+/.test(c) ? "typescript" : "javascript";
  }
  if (/^\s*(def\s+\w+|class\s+\w+.*:\s*$|from\s+\w+\s+import|import\s+\w+\s*$|print\()/m.test(c)) return "python";
  if (/^\s*[.#]?[\w-]+\s*\{[^}]*:/m.test(c)) return "css";

  return "text";
}

// Splits text into prose and fenced code. Handles an unclosed fence while streaming.
function splitCode(content) {
  const segs = [];
  const re = /```([^\n`]*)\n([\s\S]*?)```/g;
  let last = 0;
  let m;
  while ((m = re.exec(content))) {
    if (m.index > last) segs.push({ type: "text", text: content.slice(last, m.index) });
    const code = m[2].replace(/\n$/, "");
    segs.push({
      type: "code",
      lang: m[1].trim() || detectLanguage(code),
      code,
    });
    last = m.index + m[0].length;
  }

  const rest = content.slice(last);
  const idx = rest.indexOf("```");
  if (idx >= 0) {
    if (idx > 0) segs.push({ type: "text", text: rest.slice(0, idx) });
    const after = rest.slice(idx + 3);
    const nl = after.indexOf("\n");
    const label = nl >= 0 ? after.slice(0, nl).trim() : after.trim();
    const code = nl >= 0 ? after.slice(nl + 1) : "";
    segs.push({ type: "code", lang: label || detectLanguage(code), code });
  } else if (rest) {
    segs.push({ type: "text", text: rest });
  }
  return segs;
}

// Returns only the code blocks of a reply: [{ lang, code }]
export function extractCodeBlocks(content) {
  return splitCode(content || "")
    .filter((seg) => seg.type === "code")
    .map((seg) => ({ lang: seg.lang, code: seg.code }));
}

// Matches markdown headings such as "## Title" or "# Title"
const HEADING_RE = /^\s*#{1,6}\s*(.+?)\s*$/;

// Groups "- Label: value" lines (2+ in a row) into boxes.
// Also turns markdown headings into plain bold lines.
function groupLines(text) {
  const lines = text.split("\n");
  const items = [];
  const kv = /^\s*[-•*]\s+([^:]{1,50}?):\s*(.{1,60}?)\s*$/;

  for (let i = 0; i < lines.length; ) {
    const heading = lines[i].match(HEADING_RE);

    if (heading) {
      items.push({ type: "heading", value: heading[1] });
      i++;
      continue;
    }

    if (kv.test(lines[i])) {
      const rows = [];
      while (i < lines.length && kv.test(lines[i])) {
        const m = lines[i].match(kv);
        rows.push({ label: m[1], value: m[2] });
        i++;
      }
      if (rows.length >= 2) {
        // Use a short plain line just above the box as its title
        let j = items.length - 1;
        while (j >= 0 && items[j].type === "line" && !items[j].value.trim()) j--;
        let title = null;
        if (j >= 0 && items[j].type === "line") {
          const candidate = items[j].value.trim();
          if (candidate && candidate.length < 60 && !candidate.includes(":") && !candidate.startsWith("-")) {
            title = candidate;
            items.splice(j);
          }
        }
        items.push({ type: "box", title, rows });
      } else {
        rows.forEach((r) => items.push({ type: "line", value: `- ${r.label}: ${r.value}` }));
      }
    } else {
      items.push({ type: "line", value: lines[i] });
      i++;
    }
  }
  return items;
}

function renderInline(text) {
  return text
    .replace(/\s*#+\s*$/, "")
    .split(/(\*\*[^*]+\*\*)/g)
    .map((part, i) =>
      part.length > 4 && part.startsWith("**") && part.endsWith("**") ? (
        <strong key={i}>{part.slice(2, -2)}</strong>
      ) : (
        part
      )
    );
}

function TextBlock({ text }) {
  return groupLines(text).map((item, i) => {
    if (item.type === "box") {
      return <ComparisonBox key={i} title={item.title} rows={item.rows} />;
    }
    if (item.type === "heading") {
      return (
        <div key={i} style={styles.heading}>
          {renderInline(item.value)}
        </div>
      );
    }
    if (!item.value.trim()) {
      return <div key={i} style={{ height: 10 }} />;
    }
    return (
      <div key={i} style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
        {renderInline(item.value)}
      </div>
    );
  });
}

export function FormattedMessage({ content }) {
  return splitCode(content).map((seg, i) =>
    seg.type === "code" ? (
      <CodeBlock key={i} code={seg.code} language={seg.lang} />
    ) : (
      <TextBlock key={i} text={seg.text} />
    )
  );
}

const styles = {
  wrapper: {
    margin: "12px 0",
    borderRadius: 10,
    overflow: "hidden",
    background: "#1e1e1e",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "6px 10px",
    background: "#2a2a2a",
    borderBottom: "1px solid #333",
  },
  lang: {
    fontSize: 11,
    color: "#aaa",
    textTransform: "uppercase",
  },
  actions: {
    display: "flex",
    gap: 6,
  },
  button: {
    padding: "3px 10px",
    fontSize: 12,
    color: "#d4d4d4",
    background: "transparent",
    border: "1px solid #444",
    borderRadius: 6,
    cursor: "pointer",
  },
  pre: {
    background: "#1e1e1e",
    color: "#d4d4d4",
    padding: 16,
    overflowX: "auto",
    fontSize: 13,
    lineHeight: 1.5,
    fontFamily: "Consolas, 'Courier New', monospace",
    margin: 0,
  },
  result: {
    padding: "6px 12px",
    fontSize: 12,
    background: "#252526",
    borderTop: "1px solid #333",
  },
  heading: {
    fontWeight: 700,
    fontSize: 16,
    margin: "14px 0 6px",
    color: "#142544",
  },
  box: {
    border: "1px solid #c7d7f5",
    borderRadius: 10,
    background: "#f5f9ff",
    padding: "14px 18px",
    margin: "12px 0",
    maxWidth: 440,
    fontSize: 14,
  },
  boxTitle: { fontWeight: 600, marginBottom: 8, color: "#1d4ed8" },
  row: {
    display: "flex",
    justifyContent: "space-between",
    gap: 16,
    padding: "4px 0",
    borderBottom: "1px dashed #d6e2f7",
  },
  label: { color: "#374151" },
  value: { fontWeight: 600, color: "#111827" },
};