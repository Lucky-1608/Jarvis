import os


def update_env_file(env_path: str, updates: dict[str, str]) -> None:
    """Updates or adds variables in the .env file while preserving comments and order."""
    if not os.path.exists(env_path):
        lines = []
    else:
        with open(env_path, encoding='utf-8') as f:
            lines = f.readlines()

    updated_keys = set()
    new_lines = []

    # Update existing keys
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            new_lines.append(line)
            continue

        if '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
                # update os environment directly
                os.environ[key] = str(updates[key])
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Add new keys
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")
            os.environ[key] = str(value)

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
