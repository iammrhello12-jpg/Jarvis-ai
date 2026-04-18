"use client";

import { useState, useRef, useEffect } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { cn } from "@/lib/utils";
import { Send, Bot, User, Sparkles, Loader2 } from "lucide-react";

function getMessageText(message: { parts?: Array<{ type: string; text?: string }> }): string {
  if (!message.parts || !Array.isArray(message.parts)) return "";
  return message.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text" && typeof p.text === "string")
    .map((p) => p.text)
    .join("");
}

export function Chat() {
  const [input, setInput] = useState("");
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({ api: "/api/chat" }),
  });

  const isLoading = status === "streaming" || status === "submitted";

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage({ text: input });
    setInput("");
  };

  const handleSuggestion = (suggestion: string) => {
    setInput(suggestion);
  };

  return (
    <div className="flex flex-col h-screen max-h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-[var(--card)]">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--accent)] flex items-center justify-center animate-pulse-glow">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <span className="absolute bottom-0 right-0 w-3 h-3 bg-[var(--accent)] rounded-full border-2 border-[var(--card)]" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[var(--foreground)]">JARVIS AI</h1>
            <p className="text-xs text-[var(--muted-foreground)]">Your Intelligent Assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-[var(--primary)]" />
          <span className="text-sm text-[var(--muted-foreground)]">Powered by AI</span>
        </div>
      </header>

      {/* Messages Container */}
      <main className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--accent)] flex items-center justify-center animate-pulse-glow">
              <Bot className="w-10 h-10 text-white" />
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-bold text-[var(--foreground)]">Welcome to JARVIS AI</h2>
              <p className="text-[var(--muted-foreground)] max-w-md">
                I&apos;m your intelligent assistant, ready to help you with any questions or tasks.
                How can I assist you today?
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
              {[
                "What can you help me with?",
                "Tell me a fun fact",
                "Help me write an email",
                "Explain a complex topic",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleSuggestion(suggestion)}
                  className="px-4 py-3 text-sm text-left rounded-xl border border-[var(--border)] bg-[var(--secondary)] hover:bg-[var(--muted)] hover:border-[var(--primary)] transition-all duration-200"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => {
          const text = getMessageText(message);
          if (!text) return null;

          return (
            <div
              key={message.id}
              className={cn(
                "flex gap-3 max-w-3xl",
                message.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
              )}
            >
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                  message.role === "user"
                    ? "bg-[var(--primary)]"
                    : "bg-gradient-to-br from-[var(--primary)] to-[var(--accent)]"
                )}
              >
                {message.role === "user" ? (
                  <User className="w-4 h-4 text-white" />
                ) : (
                  <Bot className="w-4 h-4 text-white" />
                )}
              </div>
              <div
                className={cn(
                  "px-4 py-3 rounded-2xl max-w-[80%]",
                  message.role === "user"
                    ? "bg-[var(--primary)] text-white rounded-tr-sm"
                    : "bg-[var(--card)] border border-[var(--border)] rounded-tl-sm"
                )}
              >
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{text}</p>
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex gap-3 max-w-3xl mr-auto">
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-gradient-to-br from-[var(--primary)] to-[var(--accent)]">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-[var(--card)] border border-[var(--border)]">
              <div className="typing-indicator flex gap-1">
                <span className="w-2 h-2 bg-[var(--muted-foreground)] rounded-full" />
                <span className="w-2 h-2 bg-[var(--muted-foreground)] rounded-full" />
                <span className="w-2 h-2 bg-[var(--muted-foreground)] rounded-full" />
              </div>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="mx-auto max-w-3xl px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <p>Something went wrong. Please try again.</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <footer className="border-t border-[var(--border)] bg-[var(--card)] px-4 py-4">
        <form onSubmit={handleSubmit} className="flex items-center gap-3 max-w-3xl mx-auto">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1 px-4 py-3 rounded-xl bg-[var(--secondary)] border border-[var(--border)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:border-transparent transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="p-3 rounded-xl bg-[var(--primary)] text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--primary)] focus:ring-offset-2 focus:ring-offset-[var(--card)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </form>
        <p className="text-center text-xs text-[var(--muted-foreground)] mt-3">
          JARVIS AI can make mistakes. Consider checking important information.
        </p>
      </footer>
    </div>
  );
}
