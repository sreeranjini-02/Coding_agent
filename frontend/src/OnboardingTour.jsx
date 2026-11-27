import { useEffect, useState } from "react";

export const TOUR_KEY = "zenex_tour_done";

const STEPS = [
  {
    target: ".sidebar-tools",
    title: "Coding tools",
    text: "Pick a tool here. Generate writes code, Debug fixes errors, Explain describes code, Review checks quality, Optimize shortens code, Tests writes test cases, and Convert translates code to another language.",
  },
  {
    target: ".sidebar-section-toggle",
    title: "Chat history",
    text: "Each tool keeps its own chats. Click CHAT HISTORY to open the list. Use × next to a chat to delete it.",
  },
  {
    target: ".chat-composer textarea",
    title: "Ask here",
    text: "Type your request and press Enter. Use Shift+Enter for a new line. Put code inside triple backticks so it is treated as code.",
  },
  {
    target: "button[title='Attach file']",
    title: "Attach a file",
    text: "Attach a text, PDF, Word, or Excel file. A preview appears before you send it.",
  },
  {
    target: ".composer-select",
    title: "Language and framework",
    text: "In Generate and Convert, choose the language and framework. Auto lets the model decide.",
  },
  {
    target: ".header-model",
    title: "Choose a model",
    text: "Pick a Gemini model. Turn on Auto fallback in the ⚙ menu, so another model answers if one is busy.",
  },
  {
    target: ".header-theme",
    title: "Light or dark",
    text: "Switch between light and dark mode here. Your choice is remembered.",
  },
];

export default function OnboardingTour({ onClose }) {
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState(null);

  const step = STEPS[index];
  const isLast = index === STEPS.length - 1;

  const finish = () => {
    localStorage.setItem(TOUR_KEY, "1");
    onClose();
  };

  // Find the element for the current step and measure it
  useEffect(() => {
    const measure = () => {
      const element = document.querySelector(step.target);

      if (!element) {
        setRect(null);
        return;
      }

      element.scrollIntoView({ block: "nearest", inline: "nearest" });
      const box = element.getBoundingClientRect();

      setRect({
        top: box.top - 6,
        left: box.left - 6,
        width: box.width + 12,
        height: box.height + 12,
      });
    };

    measure();
    window.addEventListener("resize", measure);

    return () => window.removeEventListener("resize", measure);
  }, [step]);

  // Keyboard: Escape closes, arrow keys move between steps
  useEffect(() => {
    const handleKey = (event) => {
      if (event.key === "Escape") finish();
      if (event.key === "ArrowRight" && !isLast) setIndex(index + 1);
      if (event.key === "ArrowLeft" && index > 0) setIndex(index - 1);
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, isLast]);

  return (
    <>
      {rect ? (
        <div className="tour-highlight" style={rect} />
      ) : (
        <div className="tour-backdrop" />
      )}

      <div className="tour-card" role="dialog" aria-label="Welcome tour">
        <div className="tour-progress">
          Step {index + 1} of {STEPS.length}
        </div>

        <h3 className="tour-title">{step.title}</h3>
        <p className="tour-text">{step.text}</p>

        <div className="tour-actions">
          <button className="tour-skip" onClick={finish}>
            Skip
          </button>

          <div className="tour-nav">
            <button
              className="tour-btn"
              onClick={() => setIndex(index - 1)}
              disabled={index === 0}
            >
              Back
            </button>

            {isLast ? (
              <button className="tour-btn primary" onClick={finish}>
                Finish
              </button>
            ) : (
              <button
                className="tour-btn primary"
                onClick={() => setIndex(index + 1)}
              >
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}