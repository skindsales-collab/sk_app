"""One writer per ERPNext record type (linear flow map, SK 4-Nov-2026).

Every screen, SK Hub, mail scan and import that makes a record of a type goes through its one writer here, so the record
is always made the same way: same links back, same mandatory data, same owner rule. A writer is used on the New path
only (SK Path Switch); the Old path keeps its own code until the module is verified and the old code is removed.
"""
