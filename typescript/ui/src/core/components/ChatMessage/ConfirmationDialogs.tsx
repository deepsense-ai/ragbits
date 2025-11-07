import { Button, Chip, Checkbox } from "@heroui/react";
import { ConfirmationRequest } from "@ragbits/api-client-react";
import { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";

type ConfirmationDialogsProps = {
  confirmationRequests: ConfirmationRequest[];
  confirmationStates: Record<string, "pending" | "confirmed" | "declined" | "skipped">;
  onConfirm: (confirmationId: string) => void;
  onSkip: (confirmationId: string) => void;
  onBulkConfirm: (confirmationIds: string[]) => void;
  onBulkSkip: (confirmationIds: string[]) => void;
};

const ConfirmationDialogs = ({
  confirmationRequests,
  confirmationStates,
  onConfirm,
  onSkip,
  onBulkConfirm,
  onBulkSkip,
}: ConfirmationDialogsProps) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

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
  const getShortDescription = (req: ConfirmationRequest): string => {
    // If there's a tool description, use it
    if (req.tool_description) {
      return req.tool_description;
    }

    // Otherwise, create a description from the tool name and key arguments
    const args = req.arguments;
    const toolName = req.tool_name.replace(/_/g, " ");

    // Try to find a meaningful primary argument (email, name, id, etc.)
    const primaryArg =
      args.email || args.to || args.name || args.id || args.event_id;

    if (primaryArg) {
      return `${toolName}: ${primaryArg}`;
    }

    return `Execute ${toolName}`;
  };

  const pendingRequests = confirmationRequests.filter(
    (req) => confirmationStates[req.confirmation_id] === "pending"
  );

  const hasPending = pendingRequests.length > 0;
  const hasSelected = selectedIds.size > 0;

  const handleToggleSelection = (confirmationId: string) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(confirmationId)) {
        newSet.delete(confirmationId);
      } else {
        newSet.add(confirmationId);
      }
      return newSet;
    });
  };

  const handleConfirmAll = () => {
    const pendingIds = pendingRequests.map((req) => req.confirmation_id);
    onBulkConfirm(pendingIds);
    setSelectedIds(new Set());
  };

  const handleSkipAll = () => {
    const pendingIds = pendingRequests.map((req) => req.confirmation_id);
    onBulkSkip(pendingIds);
    setSelectedIds(new Set());
  };

  const handleConfirmSelected = () => {
    const selectedArray = Array.from(selectedIds).filter((id) =>
      confirmationStates[id] === "pending"
    );
    onBulkConfirm(selectedArray);
    setSelectedIds(new Set());
  };

  const handleSingleConfirm = (confirmationId: string) => {
    onConfirm(confirmationId);
    // Remove from selection if it was selected
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      newSet.delete(confirmationId);
      return newSet;
    });
  };

  const handleSingleSkip = (confirmationId: string) => {
    onSkip(confirmationId);
    // Remove from selection if it was selected
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      newSet.delete(confirmationId);
      return newSet;
    });
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.2 }}
        className="my-2 flex flex-col gap-3"
      >
        {/* Bulk action buttons */}
        {hasPending && (
          <div className="flex gap-2 flex-wrap">
            <Button
              size="sm"
              color="success"
              variant="solid"
              onPress={handleConfirmAll}
            >
              ✓ Confirm All ({pendingRequests.length})
            </Button>
            <Button
              size="sm"
              color="default"
              variant="bordered"
              onPress={handleSkipAll}
            >
              ⏭ Skip All
            </Button>
            {hasSelected && (
              <Button
                size="sm"
                color="success"
                variant="flat"
                onPress={handleConfirmSelected}
              >
                ✓ Confirm Selected ({selectedIds.size})
              </Button>
            )}
          </div>
        )}

        {/* List of confirmations */}
        <div className={`flex flex-col gap-2 ${confirmationRequests.length > 3 ? "max-h-[400px] overflow-y-auto pr-2" : ""}`}>
          {confirmationRequests.map((req) => {
            const state = confirmationStates[req.confirmation_id] || "pending";
            const isPending = state === "pending";
            const isSkipped = state === "skipped";
            const shortDescription = getShortDescription(req);
            const argsDisplay = formatArguments(req.arguments);
            const isSelected = selectedIds.has(req.confirmation_id);

            return (
              <motion.div
                key={req.confirmation_id}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className={`rounded-medium border-small flex items-center gap-3 p-3 ${
                  isSkipped
                    ? "border-default bg-default-100/50 opacity-60 grayscale"
                    : isPending
                      ? "border-warning bg-warning-50/50"
                      : state === "confirmed"
                        ? "border-success bg-success-50/50"
                        : "border-danger bg-danger-50/50"
                }`}
              >
                {/* Checkbox for bulk selection - only show for pending */}
                {isPending && (
                  <Checkbox
                    isSelected={isSelected}
                    onValueChange={() => handleToggleSelection(req.confirmation_id)}
                    size="sm"
                    className="shrink-0"
                  />
                )}

                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    {state === "pending" && (
                      <Chip size="sm" color="warning" variant="flat">
                        ⚠️ Confirmation needed
                      </Chip>
                    )}
                    {state === "confirmed" && (
                      <Chip size="sm" color="success" variant="flat">
                        ✅ Confirmed
                      </Chip>
                    )}
                    {state === "declined" && (
                      <Chip size="sm" color="default" variant="flat">
                        ❌ Declined
                      </Chip>
                    )}
                    {state === "skipped" && (
                      <Chip size="sm" color="default" variant="flat">
                        ⏭️ Handled naturally
                      </Chip>
                    )}
                  </div>
                  <p className="text-small text-default-700 font-medium">
                    {shortDescription}
                  </p>
                  {argsDisplay && isPending && (
                    <p className="text-tiny text-default-500 mt-1 truncate">
                      {argsDisplay}
                    </p>
                  )}
                </div>

                {isPending && (
                  <div className="flex shrink-0 gap-2">
                    <Button
                      size="sm"
                      color="success"
                      variant="solid"
                      onPress={() => handleSingleConfirm(req.confirmation_id)}
                    >
                      Do it
                    </Button>
                    <Button
                      size="sm"
                      color="default"
                      variant="bordered"
                      onPress={() => handleSingleSkip(req.confirmation_id)}
                    >
                      Skip
                    </Button>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default ConfirmationDialogs;

