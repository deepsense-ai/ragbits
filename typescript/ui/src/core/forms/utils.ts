import { useCallback } from "react";
import { RJSFValidationError } from "@rjsf/utils";

/**
 * Shared error transformation function for form validation
 */
export const useTransformErrors = () => {
  return useCallback((errors: RJSFValidationError[]) => {
    return errors.map((error) => {
      if (error.name === "minLength" || error.name === "required") {
        return { ...error, message: "Field must not be empty" };
      }
      return error;
    });
  }, []);
};
