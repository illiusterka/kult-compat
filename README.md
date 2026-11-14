# KULT: Heretic Kingdoms — Proton texture-format workaround

This project contains a checksum-guarded, reversible patcher for missing menu
text and the missing Monastery Gate background seen with KULT: Heretic Kingdoms
under Proton. It includes no game assets or binaries; it edits files in the
user's own Steam installation.

**AI disclosure:** The code, installer configuration, and documentation in
this repository are 100% AI-generated.

## What it changes

The game stores a format code in texture records in `data/levels/*.dat`.
Affected records marked `0x02` have four-byte-per-pixel rows, but under the
tested Proton setup D3DX treats that code as unsupported and falls back to
one-byte `A8`. This makes menu text invisible or corrupted and leaves part of
the opening area black.

The patcher changes only those record-header fields from `0x02` to `0x15`
(`D3DFMT_A8R8G8B8`), matching the four-byte row stride. It patches every
checksum-verified interface and level archive found in this game build (16
archive pairs, including all language variants and seven level archives) by
default. It does not change texture pixels, the executable, configuration, or
Proton settings.

## Apply

Requires Python 3; no third-party packages are used. Close the game first.

1. Preview all changes:

   ```sh
   python3 kult_texture_format_patcher.py --game-dir "/path/to/Kult Heretic Kingdoms"
   ```

   Preview is the default and writes nothing.

2. Apply after reviewing the preview:

   ```sh
   python3 kult_texture_format_patcher.py --game-dir "/path/to/Kult Heretic Kingdoms" --apply
   ```

   Each original archive is preserved beside the file as
   `<archive>.dat.kult-compat.bak`. The utility verifies the resource and index
   checksums before writing, makes an atomic replacement, and checks the result
   afterward. Unknown or changed game files are refused without edits.

3. Launch the game normally through Steam/Proton.

To undo the change:

```sh
python3 kult_texture_format_patcher.py --game-dir "/path/to/Kult Heretic Kingdoms" --restore
```

## Lutris installer

[`lutris-installer.yaml`](./lutris-installer.yaml) uses Lutris's Steam source
to install or reuse Steam AppID `277650`, then downloads the patcher from this
repository's `main` branch and applies all recognized resource fixes. The
installer downloads the script from GitHub rather than using a copy in your
local checkout, so the renamed script must be present on `main` for that
download to work. Import it with:

```sh
lutris -i ./lutris-installer.yaml
```

Steam must be installed, logged in, and own the game. Lutris does not select a
Proton version; configure that in Steam's Compatibility settings if needed.

## Verification

The English menu was visually tested under Proton 11. The Monastery Gate fix
was verified in an A/B test using the same save and isolated original/patched
copies: the original showed the right side black, while the patched copy
rendered the full scene. The other level archives are patched because their
format-`0x02` textures also have four-byte strides, but those areas have not
been visually tested. The installed original files are kept in
`.kult-compat.bak` backups, and the user's save is not modified.
