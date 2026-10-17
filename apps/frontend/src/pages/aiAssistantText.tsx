import { Fragment, type ReactNode } from "react";

// Shows the light formatting chat models use (**bold**, "- " bullets, "1." lists,
// "#" headings) as real formatting. Everything is rendered as React text, never as HTML.

function inline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter((part) => part !== "");
  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`;
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

export function AiAssistantText({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let list: { ordered: boolean; items: ReactNode[] } | null = null;

  const flush = () => {
    if (!list) return;
    const key = `list-${blocks.length}`;
    blocks.push(list.ordered ? <ol key={key}>{list.items}</ol> : <ul key={key}>{list.items}</ul>);
    list = null;
  };

  text.split(/\r?\n/).forEach((raw, lineIndex) => {
    const line = raw.trimEnd();
    const bullet = /^\s*[-*•]\s+(.*)$/.exec(line);
    const numbered = /^\s*\d+[.)]\s+(.*)$/.exec(line);
    const heading = /^\s*#{1,6}\s+(.*)$/.exec(line);
    if (bullet || numbered) {
      const ordered = Boolean(numbered);
      if (!list || list.ordered !== ordered) {
        flush();
        list = { ordered, items: [] };
      }
      const content = (bullet ?? numbered)![1];
      list.items.push(<li key={`li-${lineIndex}`}>{inline(content, `li-${lineIndex}`)}</li>);
      return;
    }
    flush();
    if (!line.trim()) return;
    if (heading) {
      blocks.push(<p key={`h-${lineIndex}`} className="ai-assistant-heading"><strong>{inline(heading[1].replaceAll("**", ""), `h-${lineIndex}`)}</strong></p>);
      return;
    }
    blocks.push(<p key={`p-${lineIndex}`}>{inline(line, `p-${lineIndex}`)}</p>);
  });
  flush();
  return <>{blocks}</>;
}
