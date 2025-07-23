import { cn } from "@heroui/react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

type MarkdownContentProps = {
  content: string;
  classNames?: string;
};

const MarkdownContent = ({ content, classNames }: MarkdownContentProps) => {
  return (
    <Markdown
      className={cn(
        "markdown-container prose dark:prose-invert max-w-full text-neutral-950 dark:text-neutral-50",
        classNames,
      )}
      remarkPlugins={[remarkGfm]}
      components={{
        pre: ({ children }) => (
          <pre className="mt-2 mb-2 max-w-full overflow-auto rounded bg-neutral-200 p-2 font-mono font-normal text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200">
            {children}
          </pre>
        ),
        code: ({ children }) => (
          <code className="rounded bg-neutral-200 px-2 py-1 font-mono font-normal text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200">
            {children}
          </code>
        ),
      }}
    >
      {content}
    </Markdown>
  );
};

export default MarkdownContent;
