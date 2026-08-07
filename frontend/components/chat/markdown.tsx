"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { visit } from "unist-util-visit";
import type { Plugin } from "unified";
import type { Root } from "mdast";

const remarkCitations: Plugin<[], Root> = () => {
  return (tree) => {
    visit(tree, "text", (node: { type: string; value: string }, index: number | undefined, parent: any) => {
      if (parent === null || parent === undefined || index === undefined) return;
      const regex = /\[(\d+)\]/g;
      const matches = [...node.value.matchAll(regex)];
      if (!matches.length) return;
      const parts: any[] = [];
      let lastIndex = 0;
      for (const match of matches) {
        if (match.index !== undefined && match.index > lastIndex) {
          parts.push({ type: "text", value: node.value.slice(lastIndex, match.index) });
        }
        parts.push({
          type: "link",
          url: `#source-${match[1]}`,
          children: [{ type: "text", value: match[0] }],
        });
        lastIndex = (match.index ?? 0) + match[0].length;
      }
      if (lastIndex < node.value.length) {
        parts.push({ type: "text", value: node.value.slice(lastIndex) });
      }
      parent.children.splice(index, 1, ...parts);
    });
  };
};

interface MarkdownProps {
  content: string;
}

export function Markdown({ content }: MarkdownProps) {
  const handleClick = React.useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    const anchor = (event.target as HTMLElement).closest('a[href^="#source-"]') as HTMLAnchorElement | null;
    if (!anchor) return;
    event.preventDefault();
    const id = anchor.getAttribute("href")?.replace("#", "");
    const el = document.getElementById(id ?? "");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("ring-2", "ring-primary", "ring-offset-2");
      setTimeout(() => el.classList.remove("ring-2", "ring-primary", "ring-offset-2"), 1800);
    }
  }, []);

  return (
    <div className="markdown-body" onClick={handleClick}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkCitations]}
        rehypePlugins={[rehypeSanitize]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
