import { cn } from "@heroui/react";
import { FieldTemplateProps } from "@rjsf/utils";

export default function FieldTemplate({
  schema,
  children,
  id,
  label,
}: FieldTemplateProps) {
  const isRoot = id === "root";

  return (
    <div
      className={cn("text-default-900 flex flex-col gap-1", isRoot && "gap-4")}
    >
      {!isRoot && label}
      {schema.description && (
        <div className="text-small text-default-500">{schema.description}</div>
      )}
      {children}
    </div>
  );
}
