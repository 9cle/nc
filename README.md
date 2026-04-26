# N Compiler

This project contains a minimal compiler for `.n` source files.

## Files

- `ncc.py` — compiler script that parses `.n` files, emits a Windows COFF `.obj`, and links it to an `.exe` if a system linker is available.
- `keywords.txt` — the reserved keywords used by the `.n` language.
- `hey.n` — example source file.

## Usage

Run the compiler with Python:

```powershell
python ncc.py hey.n
```

This produces:

- `hey.obj`
- `hey.exe` (if a linker is available on the system)

If you only want the object file, use:

```powershell
python ncc.py hey.n --no-link
```

## Compiler executable

A standalone compiler executable is also built as `nc.exe` in the workspace root. Use it like this:

```powershell
./nc.exe hey.n --out hey
```

## VS Code extension

A basic language extension for `.n` files is available in the `n-extension` folder. It provides syntax highlighting and `.n` file association.

## Linker detection

The compiler attempts to invoke one of:

- `gcc`
- `clang`
- `link.exe`
- `cl.exe`

If no linker is found, the `.obj` file is still generated.
