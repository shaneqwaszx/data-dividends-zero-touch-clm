import { Fragment, type ReactNode } from "react";

import { findCaseSection } from "./caseSections";

// Shows the light formatting chat models use (**bold**, "- " bullets, "1." lists,
// "#" headings) as real formatting. Everything is rendered as React text, never as HTML.

type OnSection = ((title: string) => void) | undefined;

function inline(text: string, keyPrefix: string, onSection?: OnSection): ReactNode[] {
  const parts = text
    .split(/(\*\*[^*]+\*\*|`[^`]+`|\(section: [^)\n]{2,60}\))/g)
    .filter((part) => part !== "");
  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`;
    const section = /^\(section: ([^)]+)\)$/.exec(part);
    if (section) {
      const title = section[1].trim();
      // A link only when that section is on the page the RM is looking at.
      if (onSection && findCaseSection(title)) {
        return (
          <Fragment key={key}>
            (section:{" "}
            <button
              type="button"
              className="ai-assistant-section-link"
              aria-label={`Go to ${title} on the case page`}
              onClick={() => onSection(title)}
            >
              {title} ↓
            </button>
            {")"}
          </Fragment>
        );
      }
      return <Fragment key={key}>{part}</Fragment>;
    }
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return <code key={key}>{part.slice(1, -1)}</code>;
    }
    // Leftover single *emphasis* markers are dropped rather than shown.
    return <Fragment key={key}>{part.replace(/(^|\s)\*(\S[^*]*\S|\S)\*(?=\s|$|[.,;:!?])/g, "$1$2")}</Fragment>;
  });
}

export function AiAssistantText({ text, onSection }: { text: string; onSection?: (title: string) => void }) {
  const blocks: ReactNode[] = [];
  // An open list: its items (each item may have continuation paragraphs) and the number it
  // starts at, so a list split by an explanation keeps counting (1, 2) instead of 1, 1.
  let list: { ordered: boolean; start: number; items: ReactNode[][] } | null = null;

  const flush = () => {
    if (!list) return;
    const key = `list-${blocks.length}`;
    const items = list.items.map((parts, index) => <li key={`${key}-${index}`}>{parts}</li>);
    blocks.push(
      list.ordered
        ? <ol key={key} start={list.start === 1 ? undefined : list.start}>{items}</ol>
        : <ul key={key}>{items}</ul>,
    );
    list = null;
  };

  const lines = text.split(/\r?\n/);
  lines.forEach((raw, lineIndex) => {
    const line = raw.trimEnd();
    const bullet = /^\s*[-*•]\s+(.*)$/.exec(line);
    const numbered = /^\s*(\d+)[.)]\s+(.*)$/.exec(line);
    const heading = /^\s*#{1,6}\s+(.*)$/.exec(line);
    if (bullet || numbered) {
      const ordered = Boolean(numbered);
      if (!list || list.ordered !== ordered) {
        flush();
        list = { ordered, start: numbered ? Number(numbered[1]) : 1, items: [] };
      }
      const content = bullet ? bullet[1] : numbered![2];
      list.items.push([<Fragment key={`li-${lineIndex}`}>{inline(content, `li-${lineIndex}`, onSection)}</Fragment>]);
      return;
    }
    if (!line.trim()) {
      // A blank line ends a list only if the next text is not part of it.
      const next = lines.slice(lineIndex + 1).find((later) => later.trim());
      if (list && next !== undefined && (/^\s+\S/.test(next) || /^\s*(?:\d+[.)]|[-*•])\s+/.test(next))) return;
      flush();
      return;
    }
    if (list && /^\s+\S/.test(line) && !heading) {
      // An indented line explains the item above it.
      list.items[list.items.length - 1].push(
        <p key={`lp-${lineIndex}`} className="ai-assistant-item-detail">{inline(line.trim(), `lp-${lineIndex}`, onSection)}</p>,
      );
      return;
    }
    flush();
    if (heading) {
      blocks.push(<p key={`h-${lineIndex}`} className="ai-assistant-heading"><strong>{inline(heading[1].replaceAll("**", ""), `h-${lineIndex}`, onSection)}</strong></p>);
      return;
    }
    blocks.push(<p key={`p-${lineIndex}`}>{inline(line, `p-${lineIndex}`, onSection)}</p>);
  });
  flush();
  return <>{blocks}</>;
}
