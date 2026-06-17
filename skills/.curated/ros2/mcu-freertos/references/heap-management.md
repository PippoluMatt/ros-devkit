# Heap Management

Use this reference for FreeRTOS heap schemes, allocation failures, fragmentation, stack sizing, and memory diagnostics.

## Context To Gather

- RTOS heap implementation and SDK allocator model.
- Static versus dynamic allocation policy.
- Total RAM, special memory regions, DMA-capable memory, PSRAM, and retained memory.
- Current free heap, minimum ever free heap, stack high-water marks, and allocation failure hooks.

## Guidance

- Prefer static allocation for long-lived RTOS objects in constrained or safety-sensitive firmware.
- Avoid repeated allocate/free cycles in real-time paths unless fragmentation behavior is understood.
- Check every allocation that can fail, especially task, queue, timer, and buffer creation.
- Use heap and stack instrumentation before changing memory sizes.
- Keep DMA buffers in memory regions required by the MCU and SDK.
- Treat PSRAM or external memory as slower and sometimes unsuitable for ISR, DMA, or latency-critical data.

## Review Checklist

- Heap scheme matches allocation behavior.
- Stack sizes are based on high-water marks plus margin.
- Allocation failure hooks are enabled or errors are propagated.
- Large buffers have a clear owner and lifetime.
