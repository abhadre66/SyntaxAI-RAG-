"use client";
import React, { useState, useRef, useEffect, useMemo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";

interface Message {
  role: string;
  content: string;
  sources?: { url: string; source: string }[];
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const copyToClipboard = async (text: string, idx?: number) => {
    try {
      await navigator.clipboard.writeText(text);
      if (idx !== undefined) {
        setCopiedIdx(idx);
        setTimeout(() => setCopiedIdx(null), 2000);
      }
    } catch (error) {
      console.error("Copy failed", error);
    }
  };

  const markdownComponents = useMemo<Components>(
    () => ({
      pre(props) {
        return <pre className="m-0 overflow-x-auto" {...props} />;
      },
      code(props) {
        const { className, children, ...rest } = props as unknown as {
          className?: string;
          children: React.ReactNode;
        };
        const isBlock = className?.startsWith("language-");
        const text = React.Children.toArray(children).join("");

        if (!isBlock) {
          return (
            <code
              className="rounded-md bg-[#1e293b] px-1.5 py-0.5 text-[13px] text-indigo-300 font-mono"
              {...rest}
            >
              {children}
            </code>
          );
        }

        const lang = className?.replace("language-", "") || "";

        return (
          <div className="group relative my-3 rounded-xl border border-[#1e293b] bg-[#0c1222] overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 border-b border-[#1e293b] bg-[#0f1729]">
              <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
                {lang}
              </span>
              <button
                type="button"
                onClick={() => copyToClipboard(text)}
                className="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] text-slate-400 hover:text-white hover:bg-[#1e293b] transition-all"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
                Copy
              </button>
            </div>
            <div className="p-4 font-mono text-sm leading-6 text-[#e2e8f0] overflow-x-auto">
              <code className={className} {...rest}>
                {children}
              </code>
            </div>
          </div>
        );
      },
    }),
    []
  );

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: "user", content: input };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput("");
    setIsLoading(true);

    try {
      const API_URL =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      const history = updatedMessages.slice(-7, -1).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: input, messages: history }),
      });

      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer || "No response from backend",
          sources: data.sources,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Failed to connect to the server. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
      textareaRef.current?.focus();
    }
  };

  const welcomeCards = [
    { icon: "🐍", label: "Explain decorators", q: "What are decorators in Python and how do I use them?" },
    { icon: "⚡", label: "Async/await guide", q: "How does async/await work in Python?" },
    { icon: "🐛", label: "Debug a TypeError", q: "I'm getting a TypeError: 'NoneType' object is not subscriptable" },
    { icon: "📦", label: "Virtual environments", q: "How do I set up and use virtual environments?" },
  ];

  return (
    <div className="flex h-screen flex-col bg-[#0b0f19] text-[#e2e8f0]">
      {/* Header */}
      <header className="flex items-center justify-center px-4 py-3 border-b border-[#1e293b]">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold">
            S
          </div>
          <span className="text-lg font-semibold tracking-tight">
            Syntax<span className="text-indigo-400">AI</span>
          </span>
        </div>
      </header>

      {/* Messages area */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-4 py-6">
          {/* Welcome screen */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center pt-16 message-appear">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-600 text-2xl font-bold mb-6 shadow-lg shadow-indigo-500/20">
                S
              </div>
              <h1 className="text-3xl font-bold mb-2">
                <span className="gradient-text">SyntaxAI</span>
              </h1>
              <p className="text-slate-400 text-center mb-10 max-w-md">
                Your Python knowledge assistant. Ask me anything about Python — from basics to advanced topics.
              </p>

              <div className="grid grid-cols-2 gap-3 w-full max-w-lg">
                {welcomeCards.map((card, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setInput(card.q);
                      textareaRef.current?.focus();
                    }}
                    className="flex items-center gap-3 rounded-xl border border-[#1e293b] bg-[#111827] p-4 text-left text-sm text-slate-300 hover:border-indigo-500/40 hover:bg-[#1e293b] transition-all duration-200"
                  >
                    <span className="text-lg">{card.icon}</span>
                    <span>{card.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Chat messages */}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`message-appear mb-6 flex gap-3 ${
                msg.role === "user" ? "justify-end" : ""
              }`}
            >
              {msg.role === "assistant" && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 text-xs font-bold shadow-md">
                  S
                </div>
              )}

              <div
                className={`max-w-[85%] ${
                  msg.role === "user" ? "order-first" : ""
                }`}
              >
                <div
                  className={`rounded-2xl px-4 py-3 text-[15px] leading-relaxed ${
                    msg.role === "user"
                      ? "bg-indigo-600 text-white rounded-br-md"
                      : "bg-[#141b2d] border border-[#1e293b] text-[#e2e8f0] rounded-bl-md"
                  }`}
                >
                  {msg.role === "assistant" ? (
                    <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-transparent prose-pre:p-0">
                      <ReactMarkdown components={markdownComponents}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                </div>

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {msg.sources.map((s, idx) => (
                      <a
                        key={idx}
                        href={s.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-lg border border-[#1e293b] bg-[#111827] px-3 py-1.5 text-xs text-slate-400 hover:border-indigo-500/40 hover:text-indigo-300 transition-colors"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                          <polyline points="15 3 21 3 21 9" />
                          <line x1="10" y1="14" x2="21" y2="3" />
                        </svg>
                        {s.source}
                      </a>
                    ))}
                  </div>
                )}

                {/* Copy button for assistant */}
                {msg.role === "assistant" && (
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={() => copyToClipboard(msg.content, i)}
                      className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs text-slate-500 hover:text-slate-300 hover:bg-[#1e293b] transition-colors"
                    >
                      {copiedIdx === i ? (
                        <>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          Copied
                        </>
                      ) : (
                        <>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                          </svg>
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {isLoading && (
            <div className="message-appear mb-6 flex gap-3">
              <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 text-xs font-bold shadow-md">
                S
              </div>
              <div className="rounded-2xl rounded-bl-md bg-[#141b2d] border border-[#1e293b] px-5 py-4">
                <div className="flex gap-1.5">
                  <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
                  <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
                  <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400" />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input area */}
      <footer className="border-t border-[#1e293b] bg-[#0d1117] px-4 py-4">
        <div className="mx-auto flex w-full max-w-3xl items-end gap-3">
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              className="w-full resize-none rounded-xl border border-[#1e293b] bg-[#111827] px-4 py-3 pr-4 text-sm text-[#e2e8f0] placeholder:text-slate-500 outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-colors min-h-[48px] max-h-[200px]"
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about Python..."
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              disabled={isLoading}
            />
          </div>

          <button
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Send message"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <p className="mt-2 text-center text-[11px] text-slate-600">
          SyntaxAI can make mistakes. Verify important information.
        </p>
      </footer>
    </div>
  );
}
