# Document security (v0.14.0)

Only files explicitly selected or dropped by the user are read. Limits cover source/batch bytes, archive members and expansion, JSON/XML depth, tables, cells, blocks, text, chunks, and calls. Traversal, symlink, ZIP-bomb, DOCTYPE/ENTITY, suspicious binary, macro, script, notebook execution, include expansion, external HTML resource, URL, and directory scan paths are rejected or skipped. Optional subprocesses use fixed allowlisted arguments, `shell=False`, bounded output/time, controlled temporary data, cleanup, and validated output.
