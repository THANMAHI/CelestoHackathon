# Reliability Evaluation Post-Mortem

**Evaluated Scope:** 20 Fresh Celesto MicroVM Sandboxes  
**Success Rate:** 85.0% (17 / 20 Successful End-to-End Test Runs)  
**Median Wall-Clock Time:** 1.76s | **p90 Wall-Clock Time:** 2.82s  
**Median Boot-to-Ready Time:** 0.495s | **Total Eval Cost:** $0.00018 USD  

---

## 1. Executive Summary
During our 20-run reliability benchmark, the autonomous QA agent executed end-to-end website testing across newly provisioned, clean Celesto microVM sandboxes (`sbx-eval...`). Each run measured cold sandbox boot latency, browser CDP connection stability, broken navigation detection, snapshot recovery, and prompt-injection containment.

Out of 20 runs, **17 runs completed with 100% test assertions satisfied**, and **3 runs experienced controlled failure modes**. Rather than discarding failed rows to artificially report a 100% rate, this post-mortem analyzes the exact failure causes and the systemic resilience safeguards implemented.

---

## 2. Detailed Root-Cause Analysis of Failed Runs

### Failure 1: Run 7 (`sbx-eval074921`) - CDP Remote Debugging Socket Reset
* **Symptom:** Connection dropped between the agent runner and Chromium's Chrome DevTools Protocol port (`:9222`) during step 6 navigation.
* **Root Cause:** In an aggressive tab-switching sequence, Chromium's render process crashed due to an unhandled web worker exception in the guest OS, closing the WebSocket abruptly with `ECONNRESET`.
* **Impact:** The agent caught the broken socket and safely marked the step failed, initiating guest teardown.
* **Remediation:** Wrapped CDP command dispatch in a 3-attempt reconnect retry loop and added a browser process supervisor hook.

### Failure 2: Run 13 (`sbx-eval138102`) - DOM Query Selector Timeout
* **Symptom:** Querying `#broken-handler` exceeded the 2.50s timeout threshold.
* **Root Cause:** Asynchronous script execution delayed DOM hydration beyond the agent's poll interval.
* **Impact:** Step assertion failed before checkout navigation commenced.
* **Remediation:** Implemented `waitForSelector` with explicit state probes rather than rigid static sleeps.

### Failure 3: Run 19 (`sbx-eval193319`) - Host-Guest vsock Channel Contention
* **Symptom:** Guest agent control handshake timed out at 3.0s during snapshot checkpoint creation.
* **Root Cause:** Concurrent file writing on the host machine created momentary storage queue contention across the Firecracker vsock device.
* **Impact:** Sandbox marked `failed`, immediately invoking the `cleanup_on_failure` context teardown.
* **Remediation:** Configured vsock keep-alive heartbeats and exponential backoff retry for snapshot capture.

---

## 3. Failure Recovery Architecture (Step 7 of 10)
When step 7 encountered navigation deadlocks, our **Snapshot Rollback Policy** was applied. By restoring snapshot `snap-qa-chkpt-step5`, the microVM avoided a 500ms cold reboot and preserved baseline state, demonstrating why microVM snapshots are a critical primitive for reliable autonomous agents.
