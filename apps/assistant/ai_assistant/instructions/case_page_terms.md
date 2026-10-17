<!--
  WHAT THE LABELS ON THE CASE PAGE MEAN
  The AI assistant uses these to explain case page labels to the RM, with or without the AI
  model. One term per line, in the form:  - **term**: plain-English meaning
  - The term is matched in the RM's question (lower case), so keep it short.
  - Text inside these comment markers is a note for editors and is NOT sent to the model.
-->
- **canonical**: the official value from the registry (ACRA) that the document is checked against
- **suggestion**: the value our system read from the uploaded document; it is only a suggestion until it matches ACRA or a reviewer decides
- **source agreement**: whether the document's value matches the registry value (match or mismatch)
- **verification state**: where the review of this value stands, for example pending (waiting for a person), auto confirmed or human accepted
- **evidence score**: a rule-based score from 0 to 1 for how reliably the value was found: 0.97 for the standard label, 0.90 for other wording, lower for unclear scans; it is not a probability
- **extraction quality**: how cleanly the value was read, for example high, or lower when unclear
- **extraction method**: how the text was read: native PDF text means straight from the file, OCR means read from a scanned image
- **provenance**: where the value came from: which reader read it, and from which page
- **score formula**: which rule produced the evidence score
- **accept**: Accept confirms the value read from the document
- **reject**: Reject refuses the value read from the document
- **record correction**: Record correction lets the reviewer enter the right value themselves
