NO_ACCENT_PT = {
    '@' : 'a',
    '$' : 's',
    '&' : 'e',
    '1' : 'i',
    '0' : 'o',
    '2' : 'z',
    '5' : 's',
    '3' : 'e',
    '4' : 'a',
    '6' : 'b',
    '7' : 't',
    '8' : 'b',
    '9' : 'g',
    'á' : 'a',
    'ã' : 'a',
    'â' : 'a',
    'à' : 'a',
    'é' : 'e',
    'ê' : 'e',
    'í' : 'i',
    'ó' : 'o',
    'õ' : 'o',
    'ô' : 'o',
    'ú' : 'u',
    'ç' : 'c',
    'Á' : 'A',
    'Ã' : 'A',
    'Â' : 'A',
    'À' : 'A',
    'É' : 'E',
    'Ê' : 'E',
    'Í' : 'I',
    'Ó' : 'O',
    'Õ' : 'O',
    'Ô' : 'O',
    'Ú' : 'U',
    'Ç' : 'C',
}


def remove_accent(word):
    result = ""
    for i in range(len(word)):
        c = word[i]
        if c in NO_ACCENT_PT:
            result += NO_ACCENT_PT[c]
        else:
            result += c
    return result


def load_file_into_set(file_path):
    try:
        with open(file_path, 'r', encoding="utf8") as file:
            # Strip whitespace and return words as a set for faster lookup
            blacklist = {remove_accent(line.strip()) for line in file if line.strip()}
        return blacklist
    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
        return set()
