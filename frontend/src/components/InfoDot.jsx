import React from "react";
import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";

/**
 * InfoDot — inline contextual help icon.
 *
 * Usage:
 *   <Label>Notice Reference <InfoDot tip="Auto-generated. Format: NTC-YYYY-####." /></Label>
 *   <Button>Publish <InfoDot tip="Publishes to public Notice Board immediately." /></Button>
 *
 * Renders a small ⓘ icon that reveals `tip` on hover, focus or tap.
 * Uses the existing shadcn/Radix Tooltip primitive so styling matches the rest
 * of the app. Wrap the tree with <TooltipProvider> at the top of the app (or
 * inside the panel) — App.js already provides one at the root.
 */
export function InfoDot({
  tip,
  side = "top",
  className = "",
  size = 14,
  ariaLabel,
  testId,
}) {
  if (!tip) return null;
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            tabIndex={0}
            aria-label={ariaLabel || "More information"}
            data-testid={testId || "info-dot"}
            className={
              "inline-flex ml-1 align-middle text-slate-400 hover:text-slate-600 focus:text-slate-700 focus:outline-none " +
              className
            }
            onClick={(e) => e.preventDefault()}
          >
            <Info size={size} strokeWidth={2} />
          </button>
        </TooltipTrigger>
        <TooltipContent
          side={side}
          className="max-w-xs whitespace-normal text-left leading-snug"
        >
          {tip}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default InfoDot;
