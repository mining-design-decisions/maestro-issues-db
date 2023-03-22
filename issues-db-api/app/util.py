def read_file_in_chunks(file):
    while True:
        chunk = file.read(1024)
        if not chunk:
            break
        yield chunk
