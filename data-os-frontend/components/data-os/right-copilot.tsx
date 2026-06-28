"use client"

import { useState, useEffect, useRef } from "react"
import { Sparkles, ArrowUp, Bot, User, Database, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * OmniData Studio - AI Copilot
 * Context-aware intelligent assistant. Interfaces directly with the OmniData
 * Cognitive Router to execute SQL manipulations or Semantic Vector retrieval.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

interface Message {
  id: number
  role: "user" | "assistant"
  content: string
}

interface TableSchema {
  table_name: string
}

export function RightCopilot() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isThinking, setIsThinking] = useState(false)
  const [dbSchema, setDbSchema] = useState<TableSchema[]>([])
  const [tableGroups, setTableGroups] = useState<Record<string, string[]>>({})
  const [selectedContext, setSelectedContext] = useState<string>("All")
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    // 1. Restore Chat History
    try {
      const savedChat = localStorage.getItem("finos_chat_history")
      if (savedChat) {
        setMessages(JSON.parse(savedChat) as Message[])
      } else {
        setMessages([{ id: 0, role: "assistant", content: "System operational. Connected to Database Cloud. Awaiting your query." }])
      }
    } catch (error) {
      setMessages([{ id: 0, role: "assistant", content: "System operational. Awaiting your query." }])
    }

    // 2. Hydrate Groups
    const loadGroups = () => {
      const savedGroups = localStorage.getItem("finos_table_groups")
      if (savedGroups) setTableGroups(JSON.parse(savedGroups))
    }
    loadGroups()

    // 3. Introspect Schema
    const fetchSchema = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/schema`)
        const result = await response.json()
        if (result.status === "success") setDbSchema(result.schema)
      } catch (e) {
        console.error("Failed to load schema for Copilot", e)
      }
    }
    fetchSchema()
    
    // 4. Attach Event Listeners
    window.addEventListener("REFRESH_SCHEMA", fetchSchema)
    window.addEventListener("GROUPS_UPDATED", loadGroups) 
    return () => {
      window.removeEventListener("REFRESH_SCHEMA", fetchSchema)
      window.removeEventListener("GROUPS_UPDATED", loadGroups)
    }
  }, [])

  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem("finos_chat_history", JSON.stringify(messages))
    }
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Dynamic Textarea Auto-Resize Logic
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }, [input])

  const clearChat = () => {
    const initMessage: Message[] = [{ id: 0, role: "assistant", content: "System operational. Connected to Database Cloud. Awaiting your query." }]
    setMessages(initMessage)
    localStorage.setItem("finos_chat_history", JSON.stringify(initMessage))
  }

  const send = async () => {
    const text = input.trim()
    if (!text || isThinking) return

    const userMessageId = Date.now()
    setMessages((m) => [...m, { id: userMessageId, role: "user", content: text }])
    setInput("")
    setIsThinking(true)

    const aiPlaceholderId = userMessageId + 1
    setMessages((m) => [...m, { id: aiPlaceholderId, role: "assistant", content: "Analyzing intent & routing..." }])

    // INVISIBLE PROMPT CONTEXT BUILDING
    let contextInstruction = ""
    if (selectedContext.startsWith("GROUP_")) {
      const groupName = selectedContext.replace("GROUP_", "")
      const tablesInGroup = tableGroups[groupName] || []
      contextInstruction = `[CRITICAL INSTRUCTION: Focus STRICTLY on the tables inside the '${groupName}' domain: ${tablesInGroup.join(", ")}. Ignore other tables.] `
    } else if (selectedContext !== "All") {
      contextInstruction = `[CRITICAL INSTRUCTION: Focus STRICTLY on the '${selectedContext}' table for this query. Ignore other tables.] `
    }

    const contextualizedQuery = `${contextInstruction}${text}`

    // SMART MEMORY EXTRACTION
    // Maps the current chat state into a clean array for the backend
    const historyPayload = messages.map(msg => ({
      role: msg.role === "assistant" ? "assistant" : "user",
      content: msg.content
    }))

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          query: contextualizedQuery,
          history: historyPayload 
        }),
      })

      const data = await response.json()

      if (data.status === "success") {
        const routeBadge = data.route?.includes("SQL") 
          ? "[Routed to SQL Engine]" 
          : "[Routed to Semantic Vector]";

        let cleanResponse = data.response;

        // SMART UI INTERCEPTOR
        if (data.sql) {
          // 1. Dispatch SQL silently to the data grid editor
          window.dispatchEvent(new CustomEvent("AI_GENERATED_SQL", { detail: data.sql }))
          
          // 2. Regex to find and completely scrub markdown code blocks from the chat
          const sqlBlockRegex = /```(?:sql)?\n[\s\S]*?```/gi;
          cleanResponse = cleanResponse.replace(sqlBlockRegex, "").trim();

          // 3. Fallback if the AI only replied with a code block
          if (!cleanResponse) {
             cleanResponse = "Analysis complete.";
          }

          // 4. Append professional completion notification
          cleanResponse += "\n\n*Query dynamically generated and routed to the execution environment.*";

          // Check for DDL statements to refresh schema
          const upperSql = data.sql.toUpperCase()
          if (upperSql.includes("CREATE") || upperSql.includes("DROP") || upperSql.includes("ALTER") || upperSql.includes("RENAME")) {
            setTimeout(() => window.dispatchEvent(new CustomEvent("REFRESH_SCHEMA")), 1000)
          }
        }

        setMessages((m) => m.map((msg) => msg.id === aiPlaceholderId ? { ...msg, content: `${routeBadge}\n\n${cleanResponse}` } : msg))
      } else {
        setMessages((m) => m.map((msg) => msg.id === aiPlaceholderId ? { ...msg, content: `Error: ${data.response}` } : msg))
      }
    } catch (err) {
      setMessages((m) => m.map((msg) => msg.id === aiPlaceholderId ? { ...msg, content: "CRITICAL ERROR: API Gateway unreachable. Ensure backend is running." } : msg))
    } finally {
      setIsThinking(false)
    }
  }

  // Calculate grouped tables for context dropdown
  const groupedTableNames = Object.values(tableGroups).flat()
  const ungroupedTables = dbSchema.filter(t => !groupedTableNames.includes(t.table_name))

  return (
    <aside className="flex w-80 shrink-0 flex-col border-l border-border bg-sidebar">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold tracking-tight text-foreground">AI Copilot</span>
        </div>
        <button onClick={clearChat} title="Clear Chat History" className="text-muted-foreground hover:text-destructive transition-colors">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="shrink-0 border-b border-border px-4 py-3 bg-[#0a0a0a]">
        <div className="flex items-center justify-between mb-2">
          <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Target Context</p>
        </div>
        <div className="flex items-center gap-2">
          <Database className="h-3.5 w-3.5 text-emerald-500" />
          <select value={selectedContext} onChange={(e) => setSelectedContext(e.target.value)} className="w-full bg-background border border-border text-xs rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:border-primary transition-colors cursor-pointer">
            <option value="All">All Tables (Global Search)</option>
            
            {Object.entries(tableGroups).map(([groupName, tables]) => (
              <optgroup key={groupName} label={`[Group] ${groupName}`}>
                <option value={`GROUP_${groupName}`}>-- Entire {groupName} Group --</option>
                {tables.map(t => <option key={t} value={t}>{t}</option>)}
              </optgroup>
            ))}

            {ungroupedTables.length > 0 && (
              <optgroup label="[Ungrouped Tables]">
                {ungroupedTables.map((table, idx) => <option key={idx} value={table.table_name}>{table.table_name}</option>)}
              </optgroup>
            )}
          </select>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.map((m) => (
          <div key={m.id} className={cn("flex gap-2.5", m.role === "user" ? "flex-row-reverse" : "flex-row")}>
            <div className={cn("flex h-6 w-6 shrink-0 items-center justify-center rounded-md border", m.role === "user" ? "border-border bg-accent" : "border-primary/30 bg-primary/10")}>
              {m.role === "user" ? <User className="h-3.5 w-3.5 text-muted-foreground" /> : <Bot className="h-3.5 w-3.5 text-primary" />}
            </div>
            <div className={cn("max-w-[85%] rounded-lg border px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap overflow-x-auto", m.role === "user" ? "border-border bg-accent text-foreground" : "border-border bg-card text-foreground/90")}>
              {m.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="shrink-0 border-t border-border p-3">
        <div className="flex items-end gap-2 rounded-lg border border-border bg-input p-2 focus-within:border-primary/50">
          <textarea 
            ref={textareaRef}
            value={input} 
            onChange={(e) => setInput(e.target.value)} 
            onKeyDown={(e) => { 
              if (e.key === "Enter" && !e.shiftKey) { 
                e.preventDefault(); 
                send(); 
              } 
            }} 
            disabled={isThinking} 
            placeholder={isThinking ? "Processing pipeline..." : "Ask about your data..."} 
            className="flex-1 resize-none bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50 overflow-y-auto py-1" 
          />
          <button onClick={send} disabled={!input.trim() || isThinking} className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-40">
            <ArrowUp className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}