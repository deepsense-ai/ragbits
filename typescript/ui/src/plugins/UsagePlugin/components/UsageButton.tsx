import {
  Button,
  getKeyValue,
  Modal,
  ModalBody,
  ModalContent,
  ModalHeader,
  Table,
  TableBody,
  TableCell,
  TableColumn,
  TableHeader,
  TableRow,
  useDisclosure,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import DelayedTooltip from "../../../core/components/DelayedTooltip";
import { ChatMessage } from "../../../core/types/history";
import { MessageUsage } from "@ragbits/api-client-react";
import { upperFirst, words } from "lodash";

interface UsageButtonProps {
  usage: Exclude<ChatMessage["usage"], undefined>;
}

type TableData = MessageUsage & { model: string };

const COLUMN_OVERRIDES: Partial<Record<keyof TableData, string>> = {
  n_requests: "Number Of Requests",
  estimated_cost: "Estimated Cost ($)",
};
const PREFERRED_ORDER: (keyof TableData)[] = [
  "model",
  "n_requests",
  "prompt_tokens",
  "completion_tokens",
  "total_tokens",
  "estimated_cost",
];

function toFormattedNumber(numStr: string) {
  return numStr.replace(
    /(-?)(\d*)\.?(\d*)e([+-]\d+)/,
    function (_, sign, integerPart, fractionPart, exponent) {
      return exponent < 0
        ? sign +
            "0." +
            Array(1 - exponent - integerPart.length).join("0") +
            fractionPart +
            integerPart
        : sign +
            integerPart +
            fractionPart +
            Array(exponent - fractionPart.length + 1).join("0");
    },
  );
}

export default function UsageButton({ usage }: UsageButtonProps) {
  const models = Object.keys(usage);
  const { isOpen, onOpen, onClose } = useDisclosure();

  const onOpenChange = () => {
    onClose();
  };

  const properties = Object.keys(usage[models[0]]) as (keyof MessageUsage)[];
  const orderedProperties = [
    ...PREFERRED_ORDER.filter(
      (key) => key === "model" || properties.includes(key),
    ),
    ...properties.filter((key) => !PREFERRED_ORDER.includes(key)),
  ];
  const initialStats = properties.reduce<MessageUsage>(
    (acc, prop) => ({ ...acc, [prop]: 0 }),
    {} as MessageUsage,
  );
  const totalStats = models.reduce<MessageUsage>((acc, model) => {
    orderedProperties.reduce((internalAcc, prop) => {
      if (prop === "model") {
        return internalAcc;
      }

      internalAcc[prop] += usage[model][prop];
      return internalAcc;
    }, acc);
    return acc;
  }, initialStats);

  const columns = [
    ...orderedProperties.map((column) => ({
      key: column,
      label:
        COLUMN_OVERRIDES[column] ?? words(column).map(upperFirst).join(" "),
    })),
  ];
  const rows: TableData[] = [
    ...models.map((model) => ({
      model,
      ...usage[model],
    })),
    {
      model: "Total",
      ...totalStats,
    },
  ];

  const tooltip = (
    <div className="p-2">
      <div className="flex flex-col gap-2">
        {totalStats.prompt_tokens !== undefined && (
          <div className="flex justify-between gap-2">
            <span className="font-semibold">Prompt tokens</span>
            <span>{totalStats.prompt_tokens}</span>
          </div>
        )}

        {totalStats.completion_tokens !== undefined && (
          <div className="flex justify-between gap-2">
            <span className="font-semibold">Completion tokens</span>
            <span>{totalStats.completion_tokens}</span>
          </div>
        )}

        {totalStats.total_tokens !== undefined && (
          <div className="flex justify-between gap-2">
            <span className="font-semibold">Total tokens</span>
            <span>{totalStats.total_tokens}</span>
          </div>
        )}

        {totalStats.estimated_cost !== undefined && (
          <div className="flex justify-between gap-2">
            <span className="font-semibold">Estimated cost</span>
            <span>
              {toFormattedNumber(totalStats.estimated_cost.toString())}$
            </span>
          </div>
        )}
      </div>
      <p className="m-auto mt-2 text-center">
        Show detailed usage breakdown by model.
      </p>
    </div>
  );

  return (
    <>
      <DelayedTooltip content={tooltip} placement="bottom">
        <Button
          isIconOnly
          variant="ghost"
          className="p-0"
          aria-label="Open usage details"
          onPress={onOpen}
        >
          <Icon icon="heroicons:information-circle" />
        </Button>
      </DelayedTooltip>

      <Modal isOpen={isOpen} onOpenChange={onOpenChange} size="4xl">
        <ModalContent>
          <>
            <ModalHeader className="text-default-900 flex flex-col gap-1">
              Usage details
            </ModalHeader>
            <ModalBody>
              <Table
                aria-label="Table with detailed usage statistics for each model used to generate the message."
                fullWidth
              >
                <TableHeader columns={columns}>
                  {(column) => (
                    <TableColumn key={column.key}>{column.label}</TableColumn>
                  )}
                </TableHeader>
                <TableBody items={rows}>
                  {(item) => (
                    <TableRow
                      key={item.model}
                      className={
                        item.model === "Total"
                          ? "border-default-200 border-t-1"
                          : ""
                      }
                    >
                      {(columnKey) => (
                        <TableCell>{getKeyValue(item, columnKey)}</TableCell>
                      )}
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </ModalBody>
          </>
        </ModalContent>
      </Modal>
    </>
  );
}
