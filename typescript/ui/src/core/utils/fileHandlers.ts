export type FileDropHandler = (files: File[]) => void;

let handler: FileDropHandler | null = null;

export function registerFileDropHandler(h: FileDropHandler): () => void {
  handler = h;
  return () => {
    if (handler === h) handler = null;
  };
}

export function dispatchDroppedFiles(files: File[]): boolean {
  if (!handler || files.length === 0) return false;
  handler(files);
  return true;
}
