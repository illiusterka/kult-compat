# KULT: Heretic Kingdoms — Proton UI workaround

This package contains a small, reversible patcher for the missing/corrupted
menu UI seen with KULT: Heretic Kingdoms under Proton. It includes no game
assets, executable, DLLs, or other copyrighted game content; it edits files in
the user's own Steam installation.

## What it changes

The game stores a format code in each texture record in `data/levels/main_*.dat`.
For records whose code is `0x02`, the payload rows are four bytes per pixel.
Under the tested Proton setup, the game passes `0x02` to D3DX, which treats it
as an unsupported format and falls back to one-byte `A8`. The game then reads
only the wrong number of bytes per row, making menu labels invisible or
corrupted.

The patcher changes only those record-header fields from `0x02` to `0x15`
(`D3DFMT_A8R8G8B8`), matching the four-byte row stride. It does not change
texture pixels, the executable, configuration, or Proton settings.

## Apply

Requires Python 3; no third-party packages are used. Close the game first.

1. Preview the change. The tool detects the language in `config.cfg`:

   ```sh
   python3 kult_proton_ui_fix.py --game-dir "/path/to/Kult Heretic Kingdoms"
   ```

   Preview is the default and writes nothing. To choose a language explicitly,
   add `--language eng` (supported codes: `br`, `ch`, `de`, `eng`, `es`, `fr`,
   `it`, `ru`; `main` selects an unsuffixed `main.dat`).

2. Apply after reviewing the preview:

   ```sh
   python3 kult_proton_ui_fix.py --game-dir "/path/to/Kult Heretic Kingdoms" --apply
   ```

   The original resource is preserved next to the file as
   `main_<language>.dat.kult-compat.bak`. The utility verifies the resource and
   index checksums before writing, makes an atomic replacement, and checks the
   result afterward. Unknown or changed game files are refused without edits.

3. Launch the game normally through Steam/Proton.

To undo the change:

```sh
python3 kult_proton_ui_fix.py --game-dir "/path/to/Kult Heretic Kingdoms" --restore
```

The `--language` option also applies to `--restore`.
