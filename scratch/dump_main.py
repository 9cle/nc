import struct

def read_u32(data, offset):
    return struct.unpack_from('<L', data, offset)[0]

def read_u16(data, offset):
    return struct.unpack_from('<H', data, offset)[0]

with open('hey_fixed.obj', 'rb') as f:
    data = f.read()

num_sections = read_u16(data, 2)
# Section headers start at 20.
text_header = None
for i in range(num_sections):
    h = data[20 + i*40 : 60 + i*40]
    name = h[:8].rstrip(b'\x00').decode()
    if name == '.text':
        text_header = h
        break

if not text_header:
    print("No .text section")
    exit(1)

text_size = read_u32(text_header, 16)
text_ptr = read_u32(text_header, 20)

text_data = data[text_ptr:text_ptr+text_size]

# Find main symbol address
symbol_table_ptr = read_u32(data, 8)
num_symbols = read_u32(data, 12)
string_table_ptr = symbol_table_ptr + num_symbols * 18

def get_symbol_name(idx):
    offset = symbol_table_ptr + idx * 18
    name_field = data[offset : offset+8]
    if read_u32(name_field, 0) == 0:
        str_offset = read_u32(name_field, 4)
        # string table starts with its size (4 bytes)
        # names start after that
        s = data[string_table_ptr + str_offset:]
        return s[:s.find(b'\x00')].decode()
    else:
        return name_field.rstrip(b'\x00').decode()

main_offset = None
for i in range(num_symbols):
    name = get_symbol_name(i)
    if name == 'main':
        main_offset = read_u32(data, symbol_table_ptr + i * 18 + 8)
        break

if main_offset is None:
    print("No main symbol")
    exit(1)

main_code = text_data[main_offset:]
print(f"Main starts at {main_offset}")
print(f"Main code (hex): {main_code[:128].hex(' ')}")
