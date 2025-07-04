import { useState } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  Button,
  useDisclosure,
} from "@heroui/react";
import { Icon } from "@iconify/react/dist/iconify.js";
import DelayedTooltip from "../../../core/components/DelayedTooltip";
import { useConfigContext } from "../../../core/contexts/ConfigContext/useConfigContext";
import { FormTheme, useTransformErrors } from "../../../core/forms";
import validator from "@rjsf/validator-ajv8";
import { IChangeEvent } from "@rjsf/core";

interface ChatOptionsFormProps {
  onOptionsChange: (data: Record<string, any>) => void;
  isVisible?: boolean;
}

export default function ChatOptionsForm({
  onOptionsChange,
  isVisible = true,
}: ChatOptionsFormProps) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    config: { chat },
  } = useConfigContext();

  const schema = chat.form;

  const onOpenChange = () => {
    onClose();
  };

  const handleFormSubmit = (data: IChangeEvent) => {
    onOptionsChange(data.formData);
    onClose();
  };

  const transformErrors = useTransformErrors();

  if (!schema || !isVisible) {
    return null;
  }


  return (
    <>
      <DelayedTooltip content="Chat Options" placement="bottom">
        <Button
          isIconOnly
          variant="ghost"
          className="p-0"
          aria-label="Open chat options"
          onPress={onOpen}
        >
          <Icon icon="heroicons:cog-6-tooth" />
        </Button>
      </DelayedTooltip>

      <Modal isOpen={isOpen} onOpenChange={onOpenChange}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1 text-default-900">
                {schema.title || "Chat Options"}
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
                        aria-label="Close chat options form"
                      >
                        Cancel
                      </Button>
                      <Button
                        color="primary"
                        type="submit"
                        aria-label="Save chat options"
                      >
                        Save
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
