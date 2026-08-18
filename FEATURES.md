# Form4Agent Product Definition

This file is the source of truth for product behavior. Engineering workflow, safety, and completion rules live in `AGENTS.md`.

## Primary workflow

Form4Agent has one upload-first interface and automatically chooses between two jobs:

1. **Prepare a Form 4 for customer signature.** Multiple identity/property files, or one file that is not recognisably a Form 4, are treated as source material. The app extracts up to four tenants, finds a property address if present, fills the template, removes the salesperson signature and seven initials, and produces the customer review version.
2. **Complete a customer-signed Form 4.** One uploaded file that is recognisably a CEA Form 4 is treated as the complete signed agreement. The app immediately applies the salesperson signature and initials and returns the completed PDF.

Classification is based on content, not filename. It is a convenience decision, not a legal authenticity check. If classification is wrong, the UI must allow clearing the session and uploading the intended files again.

## Prepare-for-customer behavior

- The main screen contains one upload control accepting JPG, JPEG, PNG, and PDF files.
- Each upload may be up to 50 MB. Show immediate file-count and total-size feedback after selection.
- It accepts passports, Singapore NRIC/FIN/pass documents, and screenshots or documents that contain a property address.
- The primary action is labelled **Generate Form 4**.
- A manual property-address field appears immediately below the uploader.
- Recognised property addresses are used automatically when the manual field is empty.
- A non-blank manual property address always overrides an extracted address.
- If neither source supplies an address, Generate Form 4 stops and shows a clear warning to enter the property address.
- The app extracts up to four tenant names and identity numbers. Tenant addresses remain blank.
- `Edit details` is a small secondary action beside the primary action. It opens a compact editor for agreement date, lease term, initial commission, renewal commission, and additional terms. Tenant identity fields and property address do not appear in that editor.
- The customer output contains fixed salesperson/company information, including salesperson NRIC, but contains none of the salesperson signature or seven initials images.
- Customer PDF is preferred; DOCX remains a fallback if conversion is unavailable.

## Defaults and commission

- Agreement date defaults to today in `Asia/Singapore` and is editable.
- The same date populates agreement and signature-date placeholders.
- Lease term defaults to 12 months and is editable.
- Default initial commission is `ceil(lease_months / 12) * 0.5` months of rent: 1–12 months = 0.5, 13–24 = 1, 25–36 = 1.5, and so on. It remains manually overridable.
- Renewal commission defaults to 0.5 months of rent for every 12 months.
- Additional terms default to blank.
- Template choices remain: GST Yes, commission inclusive of GST, renewal commission shall be payable, no conflict of interest, co-broking authorised, first renewal, and every 12 months.

## Complete-after-customer behavior

- Automatic completion applies only when exactly one uploaded file is recognisably a Form 4.
- Do not require an exact page count, A4 ratio, rotation, or other structural checks.
- Perform only a broad content check that the upload resembles CEA Form 4. Never claim the document, signatures, or initials are authentic or complete.
- Recognition and signing happen in the same Generate Form 4 action. Do not add a confirmation checkbox or a second signing button.
- Locate signature and initials using a PDF rendered from `templates/Form4_Template.docx`; do not maintain unrelated hand-guessed positions or change the template.
- Locate the salesperson signature line by its `Signed by *Salesperson for and on behalf of the Estate Agent` content, using OCR for scanned files, and place the signature directly above that line rather than at a fixed page coordinate.
- Apply initials to every uploaded page. Use the seven protected template anchors for pages 1–7 and continue the same top-right placement for page 8 and any later pages.
- The final output is PDF.
- After successful signing, show the concise status **Signature added** and the final PDF download.

## Delivery, privacy, and hosting

- Downloads must work on mobile so the user can use the operating-system share sheet to select WeChat or WhatsApp. Never auto-send or choose a recipient.
- Show WeChat and WhatsApp share controls for the final PDF. Browser security still requires the user to choose the target app and recipient in the operating-system share sheet; retain the normal download fallback.
- Keep uploads, extracted identity fields, and generated documents session-scoped and in memory. Clear them on user request and do not add a database or persistent disk.
- Production remains the existing Render service in Singapore on the free plan. Free-tier sleep is acceptable; do not add keep-alive traffic to defeat it.
- The interface is mobile-first, concise, and uses progressive disclosure. Routine details stay hidden unless `Edit details` is opened.
