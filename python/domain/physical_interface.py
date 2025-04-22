#from core.command_builder import Command_builder


class Physical_interface_settings:
    def __init__(self, name: str, values: list[str]):
        """
        Initialize a physical interface with its base status data.
        """
        self.name = name
        self.type = values[0] if len(values) > 0 else None
        self.duplex_values = ["Full", "Half"]
        self.duplex = "Full"
        self.speed_values = ["10", "100", "1000", "10000"]
        self.speed = "1000"
        self.negotiation_values = ["Enabled", "Disabled"]
        self.negotiation = "Enabled"
        self.flow_ctrl_values = ["Off", "On", "Auto"]
        self.flow_ctrl = "Off"
        self.link_admin_state_values = ["shutdown", "no shutdown"]
        self.link_admin_state = "no shutdown"
        self.back_pressure_values = ["Disabled", "Enabled"]
        self.back_pressure = "Disabled"
        self.mdix_mode_values = ["Auto", "On"]
        self.mdix_mode = "Auto"

        self.ethernet_negotiation = True

        # Switchport description
        self.description = ""
        self.modes = ["access", "trunk", "general", "customer","no switchport"]
        self.active_mode = "access"
        

        # Access
        self.access_vlan = 1

        # Trunk
        self.allowed_vlans = []
        self.native_vlan = 0

        # General
        self.general_allowed_tagged = []
        self.general_allowed_untagged = []
        self.general_forbiden = []

        self.pvid_vlan = 0

        # Customer
        self.customer_vlan = 0

        # L3
        self.physical_interface_ips = {"DHCP":False}
    

    

    def __repr__(self):
        return f"<Physical_interface name={self.name} mode={self.active_mode} link={self.link_state}>"

class Physical_interface_current_status:
    def __init__(self, name: str, values: list[str]):
        """
        Initialize a physical interface with its base status data.
        """
        self.name = name
        self.type = values[0] if len(values) > 0 else None
        self.duplex = values[1] if len(values) > 1 else None
        self.speed = values[2] if len(values) > 2 else None
        self.negotiation = values[3] if len(values) > 3 else None
        self.flow_ctrl = values[4] if len(values) > 4 else None
        self.link_state = values[5] if len(values) > 5 else None
        self.back_pressure = values[6] if len(values) > 6 else None
        self.mdix_mode = values[7] if len(values) > 7 else None