import { useEffect, useRef, useState, memo } from "react";
import mermaid from "mermaid";
import { cn } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useThemeContext } from "../../contexts/ThemeContext/useThemeContext";
import { Theme } from "../../contexts/ThemeContext/ThemeContext";

type MermaidDiagramProps = {
  chart: string;
  classNames?: string;
};

const MermaidDiagram = memo(({ chart, classNames }: MermaidDiagramProps) => {
  const { theme } = useThemeContext();
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const elementRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(
    `mermaid-${Math.random().toString(36).substring(2, 11)}`,
  );

  const handleDownload = () => {
    if (!svg) return;

    // Create a blob from the SVG string
    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);

    // Create a temporary anchor element and trigger download
    const link = document.createElement("a");
    link.href = url;
    link.download = `mermaid-diagram-${Date.now()}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    const renderDiagram = async () => {
      setIsLoading(true);
      setError(null);
      setSvg("");

      try {
        // Initialize mermaid with theme and settings
        mermaid.initialize({
          startOnLoad: false,
          theme: theme === Theme.DARK ? "dark" : "default",
          securityLevel: "strict",
          fontFamily: "arial, sans-serif",
        });

        // Render the diagram
        const { svg: renderedSvg } = await mermaid.render(idRef.current, chart);

        setSvg(renderedSvg);
        setIsLoading(false);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to render diagram",
        );
        setIsLoading(false);
      }
    };

    renderDiagram();
  }, [chart, theme]);

  if (error) {
    return (
      <div
        className={cn(
          "bg-danger-50 dark:bg-danger-100 border-danger-200 dark:border-danger-300 text-danger-700 dark:text-danger-800 rounded-medium mt-2 mb-2 border p-3",
          classNames,
        )}
      >
        <div className="flex items-center gap-2">
          <Icon
            icon="heroicons:exclamation-triangle"
            className="h-5 w-5 flex-shrink-0"
          />
          <span className="font-semibold">Mermaid Syntax Error</span>
        </div>
        <pre className="mt-2 overflow-auto text-sm whitespace-pre-wrap">
          {error}
        </pre>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        className={cn(
          "bg-default rounded-medium border-default-200 mt-2 mb-2 border p-4",
          "relative overflow-hidden",
          classNames,
        )}
      >
        <div className="bg-default-200 relative flex h-32 items-center justify-center rounded">
          {/* Animated shimmer effect */}
          <div className="via-default-300/50 absolute inset-0 -translate-x-full animate-[shimmer_2s_ease-in-out_infinite] bg-gradient-to-r from-transparent to-transparent" />
          {/* Pulsing icon */}
          <Icon
            icon="heroicons:chart-bar"
            className="text-default-400 h-12 w-12 animate-[pulse_2s_ease-in-out_infinite]"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <div
        ref={elementRef}
        className={cn(
          "mermaid-container bg-default rounded-medium border-default-200 mt-2 mb-2 border p-6",
          "overflow-x-auto overflow-y-visible",
          "animate-[fadeIn_0.5s_ease-in]",
          classNames,
        )}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
      {/* Download button */}
      <button
        onClick={handleDownload}
        className={cn(
          "absolute top-4 right-4",
          "bg-default-100 hover:bg-default-200 dark:bg-default-200 dark:hover:bg-default-300",
          "text-default-700 dark:text-default-800",
          "rounded-medium p-2",
          "transition-colors duration-200",
          "flex items-center justify-center",
          "border-default-300 border",
        )}
        aria-label="Download diagram"
        title="Download as SVG"
      >
        <Icon icon="heroicons:arrow-down-tray" className="h-5 w-5" />
      </button>
    </div>
  );
});

MermaidDiagram.displayName = "MermaidDiagram";

export default MermaidDiagram;
