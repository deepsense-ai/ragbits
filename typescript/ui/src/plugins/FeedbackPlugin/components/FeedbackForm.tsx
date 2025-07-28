import { useState } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  Button,
  useDisclosure,
} from "@heroui/react";
import { FeedbackType, useRagbitsCall } from "@ragbits/api-client-react";
import { Icon } from "@iconify/react/dist/iconify.js";
import DelayedTooltip from "../../../core/components/DelayedTooltip";
import { useConfigContext } from "../../../core/contexts/ConfigContext/useConfigContext";
import { FormTheme, useTransformErrors } from "../../../core/forms";
import validator from "@rjsf/validator-ajv8";
import { IChangeEvent } from "@rjsf/core";
import { RJSFSchema } from "@rjsf/utils";

interface FeedbackFormProps {
  messageServerId: string;
}

export default function FeedbackForm({ messageServerId }: FeedbackFormProps) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    config: { feedback },
  } = useConfigContext();
  const [feedbackType, setFeedbackType] = useState<FeedbackType>("like");
  const feedbackCallFactory = useRagbitsCall("/api/feedback", {
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  const schema = feedback[
    `${feedbackType}_form` as keyof typeof feedback
  ] as RJSFSchema;
  const onOpenChange = () => {
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

  const handleFormSubmit = (data: IChangeEvent) => {
    onFeedbackFormSubmit(data.formData);
    onClose();
  };

  const onOpenFeedbackForm = async (type: FeedbackType) => {
    setFeedbackType(type);
    if (feedback[`${type}_form` as keyof typeof feedback] === null) {
      await onFeedbackFormSubmit(null);
      return;
    }

    onOpen();
  };

  const transformErrors = useTransformErrors();

  if (!schema) {
    return null;
  }

  return (
    <>
      {feedback.like.enabled && (
        <DelayedTooltip content="Like" placement="bottom">
          <Button
            isIconOnly
            variant="ghost"
            className="p-0"
            aria-label="Rate message as helpful"
            onPress={() => onOpenFeedbackForm("like")}
            data-testid="feedback-like"
          >
            <Icon icon="heroicons:hand-thumb-up" />
          </Button>
        </DelayedTooltip>
      )}
      {feedback.dislike.enabled && (
        <DelayedTooltip content="Dislike" placement="bottom">
          <Button
            isIconOnly
            variant="ghost"
            className="p-0"
            aria-label="Rate message as unhelpful"
            onPress={() => onOpenFeedbackForm("dislike")}
            data-testid="feedback-dislike"
          >
            <Icon icon="heroicons:hand-thumb-down" />
          </Button>
        </DelayedTooltip>
      )}
      <Modal isOpen={isOpen} onOpenChange={onOpenChange}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1 text-default-900">
                {schema.title ?? "Feedback"}
              </ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-4">
                  <FormTheme
                    schema={schema}
                    validator={validator}
                    onSubmit={handleFormSubmit}
                    transformErrors={transformErrors}
                    liveValidate
                  >
                    <div className="flex justify-end gap-4 py-4">
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
                        data-testid="feedback-submit"
                      >
                        Submit
                      </Button>
                    </div>
                  </FormTheme>
                </div>
              </ModalBody>
            </>
          )}
        </ModalContent>
      </Modal>
    </>
  );
}
