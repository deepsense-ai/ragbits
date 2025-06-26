import { ChangeEvent, FocusEvent } from "react";
import { Input } from "@heroui/react";
import { BaseInputTemplateProps, getInputProps } from "@rjsf/utils";
import { omit } from "lodash";

export default function FormInput({
  schema,
  id,
  options,
  label,
  value,
  type,
  placeholder,
  required,
  disabled,
  readonly,
  autofocus,
  onChange,
  onChangeOverride,
  onBlur,
  onFocus,
  rawErrors,
  hideError,
  ...rest
}: BaseInputTemplateProps) {
  const onTextChange = ({
    target: { value: val },
  }: ChangeEvent<HTMLInputElement>) => {
    onChange(val === "" ? options.emptyValue || "" : val);
  };
  const onTextBlur = ({
    target: { value: val },
  }: FocusEvent<HTMLInputElement>) => onBlur(id, val);
  const onTextFocus = ({
    target: { value: val },
  }: FocusEvent<HTMLInputElement>) => onFocus(id, val);

  const inputProps = omit(
    {
      ...rest,
      ...getInputProps(schema, type, options),
    },
    "color",
    "onBeforeInput",
  );

  const hasError = (rawErrors ? rawErrors.length > 0 : false) && !hideError;
  const defaultValue = inputProps.defaultValue?.toString();
  const spellCheck =
    inputProps.spellCheck === undefined
      ? undefined
      : inputProps.spellCheck
        ? "true"
        : "false";
  const safeValue = value ?? "";

  return (
    <Input
      id={id}
      label={label}
      value={safeValue}
      placeholder={placeholder}
      disabled={disabled}
      readOnly={readonly}
      autoFocus={autofocus}
      isInvalid={hasError}
      errorMessage={rawErrors}
      required={required}
      isRequired={required}
      isReadOnly={readonly}
      isDisabled={disabled}
      onChange={onChangeOverride || onTextChange}
      onBlur={onTextBlur}
      onFocus={onTextFocus}
      {...inputProps}
      defaultValue={defaultValue}
      spellCheck={spellCheck}
      className="mb-2"
    />
  );
}
