import { withTheme } from "@rjsf/core";
import InputTemplate from "./InputWidget";
import SelectWidget from "./SelectWidget";
import FieldTemplate from "./FieldTemplate";

function EmptyComponent() {
  return null;
}

const FormTheme = withTheme({
  templates: {
    FieldTemplate,
    ErrorListTemplate: EmptyComponent,
    TitleFieldTemplate: EmptyComponent,
    ButtonTemplates: {
      AddButton: EmptyComponent,
      CopyButton: EmptyComponent,
      MoveDownButton: EmptyComponent,
      MoveUpButton: EmptyComponent,
      RemoveButton: EmptyComponent,
      SubmitButton: EmptyComponent,
    },
    FieldErrorTemplate: EmptyComponent,
    DescriptionFieldTemplate: EmptyComponent,
  },
  widgets: {
    TextWidget: InputTemplate,
    SelectWidget,
  },
});

export default FormTheme;
