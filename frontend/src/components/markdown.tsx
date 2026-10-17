import { Fragment } from "react";

import { type Inline, parseMarkdown } from "@/lib/markdown";

const INDENT = ["pl-0", "pl-5", "pl-10", "pl-14"];

function Inlines({ items }: { items: Inline[] }) {
  return items.map((item, index) => {
    if (item.kind === "bold") return <strong key={index}>{item.text}</strong>;
    if (item.kind === "code") {
      return (
        <code key={index} className="rounded bg-black/10 px-1 font-mono text-[0.9em] dark:bg-white/15">
          {item.text}
        </code>
      );
    }
    return <Fragment key={index}>{item.text}</Fragment>;
  });
}

/** Mercek cevabını biçimli gösterir; HTML çalıştırmaz, metin React ile çizilir. */
export function Markdown({ text }: { text: string }) {
  return (
    <div className="space-y-2">
      {parseMarkdown(text).map((block, index) => {
        if (block.kind === "heading") {
          return (
            <p key={index} className="pt-1 font-semibold">
              <Inlines items={block.inlines} />
            </p>
          );
        }
        if (block.kind === "paragraph") {
          return (
            <p key={index}>
              {block.lines.map((line, lineIndex) => (
                <Fragment key={lineIndex}>
                  {lineIndex > 0 && <br />}
                  <Inlines items={line} />
                </Fragment>
              ))}
            </p>
          );
        }
        return (
          <div key={index} className={`flex gap-2 ${INDENT[block.level]} !mt-1`}>
            <span className={block.ordered ? "min-w-5 tabular-nums" : "min-w-3"} aria-hidden>
              {block.marker}
            </span>
            <span>
              {block.lines.map((line, lineIndex) => (
                <Fragment key={lineIndex}>
                  {lineIndex > 0 && <br />}
                  <Inlines items={line} />
                </Fragment>
              ))}
            </span>
          </div>
        );
      })}
    </div>
  );
}
