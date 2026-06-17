# Software Timers

Use this reference for FreeRTOS software timers, timer callbacks, debounce logic, periodic work, and deferred execution.

## Context To Gather

- Timer period, one-shot versus periodic behavior, and callback runtime.
- Timer service task priority and stack size.
- Whether the timer interacts with queues, tasks, peripherals, or ISRs.
- Required timing accuracy and jitter tolerance.

## Guidance

- Use software timers for lightweight deferred or periodic work that does not require hard real-time precision.
- Keep callbacks short; hand off heavy work to tasks.
- Do not block in timer callbacks.
- Avoid long peripheral transactions in timer callbacks.
- Use hardware timers or peripheral interrupts when timing precision is stricter than the RTOS tick and software timer jitter.
- Confirm timer service task priority is high enough for required latency but not high enough to starve critical work.

## Review Checklist

- Callback runtime is bounded.
- Callback does not block.
- Timer period and jitter tolerance are documented.
- Hardware timer use is considered for precise timing.
