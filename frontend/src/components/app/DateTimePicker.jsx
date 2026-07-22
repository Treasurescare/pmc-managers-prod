import { useState } from "react";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CalendarIcon } from "lucide-react";

/**
 * DateTimePicker — shadcn Calendar + time input, emits ISO datetime string (yyyy-MM-ddTHH:mm).
 * Props:
 *  - value: string (yyyy-MM-ddTHH:mm) or ""
 *  - onChange: (isoLocal) => void
 *  - min: Date optional
 *  - testid
 */
export default function DateTimePicker({ value, onChange, min, testid, placeholder = "Pick date & time" }) {
  const [open, setOpen] = useState(false);
  const currentDate = value ? new Date(value) : null;
  const timeString = value ? value.split("T")[1]?.slice(0, 5) || "09:00" : "09:00";

  const pad = (n) => String(n).padStart(2, "0");
  const toLocal = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const label = currentDate
    ? currentDate.toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) + " · " + timeString
    : placeholder;

  const setDate = (d) => {
    if (!d) return;
    const iso = `${toLocal(d)}T${timeString}`;
    onChange(iso);
  };
  const setTime = (t) => {
    if (!currentDate) return;
    onChange(`${toLocal(currentDate)}T${t}`);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button" data-testid={testid}
          className={`w-full h-12 px-4 border border-input bg-white text-left inline-flex items-center gap-3 hover:border-foreground focus:border-primary focus:outline-none ${!value ? "text-muted-foreground" : ""}`}
        >
          <CalendarIcon className="h-4 w-4" />
          <span className="font-mono text-sm">{label}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0 bg-white border" align="start">
        <div className="p-3">
          <Calendar
            mode="single"
            selected={currentDate || undefined}
            onSelect={setDate}
            initialFocus
            fromDate={min}
            data-testid={`${testid}-cal`}
          />
        </div>
        <div className="border-t p-3 flex items-center gap-3">
          <span className="pmc-label">Time</span>
          <input
            data-testid={`${testid}-time`}
            type="time" value={timeString} onChange={(e) => setTime(e.target.value)}
            className="h-10 px-3 border border-input font-mono text-sm bg-white"
          />
          <button type="button" onClick={() => setOpen(false)} className="ml-auto text-xs px-3 py-1.5 bg-foreground text-white">Done</button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
