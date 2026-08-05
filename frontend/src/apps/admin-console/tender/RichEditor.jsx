import { useEffect, useRef } from "react";
import DOMPurify from "dompurify";

/**
 * RichEditor — lightweight contenteditable rich text editor with
 * DOMPurify sanitisation on both ingest and emit so any pasted HTML,
 * seed text or persisted body is stripped of <script>, event handlers,
 * <iframe>, javascript: URIs, etc.
 *
 * Persists HTML strings so the body field is back-compat with the
 * existing plain-text templates (they render as-is inside the editor).
 * Toolbar: Bold, Italic, Underline, H2, H3, Bulleted list, Numbered list,
 * Quote, Clear formatting, Undo, Redo.
 */
const SANITIZE_CFG = {
  ALLOWED_TAGS: ["p", "br", "b", "strong", "i", "em", "u", "h2", "h3", "ul", "ol", "li",
                 "blockquote", "code", "pre", "span", "div", "a"],
  ALLOWED_ATTR: ["href", "target", "rel"],
  ALLOW_DATA_ATTR: false,
};
const cleanHtml = (html) => DOMPurify.sanitize(html || "", SANITIZE_CFG);
const BTN = "px-2 py-1 text-xs border border-brand-navy/20 bg-white text-brand-navy hover:bg-brand-navy/5 focus:outline-none";

function ToolbarButton({ label, onClick, testid, title }) {
  return (
    <button type="button" title={title || label}
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      data-testid={testid}
      className={BTN}>
      {label}
    </button>
  );
}

export default function RichEditor({ value, onChange, testid, placeholder }) {
  const ref = useRef(null);

  // Sync external value into the editor when it changes from outside (e.g.,
  // switching between drafts). We compare against innerHTML so we don't
  // wipe the caret on every keystroke. `next` is DOMPurify-sanitised (see
  // cleanHtml above), so this innerHTML assignment is XSS-safe.
  useEffect(() => {
    if (!ref.current) return;
    const next = cleanHtml(value);  // DOMPurify.sanitize — safe for innerHTML
    if (next !== ref.current.innerHTML) {
      ref.current.innerHTML = next;   // safe: `next` is DOMPurify-sanitised above
    }
  }, [value]);

  const emit = () => {
    if (ref.current) onChange(cleanHtml(ref.current.innerHTML));
  };

  const cmd = (name, arg = null) => {
    document.execCommand(name, false, arg);
    emit();
  };

  const onInput = () => emit();

  // Force paste to be plain text — blocks pasted <script>/<iframe> that would
  // slip past execCommand-produced markup.
  const onPaste = (e) => {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData("text/plain");
    document.execCommand("insertText", false, text);
  };

  return (
    <div className="mt-3 border border-current/20 bg-white" data-testid={`${testid}-wrap`}>
      <div className="flex flex-wrap gap-1 border-b border-current/10 p-1.5 bg-brand-pale/40">
        <ToolbarButton label="B" title="Bold" onClick={() => cmd("bold")} testid={`${testid}-bold`} />
        <ToolbarButton label={<i>I</i>} title="Italic" onClick={() => cmd("italic")} testid={`${testid}-italic`} />
        <ToolbarButton label={<u>U</u>} title="Underline" onClick={() => cmd("underline")} testid={`${testid}-underline`} />
        <span className="w-px bg-brand-navy/20 mx-1" />
        <ToolbarButton label="H2" onClick={() => cmd("formatBlock", "H2")} testid={`${testid}-h2`} />
        <ToolbarButton label="H3" onClick={() => cmd("formatBlock", "H3")} testid={`${testid}-h3`} />
        <ToolbarButton label="P"  onClick={() => cmd("formatBlock", "P")} testid={`${testid}-p`} />
        <span className="w-px bg-brand-navy/20 mx-1" />
        <ToolbarButton label="• List" onClick={() => cmd("insertUnorderedList")} testid={`${testid}-ul`} />
        <ToolbarButton label="1. List" onClick={() => cmd("insertOrderedList")} testid={`${testid}-ol`} />
        <ToolbarButton label="❝" title="Quote" onClick={() => cmd("formatBlock", "BLOCKQUOTE")} testid={`${testid}-quote`} />
        <span className="w-px bg-brand-navy/20 mx-1" />
        <ToolbarButton label="⟲" title="Undo" onClick={() => cmd("undo")} testid={`${testid}-undo`} />
        <ToolbarButton label="⟳" title="Redo" onClick={() => cmd("redo")} testid={`${testid}-redo`} />
        <ToolbarButton label="✕ Clear" title="Clear formatting" onClick={() => cmd("removeFormat")} testid={`${testid}-clear`} />
      </div>
      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        onInput={onInput}
        onPaste={onPaste}
        data-testid={testid}
        data-placeholder={placeholder || ""}
        className="rich-editor min-h-[180px] px-3 py-2 outline-none text-brand-navy text-sm leading-relaxed prose max-w-none"
      />
    </div>
  );
}
