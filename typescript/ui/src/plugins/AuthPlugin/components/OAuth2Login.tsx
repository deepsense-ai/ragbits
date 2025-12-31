import { Button } from "@heroui/react";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { useCallback, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import DOMPurify from "isomorphic-dompurify";
import type { OAuth2VisualConfig } from "../plugins/OAuth2LoginPlugin";

interface OAuth2LoginProps {
  provider: string;
  displayName: string;
  visualConfig?: OAuth2VisualConfig;
}

export default function OAuth2Login({
  provider,
  displayName,
  visualConfig,
}: OAuth2LoginProps) {
  const [isError, setError] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const authorizeLoginFactory = useRagbitsCall("/api/auth/authorize/:provider");

  const handleOAuth2Login = useCallback(async () => {
    setError(false);
    setIsLoading(true);
    try {
      // Call provider-specific authorize endpoint
      // Using fetch with client.getBaseUrl() for dynamic path parameter support
      const response = await authorizeLoginFactory.call({
        pathParams: { provider },
      });

      if (!response.authorize_url) {
        throw new Error(`Failed to get ${displayName} authorization URL`);
      }

      window.location.href = response.authorize_url;
    } catch (e) {
      setError(true);
      setErrorMessage(`Failed to initiate ${displayName} login: ${e}`);
      console.error(`Failed to start ${displayName} login`, e);
    } finally {
      setIsLoading(false);
    }
  }, [authorizeLoginFactory, displayName, provider]);

  // Compute button style from visual config
  const buttonStyle = useMemo(() => {
    if (!visualConfig?.buttonColor) return undefined;
    return {
      backgroundColor: visualConfig.buttonColor,
      color: visualConfig.textColor || "#FFFFFF",
    };
  }, [visualConfig]);

  // Render icon from SVG string provided by backend
  const renderIcon = useMemo(() => {
    if (isLoading || !visualConfig?.iconSvg) return null;
    // Sanitize the SVG string from the backend to prevent XSS attacks
    const sanitizedSvg = DOMPurify.sanitize(visualConfig.iconSvg, {
      USE_PROFILES: { svg: true },
    });
    return (
      <span
        className="flex items-center justify-center"
        dangerouslySetInnerHTML={{ __html: sanitizedSvg }}
      />
    );
  }, [isLoading, visualConfig?.iconSvg]);

  return (
    <div className="flex flex-col gap-4">
      <AnimatePresence>
        {isError && (
          <motion.div
            className="text-small text-danger"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          >
            {errorMessage || `Failed to sign in with ${displayName}`}
          </motion.div>
        )}
      </AnimatePresence>

      <Button
        onPress={handleOAuth2Login}
        color={buttonStyle ? undefined : "primary"}
        style={buttonStyle}
        isLoading={isLoading}
        startContent={renderIcon}
      >
        {isLoading ? "Redirecting..." : `Sign in with ${displayName}`}
      </Button>
    </div>
  );
}
