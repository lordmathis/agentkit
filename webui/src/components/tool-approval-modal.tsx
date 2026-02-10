import { Loader2 } from "lucide-react";
import { PendingToolApproval } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface ToolApprovalModalProps {
  approval: PendingToolApproval;
  onApprove: () => Promise<void>;
  onDeny: () => Promise<void>;
  isProcessing: boolean;
}

export function ToolApprovalModal({
  approval,
  onApprove,
  onDeny,
  isProcessing,
}: ToolApprovalModalProps) {
  return (
    <Dialog open={true}>
      <DialogContent showCloseButton={false} className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold">
            Tool Approval Required
          </DialogTitle>
          <DialogDescription>
            The assistant wants to execute the following tool:
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Tool Name */}
          <div>
            <h3 className="text-lg font-semibold text-primary mb-2">
              {approval.tool_name}
            </h3>
          </div>

          {/* Arguments */}
          <div>
            <h4 className="text-sm font-medium mb-2 text-muted-foreground">
              Arguments:
            </h4>
            <pre className="bg-muted p-4 rounded-md overflow-auto max-h-96 text-sm">
              <code>{JSON.stringify(approval.arguments, null, 2)}</code>
            </pre>
          </div>

          {isProcessing && (
            <div className="flex items-center justify-center text-muted-foreground text-sm">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Processing...
            </div>
          )}
        </div>

        <DialogFooter className="mt-6">
          <Button
            variant="outline"
            onClick={onDeny}
            disabled={isProcessing}
            className="min-w-24"
          >
            Deny
          </Button>
          <Button
            onClick={onApprove}
            disabled={isProcessing}
            className="min-w-24"
          >
            {isProcessing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Approving
              </>
            ) : (
              "Approve"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
