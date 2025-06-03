import { useMemo } from "react";
import { SubmitHandler, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  Select,
  SelectItem,
  cn,
} from "@heroui/react";
import { generateZodSchema } from "./types";
import { useThemeContext } from "../../contexts/ThemeContext/useThemeContext";
import { FormFieldResponse, FormSchemaResponse } from "../../types/api.ts";

interface FormPluginComponentProps {
  title: string;
  schema: FormSchemaResponse | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: Record<string, string>) => void;
}

const FeedbackFormPluginComponent = ({
  title,
  schema,
  isOpen,
  onClose,
  onSubmit,
}: FormPluginComponentProps) => {
  const zodSchema = useMemo(() => generateZodSchema(schema), [schema]);
  const { theme } = useThemeContext();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm({
    resolver: zodResolver(zodSchema),
  });

  const onOpenChange = () => {
    reset();
    onClose();
  };

  const handleFormSubmit: SubmitHandler<Record<string, string>> = (data) => {
    onSubmit(data);
    onClose();
  };

  if (!schema) {
    return null;
  }

  // TODO: switch to separate file or some kind of form builder with methods eg. renderSelect/Checkbox/TextField etc.
  const renderField = (field: FormFieldResponse) => {
    const error = errors[field.name]?.message as string;

    if (field.type === "select" && field.options) {
      return (
        <Select
          key={field.name}
          label={field.label}
          placeholder={`Select ${field.label.toLowerCase()}`}
          isRequired={field.required}
          errorMessage={error}
          defaultSelectedKeys={[watch(field.name)]}
          onChange={(e) => setValue(field.name, e.target.value)}
        >
          {field.options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </Select>
      );
    }

    return (
      <Input
        key={field.name}
        label={field.label}
        placeholder={`Enter ${field.label.toLowerCase()}`}
        isRequired={field.required}
        errorMessage={error}
        {...register(field.name)}
      />
    );
  };

  return (
    <Modal isOpen={isOpen} onOpenChange={onOpenChange} className={cn(theme)}>
      <ModalContent>
        {(onClose) => (
          <form onSubmit={handleSubmit(handleFormSubmit)}>
            <ModalHeader className="flex flex-col gap-1 text-default-900">
              {title}
            </ModalHeader>
            <ModalBody>
              <div className="flex flex-col gap-4">
                {schema!.fields.map(renderField)}
              </div>
            </ModalBody>
            <ModalFooter>
              <Button
                color="danger"
                variant="light"
                onPress={onClose}
                aria-label="Close feedback form"
              >
                Cancel
              </Button>
              <Button
                color="primary"
                type="submit"
                aria-label="Submit feedback"
              >
                Submit
              </Button>
            </ModalFooter>
          </form>
        )}
      </ModalContent>
    </Modal>
  );
};

export default FeedbackFormPluginComponent;
