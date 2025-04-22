import wexpect
import re
from functools import wraps
from datetime import datetime


def require_connection(method):
    """
    Decorator to ensure that the session is active before executing a method.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.connection_is_active:
            raise RuntimeError("No active SSH session.")
        return method(self, *args, **kwargs)
    return wrapper


class Session_handler:

    def __init__(self, ip: str, username: str, password: str):
        """
        Initialize the session handler with device credentials.
        """
        self.ip = ip
        self.username = username
        self.password = password
        self.child = None
        self.connection_is_active = False
        self.created_at = datetime.now()

    def connect(self) -> str:
        """
        Establish an SSH session using wexpect.
        Handles known SSH scenarios: key confirmation, connection refused, and bad credentials.
        Returns a status message instead of raising exceptions.
        """
        try:
            self.child = wexpect.spawn(f"ssh {self.ip}", timeout=10)

            index = self.child.expect([
                "The authenticity of host .* can't be established",  # First-time connection
                "ssh: connect to host .* port .*: Connection refused",  # SSH not enabled
                "User Name:",  # Normal login flow
                wexpect.EOF,
                wexpect.TIMEOUT
            ])

            if index == 0:
                # First time SSH prompt
                self.child.sendline("yes")
                self.child.expect("User Name:")

            elif index == 1:
                self.child.close()
                self.connection_is_active = False
                return "SSH connection refused (is the SSH server enabled?)"

            elif index in [3, 4]:
                self.child.close()
                self.connection_is_active = False
                return "SSH session failed to start (EOF or Timeout)"

            # Normal login flow
            self.child.sendline(self.username)
            self.child.expect("Password:")
            self.child.sendline(self.password)

            # After sending password, either we get the CLI prompt or we are asked again for "User Name:"
            index = self.child.expect([
                "#",             # Successful login
                "User Name:",    # Wrong credentials
                wexpect.EOF,
                wexpect.TIMEOUT
            ])

            if index == 0:
                self.connection_is_active = True
                return "Connection established"
            elif index == 1:
                self.disconnect()
                return "Wrong credentials!"
            else:
                self.disconnect()
                return "SSH session failed after login attempt (EOF or Timeout)"

        except Exception as e:
            self.connection_is_active = False
            return f"Connection failed: {str(e)}"    

    def disconnect(self):
        """
        Gracefully close the SSH session.
        """
        try:
            if self.child:
                self.child.close()
        except Exception as e:
            print(f"Error during disconnect: {e}")
        finally:
            self.child = None
            self.connection_is_active = False

    @require_connection
    def get_model_name(self) -> str:
        """
        Retrieves the switch model name by sending 'show system' command and parsing the output.

        Returns:
        str: The model name (e.g., 'CBS250-8T-E-2G') if found, otherwise 'Unknown'.
        """

        output = self.send_command_read_answer("show system")

        # Try to extract from 'System Description'
        match = re.search(r"System Description:\s+(CBS\d{3,4}-[A-Z0-9\-]+)", output)
        if match:
            return match.group(1)

        # Fallback: Try to extract from unit table
        match = re.search(r"\n\s*1\s+(CBS\d{3,4}-[A-Z0-9\-]+)", output)
        if match:
            return match.group(1)
        # If no match is found, return a default indicator
        return "Unknown"

    @require_connection
    def _quetly_reset_connection(self):
        """
        Quietly resets the SSH session without changing the connection state.
        Useful for reconnecting while maintaining logical session tracking.
        """
        try:
            self.child.close()
        except Exception:
            pass
        self.connect()

    @require_connection
    def get_config(self, which: str) -> list:
        """
        Retrieve and clean either the running or startup configuration.

        Args:
            which (str): 'running' or 'startup'

        Returns:
            list: Cleaned configuration lines
        """
        if which == "running":
            command = "show running-config"
        elif which == "startup":
            command = "show startup-config"
        else:
            raise ValueError("Invalid config type. Use 'running' or 'startup'.")

        self.child.sendline(command)
        self.child.expect(command)  # flush echo

        full_output = ""
        while True:
            index = self.child.expect(["More: <space>", "#", wexpect.EOF, wexpect.TIMEOUT], timeout=10)
            full_output += self.child.before
            if index == 0:
                self.child.send(" ")  # Respond to pagination
            elif index == 1:
                full_output += self.child.before
                break
            else:
                break

        # Clean and parse output
        outputlines = []
        word_to_copy = ""

        full_output = re.sub(r',?\s*Quit: q or CTRL\+Z, One line: <return> *\r?!?', '', full_output)
        full_output = full_output.replace('\r\n', '\n').replace('\r', '\n')
        full_output = re.sub(r'(privilege \d+)(username )', r'\1\n\2', full_output)
        full_output = re.sub(r'(privilege \d+)\s*(ip ssh server)', r'\1\n\2', full_output)

        i = 0
        while i < len(full_output):
            char = full_output[i]
            if char == '\n' or (char == ' ' and i + 1 < len(full_output) and full_output[i + 1] == ' '):
                cleaned = word_to_copy.strip()
                if cleaned.lower() not in ["exit", "!"] and cleaned:
                    outputlines.append(cleaned)
                word_to_copy = ""
                while i + 1 < len(full_output) and full_output[i + 1] == ' ':
                    i += 1
            else:
                word_to_copy += char
            i += 1

        # Final flush
        cleaned = word_to_copy.strip()
        if cleaned.lower() not in ["exit", "!"] and cleaned:
            outputlines.append(cleaned)

        return outputlines
    
    @require_connection
    def get_both_configs(self) -> tuple[list, list]:
        """
        Retrieve both running and startup configurations.
        Useful for external comparison logic.
        
        Returns:
            Tuple of two lists: (running_config, startup_config)
        """
        running_config = self.get_config("running")
        self._quetly_reset_connection()
        startup_config = self.get_config("startup")
        return running_config, startup_config

    @require_connection
    def send_command_read_answer(self, command: str) -> str:
        """
        Send a command and return the resulting output.
        """
        self.child.sendline(command)
        self.child.expect(command)
        self.child.expect(["#", wexpect.EOF, wexpect.TIMEOUT])
        return self.child.before.strip()

    @require_connection
    def send_command(self, command: str):
        """
        Send a command and wait for it to be echoed.
        This ensures CLI is ready for next input.
        """
        self.child.sendline(command)
        self.child.expect(command)  # Just sync on echo

    @require_connection
    def send_end(self):
        """
        Send 'end' command to exit config mode.
        Only waits for echo.
        """
        self.child.sendline("end")
        self.child.expect("end")
    
    @require_connection
    def validate_connection(self) -> bool:
        """
        Checks if the SSH session is still synchronized with the switch prompt.

        Returns:
            bool: True if prompt ends with '#', otherwise False
        """
        try:
            self.child.sendline("")  # Trigger prompt
            index = self.child.expect([r"[>#]"], timeout=2)
            print(f"Matched index: {index}")
            
            output = self.child.before.strip()
            

            matched_prompt = self.child.after
            if isinstance(matched_prompt, bytes):
                matched_prompt = matched_prompt.decode(errors="ignore")
            return matched_prompt.endswith("#")
        except Exception as e:
            return False

    @require_connection
    def get_interfaces_status(self) -> dict:
        """
        Parses 'show interfaces status' output into a structured dictionary.
        Fixes spacing issues in 'Disabled On' and similar cases.
        """
        raw = self.send_command_read_answer("show interfaces status")

        # Insert line breaks before each interface
        raw = re.sub(r"\s+(gi\d{1,2})", r"\n\1", raw)
        raw = re.sub(r"\s+(Po\d{1,2})", r"\n\1", raw)

        lines = raw.replace('\r', '').split('\n')
        result = {}
        result["headers"] = ["Type", "Duplex", "Speed", "Neg", "Flow ctrl", "Link State", "Back Pressure", "Mdix Mode"]

        iface_pattern = re.compile(r"^(gi\d+|Po\d+)\s+(.+)$")

        for line in lines:
            match = iface_pattern.match(line.strip())
            if not match:
                continue

            iface, rest = match.groups()
            fields = re.split(r'\s{2,}', rest.strip())

            # Fix split issue if one field is like "Disabled On"
            fixed_fields = []
            for field in fields:
                if field.startswith("Enabled ") or field.startswith("Disabled "):
                    parts = field.split(" ", 1)
                    fixed_fields.extend(parts)
                else:
                    fixed_fields.append(field)

            # Trim based on interface type
            if iface.startswith("gi"):
                fixed_fields = fixed_fields[:8]
            elif iface.startswith("Po"):
                fixed_fields = fixed_fields[:6]

            result[iface] = fixed_fields

        return result

    def __repr__(self):
        return f"<Session_handler ip={self.ip}, username={self.username}, created={self.created_at.strftime('%Y-%m-%d %H:%M:%S')}>"



