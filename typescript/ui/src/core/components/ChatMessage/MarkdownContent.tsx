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
        code: ({ children }) => (
          <code className="bg-default text-default-900 rounded px-1 py-0.5 font-mono text-[85%] font-normal">
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
