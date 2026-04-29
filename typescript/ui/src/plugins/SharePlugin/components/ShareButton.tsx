import {
  Button,
  Chip,
  Divider,
  Input,
  Modal,
  ModalBody,
  ModalContent,
  ModalFooter,
  ModalHeader,
  useDisclosure,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import DelayedTooltip from "../../../core/components/DelayedTooltip";
import { useState, useEffect, useCallback } from "react";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";
import { useConversationProperty } from "../../../core/stores/HistoryStore/selectors";
import {
  useRagbitsCall,
  useRagbitsContext,
  type ConversationShareResponse,
} from "@ragbits/api-client-react";

const DEFAULT_ICON = "heroicons:share";
const SUCCESS_ICON = "heroicons:check";

export default function ShareButton() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [inputValue, setInputValue] = useState("");
  const [pendingRecipients, setPendingRecipients] = useState<string[]>([]);
  const [existingRecipients, setExistingRecipients] = useState<
    ConversationShareResponse[]
  >([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [headerIcon, setHeaderIcon] = useState(DEFAULT_ICON);

  const conversationId = useHistoryStore((s) => s.currentConversation);
  const isShared = useConversationProperty((s) => s.isShared);
  const { client } = useRagbitsContext();

  const updateShares = useRagbitsCall(
    "/api/conversations/:conversationId/shares",
    { method: "PUT" },
  );
  const revokeShareCall = useRagbitsCall(
    "/api/conversations/:conversationId/shares/:recipient",
    { method: "DELETE" },
  );

  const loadShares = useCallback(async () => {
    if (!conversationId) return;
    setIsLoading(true);
    try {
      const detail = await client.makeRequest(
        "/api/conversations/:conversationId",
        {
          method: "GET",
          pathParams: { conversationId },
        },
      );
      setExistingRecipients(detail?.shares ?? []);
    } catch (err) {
      console.error("Failed to load shares", err);
      setError("Failed to load shares");
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, client]);

  useEffect(() => {
    if (isOpen) {
      loadShares();
      setPendingRecipients([]);
      setInputValue("");
      setError(null);
    }
    // We intentionally omit loadShares from deps - it's rebuilt on every render
    // by useRagbitsCall and would cause an infinite reload loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const addRecipient = () => {
    const value = inputValue.trim();
    if (!value) return;

    const allRecipients = [
      ...existingRecipients.map((r) => r.recipient),
      ...pendingRecipients,
    ];
    if (allRecipients.some((r) => r.toLowerCase() === value.toLowerCase())) {
      setError("Already added");
      return;
    }

    setPendingRecipients((prev) => [...prev, value]);
    setInputValue("");
    setError(null);
  };

  const removePending = (recipient: string) => {
    setPendingRecipients((prev) => prev.filter((r) => r !== recipient));
  };

  const removeExisting = async (recipient: string) => {
    try {
      await revokeShareCall.call({
        pathParams: { conversationId, recipient },
      });
      setExistingRecipients((prev) =>
        prev.filter((r) => r.recipient !== recipient),
      );
    } catch (err) {
      console.error("Failed to revoke share", err);
      setError("Failed to remove recipient");
    }
  };

  const handleSave = async () => {
    if (pendingRecipients.length === 0 && existingRecipients.length > 0) {
      onClose();
      return;
    }

    try {
      const allRecipients = [
        ...existingRecipients.map((r) => r.recipient),
        ...pendingRecipients,
      ];
      if (allRecipients.length === 0) {
        onClose();
        return;
      }
      const updated = await updateShares.call({
        pathParams: { conversationId },
        body: {
          recipients: allRecipients as [string, ...string[]],
        },
      });
      setExistingRecipients(updated ?? []);
      setPendingRecipients([]);
      onClose();
    } catch (err) {
      console.error("Failed to share conversation", err);
      setError("Failed to share conversation");
    }
  };

  const copyLink = () => {
    const url = `${window.location.origin}/conversation/${conversationId}`;
    navigator.clipboard.writeText(url);
    setHeaderIcon(SUCCESS_ICON);
    setTimeout(() => setHeaderIcon(DEFAULT_ICON), 2000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addRecipient();
    }
  };

  if (isShared) return null;

  const isSaving = updateShares.isLoading;

  return (
    <>
      <DelayedTooltip content="Share conversation" placement="bottom">
        <Button
          isIconOnly
          variant="ghost"
          className="p-0"
          aria-label="Share conversation"
          onPress={onOpen}
        >
          <Icon icon={DEFAULT_ICON} />
        </Button>
      </DelayedTooltip>

      <Modal isOpen={isOpen} onOpenChange={onClose} size="lg">
        <ModalContent>
          <ModalHeader className="text-default-900 flex items-center gap-2">
            Share conversation
          </ModalHeader>
          <ModalBody>
            <div className="flex flex-col gap-3">
              <Input
                placeholder="Add people by user ID or email"
                value={inputValue}
                onChange={(e) => {
                  setInputValue(e.target.value);
                  setError(null);
                }}
                onKeyDown={handleKeyDown}
                onBlur={() => {
                  if (inputValue.trim()) addRecipient();
                }}
                isInvalid={!!error}
                errorMessage={error}
                size="sm"
                aria-label="Recipient identifier"
              />

              {pendingRecipients.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {pendingRecipients.map((r) => (
                    <Chip
                      key={r}
                      size="sm"
                      variant="flat"
                      color="primary"
                      onClose={() => removePending(r)}
                    >
                      {r}
                    </Chip>
                  ))}
                </div>
              )}

              {existingRecipients.length > 0 && (
                <>
                  <Divider />
                  <div className="flex flex-col gap-1">
                    <span className="text-default-500 text-xs font-medium uppercase">
                      Shared with
                    </span>
                    {existingRecipients.map((share) => (
                      <div
                        key={share.recipient}
                        className="flex items-center justify-between py-1"
                      >
                        <span className="text-default-700 text-sm">
                          {share.recipient}
                        </span>
                        <Button
                          isIconOnly
                          size="sm"
                          variant="light"
                          color="danger"
                          aria-label={`Remove ${share.recipient}`}
                          onPress={() => removeExisting(share.recipient)}
                        >
                          <Icon icon="heroicons:x-mark" width={16} />
                        </Button>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {isLoading && (
                <span className="text-default-400 text-sm">Loading...</span>
              )}
            </div>
          </ModalBody>
          <ModalFooter className="flex items-center justify-between">
            <DelayedTooltip
              content={`${window.location.origin}/conversation/${conversationId}`}
              placement="top"
            >
              <Button
                size="sm"
                variant="flat"
                startContent={<Icon icon={headerIcon} width={16} />}
                onPress={copyLink}
                aria-label="Copy link"
              >
                Copy link
              </Button>
            </DelayedTooltip>
            <div className="flex gap-2">
              <Button variant="light" onPress={onClose} aria-label="Cancel">
                Cancel
              </Button>
              <Button
                color="primary"
                onPress={handleSave}
                isLoading={isSaving}
                isDisabled={
                  pendingRecipients.length === 0 &&
                  existingRecipients.length === 0
                }
                aria-label="Share"
              >
                Share
              </Button>
            </div>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
}
