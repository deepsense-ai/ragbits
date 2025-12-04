import { Button, Chip } from "@heroui/react";
import { ConfirmationRequest } from "@ragbits/api-client-react";
import { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";

type ConfirmationDialogProps = {
  confirmationRequest: ConfirmationRequest;
  onConfirm: () => void;
  onSkip: () => void;
  initialState?: "pending" | "confirmed" | "declined" | "skipped";
};

type ConfirmationState = "pending" | "confirmed" | "declined" | "skipped";

const ConfirmationDialog = ({
  confirmationRequest,
  onConfirm,
  onSkip,
  initialState = "pending",
}: ConfirmationDialogProps) => {
  const [confirmationState, setConfirmationState] =
    useState<ConfirmationState>(initialState);

  // Update state if initialState changes (page reload)
  useEffect(() => {
    setConfirmationState(initialState);
  }, [initialState]);

  const handleConfirm = () => {
    setConfirmationState("confirmed");
    onConfirm();
  };

  const handleSkip = () => {
    setConfirmationState("declined");
    onSkip();
  };

  // Helper function to format arguments for display
  const formatArguments = (args: Record<string, unknown>): string => {
    const entries = Object.entries(args);
    if (entries.length === 0) return "";

    // Show key arguments in a readable format
    return entries
      .slice(0, 3) // Show max 3 arguments
      .map(([key, value]) => {
        const displayValue =
          typeof value === "string"
            ? value.length > 30
              ? `${value.substring(0, 30)}...`
              : value
            : JSON.stringify(value);
        return `${key}: ${displayValue}`;
      })
      .join(", ");
  };

  // Helper function to create a short, readable description
  const getShortDescription = (): string => {
    // If there's a tool description, use it
    if (confirmationRequest.tool_description) {
      return confirmationRequest.tool_description;
    }

    // Otherwise, create a description from the tool name and key arguments
    const args = confirmationRequest.arguments;
    const toolName = confirmationRequest.tool_name.replace(/_/g, " ");

    // Try to find a meaningful primary argument (email, name, id, etc.)
    const primaryArg =
      args.email || args.to || args.name || args.id || args.event_id;

    if (primaryArg) {
      return `${toolName}: ${primaryArg}`;
    }

    return `Execute ${toolName}`;
  };

  const shortDescription = getShortDescription();
  const argsDisplay = formatArguments(confirmationRequest.arguments);
  const isSkipped = confirmationState === "skipped";

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.2 }}
        className="my-2"
      >
        <div
          className={`rounded-medium border-small flex items-center justify-between gap-3 p-3 ${
            isSkipped
              ? "border-default bg-default-100/50 opacity-60 grayscale"
              : "border-warning bg-warning-50/50"
          }`}
        >
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex items-center gap-2">
              {confirmationState === "pending" && (
                <Chip size="sm" color="warning" variant="flat">
                  ⚠️ Confirmation needed
                </Chip>
              )}
              {confirmationState === "confirmed" && (
                <Chip size="sm" color="success" variant="flat">
                  ✅ Confirmed
                </Chip>
              )}
              {confirmationState === "declined" && (
                <Chip size="sm" color="default" variant="flat">
                  ❌ Declined
                </Chip>
              )}
              {confirmationState === "skipped" && (
                <Chip size="sm" color="default" variant="flat">
                  ⏭️ Handled naturally
                </Chip>
              )}
            </div>
            <p className="text-small text-default-700 font-medium">
              {shortDescription}
            </p>
            {argsDisplay && confirmationState === "pending" && (
              <p className="text-tiny text-default-500 mt-1 truncate">
                {argsDisplay}
              </p>
            )}
          </div>

          {confirmationState === "pending" && (
            <div className="flex shrink-0 gap-2">
              <Button
                size="sm"
                color="success"
                variant="solid"
                onPress={handleConfirm}
              >
                Do it
              </Button>
              <Button
                size="sm"
                color="default"
                variant="bordered"
                onPress={handleSkip}
              >
                Skip
              </Button>
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default ConfirmationDialog;
