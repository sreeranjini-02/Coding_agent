// DiffView.jsx
import { useEffect, useMemo, useRef } from "react";

// Above this size the line matching becomes slow, so the code is shown without highlights
const MAX_HIGHLIGHT_LINES = 800;

// Marks each line that is not part of the longest common sequence of lines.
// Returns an array of booleans: true means the line changed.
function markChangedLines(lines, otherLines) {
  const n = lines.length;
  const m = otherLines.length;

  const dp = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));

  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] =
        lines[i] === otherLines[j]
          ? dp[i + 1][j + 1] + 1
          : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const changed = new Array(n).fill(true);
  let i = 0;
  let j = 0;

  while (i < n && j < m) {
    if (lines[i] === otherLines[j]) {
      changed[i] = false;
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      i++;
    } else {
      j++;
    }
  }

  return changed;
}

const normalize = (text) =>
  text.replace(/\r\n/g, "\n").split("\n").map((line) => line.trimEnd());

export default function DiffView({ original, optimized }) {
  const wrapperRef = useRef(null);

  const result = useMemo(() => {
    const a = normalize(original);
    const b = normalize(optimized);

    if (a.length > MAX_HIGHLIGHT_LINES || b.length > MAX_HIGHLIGHT_LINES) {
      return { a, b, changedA: null, changedB: null };
    }

    return {
      a,
      b,
      changedA: markChangedLines(a, b),
      changedB: markChangedLines(b, a),
    };
  }, [original, optimized]);

  // When the comparison opens, scroll the chat so it sits at the bottom of the screen
  useEffect(() => {
    wrapperRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, []);

  if (!original) {
    return (
      <div style={styles.notice}>
        The original code was not found in your message. Paste the code
        in your request (inside a code block) to compare. Code uploaded as
        a file can't be compared yet.
      </div>
    );
  }

  const { a, b, changedA, changedB } = result;
  const removedCount = changedA ? changedA.filter(Boolean).length : null;
  const addedCount = changedB ? changedB.filter(Boolean).length : null;

  return (
    <div ref={wrapperRef} style={styles.wrapper}>
      <div style={styles.summary}>
        <span>Original: {a.length} lines</span>
        <span>Optimized: {b.length} lines</span>
        {removedCount !== null && (
          <span style={{ color: "#f87171" }}>{removedCount} removed</span>
        )}
        {addedCount !== null && (
          <span style={{ color: "#4ade80" }}>{addedCount} added</span>
        )}
      </div>

      <div style={styles.columns}>
        <CodeColumn
          title="Original"
          lines={a}
          changed={changedA}
          changedColor="rgba(248, 113, 113, 0.22)"
        />
        <CodeColumn
          title="Optimized"
          lines={b}
          changed={changedB}
          changedColor="rgba(74, 222, 128, 0.2)"
        />
      </div>
    </div>
  );
}

function CodeColumn({ title, lines, changed, changedColor }) {
  return (
    <div style={styles.column}>
      <div style={styles.columnTitle}>{title}</div>
      <div style={styles.code}>
        {lines.map((line, i) => (
          <div
            key={i}
            style={{
              ...styles.line,
              background: changed && changed[i] ? changedColor : "transparent",
            }}
          >
            {line || " "}
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    margin: "10px 0",
    borderRadius: 10,
    overflow: "hidden",
    border: "1px solid #243654",
    background: "#1e1e1e",
  },
  summary: {
    display: "flex",
    flexWrap: "wrap",
    gap: 16,
    padding: "6px 12px",
    fontSize: 12,
    color: "#ddd",
    background: "#2a2a2a",
    borderBottom: "1px solid #333",
  },
  columns: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 1,
    background: "#333",
  },
  column: {
    minWidth: 0,
    background: "#1e1e1e",
  },
  columnTitle: {
    padding: "6px 12px",
    fontSize: 11,
    color: "#aaa",
    textTransform: "uppercase",
    background: "#2a2a2a",
    borderBottom: "1px solid #333",
  },
  code: {
    padding: "8px 0",
    fontFamily: "Consolas, 'Courier New', monospace",
    fontSize: 12,
    color: "#d4d4d4",
  },
  line: {
    padding: "0 12px",
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    overflowWrap: "anywhere",
  },
  notice: {
    margin: "10px 0",
    padding: "10px 12px",
    borderRadius: 8,
    fontSize: 13,
    background: "#fff4e5",
    border: "1px solid #f5c26b",
    color: "#7a4a00",
  },
};