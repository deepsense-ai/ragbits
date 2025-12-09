import { Button } from "@heroui/react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useCallback, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { OAuth2VisualConfig } from "../plugins/OAuth2LoginPlugin";

/**
 * Response type for OAuth2 authorization endpoint.
 */
interface OAuth2AuthorizeResponse {
  authorize_url: string;
  state: string;
}

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
  const { client } = useRagbitsContext();

  const handleOAuth2Login = useCallback(async () => {
    setError(false);
    setIsLoading(true);
    try {
      // Call provider-specific authorize endpoint
      // Using fetch with client.getBaseUrl() for dynamic path parameter support
      const response = await fetch(
        `${client.getBaseUrl()}/api/auth/authorize/${provider}`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
        },
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = (await response.json()) as OAuth2AuthorizeResponse;

      if (!data.authorize_url) {
        setError(true);
        setErrorMessage(`Failed to get ${displayName} authorization URL`);
        return;
      }

      // Redirect to OAuth2 provider authorization page
      // The backend will handle the callback and redirect back to frontend
      window.location.href = data.authorize_url;
    } catch (e) {
      setError(true);
      setErrorMessage(`Failed to initiate ${displayName} login`);
      console.error(`Failed to start ${displayName} login`, e);
      setIsLoading(false);
    }
  }, [client, provider, displayName]);

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
    // Render the SVG string from the backend
    return (
      <span
        className="flex items-center justify-center"
        dangerouslySetInnerHTML={{ __html: visualConfig.iconSvg }}
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
