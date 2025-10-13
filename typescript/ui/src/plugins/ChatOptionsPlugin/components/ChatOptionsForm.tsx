import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  Button,
  useDisclosure,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import DelayedTooltip from "../../../core/components/DelayedTooltip";
import { useConfigContext } from "../../../core/contexts/ConfigContext/useConfigContext";
import { FormTheme, transformErrors } from "../../../core/forms";
import validator from "@rjsf/validator-ajv8";
import { IChangeEvent } from "@rjsf/core";
import { FormEvent, useEffect, useRef } from "react";
import { getDefaultBasedOnSchemaType } from "@rjsf/utils/lib/schema/getDefaultFormState";
import {
  useConversationProperty,
  useHistoryActions,
} from "../../../core/stores/HistoryStore/selectors";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";
import { useLocalStorage } from "usehooks-ts";
import { pluginManager } from "../../../core/utils/plugins/PluginManager";
import { ChatHistoryPlugin } from "../../ChatHistoryPlugin";
import { AnimationDefinition } from "framer-motion";

const CHAT_OPTIONS_KEY = "ragbits-no-history-chat-options";

export default function ChatOptionsForm() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const chatOptions = useConversationProperty((s) => s.chatOptions);
  // Needed to solve flicker to default settings when the modal is closing
  const pendingSettingsRef = useRef<Record<string, unknown> | null>(null);
  const { setConversationProperties, initializeChatOptions } =
    useHistoryActions();
  const currentConversation = useHistoryStore((s) => s.currentConversation);
  const {
    config: { user_settings: userSettings },
  } = useConfigContext();
  const [savedSettings, setSettings] = useLocalStorage<Record<
    string,
    unknown
  > | null>(CHAT_OPTIONS_KEY, null);

  const schema = userSettings?.form;

  const ensureSyncWithStorage = (data: Record<string, unknown>) => {
    // Sync to localStorage only when history is disabled
    if (pluginManager.isPluginActivated(ChatHistoryPlugin.name)) {
      return;
    }

    setSettings(data);
  };

  const onModalOpen = () => {
    onOpen();
  };

  const handleFormSubmit = (data: IChangeEvent, event: FormEvent) => {
    event.preventDefault();
    pendingSettingsRef.current = data.formData;
    onClose();
  };

  const onRestoreDefaults = () => {
    if (!schema) {
      return;
    }

    const defaultState = getDefaultBasedOnSchemaType(validator, schema);
    pendingSettingsRef.current = defaultState;
    onClose();
  };

  const onOpenChange = () => {
    onClose();
  };

  const onAnimationComplete = (definition: AnimationDefinition) => {
    if (definition !== "exit" || !pendingSettingsRef.current) {
      return;
    }

    const settings = pendingSettingsRef.current;
    setConversationProperties(currentConversation, { chatOptions: settings });
    ensureSyncWithStorage(settings);
    pendingSettingsRef.current = null;
  };

  useEffect(() => {
    if (!schema) {
      return;
    }

    const defaultState = getDefaultBasedOnSchemaType(validator, schema);
    // When history is active, use default state for new conversations
    if (pluginManager.isPluginActivated(ChatHistoryPlugin.name)) {
      initializeChatOptions(defaultState);
      // Otherwise if we have saved settings, use them
    } else if (savedSettings !== null) {
      initializeChatOptions(savedSettings);
      // Otherwise just use defaults
    } else {
      initializeChatOptions(defaultState);
      setSettings(defaultState);
    }
  }, [
    initializeChatOptions,
    schema,
    currentConversation,
    savedSettings,
    setSettings,
  ]);

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
          onPress={onModalOpen}
          data-testid="open-chat-options"
        >
          <Icon icon="heroicons:cog-6-tooth" />
        </Button>
      </DelayedTooltip>

      <Modal
        isOpen={isOpen}
        onOpenChange={onOpenChange}
        motionProps={{
          onAnimationComplete,
        }}
      >
        <ModalContent>
          <ModalHeader className="text-default-900 flex flex-col gap-1">
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
                    className="mr-auto"
                    color="primary"
                    variant="light"
                    onPress={onRestoreDefaults}
                    aria-label="Restore default user settings"
                  >
                    Restore defaults
                  </Button>
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
        </ModalContent>
      </Modal>
    </>
  );
}
