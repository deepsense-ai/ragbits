import { Reference } from "@ragbits/api-client-react";

type MessageReferencesProps = {
  references: Reference[];
};

const MessageReferences = ({ references }: MessageReferencesProps) => {
  return (
    <div className="text-default-500 text-xs italic">
      <ul className="list-disc pl-4">
        {references.map((reference, index) => (
          <li key={index}>
            <a
              href={reference.url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:underline"
            >
              {reference.title}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default MessageReferences;
