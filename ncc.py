#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import struct
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

KEYWORDS = [
    "import",
    "std",
    "void",
    "pub",
    "type",
    "let",
    "var",
    "mut",
    "nil",
    "if",
    "else",
    "match",
    "loop",
    "break",
    "continue",
    "int",
    "true",
    "false",
    "is",
    "as",
    "defer",
    "test",
    "error",
    "return",
]

TOKEN_SPECIFICATION = [
    ("NUMBER", r"\d+"),
    ("STRING", r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''),
    ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP", r"!=|==|::|\.|\(|\)|\{|\}|;|,|<=|>=|<|>|=|:"),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t\r]+"),
    ("COMMENT", r"//.*"),
]
TOKEN_REGEX = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECIFICATION))

@dataclass
class Token:
    kind: str
    value: str
    line: int
    column: int


def tokenize(source: str) -> List[Token]:
    tokens: List[Token] = []
    line = 1
    line_start = 0
    for mo in TOKEN_REGEX.finditer(source):
        kind = mo.lastgroup
        value = mo.group(kind)
        column = mo.start() - line_start + 1
        if kind == "NEWLINE":
            line += 1
            line_start = mo.end()
        elif kind in ("SKIP", "COMMENT"):
            continue
        else:
            tokens.append(Token(kind, value, line, column))
    tokens.append(Token("EOF", "", line, 1))
    return tokens

@dataclass
class Program:
    imports: List[str]
    functions: List[Any]

@dataclass
class FunctionDecl:
    name: str
    body: List[Any]

@dataclass
class VarDecl:
    type_name: str
    name: str
    value: Any

@dataclass
class IfStmt:
    condition: Any
    then_branch: List[Any]
    elif_branches: List[Tuple[Any, List[Any]]]
    else_branch: Optional[List[Any]]

@dataclass
class ReturnStmt:
    expr: Optional[Any]

@dataclass
class ExprStmt:
    expr: Any

@dataclass
class CallExpr:
    target: str
    args: List[Any]

@dataclass
class BinaryOp:
    op: str
    left: Any
    right: Any

@dataclass
class Ident:
    name: str

@dataclass
class IntLit:
    value: int

@dataclass
class StringLit:
    value: str

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self) -> Token:
        return self.tokens[self.pos]

    def eat(self, kind: str, value: Optional[str] = None) -> Token:
        tok = self.current()
        if tok.kind != kind and tok.value != kind:
            raise SyntaxError(f"Expected {kind} but got {tok.kind} ({tok.value}) at {tok.line}:{tok.column}")
        if value is not None and tok.value != value:
            raise SyntaxError(f"Expected {value} but got {tok.value} at {tok.line}:{tok.column}")
        self.pos += 1
        return tok

    def accept(self, kind: str, value: Optional[str] = None) -> Optional[Token]:
        tok = self.current()
        if tok.kind == kind or tok.value == kind:
            if value is None or tok.value == value:
                self.pos += 1
                return tok
        return None

    def parse(self) -> Program:
        imports: List[str] = []
        functions: List[Any] = []
        while self.current().kind != "EOF":
            if self.current().value == "import":
                self.eat("ID")
                imports.append(self.parse_import())
            elif self.current().value == "void":
                self.eat("ID")
                functions.append(self.parse_function())
            else:
                raise SyntaxError(f"Unexpected token {self.current().value} at {self.current().line}:{self.current().column}")
        return Program(imports, functions)

    def parse_import(self) -> str:
        name = self.eat("ID").value
        self.eat(";")
        return name

    def parse_function(self) -> FunctionDecl:
        name = self.eat("ID").value
        self.eat("(")
        self.eat(")")
        self.eat("{")
        body = self.parse_block()
        return FunctionDecl(name, body)

    def parse_block(self) -> List[Any]:
        stmts: List[Any] = []
        while not self.accept("}"):
            stmts.append(self.parse_statement())
        return stmts

    def parse_statement(self) -> Any:
        tok = self.current()
        if tok.value == "int":
            return self.parse_var_decl()
        if tok.value == "return":
            self.eat("ID")
            expr = None
            if self.current().value != ";":
                expr = self.parse_expression()
            self.eat(";")
            return ReturnStmt(expr)
        if tok.value == "if":
            return self.parse_if()
        expr = self.parse_expression()
        if self.current().value == ";":
            self.eat(";")
        return ExprStmt(expr)

    def parse_var_decl(self) -> VarDecl:
        self.eat("ID")
        name = self.eat("ID").value
        self.eat("OP", ":")
        value = self.parse_expression()
        self.eat(";")
        return VarDecl("int", name, value)

    def parse_if(self) -> IfStmt:
        self.eat("ID")
        if self.accept("("):
            cond = self.parse_expression()
            self.eat(")")
        else:
            cond = self.parse_expression()
        self.eat("{")
        then_branch = self.parse_block()
        elif_branches: List[Tuple[Any, List[Any]]] = []
        else_branch: Optional[List[Any]] = None
        while self.accept("ID", "else"):
            if self.accept("ID", "if"):
                if self.accept("("):
                    elif_cond = self.parse_expression()
                    self.eat(")")
                else:
                    elif_cond = self.parse_expression()
                self.eat("{")
                elif_body = self.parse_block()
                elif_branches.append((elif_cond, elif_body))
            else:
                self.eat("{")
                else_branch = self.parse_block()
                break
        return IfStmt(cond, then_branch, elif_branches, else_branch)

    def parse_expression(self) -> Any:
        node = self.parse_primary()
        if self.current().value in ("==", "!="):
            op = self.current().value
            self.eat("OP")
            right = self.parse_primary()
            return BinaryOp(op, node, right)
        return node

    def parse_inline_expression(self, source: str) -> Any:
        tokens = tokenize(source)
        parser = Parser(tokens)
        expr = parser.parse_expression()
        if parser.current().kind != "EOF":
            raise SyntaxError(f"Unexpected token in embedded code: {parser.current().value}")
        return expr

    def parse_primary(self) -> Any:
        tok = self.current()
        if tok.kind == "STRING":
            self.pos += 1
            return StringLit(eval(tok.value))
        if tok.kind == "NUMBER":
            self.pos += 1
            return IntLit(int(tok.value))
        if tok.kind == "ID":
            name = self.eat("ID").value
            while self.current().kind == "OP" and self.current().value in (".", "::"):
                connector = self.current().value
                self.eat("OP", connector)
                name += "." + self.eat("ID").value
            if self.current().kind == "OP" and self.current().value == "(":
                self.eat("OP", "(")
                args: List[Any] = []
                if self.current().value != ")":
                    args.append(self.parse_expression())
                    while self.accept("OP", ","):
                        args.append(self.parse_expression())
                self.eat("OP", ")")
                return CallExpr(name, args)
            return Ident(name)
        if tok.value == "(":
            self.eat("OP", "(")
            expr = self.parse_expression()
            self.eat("OP", ")")
            return expr
        raise SyntaxError(f"Unexpected expression token {tok.value} at {tok.line}:{tok.column}")

