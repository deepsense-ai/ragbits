import { ChatMessageProps } from "./core/components/ChatMessage";

const exampleConversation: ChatMessageProps[] = [
  {
    message:
      "I'm writing an out-of-office message and need your help. Here's what I want to say: I'm out from 2024-5-24 to 2024-5-29, contact my colleague for questions, and I will check email when I'm back.",
    name: "You",
    isRTL: true,
  },
  {
    message:
      "Here's an out-of-office message based on what you provided: \n\n Subject: Out of Office - [Your Name]\n\n Thank you for your email. I am currently out of the office from Friday, May 24th, 2024 to Wednesday, May 29th, 2024. For urgent inquiries during this time, please contact my colleague, [Colleague Name], at [Colleague Email Address]. I will check my emails upon my return and respond to them as soon as possible.\n\n Thank you for your understanding.",
    name: "Ragbits",
  },
  {
    message: "Thank you!",
    name: "You",
    isRTL: true,
  },
];

export default exampleConversation;
