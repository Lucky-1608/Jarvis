"""
Text formatting utilities for Jarvis.
Ensures responses are clean, readable, and mobile/chat-friendly.
"""
from __future__ import annotations

import re


def convert_tables_to_readable_format(text: str) -> str:
    """
    Converts markdown tables into clean, readable bullet points.
    Tables look terrible on messaging platforms (WhatsApp, Telegram, SMS)
    and terminal/mobile UIs because of wrapping and pipes.
    This converts table rows into formatted key-value bullet points.
    """
    if not text or "|" not in text:
        return text

    lines = text.split("\n")
    output_lines: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if line looks like markdown table header followed by separator (|---|---|)
        if (
            stripped.startswith("|")
            and stripped.endswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", lines[i + 1].strip())
        ):
            header_line = stripped
            raw_headers = [c.strip() for c in header_line.strip("|").split("|")]
            headers = [re.sub(r"^\*+|\*+$", "", h).strip() for h in raw_headers]

            i += 2  # Skip header and separator

            table_rows: list[list[str]] = []
            while i < len(lines):
                row_line = lines[i].strip()
                if not (row_line.startswith("|") and "|" in row_line):
                    break
                raw_cells = [c.strip() for c in row_line.strip("|").split("|")]
                table_rows.append(raw_cells)
                i += 1

            formatted_bullets: list[str] = []
            for cells in table_rows:
                cleaned_cells: list[str] = []
                for cell in cells:
                    # Clean <br> tags into newlines with indentation
                    c = re.sub(r"<\s*br\s*/?>", "\n    ", cell, flags=re.IGNORECASE)
                    cleaned_cells.append(c.strip())

                if len(cleaned_cells) >= 2:
                    k, v = cleaned_cells[0], cleaned_cells[1]
                    clean_k = re.sub(r"^\*+|\*+$", "", k).strip()
                    if len(cleaned_cells) == 2:
                        if "\n" in v:
                            formatted_bullets.append(f"• **{clean_k}:**\n    {v}")
                        else:
                            formatted_bullets.append(f"• **{clean_k}:** {v}")
                    else:
                        first_cell = clean_k
                        rest_parts = [
                            f"*{h}*: {val}"
                            for h, val in zip(headers[1:], cleaned_cells[1:])
                            if val
                        ]
                        details = " | ".join(rest_parts)
                        formatted_bullets.append(f"• **{first_cell}** — {details}")
                elif len(cleaned_cells) == 1 and cleaned_cells[0]:
                    formatted_bullets.append(f"• {cleaned_cells[0]}")

            if formatted_bullets:
                output_lines.append("\n".join(formatted_bullets))
            continue

        output_lines.append(line)
        i += 1

    return "\n".join(output_lines)