@dataclass
class Relocation:
    symbol_name: str
    offset: int
    type: int

@dataclass
class FunctionCode:
    name: str
    code: bytearray = field(default_factory=bytearray)
    relocs: List[Relocation] = field(default_factory=list)
    label_positions: Dict[str, int] = field(default_factory=dict)
    patches: List[Tuple[int, str]] = field(default_factory=list)
    locals: Dict[str, int] = field(default_factory=dict)
    next_local_slot: int = 0
    label_gen: int = 0

    def position(self) -> int:
        return len(self.code)

    def emit(self, data: bytes) -> None:
        self.code.extend(data)

    def emit_u32(self, value: int) -> None:
        self.code.extend(struct.pack("<I", value & 0xFFFFFFFF))

    def add_reloc(self, symbol_name: str, offset: int) -> None:
        self.relocs.append(Relocation(symbol_name, offset, 0x0004))

    def define_label(self, label: str) -> None:
        self.label_positions[label] = self.position()

    def unique_label(self, prefix: str) -> str:
        label = f"{prefix}_{self.label_gen}"
        self.label_gen += 1
        return label

    def emit_call(self, symbol: str) -> None:
        self.emit(b"\xE8")
        self.emit_u32(0)
        self.add_reloc(symbol, self.position() - 4)

    def emit_lea_rip(self, reg: int, symbol: str) -> None:
        self.emit(b"\x48")
        self.emit(bytes([0x8D, 0x05 + (reg << 3)]))
        self.emit_u32(0)
        self.add_reloc(symbol, self.position() - 4)

    def emit_jmp(self, label: str) -> None:
        self.emit(b"\xE9")
        self.emit_u32(0)
        self.patches.append((self.position() - 4, label))

    def emit_cond_jmp(self, opcode: bytes, label: str) -> None:
        self.emit(opcode)
        self.emit_u32(0)
        self.patches.append((self.position() - 4, label))

    def patch_labels(self) -> None:
        for offset, label in self.patches:
            if label not in self.label_positions:
                raise RuntimeError(f"Undefined label {label}")
            target = self.label_positions[label]
            rel = target - (offset + 4)
            self.code[offset:offset + 4] = struct.pack("<i", rel)

    def allocate_local(self, name: str) -> int:
        if name in self.locals:
            return self.locals[name]
        offset = -4 - self.next_local_slot * 4
        self.next_local_slot += 1
        self.locals[name] = offset
        return offset

    def get_local_offset(self, name: str) -> int:
        return self.locals[name]

