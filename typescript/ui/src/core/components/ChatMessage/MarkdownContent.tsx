import { cn } from "@heroui/react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Icon } from "@iconify/react";
import { useMemo } from "react";
import MermaidDiagram from "./MermaidDiagram";

type MarkdownContentProps = {
  content: string;
  classNames?: string;
  isStreaming?: boolean;
};

type ContentChunk = {
  type: "text" | "mermaid";
  content: string;
  key: string;
};

/**
 * Splits markdown content into text and mermaid diagram chunks
 * Handles incomplete mermaid blocks during streaming
 */
function parseContentChunks(content: string, isStreaming: boolean) {
  const result: ContentChunk[] = [];
  let remainingContent = content;
  let hasIncomplete = false;
  let chunkIndex = 0;

  // Check for incomplete mermaid block at the end during streaming
  if (isStreaming) {
    const lastMermaidStart = content.lastIndexOf("```mermaid");
    const codeBlockCount = (content.match(/```/g) || []).length;

    // If odd number of ``` and last one starts mermaid, it's incomplete
    if (codeBlockCount % 2 !== 0 && lastMermaidStart !== -1) {
      const afterLastMarker = content.substring(lastMermaidStart);
      if (afterLastMarker.startsWith("```mermaid")) {
        hasIncomplete = true;
        // Remove incomplete block from processing
        remainingContent = content.substring(0, lastMermaidStart);
      }
    }
  }

  // Split by mermaid blocks
  const mermaidRegex = /```mermaid\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = mermaidRegex.exec(remainingContent)) !== null) {
    // Add text chunk before this mermaid block
    if (match.index > lastIndex) {
      const textContent = remainingContent.substring(lastIndex, match.index);
      if (textContent.trim()) {
        result.push({
          type: "text",
          content: textContent,
          key: `text-${chunkIndex}`,
        });
        chunkIndex++;
      }
    }

    // Add mermaid chunk
    const mermaidContent = match[1];
    result.push({
      type: "mermaid",
      content: mermaidContent,
      key: `mermaid-${chunkIndex}`,
    });
    chunkIndex++;
    lastIndex = match.index + match[0].length;
  }

  // Add remaining text after last mermaid block
  if (lastIndex < remainingContent.length) {
    const textContent = remainingContent.substring(lastIndex);
    if (textContent.trim()) {
      result.push({
        type: "text",
        content: textContent,
        key: `text-${chunkIndex}`,
      });
    }
  }

  return { chunks: result, hasIncompleteMermaid: hasIncomplete };
}

const MarkdownContent = ({
  content,
  classNames,
  isStreaming = false,
}: MarkdownContentProps) => {
  // Split content into text and mermaid chunks
  const { chunks, hasIncompleteMermaid } = useMemo(
    () => parseContentChunks(content, isStreaming),
    [content, isStreaming],
  );

  return (
    <>
      {chunks.map((chunk) => {
        if (chunk.type === "mermaid") {
          return <MermaidDiagram key={chunk.key} chart={chunk.content} />;
        }

        return (
          <Markdown
            key={chunk.key}
            className={cn(
              "markdown-container prose dark:prose-invert text-default-900 max-w-full",
              classNames,
            )}
            remarkPlugins={[remarkGfm]}
            components={{
              pre: ({ children }) => (
                <pre className="bg-default text-default-900 mt-2 mb-2 max-w-full overflow-auto rounded p-2 font-mono text-[90%] font-normal">
                  {children}
                </pre>
              ),
              code: ({ children, ...props }) => (
                <code
                  className="bg-default text-default-900 rounded px-1 py-0.5 font-mono text-[85%] font-normal"
                  {...props}
                >
                  {children}
                </code>
              ),
            }}
          >
            {chunk.content}
          </Markdown>
        );
      })}
      {/* Show placeholder for streaming mermaid block */}
      {hasIncompleteMermaid && (
        <div
          className={cn(
            "bg-default rounded-medium border-default-200 mt-2 mb-2 border p-4",
            "relative overflow-hidden",
          )}
        >
          <div className="bg-default-200 relative flex h-32 items-center justify-center rounded">
            <div className="via-default-300/50 absolute inset-0 animate-[shimmer_2s_ease-in-out_infinite] bg-gradient-to-r from-transparent to-transparent" />
            <Icon
              icon="heroicons:chart-bar"
              className="text-default-400 h-12 w-12 animate-[pulse_2s_ease-in-out_infinite]"
            />
          </div>
        </div>
      )}
    </>
  );
};

export default MarkdownContent;
