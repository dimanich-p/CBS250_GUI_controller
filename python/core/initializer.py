from infrastructure.ssh_client import Session_handler
from domain.physical_interface import Physical_interface_current_status, Physical_interface_settings


class Initializer:
    def __init__(self, session: Session_handler):
        """
        Takes an active Session_handler object and prepares for initialization tasks.
        """
        self.initialization_log = []
        self.session = session
        self.running_config = []
        self.startup_config = []
        self.model_name = "Unknown"
        self.interfaces_status = {}
        self.physical_interfaces_settings_objects = {}
        self.interfaces_current_status_objects = {}

    def initialize(self):
        self._get_data()
        self._initialize_physical_interfaces_and_current_status()
        self.session._quetly_reset_connection()

    def _get_data(self):
        """
        Gathers basic switch data:
        - Running config
        - Startup config
        - Model name
        - Interface status
        """
        try:
            self.running_config, self.startup_config = self.session.get_both_configs()
            self.model_name = self.session.get_model_name()
            self.interfaces_status = self.session.get_interfaces_status()
            self.initialization_log.append("Data collected successfully.")
        except RuntimeError as e:
            self.initialization_log.append(f"SSH session not active during data collection: {e}")
        except Exception as e:
            self.initialization_log.append(f"Unexpected error in _get_data: {e}")

        
    def _initialize_physical_interfaces_and_current_status(self):
        """
        Initializes both Physical_interface_settings and Physical_interface_current_status
        objects based on running config and real-time status.
        """
        try:
            if not self.interfaces_status or not self.running_config:
                self.initialization_log.append("Missing interfaces_status or running_config.")
                return

            self.physical_interfaces = {}
            self.interfaces_current_status_objects = {}

            # Group config blocks
            current_iface = None
            iface_blocks = {}

            for line in self.running_config:
                if line.startswith("interface GigabitEthernet"):
                    current_iface = "gi" + line.split("GigabitEthernet")[1].strip()
                    iface_blocks[current_iface] = []
                elif current_iface:
                    iface_blocks[current_iface].append(line.strip())

            # Parse each interface
            for iface_name, status_values in self.interfaces_status.items():
                if iface_name == "headers" or not iface_name.startswith("gi"):
                    continue

                # Initialize both objects
                settings_obj = Physical_interface_settings(name=iface_name, values=status_values)
                status_obj = Physical_interface_current_status(name=iface_name, values=status_values)

                if iface_name in iface_blocks:
                    config_lines = iface_blocks[iface_name]

                    for line in config_lines:
                        if line.startswith("description"):
                            settings_obj.description = line.replace("description", "").strip()
                        elif line == "no negotiation":
                            settings_obj.negotiation = "Disabled"
                            settings_obj.ethernet_negotiation = False
                        elif line.startswith("speed"):
                            settings_obj.speed = line.split()[-1]
                        elif line.startswith("duplex"):
                            settings_obj.duplex = line.split()[-1].capitalize()
                        elif line.startswith("mdix"):
                            settings_obj.mdix_mode = line.split()[-1].capitalize()
                        elif line.startswith("flowcontrol"):
                            settings_obj.flow_ctrl = "On" if "on" in line else "Off"
                        elif line.startswith("back-pressure"):
                            settings_obj.back_pressure = "Enabled"
                        elif line == "shutdown":
                            settings_obj.link_admin_state = "shutdown"

                        # Layer 2/3 settings (same as before)
                        elif line.startswith("ip address dhcp"):
                            settings_obj.physical_interface_ips = {"DHCP": True}
                        elif line.startswith("ip address"):
                            if settings_obj.physical_interface_ips.get("DHCP") != True:
                                parts = line.split()
                                if len(parts) == 4:
                                    ip = parts[2]
                                    mask = parts[3]
                                    settings_obj.physical_interface_ips[ip] = mask
                        elif line == "no switchport":
                            settings_obj.active_mode = "no switchport"
                        elif "switchport mode access" in line:
                            settings_obj.active_mode = "access"
                        elif "switchport mode trunk" in line:
                            settings_obj.active_mode = "trunk"
                        elif "switchport mode general" in line:
                            settings_obj.active_mode = "general"
                        elif "switchport mode customer" in line:
                            settings_obj.active_mode = "customer"
                        elif line.startswith("switchport access vlan"):
                            vlan = line.split()[-1]
                            if vlan.isdigit():
                                settings_obj.access_vlan = int(vlan)
                        elif line.startswith("switchport trunk allowed vlan"):
                            vlans = line.split()[-1].split(",")
                            settings_obj.allowed_vlans = [int(v) for v in vlans if v.isdigit()]
                        elif line.startswith("switchport trunk native vlan"):
                            vlan = line.split()[-1]
                            if vlan.isdigit():
                                settings_obj.native_vlan = int(vlan)
                        elif line.startswith("switchport general allowed vlan add"):
                            parts = line.split()
                            vlan = parts[5]
                            tag_type = parts[6]
                            if vlan.isdigit():
                                if tag_type == "tagged":
                                    settings_obj.general_allowed_tagged.append(int(vlan))
                                elif tag_type == "untagged":
                                    settings_obj.general_allowed_untagged.append(int(vlan))
                        elif line.startswith("switchport general forbidden vlan add"):
                            vlan = line.split()[-1]
                            if vlan.isdigit():
                                settings_obj.general_forbiden.append(int(vlan))
                        elif line.startswith("switchport general pvid"):
                            vlan = line.split()[-1]
                            if vlan.isdigit():
                                settings_obj.pvid_vlan = int(vlan)
                        elif line.startswith("switchport customer vlan"):
                            vlan = line.split()[-1]
                            if vlan.isdigit():
                                settings_obj.customer_vlan = int(vlan)

                self.physical_interfaces_settings_objects[iface_name] = settings_obj
                self.interfaces_current_status_objects[iface_name] = status_obj

            self.initialization_log.append(f"Initialized {len(self.physical_interfaces)} physical interface settings.")
            self.initialization_log.append(f"Initialized {len(self.interfaces_current_status_objects)} current interface status objects.")

        except Exception as e:
            self.initialization_log.append(f"Error in _initialize_physical_interfaces_and_current_status: {e}")

