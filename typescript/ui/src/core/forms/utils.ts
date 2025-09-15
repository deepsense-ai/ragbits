import { RJSFValidationError } from "@rjsf/utils";

/**
 * Shared error transformation function for form validation
 */
export const transformErrors = (errors: RJSFValidationError[]) => {
  return errors.map((error) => {
    if (error.name === "minLength" || error.name === "required") {
      return { ...error, message: "Field must not be empty" };
    }
    return error;
  });
};
