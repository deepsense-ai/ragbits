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
        "markdown-container prose max-w-full dark:prose-invert",
        classNames,
      )}
      remarkPlugins={[remarkGfm]}
      components={{
        pre: ({ children }) => (
          <pre className="max-w-full overflow-auto rounded bg-gray-200 p-2 font-mono font-normal text-gray-800 dark:bg-gray-800 dark:text-gray-200">
            {children}
          </pre>
        ),
        code: ({ children }) => (
          <code className="rounded bg-gray-200 px-2 py-1 font-mono font-normal text-gray-800 dark:bg-gray-800 dark:text-gray-200">
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
