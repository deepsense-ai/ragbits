import { Checkbox } from "@heroui/react";
import { WidgetProps } from "@rjsf/utils";

export default function CheckboxWidget({
  id,
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
  const hasError = (rawErrors ? rawErrors.length > 0 : false) && !hideError;

  return (
    <Checkbox
      type="checkbox"
      key={id}
      isSelected={value}
      required={required}
      disabled={disabled || readonly}
      onValueChange={(state) => onChange(state)}
      isRequired={required}
      isDisabled={disabled || readonly}
      isInvalid={hasError}
      onBlur={() => onBlur?.(id, value)}
      onFocus={() => onFocus?.(id, value)}
      className="mb-2"
      classNames={{
        label: "mt-0.5",
      }}
    >
      {label}
    </Checkbox>
  );
}
