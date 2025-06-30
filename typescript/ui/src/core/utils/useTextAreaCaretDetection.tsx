import { useCallback } from "react";

export function useCaretLogicalLineDetection() {
  const createMirrorDiv = (textarea: HTMLTextAreaElement): HTMLDivElement => {
    const style = window.getComputedStyle(textarea);
    const div = document.createElement("div");

    div.style.whiteSpace = "pre-wrap";
    div.style.wordWrap = "break-word";
    div.style.position = "absolute";
    div.style.visibility = "hidden";
    div.style.font = style.font;
    div.style.lineHeight = style.lineHeight;
    div.style.padding = style.padding;
    div.style.border = style.border;
    div.style.boxSizing = style.boxSizing;
    div.style.width = `${textarea.clientWidth}px`;

    return div;
  };

  const getCaretLineIndex = useCallback(
    (textarea: HTMLTextAreaElement): number => {
      const value = textarea.value.slice(0, textarea.selectionStart);
      const mirrorDiv = createMirrorDiv(textarea);
      const style = window.getComputedStyle(textarea);

      const span = document.createElement("span");
      span.textContent = "\u200b"; // Zero-width space

      mirrorDiv.textContent = value;
      mirrorDiv.appendChild(span);
      document.body.appendChild(mirrorDiv);

      const caretTop = span.offsetTop;
      const lineHeight = parseFloat(style.lineHeight || "16");
      const caretLineIndex = Math.round(caretTop / lineHeight);

      document.body.removeChild(mirrorDiv);
      return caretLineIndex;
    },
    [],
  );

  const getTotalLineCount = useCallback(
    (textarea: HTMLTextAreaElement): number => {
      const mirrorDiv = createMirrorDiv(textarea);
      const style = window.getComputedStyle(textarea);

      let text = textarea.value;
      if (text.endsWith("\n") || text === "") {
        text += "\u200b"; // zero-width space forces final line render
      }

      mirrorDiv.textContent = text;
      document.body.appendChild(mirrorDiv);
      const totalHeight = mirrorDiv.offsetHeight;
      const lineHeight = parseFloat(style.lineHeight || "16");
      const totalLines = Math.round(totalHeight / lineHeight);

      document.body.removeChild(mirrorDiv);
      return totalLines;
    },
    [],
  );

  const isCaretInFirstLine = useCallback(
    (textarea: HTMLTextAreaElement): boolean => {
      return getCaretLineIndex(textarea) === 0;
    },
    [getCaretLineIndex],
  );

  const isCaretInLastLine = useCallback(
    (textarea: HTMLTextAreaElement): boolean => {
      const caretLine = getCaretLineIndex(textarea);
      const totalLines = getTotalLineCount(textarea);
      return caretLine === totalLines - 1;
    },
    [getCaretLineIndex, getTotalLineCount],
  );

  return {
    isCaretInFirstLine,
    isCaretInLastLine,
  };
}
