# Semaphores And Mutexes

Use this reference for binary semaphores, counting semaphores, mutexes, priority inheritance, and shared resource protection.

## Context To Gather

- Which data or peripheral is shared and who owns it.
- Whether access can happen from tasks, ISRs, or both.
- Whether priority inversion is possible.
- Whether the primitive is used for signaling, resource counting, or mutual exclusion.

## Guidance

- Use mutexes for mutual exclusion between tasks because FreeRTOS mutexes can provide priority inheritance.
- Use binary semaphores or direct task notifications for task signaling.
- Use counting semaphores for pools or repeated events when counts matter.
- Do not take mutexes from ISRs; use ISR-safe semaphore or notification APIs when supported.
- Keep mutex hold times short and avoid blocking while holding a mutex.
- Prefer single-owner task design for peripherals when it simplifies locking.

## Review Checklist

- The primitive matches the intent: signal, count, or protect.
- ISR paths use only ISR-safe APIs.
- Lock order is consistent when multiple locks exist.
- Shared buffers have clear lifetime and ownership rules.
