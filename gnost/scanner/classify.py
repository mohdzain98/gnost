def classify_lines(lines, comment_prefix):
    code = comments = blanks = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            blanks += 1
        elif stripped.startswith(comment_prefix):
            comments += 1
        else:
            code += 1

    return code, comments, blanks
