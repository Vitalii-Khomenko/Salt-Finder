# Hashcat Salted Batch Attack (Optimized)

A professional-grade Python automation script for cracking salted hashes with [Hashcat](https://hashcat.net/hashcat/). 

This tool solves the "1 Hash + 1000 Salts" problem by **batching** all combinations into a single, high-speed Hashcat session. It prevents the common pitfall of restarting Hashcat for every salt, which can take hours instead of minutes.

## ❓ The "Why": Understanding the Problem

If you have a salted hash but do not know the salt, you cannot simply provide Hashcat with a hash and a separate file of salts hoping it will mix and match them efficiently against a wordlist.

### The Limitation of Standard Hashcat
In modes like `1420` (`sha256($salt.$pass)`), Hashcat expects the input to be in the strict format `hash:salt`. It assumes you know exactly which salt belongs to which hash.

If you have **1 target hash** and a list of **1000 possible salts** (e.g., usernames, IDs, or extracted strings), you face a dilemma:

1.  **The Naive Approach (Bash Loop):** You write a script to pick Salt #1, run Hashcat, wait, pick Salt #2, run Hashcat...
    *   **The Fail:** Hashcat takes 2-10 seconds just to initialize the GPU and compile OpenCL kernels.
    *   **The math:** 1000 salts x 5 seconds startup = **~1.5 hours of wasted time** just staring at the initializing screen, covering zero passwords.

2.  **The Manual Approach:** You manually copy-paste the hash 1000 times and append the salts. This is tedious and error-prone.

### The Solution: Pre-Computed Batching
This script acts as a high-performance **pre-processor**.

1.  It takes your single `hash` and your file of `salts`.
2.  It instantly generates a temporary target file containing every possible combination:
    ```text
    target_hash:salt_candidate_1
    target_hash:salt_candidate_2
    ...
    target_hash:salt_candidate_1000
    ```
3.  It invokes Hashcat **ONCE**.
4.  Hashcat initializes one single time and then attacks the entire block at full GPU speed.

## 🚀 Key Features

*   **Hybrid Data Bridge**: Generates optimized `hash:salt` lists in a temporary buffer, allowing Hashcat to run at full speed without pipe instability.
*   **Dry Run Estimation (`--check`)**: Instantly estimates attack duration based on your specific hardware speed and keyspace size.
*   **Disk Space Safety**: Checks for sufficient disk space before generating large temporary files to prevent crashes.
*   **Smart Cleanup**: Guarantees removal of temporary files after execution.
*   **Automated Result Extraction**: Automatically runs `hashcat --show` to retrieve passwords even if the session reports "Exhausted".

## 🛠 Prerequisites

- **Python 3.x**
- **[Hashcat](https://hashcat.net/hashcat/)** (Must be in your PATH or current directory)

## 📖 Usage

### 1. Standard Attack
Run the attack using the target hash, list of salts, and your password wordlist.

```bash
python3 hashcat_pipe_runner.py --hash-file hash.txt --salts-file salts.txt --wordlist wordlist.txt --mode 1410
```

### 2. Dry Run / Estimation
Before running a long attack, use `--check` to see if it's feasible. This will calculate the keyspace and benchmark your hashrate.

```bash
python3 hashcat_pipe_runner.py --hash-file hash.txt --salts-file salts.txt --wordlist wordlist.txt --check
```
*Output Example:*
```text
[*] Estimated Speed: 277.7 MH/s
[*] Estimated Time:  51.6 seconds
```

### Arguments

| Argument | Description |
| :--- | :--- |
| `--hash-file` | Path to the file containing the **SINGLE** target hash. |
| `--salts-file` | Path to the file containing the list of potential salts (one per line). |
| `--wordlist` | Path to the password wordlist (dictionary). |
| `--mode` | The Hashcat mode. `1410` for `sha256($pass.$salt)`, `1420` for `sha256($salt.$pass)`. |
| `--check` | Perform a dry run to estimate time without cracking. |
| `--hashcat-bin` | (Optional) Path to Hashcat binary if not in system PATH. |

---

## 🧠 Educational: Why not just use Pipes?

While technically faster, piping (`script.py | hashcat`) is unreliable in many environments (especially VMs and Windows). It can cause "Line length exceptions" or buffering issues where the GPU idles waiting for data.

This tool uses a **Write-Once-Read-Fast** strategy using temporary files in RAM-backed directories (`/tmp` or `%TEMP%`). This offers the stability of file-based loading with near-pipe speeds.

## ⚠️ Disclaimer

This tool is for educational purposes and authorized security auditing only. Do not use this tool on systems or data you do not have permission to test.

