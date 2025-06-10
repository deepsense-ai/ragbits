import { useMemo, useState } from "react";
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
  useDisclosure,
} from "@heroui/react";
import { generateZodSchema } from "./types";
import { useThemeContext } from "../../contexts/ThemeContext/useThemeContext";
import {
  FeedbackType,
  FormFieldResponse,
  useRagbitsCall,
} from "ragbits-api-client-react";
import { Icon } from "@iconify/react/dist/iconify.js";
import DelayedTooltip from "../../core/components/DelayedTooltip";
import { useConfigContext } from "../../contexts/ConfigContext/useConfigContext";

interface FeedbackFormProps {
  messageServerId: string;
}

export default function FeedbackForm({ messageServerId }: FeedbackFormProps) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    config: { feedback },
  } = useConfigContext();
  const [feedbackType, setFeedbackType] = useState<FeedbackType>(
    FeedbackType.LIKE,
  );
  const schema = feedback[feedbackType].form;
  const feedbackCallFactory = useRagbitsCall("/api/feedback", {
    method: "POST",
  });

  const { theme } = useThemeContext();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset,
  } = useForm();

  const onOpenChange = () => {
    reset();
    onClose();
  };

  const onFeedbackFormSubmit = async (data: Record<string, string> | null) => {
    try {
      await feedbackCallFactory.call({
        body: {
          message_id: messageServerId,
          feedback: feedbackType,
          payload: data,
        },
      });
    } catch (e) {
      console.error(e);
      // TODO: Add some information to the UI about error
    }
  };

  const handleFormSubmit: SubmitHandler<Record<string, string>> = (data) => {
    onFeedbackFormSubmit(data);
    onClose();
  };

  const onOpenFeedbackForm = async (type: FeedbackType) => {
    setFeedbackType(type);
    if (feedback[type].form === null) {
      await onFeedbackFormSubmit(null);
      return;
    }

    onOpen();
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
    <>
      {feedback.like !== null && (
        <DelayedTooltip content="Like" placement="bottom">
          <Button
            isIconOnly
            variant="ghost"
            className="p-0"
            aria-label="Rate message as helpful"
            onPress={() => onOpenFeedbackForm(FeedbackType.LIKE)}
          >
            <Icon icon="heroicons:hand-thumb-up" />
          </Button>
        </DelayedTooltip>
      )}
      {feedback.dislike !== null && (
        <DelayedTooltip content="Dislike" placement="bottom">
          <Button
            isIconOnly
            variant="ghost"
            className="p-0"
            aria-label="Rate message as unhelpful"
            onPress={() => onOpenFeedbackForm(FeedbackType.DISLIKE)}
          >
            <Icon icon="heroicons:hand-thumb-down" />
          </Button>
        </DelayedTooltip>
      )}
      <Modal isOpen={isOpen} onOpenChange={onOpenChange} className={cn(theme)}>
        <ModalContent>
          {(onClose) => (
            <form onSubmit={handleSubmit(handleFormSubmit)}>
              <ModalHeader className="flex flex-col gap-1 text-default-900">
                {schema.title}
              </ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-4">
                  <p>Dummy form</p>
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
    </>
  );
}
