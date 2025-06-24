import { FormSchemaResponse } from "ragbits-api-client-react";

export interface FeedbackFormComponentProps {
  title: string;
  schema: FormSchemaResponse | null;
  onClose: () => void;
  onSubmit: (data: Record<string, string> | null) => void;
  isOpen: boolean;
}
