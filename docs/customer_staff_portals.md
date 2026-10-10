# Customer and staff portals

Run from the project folder:

```bash
source .venv/bin/activate
python -m app.server
```

Customer: http://127.0.0.1:8765/customer

Staff: http://127.0.0.1:8765/staff

The customer account is `customer001`, with password `Refund123!`. The one test account owns the current 70 demo orders. The existing refund application fields remain available after sign-in. The avatar and My refunds button open three collapsible groups: In progress, Declined and Refunded.

Automatic refunds complete immediately in the local workflow; confirmed product mismatches are declined. Unidentified product types require staff review. Other existing evidence and policy checks still apply.

Staff see Pending and Completed side by side. Pending contains human-review applications. Completed contains automatic or staff-approved refunds and declined applications. Requesting more evidence removes an application from the staff queue while the customer sees a request to upload another photo. Resubmission reassesses the same application and routes it again, preserving prior assessments and review notes.

Applications and images are saved in `.local_refund`. Customer requests require a customer session and ownership checks. The staff page opens a separate local staff session. Staff authentication has not been added; the server binds to the local computer and is not a production staff portal.

## Branch and model integration

These changes are on `codex/customer-staff-portals`, based on the local main version. `member2-v2-evaluation` has not been merged. The website calls the shared analysis pipeline, so the later Member 2 update can be integrated without recreating the pages. Review overlapping changes in the decision engine and service integration when merging, preserving the confirmed-mismatch rejection and unidentified-product review rules.

## Validation

58 relevant tests passed, covering routing, persistence, customer login and ownership, staff review permissions, evidence resubmission and the existing workflow. Workflow tests use an explicit controlled pipeline and do not establish real image-recognition accuracy. Customer and staff pages were inspected in the browser.
