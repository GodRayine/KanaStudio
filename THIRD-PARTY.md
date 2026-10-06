# Third-party components

The application's original Python code is provided under GNU GPL version 3 or any later version (GPL-3.0-or-later). See LICENSE and COPYRIGHT. Copyright (C) 2026 GodRayine. The bundled runtime and libraries retain their own licenses and copyrights.

- **Python 3.12.9** — Python Software Foundation and other copyright holders. License and notices: `licenses/Python.txt`. Source: https://www.python.org/downloads/release/python-3129/.
- **PySide6 6.11.2, Shiboken6 6.11.2, Qt 6.11.2** — The Qt Company Ltd. and contributors. The LGPLv3 option is used for these libraries. Full LGPLv3 and GPLv3 texts: `licenses/LGPL-3.0.txt` and `licenses/GPL-3.0.txt`. Corresponding source repositories: https://code.qt.io/cgit/pyside/pyside-setup.git/ and https://code.qt.io/cgit/qt/qtbase.git/. Versions are pinned in `requirements.txt`; Qt sources use tag `v6.11.2`. The application's source and build script are supplied so it can be rebuilt with modified PySide6/Qt libraries. Reverse engineering for debugging modifications to these libraries is permitted under their license terms.
- **PyInstaller 6.22.3** — PyInstaller Development Team. GPL with the bootloader exception; see `licenses/PyInstaller.txt`. Source: https://github.com/pyinstaller/pyinstaller/tree/v6.22.3.

System fonts belong to their respective copyright holders and are not redistributed.

Method attribution: Ilya Vinogradov proposed the Russian text replacement method; Alexey Sergeev wrote the original KANAnization. The method description is at https://www.japlang.ru/soft/index.html. No original executable or program source is redistributed.
