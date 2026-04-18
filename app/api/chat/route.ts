import { streamText, convertToModelMessages, UIMessage } from "ai";

export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();

  const result = streamText({
    model: "anthropic/claude-sonnet-4-20250514",
    system: `You are JARVIS, an advanced AI assistant designed to help users with all aspects of their life. You are:

- Knowledgeable and helpful across a wide range of topics
- Concise but thorough in your responses
- Friendly and professional in tone
- Proactive in offering solutions and suggestions
- Able to break down complex topics into understandable explanations

When users ask questions, provide clear, actionable answers. If you're unsure about something, be honest about it. Always prioritize being helpful and accurate.`,
    messages: await convertToModelMessages(messages),
    abortSignal: req.signal,
  });

  return result.toUIMessageStreamResponse();
}
