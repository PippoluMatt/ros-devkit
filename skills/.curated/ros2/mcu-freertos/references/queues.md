# Queues

Use this reference for RTOS queues, producer-consumer pipelines, message ownership, and ISR-to-task handoff.

## Context To Gather

- Producers and consumers, including ISR producers.
- Message size, rate, burst size, and acceptable loss behavior.
- Whether queued data is copied by value, pointer, or handle.
- Backpressure policy when the queue is full.

## Guidance

- Use queues when messages need ordering, buffering, or decoupled producer-consumer behavior.
- Keep queue items small; pass pointers or fixed-size handles for large payloads when ownership is clear.
- Define what happens on full queues: block, drop newest, drop oldest, overwrite, or signal overload.
- Use ISR-safe send APIs from interrupts.
- Size queues from measured bursts and consumer latency, not guesswork.
- Consider direct task notifications for single-consumer events that do not need payload buffering.

## Review Checklist

- Queue depth has a reason.
- Message lifetime is safe after enqueue and dequeue.
- Full and empty queue behavior is explicit.
- Consumers cannot block forever unless shutdown is impossible or handled elsewhere.