class CodeGenerator:
    def __init__(self, program: Program):
        self.program = program
        self.functions: Dict[str, FunctionCode] = {}
        self.string_literals: Dict[str, str] = {}
        self.string_order: List[str] = []

    def compile(self) -> Tuple[bytes, List[Tuple[int, str, int]], bytes, Dict[str, int], Dict[str, int]]:
        for func in self.program.functions:
            self.functions[func.name] = self.compile_function(func)
        for func_code in self.functions.values():
            func_code.patch_labels()

        text_data = bytearray()
        function_positions: Dict[str, int] = {}
        for func in self.program.functions:
            function_positions[func.name] = len(text_data)
            code = self.functions[func.name].code
            text_data.extend(code)

        rdata = bytearray()
        string_positions: Dict[str, int] = {}
        for label in self.string_order:
            string_positions[label] = len(rdata)
            rdata.extend(self.string_literals[label].encode("utf-8") + b"\x00")

        reloc_records: List[Tuple[int, str, int]] = []
        for func in self.program.functions:
            base = function_positions[func.name]
            for reloc in self.functions[func.name].relocs:
                reloc_records.append((base + reloc.offset, reloc.symbol_name, reloc.type))

        return bytes(text_data), reloc_records, bytes(rdata), string_positions, function_positions


    def compile_function(self, func: FunctionDecl) -> FunctionCode:
        fc = FunctionCode(func.name)
        fc.emit(b"\x55")
        fc.emit(b"\x48\x89\xE5")
        fc.emit(b"\x48\x81\xEC\x80\x00\x00\x00") # sub rsp, 128

        for stmt in func.body:
            self.compile_stmt(fc, stmt)
        fc.emit(b"\xB8\x00\x00\x00\x00")
        fc.emit(b"\xC9")
        fc.emit(b"\xC3")
        return fc

    def compile_stmt(self, fc: FunctionCode, stmt: Any) -> None:
        if isinstance(stmt, VarDecl):
            self.compile_var_decl(fc, stmt)
        elif isinstance(stmt, IfStmt):
            self.compile_if(fc, stmt)
        elif isinstance(stmt, ExprStmt):
            self.compile_expr(fc, stmt.expr)
        elif isinstance(stmt, ReturnStmt):
            if stmt.expr is not None:
                self.compile_expr(fc, stmt.expr)
            fc.emit(b"\xC9\xC3")
        else:

            raise RuntimeError(f"Unsupported statement type {type(stmt)}")

    def compile_var_decl(self, fc: FunctionCode, decl: VarDecl) -> None:
        offset = fc.allocate_local(decl.name)
        if decl.type_name != "int":
            raise RuntimeError(f"Only int declarations are supported, got {decl.type_name}")
        if not isinstance(decl.value, IntLit):
            raise RuntimeError("Only integer literals are supported in declarations")
        fc.emit(b"\xC7\x45")
        fc.emit(bytes([offset & 0xFF]))
        fc.emit(struct.pack("<I", decl.value.value))

    def compile_if(self, fc: FunctionCode, stmt: IfStmt) -> None:
        then_label = fc.unique_label("then")
        else_label = fc.unique_label("else")
        end_label = fc.unique_label("end")
        self.compile_condition(fc, stmt.condition, then_label, else_label)
        fc.define_label(then_label)
        self.compile_block(fc, stmt.then_branch)
        fc.emit_jmp(end_label)
        current_else = else_label
        for elif_cond, elif_body in stmt.elif_branches:
            fc.define_label(current_else)
            next_else = fc.unique_label("else")
            next_then = fc.unique_label("then")
            self.compile_condition(fc, elif_cond, next_then, next_else)
            fc.define_label(next_then)
            self.compile_block(fc, elif_body)
            fc.emit_jmp(end_label)
            current_else = next_else
        fc.define_label(current_else)
        if stmt.else_branch is not None:
            self.compile_block(fc, stmt.else_branch)
        fc.define_label(end_label)

    def compile_condition(self, fc: FunctionCode, expr: Any, true_label: str, false_label: str) -> None:
        if not isinstance(expr, BinaryOp):
            raise RuntimeError("Only equality conditions are supported")
        if not isinstance(expr.left, Ident) or not isinstance(expr.right, IntLit):
            raise RuntimeError("Conditions must compare a variable to an integer literal")
        offset = fc.get_local_offset(expr.left.name)
        fc.emit(b"\x83\x7D")
        fc.emit(bytes([offset & 0xFF]))
        fc.emit(bytes([expr.right.value & 0xFF]))
        if expr.op == "==":
            fc.emit_cond_jmp(b"\x0F\x84", true_label)
        elif expr.op == "!=":
            fc.emit_cond_jmp(b"\x0F\x85", true_label)
        else:
            raise RuntimeError(f"Unsupported operator {expr.op}")
        fc.emit_jmp(false_label)

    def compile_block(self, fc: FunctionCode, stmts: List[Any]) -> None:
        for stmt in stmts:
            self.compile_stmt(fc, stmt)

    def compile_expr(self, fc: FunctionCode, expr: Any) -> None:
        if isinstance(expr, CallExpr):
            self.compile_call(fc, expr)
            return
        raise RuntimeError(f"Unsupported expression {expr}")

    def compile_call(self, fc: FunctionCode, call: CallExpr) -> None:
        if call.target == "std.pln":
            if len(call.args) != 1 or not isinstance(call.args[0], StringLit):
                raise RuntimeError("std.pln only supports one string literal")
            label = self.register_string(call.args[0].value)
            fc.emit_lea_rip(1, label)
            fc.emit_call("puts")
        elif call.target == "std.repeat":
            if len(call.args) != 2 or not isinstance(call.args[0], StringLit) or not isinstance(call.args[1], IntLit):
                raise RuntimeError("std.repeat requires a string literal and an integer literal")
            count = call.args[1].value
            inner_expr = Parser(tokenize(call.args[0].value)).parse_expression()
            for _ in range(count):
                self.compile_expr(fc, inner_expr)
        elif call.target in self.functions:
            fc.emit_call(call.target)
        else:
            raise RuntimeError(f"Unknown call target {call.target}")

    def register_string(self, value: str) -> str:
        for name, text in self.string_literals.items():
            if text == value:
                return name
        label = f".L_str_{len(self.string_order)}"
        self.string_literals[label] = value
        self.string_order.append(label)
        return label

