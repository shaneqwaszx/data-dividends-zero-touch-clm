---
id: guidance.where-to-find-information
title: Which document shows which information (POC placeholder)
blocker_codes: DOCUMENT_REQUIRED, DOCUMENT_PROCESSING_FAILED, OWNERSHIP_REQUIRED
fields: registration_number, ownership
stages: Document verification, Ownership & UBO
source: AI-drafted placeholder for the POC (not sponsor-confirmed); field list from apps/backend/app/domain/documents.py
illustrative: true
---
<!--
  PLACEHOLDER: written for the proof of concept, not Delta Capita's policy.
  Replace it with the sponsor's document guide when it is confirmed (see Q-003),
  and set "illustrative: false" with the decision it comes from in "source".
-->
This guide is an illustrative placeholder for the POC, not a confirmed bank policy. Check accepted documents with your compliance team.

Where each piece of company information is usually found:
- UEN (registration number): Certificate of Incorporation, or the ACRA business profile.
- Legal name: Certificate of Incorporation or the ACRA business profile. After a name change, the certificate of change of name.
- Registered address: the ACRA business profile shows the current address. Older documents can show an earlier address, so the dates matter.
- Country of incorporation: Certificate of Incorporation.
- Company type (for example private limited): Certificate of Incorporation or the ACRA business profile.
- Directors and company secretary: the ACRA business profile.
- Shareholders and how many shares each holds: the register of members (shareholder register), share certificates with the total shares issued, or the ACRA business profile.
- People with significant control: the register of registrable controllers.
- Owners behind a corporate shareholder: that company's own register of members, or a signed ownership structure chart up to the individuals at the top.

The app currently reads four fields from an uploaded document: UEN, legal name, registered address and country of incorporation. For the UBO check, ownership evidence must show each owner's percentage, share count with the total shares, capital amount or membership interest. Directors are not treated as owners because of their role.
