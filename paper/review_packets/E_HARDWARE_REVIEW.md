---
packet_id: HARDWARE_REVIEW
manuscript_sections:
  - "13. Hardware Changes the Frontier, Not the Accounting"
  - "15. Threats to Validity"
---

# Packet E: Hardware Literature Review

## Reviewer profile

This packet is for readers who know FPGA HDC, in-memory HDC, Loihi or Lava, spiking VSA, multi-bit or analog HDC, or hardware-aware cost models.

## Sections to review

- Section 13: hardware synthesis
- hardware-related limitations in Section 15

## What the manuscript currently claims

- Hardware can move the practical price of dimension, precision, temporal state, and parallel search.
- None of the hardware claims were measured in this repository.
- The correct framing is "hardware changes the frontier, not the accounting."
- Hardware literature is used to explain which resources may become cheaper or more available, not to imply repository evidence that does not exist.

## Specific questions

1. Are measured and simulated results clearly separated?
2. Are hardware claims technically accurate and appropriately qualified?
3. Is the phrase "hardware changes the frontier, not the accounting" defensible and fair?
4. Are energy, latency, and temporal-state statements scoped correctly?
5. Which hardware or neuromorphic primary source is still missing?

## Compact extract

The hardware section is literature synthesis only. Its purpose is to prevent the software-centric mistake of assuming bytes are the only place recoverability cost can be paid, while still refusing to claim any measured hardware result the repository never ran.
