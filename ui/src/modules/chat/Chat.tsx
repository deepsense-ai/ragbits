import { useState } from "react";
import { Textarea } from "@heroui/input";
import { Button } from "@heroui/react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "github-markdown-css/github-markdown-light.css";

export default function Chat() {
  const [messages, setMessages] = useState<{ content: string; type: string }[]>(
    [],
  );
  const [message, setMessage] = useState("");

  const handleSendMessage = () => {
    setMessages((state) => [
      ...state,
      { content: message, type: "user" },
      {
        content: `
Below is an **overview and rough comparison** of estimated 2023 GDP per capita (nominal) for some of Europe's highest-income countries. Exact figures may vary by source (e.g., IMF, World Bank, OECD) and can be revised over time. The numbers below are rounded to give a general sense of scale. All figures are in **U.S. dollars (USD)**.

| **Rank** | **Country**    | **Estimated 2023 GDP per Capita (USD)** | **Key Notes**                                                         |
|----------|----------------|------------------------------------------|-----------------------------------------------------------------------|
| 1        | **Luxembourg** | $120,000 – $135,000                    | Small population, large financial sector; very high GDP per capita.   |
| 2        | **Ireland**    | $90,000 – $110,000                     | Figures can be influenced by multinational corporate tax strategies.  |
| 3        | **Switzerland**| $85,000 – $90,000                      | Known for banking, finance, high-value manufacturing.                 |
| 4        | **Norway**     | $80,000 – $85,000                      | Wealth bolstered by oil/gas sector and strong social programs.        |
| 5        | **Denmark**    | $65,000 – $70,000                      | Diverse, high-income economy with strong welfare system.              |
| 6        | **Iceland**    | $60,000 – $70,000                      | Small population, focus on services, tourism, and fishing.            |
| 7        | **Netherlands**| $55,000 – $60,000                      | Major trading nation with robust logistics and service sectors.       |
| 8        | **Sweden**     | $55,000 – $60,000                      | Innovative economy with strong industrial and tech presence.          |
| 9        | **Germany**    | $50,000 – $55,000                      | Europe's largest overall economy, strong manufacturing base.          |
| 10       | **Austria**    | $50,000 – $55,000                      | Balanced economy with tourism, manufacturing, and services.           |

### Important Context

1. **Nominal GDP vs. Purchasing Power Parity (PPP)**  
   - The figures shown are typically nominal GDP per capita in USD, reflecting market exchange rates.  
   - PPP-adjusted GDP per capita can look different, especially for countries where cost of living and local price levels vary significantly.

2. **Small Countries, High Financial Activity**  
   - Places like **Luxembourg** and (to some extent) **Ireland** have high nominal GDP per capita figures partly because of large financial sectors and multinational corporate registrations relative to their small populations.

3. **Data Sources & Variations**  
   - The **IMF**, **World Bank**, **OECD**, and other institutions each publish GDP estimates. Numbers can shift based on revisions, new data, or different methodologies.

4. **2023 Figures Are Projections**  
   - Because official year-end data for 2023 is not typically available until well into the following year (2024), most current-year numbers are forecasts or early estimates.

---

#### Key Takeaways

- **Luxembourg** usually tops the list for highest GDP per capita in Europe.  
- **Ireland**'s figure can appear unusually high due to foreign direct investment and the way multinational profits are booked there.  
- **Switzerland**, **Norway**, and the **Nordic countries** consistently rank among the top, reflecting high levels of productivity, resource wealth (in Norway's case), and strong social models.  
- **Germany** has the largest overall GDP in Europe, but per-capita values are somewhat lower than the smaller, wealthier states.

Use this table as a reference point for a **broad comparison**—for the most accurate and up-to-date data, always consult the latest releases from major statistical agencies or international financial institutions.
        `,
        type: "system",
      },
    ]);
    setMessage("");
  };

  return (
    <>
      <div className="relative flex-1 overflow-hidden">
        <div className="scrollbar scrollbar-w-2 scrollbar-thumb-gray-700 scrollbar-track-transparent hover:scrollbar-thumb-gray-600 h-[100dvh] overflow-y-scroll px-8 pb-[164px]">
          <div className="flex flex-col gap-4 pt-8">
            {messages.map((message) => {
              if (message.type === "user") {
                return (
                  <div className="leading-1.5 ml-auto mr-0 w-auto max-w-4xl rounded-xl rounded-tr-none bg-primary p-4 text-left text-white">
                    {message.content}
                  </div>
                );
              }

              if (message.type === "system") {
                return (
                  <div className="w-full max-w-4xl">
                    <Markdown
                      className="prose max-w-full"
                      remarkPlugins={[remarkGfm]}
                    >
                      {message.content}
                    </Markdown>
                  </div>
                );
              }

              return <span>unknown type of message</span>;
            })}
          </div>
        </div>
      </div>
      <div className="absolute bottom-0 ml-0 flex h-[164px] w-[calc(100%-12px)] items-end justify-end gap-4 border-t-1 bg-light pb-8 pl-8 pr-8">
        <Textarea
          isClearable
          label="Message"
          placeholder="Type message..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onClear={() => setMessage("")}
        />
        <Button color="primary" onPress={handleSendMessage}>
          Send
        </Button>
      </div>
    </>
  );
}
