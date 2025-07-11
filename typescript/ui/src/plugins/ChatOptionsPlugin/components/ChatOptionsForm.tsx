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
import {
  useHistoryActions,
  useHistoryStore,
} from "../../../core/stores/historyStore";
import { useEffect } from "react";
import { getDefaultBasedOnSchemaType } from "@rjsf/utils/lib/schema/getDefaultFormState";

export default function ChatOptionsForm() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const chatOptions = useHistoryStore((s) => s.chatOptions);
  const { setChatOptions } = useHistoryActions();

  const {
    config: { user_settings: userSettings },
  } = useConfigContext();

  const schema = userSettings?.form;

  const onOpenChange = () => {
    onClose();
  };

  const handleFormSubmit = (data: IChangeEvent) => {
    setChatOptions(data.formData);
    onClose();
  };

  const transformErrors = useTransformErrors();

  useEffect(() => {
    if (!schema) {
      return;
    }

    const defaultState = getDefaultBasedOnSchemaType(validator, schema);
    setChatOptions(defaultState);
  }, [schema, setChatOptions]);

  if (!schema) {
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
          data-testid="open-chat-options"
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
                    formData={chatOptions}
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
                        data-testid="chat-options-submit"
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
