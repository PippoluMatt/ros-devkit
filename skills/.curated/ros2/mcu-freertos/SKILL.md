---
name: mcu-freertos
description: Create, edit, and maintain MCU firmware that uses FreeRTOS or similar RTOS patterns. Use when working on embedded firmware for microcontrollers such as ESP32-S3, Arduino-class boards, STM32, RP2040, or when the user mentions RTOS tasks, scheduling, queues, semaphores, mutexes, timers, heap, SMP, or AMP.
---

# MCU FreeRTOS

Use this skill to help with MCU firmware that runs FreeRTOS or an RTOS with similar primitives.

## Questionnaire

Ask 3 to 4 questions before changing code unless the user already gave enough context:

1. Which MCU, board, SDK, and RTOS are in use?
2. What firmware goal or bug should be handled?
3. Which RTOS topic is involved: multiprocessing, scheduling, semaphores/mutexes, queues, heap, or software timers?
4. What constraints matter most: latency, memory, power, safety, portability, or simplicity?

After the answers, restate the assumptions and choose the smallest relevant reference set.

## Workflow

1. Identify the MCU, clock model, interrupt model, memory limits, and available RTOS APIs.
2. Inspect existing task priorities, stack sizes, synchronization objects, queues, timers, and heap configuration.
3. Prefer the simplest RTOS primitive that matches the data ownership and timing requirement.
4. Keep ISR work short; defer processing to tasks with notifications, queues, or semaphores.
5. Verify changes with build output, runtime logs, stack high-water marks, heap checks, and timing measurements when available.

## Load References

Load only the references needed for the user request:

- Multiprocessing: [references/multiprocessing.md](references/multiprocessing.md)
- Preemptive scheduling: [references/preemptive-scheduling.md](references/preemptive-scheduling.md)
- Semaphores and mutexes: [references/semaphores-mutexes.md](references/semaphores-mutexes.md)
- Queues: [references/queues.md](references/queues.md)
- Heap management: [references/heap-management.md](references/heap-management.md)
- Software timers: [references/software-timers.md](references/software-timers.md)

## Guardrails

- Do not assume desktop threading rules apply to MCU RTOS firmware.
- Do not add tasks when an existing task, timer, queue, or direct task notification is enough.
- Do not call blocking APIs from ISRs unless the SDK explicitly provides an ISR-safe variant.
- Do not change priorities, core affinity, heap scheme, or stack sizes without explaining the timing and memory tradeoff.
