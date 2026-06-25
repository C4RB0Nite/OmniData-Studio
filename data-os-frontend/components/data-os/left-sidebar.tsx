"use client"

import { useState, useRef, useEffect } from "react"
import { Table2, Upload, CheckCircle2, Loader2, MoreVertical, Search, ChevronDown, Check, Folder, FolderPlus, Clock } from "lucide-react"
import { cn } from "@/lib/utils"

/**
 * OmniData Studio - Sidebar Navigator
 * Handles database schema introspection, user-defined table groups, and the multi-modal 
 * file upload pipeline. Communicates state to the Copilot via local storage and Event Bus.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"

interface TableSchema {
  table_name: string
}

interface QueryRecord {
  sql: string
  time: string
}

export function LeftSidebar() {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)
  const [dbSchema, setDbSchema] = useState<TableSchema[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [isSchemaDropdownOpen, setIsSchemaDropdownOpen] = useState(false)
  
  const [tableGroups, setTableGroups] = useState<Record<string, string[]>>({})
  const [queryHistory, setQueryHistory] = useState<QueryRecord[]>([])
  const [activeTab, setActiveTab] = useState<"tables" | "queries">("tables")

  const [menuOpenFor, setMenuOpenFor] = useState<string | null>(null)
  const [isCreatingGroupFor, setIsCreatingGroupFor] = useState<string | null>(null)
  const [newGroupName, setNewGroupName] = useState("")
  const [isAddingGlobalGroup, setIsAddingGlobalGroup] = useState(false)
  const [globalGroupName, setGlobalGroupName] = useState("")

  const fileInputRef = useRef<HTMLInputElement>(null)
  const systemSchemas = ["auth", "extensions", "public", "storage"]

  useEffect(() => {
    const savedGroups = localStorage.getItem("finos_table_groups")
    if (savedGroups) setTableGroups(JSON.parse(savedGroups))

    const savedHistory = localStorage.getItem("finos_query_history")
    if (savedHistory) setQueryHistory(JSON.parse(savedHistory))

    const fetchSchema = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/schema`)
        const result = await response.json()
        if (result.status === "success") setDbSchema(result.schema)
      } catch (e) {
        console.error("Failed to load schema tree", e)
      }
    }
    
    fetchSchema()
    
    const handleNewQuery = (e: CustomEvent<string>) => {
      const sql = e.detail
      setQueryHistory(prev => {
        const newHistory = [{ sql, time: new Date().toLocaleTimeString() }, ...prev].slice(0, 50)
        localStorage.setItem("finos_query_history", JSON.stringify(newHistory))
        return newHistory
      })
    }

    window.addEventListener("REFRESH_SCHEMA", fetchSchema)
    window.addEventListener("AI_GENERATED_SQL", handleNewQuery as EventListener)
    return () => {
      window.removeEventListener("REFRESH_SCHEMA", fetchSchema)
      window.removeEventListener("AI_GENERATED_SQL", handleNewQuery as EventListener)
    }
  }, [])

  const saveGroups = (newGroups: Record<string, string[]>) => {
    setTableGroups(newGroups)
    localStorage.setItem("finos_table_groups", JSON.stringify(newGroups))
    window.dispatchEvent(new CustomEvent("GROUPS_UPDATED"))
  }

  const handleCreateGlobalGroup = () => {
    if (globalGroupName.trim() && !tableGroups[globalGroupName.trim()]) {
      saveGroups({ ...tableGroups, [globalGroupName.trim()]: [] })
    }
    setIsAddingGlobalGroup(false)
    setGlobalGroupName("")
  }

  const assignTableToGroup = (tableName: string, targetGroup: string) => {
    const newGroups = { ...tableGroups }
    Object.keys(newGroups).forEach(g => {
      newGroups[g] = newGroups[g].filter(t => t !== tableName)
    })
    if (!newGroups[targetGroup]) newGroups[targetGroup] = []
    newGroups[targetGroup].push(tableName)

    saveGroups(newGroups)
    setMenuOpenFor(null)
    setIsCreatingGroupFor(null)
    setNewGroupName("")
  }

  const removeTableFromGroups = (tableName: string) => {
    const newGroups = { ...tableGroups }
    Object.keys(newGroups).forEach(g => {
      newGroups[g] = newGroups[g].filter(t => t !== tableName)
    })
    saveGroups(newGroups)
    setMenuOpenFor(null)
  }

  const handleCreateGroupForTable = (tableName: string) => {
    if (newGroupName.trim()) {
      assignTableToGroup(tableName, newGroupName.trim())
    }
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    setIsUploading(true)
    setUploadStatus(`Ingesting...`)

    try {
        for (let i = 0; i < files.length; i++) {
          const formData = new FormData()
          formData.append("file", files[i])
          
          const response = await fetch(`${API_BASE}/api/upload`, { 
              method: "POST", 
              body: formData 
          })
          
          if (!response.ok) throw new Error("Upload processing failed")
        }
        setUploadStatus("Complete!")
    } catch (error) {
        console.error("Upload error:", error)
        setUploadStatus("Error uploading file")
    } finally {
        setIsUploading(false)
        if (fileInputRef.current) fileInputRef.current.value = ""
        setTimeout(() => setUploadStatus(null), 3000)
        window.dispatchEvent(new CustomEvent("REFRESH_SCHEMA"))
    }
  }

  const filteredSchema = dbSchema.filter(table => table.table_name.toLowerCase().includes(searchQuery.toLowerCase()))
  const groupedTableNames = Object.values(tableGroups).flat()
  const ungroupedTables = filteredSchema.filter(t => !groupedTableNames.includes(t.table_name))

  const renderTableRow = (tableName: string) => (
    <div key={tableName} className="relative flex w-full items-center justify-between rounded-md px-2 py-1 text-muted-foreground hover:bg-[#2a2a2a] hover:text-foreground group cursor-pointer">
      <button onClick={() => window.dispatchEvent(new CustomEvent("AI_GENERATED_SQL", { detail: `SELECT *\nFROM "${tableName}"\nLIMIT 50;` }))} className="flex flex-1 items-center gap-2 text-left">
        <Table2 className="h-3.5 w-3.5" /> <span className="truncate text-[12px] font-mono">{tableName}</span>
      </button>
      
      <button 
        onClick={() => setMenuOpenFor(menuOpenFor === tableName ? null : tableName)} 
        className={cn("p-1 transition-opacity", menuOpenFor === tableName ? "opacity-100 text-emerald-400" : "opacity-0 group-hover:opacity-100 hover:text-emerald-400")}
      >
        <MoreVertical className="h-3.5 w-3.5" />
      </button>

      {menuOpenFor === tableName && (
        <div className="absolute right-6 top-6 w-52 bg-[#1c1c1c] border border-[#3e3e3e] rounded-md shadow-2xl z-50 p-1 flex flex-col gap-0.5">
          <div className="px-2 py-1 text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Actions</div>
          
          {Object.keys(tableGroups).length > 0 && (
            <div className="mb-1 border-b border-[#3e3e3e] pb-1 flex flex-col gap-0.5">
              {Object.keys(tableGroups).map(g => (
                <button key={g} onClick={() => assignTableToGroup(tableName, g)} className="w-full text-left px-2 py-1.5 text-xs text-foreground hover:bg-[#2a2a2a] rounded">
                  Move to {g}
                </button>
              ))}
            </div>
          )}

          {isCreatingGroupFor === tableName ? (
            <div className="flex items-center px-1 py-1 gap-1">
              <input autoFocus type="text" value={newGroupName} onChange={e => setNewGroupName(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') handleCreateGroupForTable(tableName) }} placeholder="Group name..." className="w-full bg-[#0a0a0a] border border-[#3e3e3e] text-xs px-2 py-1.5 rounded text-foreground outline-none focus:border-primary" />
              <button onClick={() => handleCreateGroupForTable(tableName)} className="text-emerald-400 hover:text-emerald-300 p-1 bg-[#2a2a2a] rounded border border-[#3e3e3e]"><Check className="h-3 w-3"/></button>
            </div>
          ) : (
            <button onClick={() => setIsCreatingGroupFor(tableName)} className="w-full text-left px-2 py-1.5 text-xs text-emerald-400 hover:bg-[#2a2a2a] rounded">
              + Create New Group
            </button>
          )}

          <button onClick={() => removeTableFromGroups(tableName)} className="w-full text-left px-2 py-1.5 text-xs text-muted-foreground hover:bg-[#2a2a2a] rounded mt-1">
            Remove from group
          </button>
          <button onClick={() => { window.dispatchEvent(new CustomEvent("AI_GENERATED_SQL", { detail: `DROP TABLE "${tableName}";` })); setMenuOpenFor(null); }} className="w-full text-left px-2 py-1.5 text-xs text-destructive hover:bg-[#2a2a2a] rounded">
            Drop Table
          </button>
        </div>
      )}
    </div>
  )

  return (
    <div className="flex h-full flex-col bg-[#1c1c1c] border-r border-border text-sm select-none w-64" onClick={(e) => {
      if (!(e.target as HTMLElement).closest('.group')) setMenuOpenFor(null)
    }}>
      <div className="flex h-14 shrink-0 items-center justify-center border-b border-[#3e3e3e] bg-[#1c1c1c] px-2 gap-1">
        <button onClick={() => setActiveTab("tables")} className={cn("flex-1 py-1.5 rounded-md text-center text-xs font-semibold transition-colors", activeTab === "tables" ? "bg-[#2a2a2a] text-foreground border border-[#3e3e3e]" : "text-muted-foreground hover:text-foreground")}>Tables</button>
        <button onClick={() => setActiveTab("queries")} className={cn("flex-1 py-1.5 rounded-md text-center text-xs font-semibold transition-colors", activeTab === "queries" ? "bg-[#2a2a2a] text-foreground border border-[#3e3e3e]" : "text-muted-foreground hover:text-foreground")}>History</button>
      </div>

      {activeTab === "tables" ? (
        <div className="flex-1 overflow-y-auto py-4 px-3 space-y-4">
          <div className="relative">
            <button onClick={() => setIsSchemaDropdownOpen(!isSchemaDropdownOpen)} className="flex w-full items-center justify-between rounded-md bg-[#2a2a2a] border border-[#3e3e3e] px-3 py-2 text-foreground hover:bg-[#333333] transition-colors">
              <span className="text-xs font-mono text-muted-foreground">schema <span className="text-foreground font-semibold">public</span></span>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </button>
            {isSchemaDropdownOpen && (
              <div className="absolute top-full left-0 mt-1 w-full bg-[#1c1c1c] border border-[#3e3e3e] rounded-md shadow-xl z-50 py-1 max-h-48 overflow-y-auto">
                {systemSchemas.map(s => (
                  <button key={s} onClick={() => setIsSchemaDropdownOpen(false)} className="flex w-full items-center justify-between px-3 py-1.5 text-xs text-muted-foreground hover:bg-[#2a2a2a] hover:text-foreground">
                    <span>{s}</span>{s === 'public' && <Check className="h-3.5 w-3.5 text-emerald-500" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 bg-[#2a2a2a] border border-[#3e3e3e] rounded-md px-3 py-1.5 focus-within:border-primary">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input type="text" placeholder="Search tables..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="bg-transparent border-none outline-none text-sm text-foreground w-full placeholder:text-muted-foreground" />
          </div>
          
          <div className="pt-2">
            {isAddingGlobalGroup ? (
              <div className="flex items-center gap-2 mb-3 px-1">
                <input autoFocus type="text" value={globalGroupName} onChange={e => setGlobalGroupName(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') handleCreateGlobalGroup() }} onBlur={() => { if(!globalGroupName) setIsAddingGlobalGroup(false) }} placeholder="New group name..." className="w-full bg-[#0a0a0a] border border-[#3e3e3e] text-xs px-2 py-1.5 rounded text-foreground outline-none focus:border-primary" />
                <button onClick={handleCreateGlobalGroup} className="text-emerald-400 hover:text-emerald-300 p-1 bg-[#2a2a2a] rounded border border-[#3e3e3e]"><Check className="h-3 w-3"/></button>
              </div>
            ) : (
              <button onClick={() => setIsAddingGlobalGroup(true)} className="flex items-center gap-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors mb-3 px-1">
                <FolderPlus className="h-3.5 w-3.5" /> + New Group
              </button>
            )}

            {Object.entries(tableGroups).map(([groupName, tables]) => (
              <div key={groupName} className="mb-4">
                <div className="flex items-center gap-2 mb-1 px-1">
                  <Folder className="h-3.5 w-3.5 text-blue-400" />
                  <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{groupName}</span>
                </div>
                <div className="border-l border-[#3e3e3e] ml-2 pl-2 space-y-0.5">
                  {tables.length === 0 && <span className="text-[10px] text-muted-foreground/50 italic ml-2">Empty group</span>}
                  {tables.map(t => renderTableRow(t))}
                </div>
              </div>
            ))}

            <div className="mb-4">
              <div className="flex items-center gap-2 mb-1 px-1">
                <Folder className="h-3.5 w-3.5 text-zinc-500" />
                <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">ALL</span>
              </div>
              <div className="border-l border-[#3e3e3e] ml-2 pl-2 space-y-0.5">
                {ungroupedTables.map((table) => renderTableRow(table.table_name))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto py-4 px-3">
           <div className="flex items-center justify-between px-1 mb-3">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Recent Queries</span>
              <button onClick={() => {setQueryHistory([]); localStorage.removeItem("finos_query_history")}} className="text-[10px] text-destructive hover:underline">Clear All</button>
           </div>
           <div className="space-y-2">
             {queryHistory.length === 0 && <div className="text-xs text-muted-foreground text-center mt-10">No queries run yet.</div>}
             {queryHistory.map((q, i) => (
               <div key={i} className="bg-[#2a2a2a] border border-[#3e3e3e] rounded-md p-2 group">
                 <div className="flex items-center justify-between mb-1 text-[10px] text-muted-foreground">
                   <div className="flex items-center gap-1"><Clock className="h-3 w-3" /> {q.time}</div>
                   <button onClick={() => window.dispatchEvent(new CustomEvent("AI_GENERATED_SQL", { detail: q.sql }))} className="opacity-0 group-hover:opacity-100 text-emerald-400 hover:underline">Re-run</button>
                 </div>
                 <div className="text-[11px] font-mono text-foreground/80 break-words max-h-20 overflow-hidden relative">
                   {q.sql}
                   <div className="absolute bottom-0 left-0 right-0 h-4 bg-gradient-to-t from-[#2a2a2a] to-transparent"></div>
                 </div>
               </div>
             ))}
           </div>
        </div>
      )}

      <div className="p-4 border-t border-border bg-[#1c1c1c]">
        <input type="file" multiple accept=".pdf,.csv" className="hidden" ref={fileInputRef} onChange={handleFileChange} />
        <button onClick={() => fileInputRef.current?.click()} disabled={isUploading} className={cn("group relative flex w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-[#3e3e3e] bg-[#2a2a2a] p-4 transition-all hover:border-primary disabled:opacity-50")}>
          {isUploading ? <Loader2 className="h-5 w-5 animate-spin text-primary" /> : uploadStatus === "Complete!" ? <CheckCircle2 className="h-5 w-5 text-emerald-500" /> : <Upload className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />}
          <span className="text-xs font-medium text-muted-foreground group-hover:text-foreground">{uploadStatus || "Upload Data File"}</span>
        </button>
      </div>
    </div>
  )
}