/**
 * Mercek cevapları için küçük Markdown ayrıştırıcı.
 * Desteklenen: başlık (#…), madde (- / *), numaralı liste (1.), girinti, paragraf,
 * satır içi **kalın** ve `kod`. HTML üretmez; çıktı React ile güvenle çizilir.
 */

export type Inline = { kind: "text" | "bold" | "code"; text: string };

export type Block =
  | { kind: "heading"; inlines: Inline[] }
  | { kind: "paragraph"; lines: Inline[][] }
  | { kind: "item"; marker: string; ordered: boolean; level: number; lines: Inline[][] };

const HEADING = /^#{1,6}\s+(.*)$/;
const BULLET = /^(\s*)[-*•]\s+(.*)$/;
const ORDERED = /^(\s*)(\d+)[.)]\s+(.*)$/;
const INLINE = /(\*\*[^*]+\*\*|`[^`]+`)/g;

export function parseInline(text: string): Inline[] {
  return text
    .split(INLINE)
    .filter((part) => part !== "")
    .map((part) => {
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        return { kind: "bold", text: part.slice(2, -2) };
      }
      if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
        return { kind: "code", text: part.slice(1, -1) };
      }
      return { kind: "text", text: part };
    });
}

function indentLevel(spaces: string): number {
  return Math.min(Math.floor(spaces.replace(/\t/g, "  ").length / 2), 3);
}

export function parseMarkdown(source: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: Inline[][] = [];

  const flush = () => {
    if (paragraph.length) blocks.push({ kind: "paragraph", lines: paragraph });
    paragraph = [];
  };

  for (const raw of source.replace(/\r\n/g, "\n").split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flush();
      continue;
    }
    const heading = line.match(HEADING);
    const bullet = line.match(BULLET);
    const ordered = line.match(ORDERED);
    if (heading) {
      flush();
      blocks.push({ kind: "heading", inlines: parseInline(heading[1]) });
    } else if (bullet) {
      flush();
      blocks.push({
        kind: "item",
        marker: "•",
        ordered: false,
        level: indentLevel(bullet[1]),
        lines: [parseInline(bullet[2])],
      });
    } else if (ordered) {
      flush();
      blocks.push({
        kind: "item",
        marker: `${ordered[2]}.`,
        ordered: true,
        level: indentLevel(ordered[1]),
        lines: [parseInline(ordered[3])],
      });
    } else if (/^\s/.test(line) && !paragraph.length && blocks.at(-1)?.kind === "item") {
      // Liste maddesinin altındaki girintili açıklama satırı maddeye eklenir.
      const item = blocks.at(-1) as Extract<Block, { kind: "item" }>;
      item.lines.push(parseInline(line.trim()));
    } else {
      paragraph.push(parseInline(line.trim()));
    }
  }
  flush();
  return blocks;
}
