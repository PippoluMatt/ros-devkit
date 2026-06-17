# Preemptive Scheduling

Use this reference for task priority, time slicing, blocking, starvation, jitter, and real-time responsiveness.

## Context To Gather

- Task list with priority, stack size, period, deadline, and blocking calls.
- Tick rate, time slicing setting, and available high-resolution timers.
- Interrupt priorities and which ISRs interact with RTOS APIs.
- Symptoms: missed deadlines, watchdog resets, jitter, CPU saturation, or starvation.

## Guidance

- Assign priorities by deadline and blocking behavior, not by perceived importance.
- Prefer blocking on RTOS objects over polling loops.
- Keep equal-priority tasks only when time slicing and fairness are intentional.
- Avoid long critical sections; they increase interrupt latency and scheduler jitter.
- Use `vTaskDelayUntil` or SDK equivalent for periodic tasks instead of accumulating drift with relative delays.
- Measure stack high-water marks and execution time before increasing stack sizes or priorities.

## Review Checklist

- Every task has a reason for its priority.
- Periodic tasks have bounded runtime and stable timing.
- Low-priority maintenance work cannot block high-priority control paths.
- Watchdog feeding is tied to real progress, not just task liveness.
