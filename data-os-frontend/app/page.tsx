import { LeftSidebar } from "@/components/data-os/left-sidebar"
import { CenterWorkspace } from "@/components/data-os/center-workspace"
import { RightCopilot } from "@/components/data-os/right-copilot"

export default function Page() {
  return (
    <div className="flex h-dvh w-full overflow-hidden bg-background text-foreground">
      <LeftSidebar />
      <CenterWorkspace />
      <RightCopilot />
    </div>
  )
}
