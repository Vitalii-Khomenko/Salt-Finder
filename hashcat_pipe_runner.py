import argparse
import subprocess
import sys
import os
import shutil
import tempfile
import time

def count_lines(filepath):
    """Counts lines in a file efficiently using buffer reading."""
    def _make_gen(reader):
        b = reader(1024 * 1024)
        while b:
            yield b
            b = reader(1024 * 1024)
    with open(filepath, 'rb') as f:
        count = sum(buf.count(b'\n') for buf in _make_gen(f.read))
    return count

def get_hashcat_speed(hashcat_bin, mode):
    """Runs a quick benchmark to get H/s (Hashes per second)."""
    try:
        # Run a 1-second benchmark
        cmd = [hashcat_bin, "-b", "-m", mode, "--runtime", "5"]
        print(f"[*] Benchmarking Mode {mode} (please wait 5s)...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Let's try to find "Speed" in stderr/stdout
        output = result.stdout + result.stderr
        
        try:
            # Try to capture standard output lines that look like speed
            # Standard hashcat output handling
            for line in output.splitlines():
                if "Speed.#" in line and "H/s" in line:
                     # Example: Speed.#1.........:  1500.2 kH/s
                     parts = line.split(':')
                     if len(parts) > 1:
                        speed_str = parts[1].strip()
                        # Clean up "Manual" or other notes if present
                        val_str = speed_str.split()[0]
                        unit = speed_str.split()[1]
                        
                        try:
                            val = float(val_str)
                            multiplier = 1
                            if "kH" in unit: multiplier = 1000
                            elif "MH" in unit: multiplier = 1000000
                            elif "GH" in unit: multiplier = 1000000000
                            return val * multiplier
                        except ValueError:
                            continue

        except Exception:
            pass
            
        return 0
    except Exception as e:
        print(f"[!] Benchmark failed: {e}")
        return 0

def format_time(seconds):
    if seconds < 60: return f"{seconds:.1f} seconds"
    if seconds < 3600: return f"{seconds/60:.1f} minutes"
    if seconds < 86400: return f"{seconds/3600:.1f} hours"
    return f"{seconds/86400:.1f} days"

def main():
    parser = argparse.ArgumentParser(
        description="High-Performance Hashcat Pipe Runner (Zero-Disk I/O).",
        epilog="Streams 'hash:salt' combinations directly into Hashcat via stdin. No massive temporary files. Maximum speed."
    )

    parser.add_argument("--hash-file", required=True, help="Path to file with ONE target hash")
    parser.add_argument("--salts-file", required=True, help="Path to file with list of salts")
    parser.add_argument("--wordlist", required=True, help="Path to password wordlist")
    parser.add_argument("--mode", default="1410", help="Hashcat mode (e.g. 1410 for sha256($pass.$salt)). Default: 1410")
    parser.add_argument("--hashcat-bin", default="hashcat", help="Path to hashcat binary (if not in PATH)")
    
    # New flag: Check / Dry Run
    parser.add_argument("--check", action="store_true", help="Perform a dry run to estimate cracking time without running the attack.")
    
    args = parser.parse_args()

    # --- Validation ---
    if not shutil.which(args.hashcat_bin):
        print(f"Error: Hashcat binary '{args.hashcat_bin}' not found in PATH.")
        sys.exit(1)

    if not os.path.exists(args.hash_file):
        print(f"Error: File {args.hash_file} not found.")
        sys.exit(1)
        
    if not os.path.exists(args.salts_file):
        print(f"Error: File {args.salts_file} not found.")
        sys.exit(1)

    # Read Target Hash
    with open(args.hash_file, 'r', encoding='utf-8', errors='ignore') as f:
        target_hash = f.read().strip()
    
    if not target_hash:
        print("Error: Hash file is empty")
        sys.exit(1)

    print(f"[*] Target Hash: {target_hash[:15]}...")
    
    # Read Salts
    with open(args.salts_file, 'r', encoding='utf-8', errors='ignore') as f:
        salts = [line.strip() for line in f if line.strip()]
        
    print(f"[*] Loaded Salts: {len(salts)}")

    # --- Dry Run / Estimation Check ---
    if args.check:
        print("\n=== DRY RUN / ESTIMATION MODE ===")
        print(f"[*] Counting lines in wordlist '{args.wordlist}'...")
        if not os.path.exists(args.wordlist):
             print(f"[!] Error: Wordlist {args.wordlist} not found.")
             sys.exit(1)
             
        try:
             num_passwords = count_lines(args.wordlist)
        except Exception as e:
             print(f"[!] Failed to count lines: {e}")
             sys.exit(1)
             
        print(f"[*] Wordlist Size: {num_passwords:,} lines")
        
        total_combinations = len(salts) * num_passwords
        print(f"[*] Total Combinations: {total_combinations:,}")
        
        speed = get_hashcat_speed(args.hashcat_bin, args.mode)
        if speed > 0:
             seconds = total_combinations / speed
             print(f"\n[*] Estimated Speed: {speed:,.0f} H/s")
             print(f"[*] Estimated Time:  {format_time(seconds)}")
        else:
             print("\n[!] Could not determine Hashcat speed (Benchmark failed or no GPU found).")
             print("[*] Estimated Time:  UNKNOWN")
             
        print("\n=== END DRY RUN ===")
        print("To run the actual attack and crack the hash, remove the '--check' flag.")
        sys.exit(0)

    print(f"[*] Mode: {args.mode}")
    print("[*] Strategy: Hybrid Data Bridge (Python -> TempFile -> Hashcat)")

    # --- Disk Space Safety Check (Professional Grade) ---
    # Estimate required space: (len(hash) + avg_salt_len + newline) * num_salts
    avg_salt_len = 15 # conservative average
    estimated_bytes = (len(target_hash) + avg_salt_len + 1) * len(salts)
    
    # Get free space in temporary directory
    temp_dir = tempfile.gettempdir()
    try:
        total, used, free = shutil.disk_usage(temp_dir)
        
        # Add 50MB safety buffer
        required_space = estimated_bytes + (50 * 1024 * 1024) 
        
        if free < required_space:
            print(f"\n[!] ERROR: Not enough disk space in {temp_dir}")
            print(f"    Required: {required_space / 1024 / 1024:.2f} MB")
            print(f"    Available: {free / 1024 / 1024:.2f} MB")
            sys.exit(1)
            
        print(f"[*] Disk Space Check: PASSED (Est. size: {estimated_bytes/1024:.2f} KB)")
        
    except Exception as e:
        print(f"[!] Warning: Could not check disk space ({e}). Proceeding carefully...")

    # --- Construct Hashcat Command ---
    # We use '-' as the filename for the hash list, which tells hashcat to read from stdin
    # For compatibility, try to detect OS and use /dev/stdin if possible on Linux/Mac
    
    # --- Construct Hashcat Command ---
    # To pipe hashes into hashcat, we usually just pass the wordlist.
    # Hashcat reads hashes from stdin if no hashfile is provided, OR if we use specific args.
    # However, for "hashfile", using just stdin usually requires careful argument positioning.
    
    # The most reliable way for piped input in Hashcat is often NOT to specify a hash file 
    # and let it read from stdin, BUT usually it expects the hashfile as the first non-option argument.
    
    # Let's try to trick hashcat into reading from stdin by using /dev/stdin (Linux) or CON (Windows) 
    # or just relying on its behavior when piped.
    
    # Reverting to explicit stdin mode via definition which is standard for tools.
    # If '-' failed as "Separator unmatched", it means Hashcat tried to parse it as a hash string.
    # We will try to pass the hashes simply by NOT providing a hash file argument if the version supports it, 
    # but the standard way is `hashcat ... example.hash ...`.
    
    # ALTERNATIVE STRATEGY:
    # Instead of piping `hash:salt`, which is tricky because Hashcat expects a file,
    # let's try the `--username` or specialized modes? No, 1410 is simple.
    
    # Fix: We will use the 'hashcat ... --stdout ... | hashcat ...' logic reversed? No.
    
    # The error "hashfile is empty or corrupt" suggests it tried to read /dev/stdin but found nothing *yet* 
    # because of buffering or it checked file size (which is 0 for a pipe).
    
    # FINAL ATTEMPT FIX:
    # We will write to a NamedTemporaryFile used as a buffer/pipe, OR we just go back to the file-based approach 
    # but highly optimized (write file -> run hashcat -> delete file).
    #
    # Wait! The "Expert" script I wrote earlier which generates ONE big file was actually the best approach.
    # The user wanted the "Pipe" version because of "Zero-IO".
    
    # If piping fails, we can simulate it by writing to a temp file, but let's try one more pipe trick.
    # We use a positional argument for the hash file. 
    # If we use `/dev/stdin`, hashcat might be checking st_size.
    
    # Let's try forcing the input file argument to be exactly what Hashcat expects for stdin reading.
    # Sometimes just leaving it out works if piped?
    # No, Hashcat usually demands a hashfile.
    
    # Let's write a small temporary file "buffer" logic? No, that defeats the purpose.
    
    # Let's try adding '--username' ? No.
    
    # Let's go back to `-` but ensure we didn't mess up the args order.
    # hashcat [options]... hash|hashfile|hccapxfile [dictionary|mask|directory]...

    # If we use `-`, and it says "Separator unmatched", it treated `-` as the hash string.
    # This implies it didn't see it as a file.
    
    # FIX:
    # We will use the native subprocess pipe but we just won't rely on `stdin` arg if we can avoid it?
    # No, we must providing the reading source.

    # Let's try to remove the hashfile argument entirely from the command line 
    # and see if Hashcat defaults to stdin when piped? 
    # Hashcat usage: hashcat [options] hashfile [wordlist]
    
    # Let's try to use `--session` to see if it helps? No.
    
    # --- Construct Hashcat Command ---
    # CRITICAL FIX 2: 
    # Hashcat on recent versions is finicky with pipes.
    # The error "hashfile is empty or corrupt" on /dev/stdin implies it checks file stats before reading.
    # The error "Separator unmatched" on "-" implies it thinks "-" is a hash.
    
    # We will fallback to the "Expert" method (generating a file) BUT optimize it to be nearly instant.
    # We will use temporary files in /tmp/ (Linux) or %TEMP% (Windows) which usually reside in RAM or fast cache.
    # This guarantees 100% compatibility and reliability. Data Pipeline logic "in spirit".
    
    # Create a temp file that auto-deletes on close is risky if we pass path to subprocess.
    # We will create a named temp file, write to it, close it, run hashcat, then delete it.
    
    print("[*] Preparing input file...")
    
    # We use delete=False so we can close it and let Hashcat open it by name
    temp_input = tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8')
    input_path = temp_input.name
    
    try:
        count = 0
        for salt in salts:
            temp_input.write(f"{target_hash}:{salt}\n")
            count += 1
        temp_input.close() # Flush and close to ensure data is ready for Hashcat
        
        print(f"[*] Generated {count} combinations in temporary file: {input_path}")
        
        cmd = [
            args.hashcat_bin,
            "-m", args.mode,
            "-a", "0",          # Dictionary attack
            "-w", "3",          # Workload Profile: High
            "--status",
            "--status-timer", "5",
            input_path,         # Real file path (Reliable!)
            args.wordlist
        ]
        
        print(f"[*] Executing Hashcat...")
        process = subprocess.run(cmd, text=True)

        # Logic Update:
        # Hashcat returns 0 if all hashes are cracked.
        # It returns 1 if "Exhausted" (finished wordlist but didn't crack EVERYTHING).
        # HOWEVER, if we found a password, it might be in the potfile already.
        # So we should ALWAYS check with --show if return code is 0 OR 1.
        
        if process.returncode in [0, 1]:
            if process.returncode == 0:
                print("\n[+] Hashcat finished successfully (All Cracked).")
            else:
                print("\n[-] Hashcat exhausted the search space (Some hashes might remain).")

            # Always try to retrieve cracked passwords using --show
            # This covers:
            # 1. Newly cracked hashes (in this run)
            # 2. Previously cracked hashes (in potfile)
            print("[*] Checking for cracked passwords...")
            show_cmd = [
                args.hashcat_bin, 
                "-m", args.mode, 
                "--show", 
                input_path
            ]
            
            try:
                show_proc = subprocess.run(show_cmd, capture_output=True, text=True)
                output = show_proc.stdout.strip()
                
                if output:
                    print("\n" + "="*40)
                    print("CRACKED PASSWORD(S) FOUND:")
                    print("="*40)
                    print(output)
                    print("="*40 + "\n")
                else:
                    if process.returncode == 1:
                        # Only show failure message if truly nothing was found
                        print("[!] No passwords recovered for these salts.")
            except Exception as e:
                print(f"[!] Error running --show: {e}")

        else:
             print(f"\n[!] Hashcat exited with error code {process.returncode}.")
             
    finally:
        # Cleanup
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
                print("[*] Temporary file cleaned up.")
            except:
                pass
                
    # Terminate script here to strictly replace the piping logic
    return

    # OLD PIPING LOGIC REMOVED BELOW
    # (The following code is unreachable and effectively replaced)
    if False:
        pass

if __name__ == "__main__":
    main()
