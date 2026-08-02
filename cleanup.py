import os
import shutil

def remove_path(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
            print(f"Deleted directory: {path}")
        else:
            os.remove(path)
            print(f"Deleted file: {path}")
    else:
        print(f"Path not found (already deleted?): {path}")

paths_to_remove = [
    os.path.join("jarvis", "team", "specialists", "health_agent.py"),
    os.path.join("jarvis", "plugins", "jira_tracker"),
    os.path.join("jarvis", "plugins", "stripe_monitor"),
    os.path.join("jarvis", "plugins", "health_api")
]

for p in paths_to_remove:
    remove_path(p)

print("Cleanup complete! You can safely delete this script.")
