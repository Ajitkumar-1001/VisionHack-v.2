// The one client island (frontend contract: interactivity isolated in a leaf
// client component; the page itself stays server-rendered). Polls /api/status
// and spring-animates state transitions — framer-motion owns only this subtree,
// app.js owns the rest of the console and never touches this element.
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

type Status = { agent_state?: string; event_count?: number };

const spring = { type: "spring", stiffness: 100, damping: 20 } as const;

export default function Heartbeat() {
  const [status, setStatus] = useState<Status>({});

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const r = await fetch("/api/status");
        if (alive) setStatus(await r.json());
      } catch {
        /* console must never blank on a failed poll */
      }
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const state = status.agent_state ?? "—";
  const alerting = state === "CONFLICT" || state === "ALERT_CREATED";

  return (
    <div className="flex items-center gap-2 text-[11px] tracking-widest font-bold">
      <motion.span
        className={`inline-block h-[7px] w-[7px] rounded-full ${alerting ? "bg-[#f45b47]" : "bg-[#34d399]"}`}
        animate={{ scale: [1, 1.5, 1], opacity: [1, 0.6, 1] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
      />
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={state}
          initial={{ y: 8, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -8, opacity: 0 }}
          transition={spring}
          className={alerting ? "text-[#f45b47]" : "text-[#8a94a3]"}
        >
          {state}
        </motion.span>
      </AnimatePresence>
      {typeof status.event_count === "number" && status.event_count > 0 && (
        <motion.span
          layout
          transition={spring}
          className="rounded-full border border-[#f5a623]/40 px-2 py-[1px] text-[#f5a623]"
        >
          {status.event_count}
        </motion.span>
      )}
    </div>
  );
}
