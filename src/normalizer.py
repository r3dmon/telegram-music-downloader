import re
from typing import List

def fix_extra_spaces(text: str) -> str:
    """Remove extra spaces and trim the string."""
    return re.sub(r'\s{2,}', ' ', text).strip()

def fix_spaces_in_brackets(text: str) -> str:
    """Remove spaces after opening and before closing brackets."""
    text = re.sub(r'(\[|\()\s+', r'\1', text)
    text = re.sub(r'\s+(\]|\))', r'\1', text)
    return text

def fix_missing_spaces_around_brackets(text: str) -> str:
    """Ensure spaces around brackets where needed."""
    text = re.sub(r'(?<!\s)(?=\[|\()', ' ', text)
    text = re.sub(r'(?<=\]|\))(?=\S)', ' ', text)
    return text.strip()

def fix_underscores_with_spaces(text: str) -> str:
    """Replace underscores with spaces and remove extra spaces."""
    return re.sub(r'\s{2,}', ' ', text.replace('_', ' ')).strip()

def remove_message_id(text: str) -> str:
    """Remove message IDs or trailing numbers that are not part of the title."""
    # Typical pattern: double underscores followed by digits at the end
    return re.sub(r'__\d+$', '', text)

def fix_extra_spaces(text: str) -> str:
    """Remove extra spaces and trim the string."""
    return re.sub(r'\s{2,}', ' ', text).strip()

def fix_spaces_in_brackets(text: str) -> str:
    """Remove spaces after opening and before closing brackets."""
    text = re.sub(r'(\[|\()\s+', r'\1', text)
    text = re.sub(r'\s+(\]|\))', r'\1', text)
    return text

def fix_missing_spaces_around_brackets(text: str) -> str:
    """Ensure spaces around brackets where needed."""
    text = re.sub(r'(?<!\s)(?=\[|\()', ' ', text)
    text = re.sub(r'(?<=\]|\))(?=\S)', ' ', text)
    return text.strip()

def fix_underscores_with_spaces(text: str) -> str:
    """Replace underscores with spaces and remove extra spaces."""
    return re.sub(r'\s{2,}', ' ', text.replace('_', ' ')).strip()

def wrap_and_move_mix_types(file_name: str) -> str:
    """Wrap mix types in parentheses and move them to the end if needed."""
    mix_types = [
        "Original Mix", "Radio Edit", "Extended Mix", "Club Mix", "Dub Mix",
        "Vocal Mix", "Instrumental Mix", "Remix", "VIP Mix", "Bootleg Mix",
        "Mashup", "Radio Mix", "Dance Mix", "Progressive Mix", "Deep Mix",
        "Tech Mix", "Minimal Mix", "Acoustic Mix", "Unplugged Mix", "Live Mix",
        "Studio Mix", "Demo Mix", "Alternative Mix", "Special Mix", "Bonus Mix",
        "Short Mix", "Long Mix", "Full Mix", "Edit", "Version", "Rework"
    ]
    found_mixes: List[str] = []
    for mix_type in mix_types:
        pattern = rf'(?<!\[|\()({re.escape(mix_type)})(?!\]|\))'
        matches = re.findall(pattern, file_name, re.IGNORECASE)
        for match in matches:
            cap = capitalize_words(match)
            found_mixes.append(f'({cap})')
        file_name = re.sub(pattern, '', file_name, flags=re.IGNORECASE)
    if found_mixes:
        file_name = re.sub(r'\s{2,}', ' ', file_name).strip()
        mixes_string = ' '.join(found_mixes)
        return f'{file_name} {mixes_string}'.strip()
    return file_name

def move_square_bracket_content_to_end(text: str) -> str:
    """Move all [...] blocks to the end, preserving order."""
    matches = re.findall(r'\[[^\]]+\]', text)
    text_wo_brackets = re.sub(r'\[[^\]]+\]', '', text)
    text_wo_brackets = fix_extra_spaces(text_wo_brackets)
    return fix_extra_spaces(text_wo_brackets + ' ' + ' '.join(matches))

def move_vinyl_track_numbers_to_start(text: str) -> str:
    """Move vinyl track numbers (like A1, B2) to the beginning."""
    match = re.search(r'(?:\s|^)([A-D][0-9]{1,2})(?:\s|$)', text)
    if match:
        number = match.group(1)
        text = re.sub(r'(?:\s|^)' + re.escape(number) + r'(?:\s|$)', ' ', text)
        text = fix_extra_spaces(text)
        text = f'{number} {text}'
    return text

def remove_vinyl_tags(text: str) -> str:
    """Remove tags like 'Vinyl', 'LP', 'EP', 'Single' in brackets or standalone."""
    return re.sub(r'\b(?:Vinyl|LP|EP|Single)\b', '', text, flags=re.IGNORECASE)

def remove_musical_keys(text: str) -> str:
    """Remove Camelot musical keys (e.g., 1A, 2B) in brackets or standalone."""
    camelot = [f'{i}{k}' for i in range(1,13) for k in ['A','B']]
    for key in camelot:
        text = re.sub(rf'(\s|\[|\()({key})(\s|\]|\))', ' ', text, flags=re.IGNORECASE)
    return fix_extra_spaces(text)

def remove_audio_tags(text: str) -> str:
    """Remove common audio tags (e.g., 320kbps, FLAC, WEB, etc.)"""
    tags = [
        r'320\s?kbps', r'192\s?kbps', r'256\s?kbps', r'flac', r'web', r'cdq', r'promo',
        r'cdm', r'cd', r'single', r'ep', r'lp', r'vinyl', r'album', r'original', r'mix', r'edit',
        r'extended', r'full', r'clean', r'dirty', r'instrumental', r'acapella', r'remix', r'bootleg', r'cover'
    ]
    for tag in tags:
        text = re.sub(rf'\b{tag}\b', '', text, flags=re.IGNORECASE)
    return fix_extra_spaces(text)

def fix_residual_characters(text: str) -> str:
    """Remove trailing dashes, dots, and fix double spaces."""
    text = re.sub(r'[-–—.\s]+$', '', text)
    text = re.sub(r'^[-–—.\s]+', '', text)
    return fix_extra_spaces(text)

"""Apply all normalization steps to a track name in strict order."""

def normalize_track_name(file_name: str) -> str:
    name = file_name
    name = remove_message_id(name)
    name = fix_extra_spaces(name)
    name = fix_spaces_in_brackets(name)
    name = fix_missing_spaces_around_brackets(name)
    name = fix_underscores_with_spaces(name)
    name = wrap_and_move_mix_types(name)
    name = move_square_bracket_content_to_end(name)
    name = move_vinyl_track_numbers_to_start(name)
    name = remove_vinyl_tags(name)
    name = remove_musical_keys(name)
    name = remove_audio_tags(name)
    name = fix_residual_characters(name)
    return name

# You can expand this module with more rules from the C# code as needed.
