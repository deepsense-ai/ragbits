import { Button, Card, CardBody, CardFooter, CardHeader } from "@heroui/react";
import { ConfirmationRequest } from "@ragbits/api-client-react";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

type ConfirmationDialogProps = {
  confirmationRequest: ConfirmationRequest;
  onConfirm: () => void;
  onSkip: () => void;
};

const ConfirmationDialog = ({
  confirmationRequest,
  onConfirm,
  onSkip,
}: ConfirmationDialogProps) => {
  const [isResponded, setIsResponded] = useState(false);

  const handleConfirm = () => {
    setIsResponded(true);
    onConfirm();
  };

  const handleSkip = () => {
    setIsResponded(true);
    onSkip();
  };

  if (isResponded) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="border-warning bg-warning-50 border-2">
          <CardHeader className="flex-col items-start gap-1">
            <h4 className="text-warning-700 text-lg font-semibold">
              ⚠️ Confirmation Required
            </h4>
            <p className="text-warning-600 text-sm">
              {confirmationRequest.tool_description}
            </p>
          </CardHeader>
          <CardBody className="gap-2 pt-0">
            <div className="text-small text-default-700">
              <p className="font-semibold">
                Tool: {confirmationRequest.tool_name}
              </p>
              {Object.keys(confirmationRequest.arguments).length > 0 && (
                <div className="bg-default-100 rounded-small mt-2 p-2">
                  <p className="text-tiny mb-1 font-semibold">Arguments:</p>
                  <pre className="text-tiny overflow-x-auto">
                    {JSON.stringify(confirmationRequest.arguments, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </CardBody>
          <CardFooter className="gap-2">
            <Button
              color="success"
              variant="solid"
              onPress={handleConfirm}
              className="flex-1"
            >
              ✓ Do it
            </Button>
            <Button
              color="default"
              variant="bordered"
              onPress={handleSkip}
              className="flex-1"
            >
              ✕ Skip
            </Button>
          </CardFooter>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
};

export default ConfirmationDialog;



