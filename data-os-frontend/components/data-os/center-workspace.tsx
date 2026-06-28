"use client"

import { useCallback, useRef, useState, useEffect } from "react"
import {
  Table as TableIcon,
  BarChart3,
  Play,
  RefreshCw,
  GripHorizontal,
} from "lucide-react"
import { cn } from "@/lib/utils"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

interface LedgerRow {
  [key: string]: string | number | boolean | null
}

export function CenterWorkspace() {
  const [tab, setTab] = useState<"table" | "viz">("table")
  const [ledgerData, setLedgerData] = useState<LedgerRow[]>([])
  
  // THE FIX: Use a safe system query as the default instead of a hardcoded table name
  // This will never crash, even if the database is completely empty.
  const [sqlQuery, setSqlQuery] = useState(`SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' LIMIT 1;`)
  
  const [isLoading, setIsLoading] = useState(false)
  const [topPct, setTopPct] = useState(60)
  const containerRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  const refreshLedger = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql: sqlQuery }),
      })
      const result = await response.json()
      if (result.status === "success") {
        setLedgerData(result.data)
      } else {
        console.error("SQL Error:", result.message)
        setLedgerData([]) // Clear data if query fails
      }
    } catch (error) {
      console.error("Failed to sync database ledger:", error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refreshLedger()
  }, [])

  useEffect(() => {
    const handleAiSql = (e: CustomEvent<string>) => {
      const generatedSql = e.detail
      setSqlQuery(generatedSql) 
      // Small timeout allows state to update before execution
      setTimeout(refreshLedger, 100)
    }

    window.addEventListener("AI_GENERATED_SQL", handleAiSql as EventListener)
    return () => window.removeEventListener("AI_GENERATED_SQL", handleAiSql as EventListener)
  }, [sqlQuery])

  const onMouseDown = useCallback(() => {
    dragging.current = true
    document.body.style.cursor = "row-resize"
    document.body.style.userSelect = "none"
  }, [])

  const onMouseMove = useCallback((e: any) => {
    if (!dragging.current || !containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const pct = ((e.clientY - rect.top) / rect.height) * 100
    setTopPct(Math.min(80, Math.max(20, pct)))
  }, [])

  const stop = useCallback(() => {
    dragging.current = false
    document.body.style.cursor = ""
    document.body.style.userSelect = ""
  }, [])

  // DYNAMIC SCHEMA DETECTION
  const columns = ledgerData.length > 0 ? Object.keys(ledgerData[0]) : []
  
  // Auto-detect columns for the chart
  const numericCol = columns.find(col => typeof ledgerData[0]?.[col] === 'number') || columns[1] || ""
  const labelCol = columns.find(col => typeof ledgerData[0]?.[col] === 'string') || columns[0] || ""
  const maxAmount = ledgerData.length > 0 && numericCol 
    ? Math.max(...ledgerData.map(d => Number(d[numericCol]) || 0), 1) 
    : 1

  return (
    <main
      ref={containerRef}
      onMouseMove={onMouseMove}
      onMouseUp={stop}
      onMouseLeave={stop}
      className="flex min-w-0 flex-1 flex-col bg-card"
    >
      {/* 1. DATA VIEWER PANEL */}
      <div style={{ height: `${topPct}%` }} className="min-h-0 flex flex-col overflow-hidden">
        <div className="flex h-11 shrink-0 items-center justify-between border-b border-border px-3">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setTab("table")}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors",
                tab === "table" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <TableIcon className="h-4 w-4" />
              Data Grid
            </button>
            <button
              onClick={() => setTab("viz")}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors",
                tab === "viz" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <BarChart3 className="h-4 w-4" />
              Auto-Viz
            </button>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {ledgerData.length} records mapped
            </span>
            <button 
              onClick={refreshLedger}
              className={cn("rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground", isLoading && "animate-spin")}
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-auto">
          {tab === "table" ? (
            <div className="min-w-full inline-block align-middle">
              <table className="min-w-full border-collapse text-sm table-auto">
                <thead className="sticky top-0 z-10 bg-[#0e0e0e] shadow-sm">
                  <tr className="bg-card">
                    {columns.map((col, idx) => (
                      <th key={idx} className="border-b border-r border-border px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {ledgerData.length === 0 ? (
                    <tr><td className="p-4 text-muted-foreground text-xs italic text-center">No data found or query returned 0 rows.</td></tr>
                  ) : (
                    ledgerData.map((row, i) => (
                      <tr key={i} className="group hover:bg-accent/50 transition-colors">
                        {columns.map((col, idx) => (
                          <td key={idx} className="border-b border-r border-border px-4 py-2 font-mono text-xs text-foreground/90 whitespace-nowrap max-w-md overflow-hidden text-ellipsis" title={String(row[col])}>
                            {String(row[col])}
                          </td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex h-full flex-col p-6 overflow-hidden">
              <p className="mb-4 text-sm font-medium text-foreground tracking-wide">
                {numericCol ? `Distribution of ${numericCol} by ${labelCol}` : "Not enough numeric data for auto-viz."}
              </p>
              
              <div className="flex flex-1 items-end gap-2 h-64 border-b border-l border-border pb-1 pl-2 relative mt-4">
                {!numericCol && (
                  <p className="text-muted-foreground text-xs absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                    Query must contain at least one numeric column to visualize.
                  </p>
                )}
                
                {numericCol && ledgerData.map((row, i) => (
                  <div key={i} className="group relative flex flex-1 flex-col items-center justify-end h-full">
                    <div
                      className="w-full max-w-[48px] rounded-t bg-emerald-500/80 transition-all duration-500 hover:bg-emerald-400 cursor-crosshair border-t border-x border-emerald-400/50"
                      style={{ 
                        height: `${(Number(row[numericCol]) / maxAmount) * 100}%`, 
                        minHeight: '4px' 
                      }}
                    />
                    <span className="mt-2 text-[9px] text-muted-foreground truncate w-full text-center font-mono">
                      {String(row[labelCol]).substring(0, 6)}..
                    </span>
                    <div className="absolute bottom-full mb-2 hidden group-hover:block bg-[#0e0e0e] text-foreground text-xs px-3 py-2 rounded-md shadow-xl z-50 border border-border whitespace-nowrap">
                      <p className="font-mono text-muted-foreground mb-1">{String(row[labelCol])}</p>
                      <p className="font-bold text-emerald-400">{numericCol}: {row[numericCol]}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 2. RESIZABLE DIVIDER */}
      <div
        onMouseDown={onMouseDown}
        className="group flex h-1.5 shrink-0 cursor-row-resize items-center justify-center border-y border-border bg-background transition-colors hover:bg-primary/20"
      >
        <GripHorizontal className="h-3 w-3 text-muted-foreground group-hover:text-primary" />
      </div>

      {/* 3. DETERMINISTIC SQL CONSOLE */}
      <div style={{ height: `${100 - topPct}%` }} className="min-h-0 flex flex-col overflow-hidden bg-card border-t border-border">
        <div className="flex h-11 shrink-0 items-center justify-between border-b border-border px-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">Universal Database Connection</span>
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-muted-foreground">Ready</span>
          </div>
          <button 
            onClick={refreshLedger} 
            disabled={isLoading}
            className="flex items-center gap-1.5 rounded-md bg-emerald-600/20 text-emerald-500 hover:bg-emerald-600/30 px-3 py-1.5 text-sm font-medium transition-colors border border-emerald-500/20 disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            {isLoading ? "Executing..." : "Run Query"}
          </button>
        </div>
        <div className="flex min-h-0 flex-1 overflow-hidden font-mono text-sm bg-[#0a0a0a]">
          <div className="select-none border-r border-border px-3 py-3 text-right text-xs text-muted-foreground/40 bg-[#0e0e0e]">
            {sqlQuery.split('\n').map((_, i) => <div key={i}>{i + 1}</div>)}
          </div>
          <textarea
            value={sqlQuery}
            onChange={(e) => setSqlQuery(e.target.value)}
            spellCheck="false"
            className="flex-1 px-4 py-3 leading-6 text-emerald-400 bg-transparent focus:outline-none resize-none font-mono whitespace-pre"
          />
        </div>
      </div>
    </main>
  )
}