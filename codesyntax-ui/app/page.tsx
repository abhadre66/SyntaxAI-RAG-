

"use client";
import React, { useState, useMemo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";

export default function Home() {
  interface Message {
    role: string;
    content: string;
    sources?: { url: string; source: string }[];
  }

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error("Copy failed", error);
    }
  };

  const markdownComponents = useMemo<Components>(() => ({
    pre(props) {
      return (
        <div className="relative my-3 rounded-xl border border-[#2e4366] bg-[#0d1430] shadow-[0_0_0_1px_rgba(148,163,184,0.15)]">
          <div className="absolute right-2 top-2 z-10 rounded bg-[#1e2a4a] px-2 py-1 text-[11px] text-[#cbd5e1]">Code</div>
          <pre className="m-0 overflow-x-auto rounded-xl p-4 font-mono text-sm leading-6 text-[#dbeafe]" {...props} />
        </div>
      );
    },
    code(props) {
      const { inline, className, children, ...rest } = props as unknown as {
        inline?: boolean;
        className?: string;
        children: React.ReactNode;
      };

      if (inline) {
        return (
          <code className="rounded bg-[#1f2937] px-1 py-[0.1rem] text-xs" {...rest}>
            {children}
          </code>
        );
      }

      const text = React.Children.toArray(children).join("");

      return (
        <div className="relative">
          <button
            type="button"
            onClick={() => copyToClipboard(text)}
            className="absolute right-2 top-2 z-10 rounded bg-[#1f2a54] p-2 text-xs hover:bg-[#304a83]"
            aria-label="Copy code"
          >
            <span aria-hidden="true" className="text-white">📋</span>
          </button>
          <div className="my-2 rounded-xl border border-[#2e4366] bg-[#0d1430] p-4 text-sm font-mono leading-6 text-[#dbeafe] shadow-[0_8px_30px_-15px_rgba(0,0,0,0.65)]">
            <code className={className} {...rest}>
              {children}
            </code>
          </div>
        </div>
      );
    },
  }), []);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: "user", content: input };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setIsLoading(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      // Send last 6 messages as chat history (up to 3 exchanges)
      const history = updatedMessages.slice(-7, -1).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: input, messages: history }),
      });

      const data = await res.json();

      const botMessage = {
        role: "assistant",
        content: data.answer || "No response from backend",
        sources: data.sources,
      };

      setMessages((prev) => [...prev, botMessage]);
      setInput("");
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Failed to fetch response. Please check backend server.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex text-white bg-[#0b0f19]">
      <aside className="hidden md:flex flex-col w-72 p-4 border-r border-gray-800 bg-[#090b10]">
        <button className="w-full text-left rounded-lg bg-[#1f2937] px-3 py-2 text-sm font-medium hover:bg-[#111827] transition">
          + New chat
        </button>
        <div className="mt-4 flex-1 overflow-y-auto space-y-2 text-sm">
          <div className="rounded-lg bg-[#111827] p-3">Example: How do Python lists work?</div>
          <div className="rounded-lg bg-[#111827] p-3">Example: Explain dataclass vs class</div>
        </div>
      </aside>

      <main className="flex-1 flex flex-col">
        <header className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-[#111827]">
          <div className="font-semibold text-lg">CodeSyntax Chat</div>
        </header>

        <section className="flex-1 overflow-y-auto p-4">
          <div className="mx-auto w-full max-w-3xl space-y-4">
            {messages.length === 0 && (
              <div className="rounded-2xl border border-dashed border-gray-700 bg-[#111827] p-6 text-center text-gray-400">
                Start a conversation by typing in the box below.
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className="flex gap-3">
                <div
                  className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold ${
                    msg.role === "assistant" ? "bg-[#10a37f]" : "bg-blue-500"
                  }`}>
                  {msg.role === "assistant" ? "AI" : "YOU"}
                </div>

                <div className="flex-1">
                  <div
                    className={`rounded-2xl p-4 prose max-w-none ${
                      msg.role === "assistant"
                        ? "bg-white text-gray-800 border border-gray-200"
                        : "bg-[#e0f2fe] text-gray-800 border border-blue-200"
                    }`}
                  >
                    <div>
                    <ReactMarkdown
                      components={markdownComponents}
                    >
                      {msg.content}
                    </ReactMarkdown>
                    </div>
                  </div>

                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 border-l-2 border-blue-400 pl-3 text-xs text-blue-200">
                      <p className="text-gray-300">Sources</p>
                      <ul className="space-y-1">
                        {msg.sources.map((s, idx) => (
                          <li key={idx}>
                            <a
                              href={s.url}
                              target="_blank"
                              rel="noreferrer"
                              className="underline"
                            >
                              [{idx + 1}] {s.source}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {msg.role === "assistant" && (
                    <button
                      type="button"
                      onClick={() => copyToClipboard(msg.content)}
                      className="mt-3 rounded-lg border border-gray-600 px-3 py-1 text-xs text-gray-200 hover:bg-gray-700"
                    >
                      Copy answer
                    </button>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3 items-start">
                <div className="h-8 w-8 rounded-full bg-[#10a37f] flex items-center justify-center text-xs font-bold">AI</div>
                <div className="flex-1 rounded-2xl bg-[#343541] p-4 text-gray-300 animate-pulse">AI is typing...</div>
              </div>
            )}
          </div>
        </section>

        <footer className="border-t border-gray-800 bg-[#111827] p-4">
          <div className="mx-auto flex w-full max-w-3xl gap-3">
            <textarea
              className="flex-1 resize-none rounded-xl border border-gray-700 bg-[#0f172a] p-3 text-sm text-white outline-none focus:ring-2 focus:ring-blue-500"
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Send a message. Shift+Enter for newline."
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              disabled={isLoading}
            />

            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="rounded-xl bg-[#10a37f] px-6 py-2 text-sm font-semibold text-white hover:bg-[#0f8b6b] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Sending..." : "Send"}
            </button>
          </div>
        </footer>
      </main>
    </div>
  );
}
