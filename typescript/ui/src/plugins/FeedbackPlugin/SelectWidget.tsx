import { Select, SelectItem } from "@heroui/react";
import { WidgetProps } from "@rjsf/utils";

export default function SelectWidget({
  id,
  options,
  label,
  value,
  required,
  disabled,
  readonly,
  onChange,
  onBlur,
  onFocus,
  rawErrors,
  hideError,
}: WidgetProps) {
  const { enumOptions } = options;
  const hasError = (rawErrors ? rawErrors.length > 0 : false) && !hideError;

  if (!enumOptions) {
    return null;
  }

  return (
    <Select
      key={id}
      label={label}
      placeholder={`Select ${label.toLowerCase()}`}
      isRequired={required}
      isDisabled={disabled || readonly}
      errorMessage={rawErrors}
      isInvalid={hasError}
      onChange={(e) => onChange(e.target.value)}
      onBlur={() => onBlur?.(id, value)}
      onFocus={() => onFocus?.(id, value)}
      className="mb-2"
    >
      {enumOptions.map((option: { label: string; value: any }) => (
        <SelectItem key={option.label}>{option.label}</SelectItem>
      ))}
    </Select>
  );
}
