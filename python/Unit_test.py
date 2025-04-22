from infrastructure.ssh_client import Session_handler
from core.initializer import Initializer
import time

def print_getdata_output(ip:str, username:str, password:str):
    session = Session_handler(ip, username, password)
    initializer = Initializer(session)
    print(session.connect())
    initializer.initialize()
    for line in initializer.running_config:print(line)
    print("\n" * 3)
    for line in initializer.startup_config:print(line)
    print("\n" * 3)
    print(f"Model name:{initializer.model_name}")
    print('\n')
    print(initializer.interfaces_status)  
    session.disconnect()

def print_physical_interfaces(ip: str, username: str, password: str):
    session = Session_handler(ip, username, password)
    initializer = Initializer(session)
    print(session.connect())
    initializer.initialize()

    for iface_name, iface_obj in initializer.physical_interfaces_settings_objects.items():
        print(f"\n--- Interface: {iface_name} ---")
        for key, value in vars(iface_obj).items():
            print(f"{key}: {value}")
    

    session.disconnect()

if __name__ == '__main__':
    print_physical_interfaces("172.20.30.198", "TestAdmin", "Pa$$w0rd")
    #print_getdata_output("172.20.30.198", "TestAdmin", "Pa$$w0rd")
