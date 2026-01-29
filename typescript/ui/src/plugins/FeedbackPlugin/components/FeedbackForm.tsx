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
import { Icon } from "@iconify/react";
import DelayedTooltip from "../../../core/components/DelayedTooltip";
import { useConfigContext } from "../../../core/contexts/ConfigContext/useConfigContext";
import { FormTheme, transformErrors } from "../../../core/forms";
import validator from "@rjsf/validator-ajv8";
import { IChangeEvent } from "@rjsf/core";
import { ChatMessage } from "../../../core/types/history";
import { useHistoryActions } from "../../../core/stores/HistoryStore/selectors";

interface FeedbackFormProps {
  message: ChatMessage;
}

export default function FeedbackForm({ message }: FeedbackFormProps) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { mergeExtensions } = useHistoryActions();
  const {
    config: { feedback },
  } = useConfigContext();
  const [feedbackType, setFeedbackType] = useState<FeedbackType>(
    FeedbackType.Like,
  );
  const feedbackCallFactory = useRagbitsCall("/api/feedback", {
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  if (!message.serverId) {
    return null;
  }

  const schema = feedback[feedbackType].form;
  const onOpenChange = () => {
    onClose();
  };

  const onFeedbackFormSubmit = async (data: Record<string, string> | null) => {
    if (!message.serverId) {
      throw new Error(
        'Feedback is only available for messages with "serverId" set',
      );
    }

    try {
      await feedbackCallFactory.call({
        body: {
          message_id: message.serverId,
          feedback: feedbackType,
          payload: data ?? {},
        },
      });
    } catch (e) {
      console.error(e);
      // TODO: Add some information to the UI about error
    }
  };

  const handleFormSubmit = (data: IChangeEvent) => {
    mergeExtensions(message.id, {
      feedbackType,
    });
    onFeedbackFormSubmit(data.formData);
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

  const selectedFeedback = message.extensions?.feedbackType;
  return (
    <>
      {feedback.like.enabled && (
        <DelayedTooltip content="Like" placement="bottom">
          <Button
            isIconOnly
            variant="ghost"
            className="p-0"
            aria-label="Rate message as helpful"
            onPress={() => onOpenFeedbackForm(FeedbackType.Like)}
            data-testid="feedback-like"
          >
            <Icon
              icon={
                selectedFeedback === FeedbackType.Like
                  ? "heroicons:hand-thumb-up-solid"
                  : "heroicons:hand-thumb-up"
              }
            />
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
            onPress={() => onOpenFeedbackForm(FeedbackType.Dislike)}
            data-testid="feedback-dislike"
          >
            <Icon
              icon={
                selectedFeedback === FeedbackType.Dislike
                  ? "heroicons:hand-thumb-down-solid"
                  : "heroicons:hand-thumb-down"
              }
            />
          </Button>
        </DelayedTooltip>
      )}
      <Modal isOpen={isOpen} onOpenChange={onOpenChange}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="text-default-900 flex flex-col gap-1">
                {schema.title}
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
