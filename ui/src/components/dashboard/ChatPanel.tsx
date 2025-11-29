import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage } from "@/types/article";
import { Send, Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

interface ChatPanelProps {
  articleId: string;
}

export const ChatPanel = ({ articleId }: ChatPanelProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Fetch chat history when article changes
    const fetchMessages = async () => {
      try {
        const response = await apiFetch(`/articles/${articleId}/chat/`);

        if (response.ok) {
          const data = await response.json();
          setMessages(data);
        } else {
          // Mock initial message
          setMessages([
            {
              id: "1",
              role: "assistant",
              content: "Hi! I'm the FTL Bot. Ask me anything about this article and I'll help you understand it better.",
              timestamp: Date.now()
            }
          ]);
        }
      } catch (error) {
        // Mock initial message
        setMessages([
          {
            id: "1",
            role: "assistant",
            content: "Hi! I'm the FTL Bot. Ask me anything about this article and I'll help you understand it better.",
            timestamp: Date.now()
          }
        ]);
      }
    };

    fetchMessages();
  }, [articleId]);

  useEffect(() => {
    // Auto-scroll to bottom
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await apiFetch(`/articles/${articleId}/chat/send`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: input })
      });

      if (response.ok) {
        const data = await response.json();
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: data.response,
          timestamp: Date.now()
        }]);
      } else {
        throw new Error("Failed to send message");
      }
    } catch (error) {
      // Mock response
      setTimeout(() => {
        const mockResponse: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "That's an interesting question about the article. Based on the content, I can provide some insights...",
          timestamp: Date.now()
        };
        setMessages(prev => [...prev, mockResponse]);
        setIsLoading(false);
      }, 1000);
      return;
    }

    setIsLoading(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <Bot className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">FTL Bot</h3>
            <p className="text-xs text-muted-foreground">Ask me about this article</p>
          </div>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex gap-3",
                message.role === "user" && "flex-row-reverse"
              )}
            >
              <div className={cn(
                "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
                message.role === "assistant" ? "bg-primary/10" : "bg-secondary"
              )}>
                {message.role === "assistant" ? (
                  <Bot className="w-5 h-5 text-primary" />
                ) : (
                  <User className="w-5 h-5 text-secondary-foreground" />
                )}
              </div>
              <div
                className={cn(
                  "rounded-lg px-4 py-2 max-w-[80%]",
                  message.role === "assistant"
                    ? "bg-muted"
                    : "bg-primary text-primary-foreground"
                )}
              >
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {message.content}
                </p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Bot className="w-5 h-5 text-primary animate-pulse" />
              </div>
              <div className="bg-muted rounded-lg px-4 py-2">
                <p className="text-sm text-muted-foreground">Thinking...</p>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question..."
            disabled={isLoading}
          />
          <Button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            size="icon"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};