@dataclass
class Section:
    name: str
    data: bytes
    relocations: List[Tuple[int, int, int]]
    characteristics: int
    pointer_to_raw: int = 0
    pointer_to_relocs: int = 0

class ObjectWriter:
    def __init__(self, text: bytes, relocations: List[Tuple[int, str, int]], rdata: bytes, string_positions: Dict[str, int], function_positions: Dict[str, int]):
        self.text = text
        self.relocations = relocations
        self.rdata = rdata
        self.string_positions = string_positions
        self.function_positions = function_positions

    def write(self, path: str) -> None:
        sections: List[Section] = [
            Section(".text", self.text, [], 0x60000020),
            Section(".rdata", self.rdata, [], 0x40000040),
        ]
        symbol_entries: List[Tuple[str, int, int, int, int]] = []
        symbol_index: Dict[str, int] = {}
        for func_name, offset in self.function_positions.items():
            symbol_index[func_name] = len(symbol_entries)
            symbol_entries.append((func_name, offset, 1, 0x20, 2))
        for label, pos in self.string_positions.items():
            symbol_index[label] = len(symbol_entries)
            symbol_entries.append((label, pos, 2, 0, 3))
        symbol_index["puts"] = len(symbol_entries)
        symbol_entries.append(("puts", 0, 0, 0x20, 2))
        for reloc_offset, symbol_name, type_val in self.relocations:
            sym_idx = symbol_index[symbol_name]
            sections[0].relocations.append((reloc_offset, sym_idx, type_val))
        header_size = 20 + len(sections) * 40
        pointer = header_size
        for section in sections:
            pointer = self.align(pointer, 4)
            section.pointer_to_raw = pointer
            pointer += self.align(len(section.data), 4)
        for section in sections:
            if section.relocations:
                pointer = self.align(pointer, 4)
                section.pointer_to_relocs = pointer
                pointer += len(section.relocations) * 10
            else:
                section.pointer_to_relocs = 0
        symbol_table_pos = self.align(pointer, 4)
        string_table, string_offsets = self.build_string_table(symbol_entries)
        file_data = bytearray()
        file_data.extend(struct.pack("<HHLLLHH", 0x8664, len(sections), 0, symbol_table_pos, len(symbol_entries), 0, 0))
        for section in sections:
            name_bytes = section.name.encode("utf-8")
            file_data.extend(name_bytes.ljust(8, b"\x00"))
            file_data.extend(struct.pack("<LLLLLLHHL", 0, 0, len(section.data), section.pointer_to_raw, section.pointer_to_relocs, 0, len(section.relocations), 0, section.characteristics))
        for section in sorted(sections, key=lambda s: s.pointer_to_raw):
            while len(file_data) < section.pointer_to_raw:
                file_data.append(0)
            file_data.extend(section.data)
            while len(file_data) < section.pointer_to_raw + self.align(len(section.data), 4):
                file_data.append(0)
        for section in sorted(sections, key=lambda s: s.pointer_to_relocs or float("inf")):
            if section.relocations:
                while len(file_data) < section.pointer_to_relocs:
                    file_data.append(0)
                for offset, sym_idx, type_val in section.relocations:
                    file_data.extend(struct.pack("<LLH", offset, sym_idx, type_val))
        while len(file_data) < symbol_table_pos:
            file_data.append(0)
        for name, value, section_number, type_val, storage_class in symbol_entries:
            file_data.extend(self.symbol_record(name, value, section_number, type_val, storage_class, string_offsets))
        file_data.extend(string_table)
        with open(path, "wb") as f:
            f.write(file_data)

    def symbol_record(self, name: str, value: int, section_number: int, type_val: int, storage_class: int, string_offsets: Dict[str, int]) -> bytes:
        if len(name) <= 8:
            name_field = name.encode("utf-8").ljust(8, b"\x00")
        else:
            offset = string_offsets[name]
            name_field = struct.pack("<LL", 0, offset)
        rec = bytearray(name_field)
        rec.extend(struct.pack("<LhHBB", value, section_number, type_val, storage_class, 0))
        return bytes(rec)

    def build_string_table(self, symbol_entries: List[Tuple[str, int, int, int, int]]) -> Tuple[bytes, Dict[str, int]]:
        data = bytearray(b"\x00\x00\x00\x00")
        offsets = {}
        for name, *_ in symbol_entries:
            if len(name) > 8:
                offsets[name] = len(data)
                data.extend(name.encode("utf-8") + b"\x00")
        return struct.pack("<L", len(data)) + data[4:], offsets


    @staticmethod
    def align(value: int, alignment: int) -> int:
        return (value + alignment - 1) // alignment * alignment


