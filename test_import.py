import sys
sys.path.insert(0, 'D:/Programacion/Python/OpenCode/MQTT_Dashboard')

# Clear any cached modules
for mod in list(sys.modules.keys()):
    if 'src' in mod or 'mqtt' in mod:
        del sys.modules[mod]

print("Python:", sys.executable)
print("Module path:", __file__)

# Direct import
from src import mqtt_callbacks
import inspect

print("\n=== Codigo fuente de get_tasks_info_from_globals ===")
print(inspect.getsource(mqtt_callbacks.get_tasks_info_from_globals))
