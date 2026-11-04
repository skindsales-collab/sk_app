"""SK App shared base (rebuild plan, Phase 0, SK approved 4-Nov-2026).

One place for what every module needs, so a fix made here reaches every screen at once (horizontal by design):
- people:  who the user is, their functions, whether they are the CEO
- options: dropdown choices read from ERPNext (Select fields and masters), never fixed lists in a screen
- switch:  Old / New path per module and per pilot user (SK Path Switch), so work never stops while a module is rebuilt
- rules:   one way to report a broken rule: "Warn only" writes SK Rule Log, "Enforce" stops the save
"""
