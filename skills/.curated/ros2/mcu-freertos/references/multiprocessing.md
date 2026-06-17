# Multiprocessing

Use this reference for asymmetric multiprocessing, symmetric multiprocessing, dual-core MCUs, and core affinity decisions.

## Context To Gather

- MCU family and RTOS port, especially whether SMP is supported by the vendor SDK.
- Which cores exist, what each core is allowed to run, and whether radio, USB, Wi-Fi, BLE, or system services reserve a core.
- Shared peripherals, DMA engines, cache coherency rules, and interrupt routing.
- Whether tasks have core affinity or can migrate.

## Guidance

- Use AMP when one core has a fixed responsibility, isolated firmware image, vendor stack, or real-time control loop that should not share the scheduler.
- Use SMP when the RTOS port supports it well and the workload benefits from task migration or balanced CPU use.
- Pin latency-sensitive tasks only when migration causes jitter, cache effects, or peripheral ownership problems.
- Treat shared peripheral drivers as single-owner unless the SDK documents thread safety.
- Protect shared state with RTOS primitives, not volatile alone.
- Keep cross-core communication explicit with queues, task notifications, event groups, or lock-free SDK primitives that are documented for the target.

## Review Checklist

- Core ownership is documented.
- Shared resources have one clear owner or one clear synchronization rule.
- ISRs wake the correct task on the correct core when affinity matters.
- Priority and affinity choices do not starve vendor system tasks.