def find_linker() -> Optional[Tuple[str, List[str]]]:
    for cmd in ["gcc", "clang", "link.exe", "cl.exe"]:
        path = shutil.which(cmd)
        if path:
            if cmd in ("gcc", "clang"):
                return cmd, [cmd]
            if cmd == "link.exe":
                return cmd, [cmd, "/NOLOGO"]
            if cmd == "cl.exe":
                return cmd, [cmd, "/nologo"]
    return None


def link_object(obj_path: str, exe_path: str) -> bool:
    linker = find_linker()
    if not linker:
        print("No linker found on system. Object file generated but not linked.")
        return False
    cmd_name, cmd_base = linker
    if cmd_name in ("gcc", "clang"):
        cmd = cmd_base + ["-o", exe_path, obj_path]
    elif cmd_name == "link.exe":
        cmd = cmd_base + ["/OUT:" + exe_path, obj_path]
    elif cmd_name == "cl.exe":
        cmd = cmd_base + [obj_path, "/Fe:" + exe_path]
    else:
        print(f"Unsupported linker {cmd_name}")
        return False
    print("Linking with:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        return False
    return True


def load_keywords(path: str) -> List[str]:
    if not os.path.exists(path):
        return KEYWORDS
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    words = [line.strip().split()[0] for line in lines if line.strip() and not line.startswith("//")]
    return [w for w in words if w]


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal .n compiler that emits Windows COFF .obj and links to .exe")
    parser.add_argument("source", help="Input .n source file")
    parser.add_argument("--out", help="Output base name (without extension)", default=None)
    parser.add_argument("--no-link", action="store_true", help="Only emit .obj and do not link")
    args = parser.parse_args()

    if not args.source.endswith(".n"):
        print("Source file must use .n extension")
        return 1
    base = args.out or os.path.splitext(os.path.basename(args.source))[0]
    obj_path = base + ".obj"
    exe_path = base + ".exe"

    with open(args.source, "r", encoding="utf-8") as f:
        source_text = f.read()
    tokens = tokenize(source_text)
    program = Parser(tokens).parse()
    cg = CodeGenerator(program)
    text_data, relocations, rdata, string_positions, function_positions = cg.compile()
    writer = ObjectWriter(text_data, relocations, rdata, string_positions, function_positions)
    writer.write(obj_path)
    print(f"Wrote {obj_path}")
    if not args.no_link:
        if link_object(obj_path, exe_path):
            print(f"Linked {exe_path}")
        else:
            print(f"Failed to link {exe_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())