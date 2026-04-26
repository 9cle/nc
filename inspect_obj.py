import importlib
from pathlib import Path
import ncc
importlib.reload(ncc)

source = Path('c:/Users/pc/Downloads/N/hey.n').read_text()
program = ncc.Parser(ncc.tokenize(source)).parse()
cg = ncc.CodeGenerator(program)
text, reloc, rdata, string_positions, function_positions = cg.compile()

sections = [
    ncc.Section('.text', text, reloc, 0x60000020),
    ncc.Section('.rdata', rdata, [], 0x40000040),
]

header_size = 20 + len(sections) * 40
ptr = header_size

def align(v, a):
    return (v + a - 1) // a * a

print('header_size', header_size)
for sec in sections:
    ptr = align(ptr, 4)
    sec.pointer_to_raw = ptr
    print('section', sec.name, 'pointer_to_raw', sec.pointer_to_raw, 'size', len(sec.data))
    ptr += align(len(sec.data), 4)
print('after raw ptr', ptr)
for sec in sections:
    if sec.relocations:
        ptr = align(ptr, 4)
        sec.pointer_to_relocs = ptr
        print('section', sec.name, 'pointer_to_relocs', sec.pointer_to_relocs, 'count', len(sec.relocations))
        ptr += len(sec.relocations) * 10
    else:
        sec.pointer_to_relocs = 0
print('after relocs ptr', ptr)
print('symbol_table_pos', align(ptr, 4))
print('rdata head', rdata[:40])
print('text head', text[:40])
print('string_positions', string_positions)
print('function_positions', function_positions)

file_data = bytearray()
for section in sections:
    while len(file_data) < section.pointer_to_raw:
        file_data.append(0)
    print('before write', section.name, 'len', len(file_data), 'data head', section.data[:24])
    file_data.extend(section.data)
    print('after write', section.name, 'len', len(file_data))
    while len(file_data) < section.pointer_to_raw + align(len(section.data), 4):
        file_data.append(0)
    print('after pad', section.name, 'len', len(file_data))
print('final len after sections', len(file_data))
