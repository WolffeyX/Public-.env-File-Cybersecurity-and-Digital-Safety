# Semak Dulu: Software Requirements Specification

|                      |                                                                                                                                                                                |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Product**          | Semak Dulu ("Check First"), a Telegram bot that checks payment QR codes for seniors                                                                                            |
| **Track**            | Cybersecurity: scam prevention for vulnerable Malaysians                                                                                                                       |
| **Version**          | 1.2, 21 Oct 2026                                                                                                                                                               |
| **Changes in 1.1**   | Telegram is the only _channel_. WhatsApp-only constraints were removed. NFR-UI-03 now allows 10 lines and 700 characters. The third question button is "Keluarga/Kawan/Kedai". |
| **Status**           | Final                                                                                                                                                                          |
| **Related document** | Software Design Document (SDD) v1.2, which describes **how** the system meets these requirements                                                                               |
| **Template**         | Follows the SRS template from an educational institution curriculum                                                                                                            |

### How to read this document

This SRS describes **what** the system must do, from the users' point of view. It does not describe **how** the system does it. Implementation details (AWS, queues, databases) are in the SDD. The only exception is section 3.6, which the template asks for.

| Marker             | Meaning                                                                                                                                         |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **FR-nn**          | Functional requirement                                                                                                                          |
| **DR-nn**          | Data requirement                                                                                                                                |
| **NFR-xx-nn**      | Non-functional requirement (xx = section, for example UI, US, PF)                                                                               |
| **Priority**       | **M** = Must (MVP fails without it), **S** = Should (planned for the MVP, can be dropped if time runs out), **C** = Could (only if time allows) |
| **AC**             | Acceptance criterion: the test that proves the requirement is met                                                                               |
| **Not applicable** | The template section does not apply to this product (kept, not deleted)                                                                         |

Words in _italics_ inside requirements (for example _parent_, _check_, _verdict_) have the fixed meaning given in the dictionary in section 1.4, and are used only with that meaning.

---

## Contents

1. [Introduction](#1-introduction)
   - 1.1 Background and goals · 1.2 Users · 1.3 Constraints · 1.4 Naming conventions and definitions
2. [Functional and data requirements](#2-functional-and-data-requirements)
   - 2.1 Scope of the product · 2.2 Functional requirements · 2.3 Data requirements
3. [Non-functional requirements](#3-non-functional-requirements)
   - 3.1 Look and feel · 3.2 Usability · 3.3 Performance · 3.4 Maintainability · 3.5 Security · 3.6 Development and target environment · 3.7 Other
4. [References](#4-references)

- [Appendix A: How the writing rules were applied](#appendix-a-how-the-writing-rules-were-applied)
- [Appendix B: Traceability to the SDD](#appendix-b-traceability-to-the-sdd)

---

## 1. Introduction

### 1.1 Background and goals

#### Why is the product needed?

Malaysians lost about RM2.7 billion to cybercrime in 2025 (hackathon brief). People aged 50 and over are among the most targeted. Many of them have low digital literacy.

A common scam follows these steps:

1. A caller pretends to be a trusted person: a bank officer, a police or court officer, a courier, or a friend or relative.
2. The caller creates urgency, for example "we transferred money to you by mistake" or "your account will be frozen".
3. The caller sends a QR code and asks the senior to pay.

The senior believes the caller. General advice such as "don't send money to strangers" does not help, because the senior does not see the caller as a stranger.

#### What work does the user want to do with the product?

| User              | Work they want to do                                                                                              |
| ----------------- | ----------------------------------------------------------------------------------------------------------------- |
| _Parent_          | Find out, before paying, whether a payment request is likely a scam, without installing anything or typing.       |
| _Primary contact_ | Set up protection for the parent once, and be told within seconds if the parent is about to pay a likely scammer. |
| _Second contact_  | Act as a backup when the primary contact does not respond.                                                        |

#### Goals

| ID  | Goal                                                     | How we measure it                                                                                                 |
| --- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| G-1 | Stop the trusted-caller QR scam at the moment of payment | The system gives a _STOP verdict_ in every case where the _parent_ says a bank, police or court asked for payment |
| G-2 | Never give false reassurance                             | No message from the system tells a user that a QR code or a payment is safe (FR-10)                               |
| G-3 | Bring a family member in quickly                         | The _primary contact_ receives an _alert_ within 3 seconds of a _STOP verdict_ (NFR-PF-03)                        |
| G-4 | Be usable by seniors with low digital literacy           | A _parent_ completes a _check_ with 1 forward and 1 tap (NFR-US-01)                                               |
| G-5 | Support Bahasa Melayu                                    | Every message exists in BM, and BM is the default (FR-04)                                                         |

#### Not in scope (product boundaries)

The system does **not**: detect AI-cloned voices, scan phishing links, detect deepfake images or videos, connect to MCMC, PDRM or bank databases, or block payments. It gives advice; the _parent_ decides.

### 1.2 Users

| User group                        | Profile                                                                                                                                         | Abilities and knowledge                                                                                                                                               | How they use the product                                                |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **Parent** (main user)            | Malaysian, 50 years or older. Uses WhatsApp daily for family chats. May have low digital literacy. May be anxious or rushed during a scam call. | Can open a chat app, forward an image, and tap a button. May not be able to type quickly, find files in a gallery, or open a website. BM is the most likely language. | Forwards a QR image, taps one answer, reads the _verdict_.              |
| **Primary contact** (set-up user) | Adult son or daughter, typically 25 to 45 years old. Confident smartphone user. Often busy at work.                                             | Can save a contact, type short commands, and follow short instructions.                                                                                               | Sets up the service on a visit, receives _alerts_, taps "Saya uruskan". |
| **Second contact** (optional)     | Another family member: sibling, spouse or relative.                                                                                             | Same as the primary contact.                                                                                                                                          | Receives _alerts_ only when the primary contact does not respond.       |

### 1.3 Constraints

#### Assumptions

| ID   | Assumption                                                                                                                         | Status                                                                 |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| AS-2 | A DuitNow QR code with merchant category code `0000` belongs to a personal account. This held for 3 of 3 personal QR codes tested. | Accepted                                                               |
| AS-3 | The value `A0000006150001` in tag 26 identifies a DuitNow QR code.                                                                 | Accepted                                                               |
| AS-4 | The _parent_ forwards the QR image to the system before paying. The setup visit and practice check build this habit.               | Accepted risk: the system cannot help a _parent_ who does not forward. |
| AS-5 | The _parent_ and _contacts_ have a smartphone with Telegram and a mobile data connection.                                          | Accepted                                                               |

#### Constraints

| ID   | Constraint                                                                          | Source                |
| ---- | ----------------------------------------------------------------------------------- | --------------------- |
| CO-1 | The system must support Bahasa Melayu.                                              | Hackathon requirement |
| CO-3 | The team has 3 to 4 developers.                                                     | Team                  |
| CO-7 | The system must comply with Malaysia's Personal Data Protection Act 2010 (PDPA).    | Law                   |
| CO-8 | The system must use free tiers or minimal-cost cloud services during the hackathon. | Budget                |

### 1.4 Naming conventions and definitions

This dictionary defines every term used in the requirements. Terms in _italics_ in the requirements have exactly this meaning.

| Term                       | Definition                                                                                                                                                                                                                                                       |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **System**                 | The Semak Dulu bot, including its logic and stored data. It does not include Telegram itself.                                                                                                                                                                    |
| **Parent**                 | A user who is linked to at least one _contact_ and has given _consent_. The person the system protects.                                                                                                                                                          |
| **Contact**                | A _primary contact_ or a _second contact_.                                                                                                                                                                                                                       |
| **Primary contact**        | The user who registered the _parent_. Exactly one per _parent_.                                                                                                                                                                                                  |
| **Second contact**         | An optional extra family member linked to the _parent_. At most one per _parent_.                                                                                                                                                                                |
| **Channel**                | The messaging app used to talk to the _system_: Telegram.                                                                                                                                                                                                        |
| **Pairing code**           | A 6-character code that the _system_ gives the _primary contact_, used once to link the _parent_. Valid for 24 hours.                                                                                                                                            |
| **Consent**                | The _parent's_ tap on the "Setuju" button, which allows the _system_ to send _alerts_ about them.                                                                                                                                                                |
| **Check**                  | One QR verification, from the moment the _parent_ forwards an image until the _system_ sends a _verdict_ or the _check_ expires.                                                                                                                                 |
| **Claim**                  | The _parent's_ answer to "Who asked you to pay?". One of three values: **OFFICIAL** (bank, police or court), **COURIER**, or **KNOWN_PERSON** (relative, friend or seller).                                                                                      |
| **Payment QR**             | A QR code that follows the EMVCo payment format.                                                                                                                                                                                                                 |
| **DuitNow QR**             | A _payment QR_ whose tag 26 contains the DuitNow identifier (AS-3).                                                                                                                                                                                              |
| **Personal account**       | A _DuitNow QR_ whose merchant category code (tag 52) is `0000` (AS-2).                                                                                                                                                                                           |
| **Business account**       | A _DuitNow QR_ whose merchant category code is any value other than `0000`.                                                                                                                                                                                      |
| **Static QR / dynamic QR** | Static: reusable, tag 01 = `11`, no amount. Dynamic: for one payment, tag 01 = `12`, usually includes an amount.                                                                                                                                                 |
| **Payee name**             | The name stored in tag 59 of a _payment QR_.                                                                                                                                                                                                                     |
| **Verdict**                | The _system's_ answer to a _check_. Exactly one of two values: _STOP_ or _VERIFY_. There is no third value.                                                                                                                                                      |
| **STOP verdict**           | The _verdict_ that tells the _parent_ not to pay. It starts an _alert_.                                                                                                                                                                                          |
| **VERIFY verdict**         | The _verdict_ that tells the _parent_ not to pay yet, and gives one check to do first.                                                                                                                                                                           |
| **Action**                 | One concrete step that the _parent_ can finish in under 60 seconds, for example "call the person back on a number you already saved".                                                                                                                            |
| **Alert**                  | A message that the _system_ sends to a _contact_ after a _STOP verdict_ or a _paid report_.                                                                                                                                                                      |
| **Acknowledge**            | A _contact_ tapping the "Saya uruskan" (I'm handling it) button on an _alert_.                                                                                                                                                                                   |
| **Escalation**             | Sending an _alert_ to the _second contact_ because the _primary contact_ has not _acknowledged_ it within 180 seconds.                                                                                                                                           |
| **Paid report**            | The _parent_ tapping "Saya sudah bayar" (I already paid).                                                                                                                                                                                                        |
| **QR report**              | A user's statement, by tapping a reason, that a QR code was used in a scam or a dispute.                                                                                                                                                                         |
| **Scam-pattern report**    | A _QR report_ with the reason "the caller pretended to be a bank, police, court or courier". Only this kind counts as evidence.                                                                                                                                  |
| **Reportable QR**          | A _static_ _DuitNow QR_. Only these can receive _QR reports_.                                                                                                                                                                                                    |
| **Evidence level**         | The number of different users who made a _scam-pattern report_ about the same _reportable QR_: none (0), few (1 to 2), or several (3 or more).                                                                                                                   |
| **Family code word**       | A secret word that the _parent_ and _contacts_ agree in person, used to confirm a caller's identity. The _system_ never stores it.                                                                                                                               |
| **Safety claim**           | Any message text that states or implies that a QR code, an account or a payment is safe, for example "selamat", "boleh bayar", "tiada masalah", "safe to pay". A sentence that negates safety, such as "itu tidak bermakna ia selamat", is not a _safety claim_. |
| **Practice check**         | A _check_ done during setup with a test QR, clearly marked as a demo.                                                                                                                                                                                            |
| **BM**                     | Bahasa Melayu                                                                                                                                                                                                                                                    |
| **MVP**                    | Minimum viable product: the version delivered on 21 Oct 2026                                                                                                                                                                                                     |
| **PDPA**                   | Personal Data Protection Act 2010 (Malaysia)                                                                                                                                                                                                                     |
| **EMVCo**                  | The organisation that sets the international payment QR standard                                                                                                                                                                                                 |
| **TLV**                    | Tag-length-value: how a _payment QR_ stores its fields                                                                                                                                                                                                           |
| **MCC**                    | Merchant category code (tag 52)                                                                                                                                                                                                                                  |
| **NSRC / 997**             | National Scam Response Centre hotline                                                                                                                                                                                                                            |
| **Semak Mule**             | PDRM's public website for checking whether an account or phone number has been reported in scams                                                                                                                                                                 |

---

## 2. Functional and data requirements

### 2.1 Scope of the product

![Product scope](diagrams/srs-01-scope.png)

The _system_ sits between the users and the messaging _channels_. It has four functional areas: setup and linking, QR check and verdict, family alerts, and QR reports.

#### Interfaces to adjacent systems

| Adjacent system                             | Data the system consumes                           | Data the system produces                     | Type                              |
| ------------------------------------------- | -------------------------------------------------- | -------------------------------------------- | --------------------------------- |
| Telegram (_channel_)                        | Text messages, images, button taps, sender chat ID | Text messages, messages with up to 3 buttons | Two-way, automated                |
| Semak Mule website                          | Nothing                                            | A link inside some messages                  | Link only, no automated exchange  |
| Banks, NSRC (997), emergency services (999) | Nothing                                            | Phone numbers or names in messages           | Named only, no automated exchange |

#### Use cases

![Use case diagram](diagrams/srs-02-usecases.png)

| ID    | Use case                                         | Actor                               | Requirements                   |
| ----- | ------------------------------------------------ | ----------------------------------- | ------------------------------ |
| UC-1  | Register and get a _pairing code_                | _Primary contact_                   | FR-01                          |
| UC-2  | Link to the _primary contact_ and give _consent_ | _Parent_                            | FR-02                          |
| UC-3  | Add a _second contact_                           | _Primary contact_, _second contact_ | FR-03                          |
| UC-4  | Choose a language                                | Any user                            | FR-04                          |
| UC-5  | Do a _practice check_                            | _Parent_                            | FR-21                          |
| UC-6  | Check a QR before paying                         | _Parent_                            | FR-05 to FR-12, FR-24 to FR-26 |
| UC-7  | Report a QR                                      | _Parent_                            | FR-14 to FR-17                 |
| UC-8  | Tell the system "I already paid"                 | _Parent_                            | FR-13                          |
| UC-9  | Receive and _acknowledge_ an _alert_             | _Primary contact_, _second contact_ | FR-18 to FR-20                 |
| UC-10 | Stop using the service                           | Any user                            | FR-22                          |

A _STOP verdict_ in UC-6 and a _paid report_ in UC-8 both start UC-9.

### 2.2 Functional requirements

Requirements are grouped by functional area. Each has an ID, a priority and an acceptance criterion (AC). IDs FR-01 to FR-20 match the earlier requirement list and the SDD. FR-21 to FR-27 were added while writing this SRS to cover cases the earlier list left out.

#### 2.2.1 Setup and linking

| ID        | Requirement                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Priority | Acceptance criterion                                                                                                                                                                                        |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **FR-01** | When a user who is not yet registered sends the word "Daftar", the _system_ shall register that user as a _primary contact_, ask how to address the _parent_ (for example "Mak" or "Ayah"), store the answer, and send the _primary contact_ a _pairing code_ that is valid for 24 hours.                                                                                                                                                                                                                                                                                                                                                                                                                                                     | M        | A new user sends "Daftar" and "Mak". The system replies with a 6-character code. The same code is rejected 24 hours later.                                                                                  |
| **FR-02** | When a user sends a valid, unused _pairing code_, the _system_ shall show that user a short explanation that the _system_ will message their _primary contact_ if it gives a _STOP verdict_, together with a "Setuju" button. When the user taps "Setuju", the _system_ shall record the user as a _parent_, link them to the _primary contact_, record the time of _consent_, mark the _pairing code_ as used, and confirm the link to both users. If the user does not tap "Setuju", the _system_ shall not link the users and shall not send _alerts_ about them. If the _pairing code_ is invalid, used or expired, the _system_ shall tell the user that the code does not work and ask them to get a new code from their family member. | M        | (1) Valid code + "Setuju": both users receive a confirmation, and the consent time is stored. (2) Valid code, no tap: no link exists. (3) Expired code: the user receives the "code does not work" message. |
| **FR-03** | When a _primary contact_ sends the word "Tambah", the _system_ shall send them a second _pairing code_. When another user sends that code and taps "Terima" (accept), the _system_ shall link that user to the _parent_ as the _second contact_. If the _parent_ already has a _second contact_, the _system_ shall tell the _primary contact_ to remove the existing one first. A _parent_ without a _second contact_ shall receive the full service.                                                                                                                                                                                                                                                                                        | S        | (1) A second user links successfully and later receives an escalated alert (FR-20). (2) A third link attempt is refused. (3) All tests for FR-05 to FR-19 pass for a parent with no second contact.         |
| **FR-04** | When a user sends their first message to the _system_, the _system_ shall ask them to choose "Bahasa Melayu" or "English" with two buttons, and shall use BM until the user chooses. The _system_ shall send every later message to that user in the chosen language. The user shall be able to change the language at any time by sending "Bahasa" or "Language".                                                                                                                                                                                                                                                                                                                                                                            | M        | (1) A first message receives the language buttons. (2) After choosing English, all messages are in English. (3) A user who never taps receives BM.                                                          |
| **FR-21** | After a _parent_ gives _consent_, the _system_ shall invite the _parent_ to forward a test QR code. When the _parent_ forwards any image during this _practice check_, the _system_ shall reply with a sample _verdict_ that is clearly labelled "[LATIHAN]" (practice), and shall not send any _alert_.                                                                                                                                                                                                                                                                                                                                                                                                                                      | S        | The parent forwards an image after linking. The reply carries the practice label, and no contact receives an alert.                                                                                         |
| **FR-22** | When any user sends the word "Berhenti", the _system_ shall ask the user to confirm with a button. After confirmation, the _system_ shall delete that user's profile and all links that include the user, stop sending them messages, and confirm the deletion. If the user is a _parent_, the _system_ shall also tell their _contacts_ that the _parent_ has left the service.                                                                                                                                                                                                                                                                                                                                                              | M        | After "Berhenti" and confirmation, the user's profile and links no longer exist, and a forwarded QR image from that user is treated as coming from a new user.                                              |
| **FR-23** | When a user sends text that the _system_ does not recognise as a command, the _system_ shall reply with a short help message that tells the user to forward a QR image, and lists the available commands.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | S        | Sending "hello" returns the help message.                                                                                                                                                                   |

#### 2.2.2 QR check

![QR check flow from the parent's view](diagrams/srs-03-check-flow.png)

| ID        | Requirement                                                                                                                                                                                                                                                                                                                                                                          | Priority | Acceptance criterion                                                                                                                       |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **FR-05** | The _system_ shall accept an image that a user forwards or sends in a Telegram chat, as the start of a _check_. The user shall not need to install any app other than Telegram, and shall not need to type anything to start a _check_.                                                                                                                                              | M        | Forwarding a QR screenshot from another chat starts a check.                                                                               |
| **FR-06** | For each image in a _check_, the _system_ shall classify the content as exactly one of: _DuitNow QR_, other _payment QR_, web link, other text, no QR code found, or unreadable image.                                                                                                                                                                                               | M        | Each test image in the fixture set (SDD section 11.2) receives its expected class.                                                         |
| **FR-07** | For each _DuitNow QR_, the _system_ shall extract the _payee name_, whether it is _static_ or _dynamic_, the amount (if the QR contains one), and whether it is a _personal account_ or a _business account_. If a field is missing from the QR, the _system_ shall record that field as unknown and shall not guess it.                                                             | M        | The 5 sample QR codes return the expected payee name, type, amount and account type. A QR without tag 52 returns "account type unknown".   |
| **FR-08** | Within 3 seconds of receiving an image, the _system_ shall ask the _parent_ "Who asked you to pay?" with exactly 3 buttons: "Bank/Polis/Mahkamah" (_claim_ OFFICIAL), "Kurier" (_claim_ COURIER), and "Keluarga/Kawan/Kedai" (_claim_ KNOWN*PERSON). The \_system* shall send this question before the result of FR-06 is known.                                                     | M        | The question with 3 buttons arrives for every forwarded image, including blurry images and images without a QR code.                       |
| **FR-09** | The _system_ shall give a _STOP verdict_ in exactly these two cases: (a) the _claim_ is OFFICIAL, whatever the image contains, including when no QR code could be read; (b) the _claim_ is COURIER and the image contains a _DuitNow QR_ for a _personal account_. The _system_ shall make this decision without using any _QR reports_.                                             | M        | Test matrix in section 2.2.3: every STOP row returns STOP, with an empty report store.                                                     |
| **FR-10** | In every case not covered by FR-09, the _system_ shall give a _VERIFY verdict_. No message that the _system_ sends, in any language, to any user, shall contain a _safety claim_.                                                                                                                                                                                                    | M        | (1) Every VERIFY row in section 2.2.3 returns VERIFY. (2) An automated scan of every message text in both languages finds no safety claim. |
| **FR-11** | Every _verdict_ message shall start with the instruction ("JANGAN BAYAR" for _STOP_, "Tunggu dulu, jangan bayar dahulu" for _VERIFY_), followed by one reason in one sentence and exactly one _action_. If the QR contains a _payee name_, the _VERIFY verdict_ shall show it.                                                                                                       | M        | Review of every verdict message: the first line is the instruction, and exactly one action is present.                                     |
| **FR-12** | When the content is a web link, other text, no QR code, an unreadable image, or a _payment QR_ that is not a _DuitNow QR_, the _system_ shall send a message written for that specific case, which tells the _parent_ not to pay yet and what to do next. The _system_ shall never open a web link found in a QR code. The _system_ shall not show technical error text to the user. | M        | Each of the 5 failure cases produces its own message. Logs show no outgoing request to the URL in the test link QR.                        |
| **FR-24** | If the _parent_ has not tapped a _claim_ button within 120 seconds after the question (FR-08), the _system_ shall send one reminder that starts with "Jangan bayar dahulu" and repeats the 3 buttons. If the _parent_ still has not tapped within 10 minutes after the question, the _system_ shall close the _check_.                                                               | S        | (1) No tap for 2 minutes: exactly one reminder arrives. (2) No tap for 10 minutes: the check is closed (see FR-25).                        |
| **FR-25** | When the _parent_ taps a button that belongs to a closed or replaced _check_, the _system_ shall reply that the check has expired and ask the _parent_ to forward the QR image again.                                                                                                                                                                                                | S        | Tapping an 11-minute-old button returns the "expired" message, and no verdict is given.                                                    |
| **FR-26** | When the _parent_ forwards a new image while a _check_ is still open, the _system_ shall close the old _check_ and start a new one with the new image.                                                                                                                                                                                                                               | S        | Two images sent 10 seconds apart: only the second receives a verdict.                                                                      |
| **FR-13** | Every _verdict_ message shall include a "Saya sudah bayar" button. When the _parent_ taps it, the _system_ shall (1) tell the _parent_, in this order, to call their bank immediately, call 997, call 999 if they are in danger, and then make a police report; and (2) start a _PAID alert_ (FR-18).                                                                                | M        | Tapping the button returns the 4 steps in order, and the primary contact receives the PAID alert.                                          |

#### 2.2.3 Verdict rules (decision table)

This table defines FR-09 and FR-10 completely. Every combination has exactly one result.

| Rule | _Claim_      | QR content                                                           | _Verdict_                                                                               | Starts an _alert_? |
| ---- | ------------ | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------ |
| V-1  | OFFICIAL     | Any, including no QR or unreadable                                   | **STOP**                                                                                | Yes                |
| V-2  | COURIER      | _DuitNow QR_, _personal account_                                     | **STOP**                                                                                | Yes                |
| V-3  | COURIER      | No QR, unreadable, web link, other text, or non-DuitNow _payment QR_ | VERIFY ("we could not check this QR")                                                   | No                 |
| V-4  | COURIER      | _DuitNow QR_, _business account_ or account type unknown             | VERIFY (show the merchant name, check it in the courier's official app)                 | No                 |
| V-5  | KNOWN_PERSON | Any                                                                  | VERIFY (show the _payee name_, call back on a saved number, ask the _family code word_) | No                 |

The _evidence level_ (FR-15) adds one line to any _verdict_. It never changes the _verdict_ or whether an _alert_ starts.

#### 2.2.4 QR reports

| ID        | Requirement                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Priority | Acceptance criterion                                                                                                         |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **FR-14** | Every _verdict_ message shall include a "Laporkan QR ini" button. When the user taps it, the _system_ shall show 3 reason buttons: "Pemanggil menyamar sebagai bank, polis, mahkamah atau kurier" (_scam-pattern report_), "Penjual atau orang itu tidak jujur" (dispute), and "Lain-lain" (other). The _system_ shall store the _QR report_ with the chosen reason and thank the user.                                                                                                 | S        | A report with each reason is stored with that reason.                                                                        |
| **FR-15** | When a _check_ contains a _reportable QR_, the _system_ shall add one line to the _verdict_ that depends on the _evidence level_: none: "Tiada laporan dijumpai, tetapi itu tidak bermakna ia selamat"; few: "Akaun ini ada {n} laporan yang belum disahkan. Berhati-hati."; several: "Beberapa orang telah melaporkan akaun ini." The _system_ shall not use the word "penipu" (scammer) in any of these lines. Dispute and other reports shall not count toward the _evidence level_. | S        | A QR with 0, 2 and 3 scam-pattern reports from different users shows the 3 lines. 5 dispute reports leave the level at none. |
| **FR-16** | The _system_ shall accept at most one _QR report_ per user per _reportable QR_. When the same user reports the same QR again, the _system_ shall tell them that their report already exists. The _system_ shall accept _QR reports_ only for _reportable QRs_. For any other QR, the _system_ shall tell the user that this QR cannot be reported.                                                                                                                                      | S        | (1) A second report from the same user is refused. (2) A report on a dynamic QR is refused, and nothing is stored.           |
| **FR-17** | The _VERIFY verdict_ message shall include a link to the Semak Mule website, with a one-line suggestion to check the account there. The _system_ shall not use Semak Mule results to decide a _verdict_.                                                                                                                                                                                                                                                                                | C        | The link appears in VERIFY messages and not in the verdict logic.                                                            |

#### 2.2.5 Family alerts

![Alert escalation](diagrams/srs-04-alerts.png)

| ID        | Requirement                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Priority | Acceptance criterion                                                                                                                                                                                                                                                                            |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **FR-18** | The _system_ shall send an _alert_ to the _primary contact_ in exactly two cases: after a _STOP verdict_, and after a _paid report_. The _system_ shall not send an _alert_ after a _VERIFY verdict_. The _alert_ shall start with "AMARAN: Telefon {address*as} sekarang." and shall state: who the caller claimed to be; whether the QR was a \_personal account*, a _business account_, or could not be read; that the _system_ does not know whether money was sent (STOP alert) or that the _parent_ reported paying (PAID alert); a reminder to ask the _family code word_; and a "Saya uruskan" button.                     | M        | (1) A STOP verdict produces an alert with all 5 elements. (2) A VERIFY verdict produces no alert. (3) A paid report produces a PAID alert.                                                                                                                                                      |
| **FR-19** | Before the _system_ sends an _alert_ after a _STOP verdict_, the _STOP verdict_ message to the _parent_ shall tell the _parent_ not to pay, to end the call, and that their _primary contact_ has been told and will call them.                                                                                                                                                                                                                                                                                                                                                                                                    | M        | The parent's STOP message arrives before the contact's alert and contains all 3 statements.                                                                                                                                                                                                     |
| **FR-20** | If no _contact_ has _acknowledged_ an _alert_ 180 seconds after it was sent, and a _second contact_ exists, the _system_ shall send the same _alert_ to the _second contact_. If no _contact_ has _acknowledged_ it 180 seconds after that, or if no _second contact_ exists, the _system_ shall send the _parent_ a message telling them to call their bank and 997. As soon as any _contact acknowledges_ the _alert_, the _system_ shall send no further messages about that _alert_ and shall tell the other _contact_ (if alerted) that someone is handling it. The _system_ shall send each _alert_ to at most 2 _contacts_. | M        | (1) No ack: the second contact is alerted at 180 ± 30 s. (2) Ack by the primary contact at 60 s: the second contact receives nothing. (3) No second contact and no ack: the parent receives the bank and 997 message at 180 ± 30 s. (4) Double tap on "Saya uruskan": exactly one confirmation. |
| **FR-27** | When a _contact_ taps "Saya uruskan", the _system_ shall confirm to that _contact_ that the _alert_ is marked as handled.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | M        | The contact receives a confirmation within 3 seconds.                                                                                                                                                                                                                                           |

### 2.3 Data requirements

#### 2.3.1 Data needed by the product

![Conceptual data model](diagrams/srs-05-data.png)

| Data                                                | Source                            | Used for                               |
| --------------------------------------------------- | --------------------------------- | -------------------------------------- |
| Messaging ID (phone number or Telegram chat ID)     | _Channel_                         | Identifying users and sending messages |
| Chosen language                                     | User (FR-04)                      | Choosing message text                  |
| Address name ("Mak", "Ayah")                        | _Primary contact_ (FR-01)         | Personalising messages                 |
| Consent time                                        | _Parent_ (FR-02)                  | Proving _consent_ before _alerts_      |
| Family links (primary, second)                      | Setup (FR-02, FR-03)              | Knowing whom to _alert_                |
| QR image                                            | _Parent_ (FR-05)                  | Decoding only                          |
| QR fields: _payee name_, amount, type, account type | Decoded from the QR image (FR-07) | _Verdict_ and messages                 |
| _Claim_                                             | _Parent_ (FR-08)                  | _Verdict_                              |
| _Alert_ stage                                       | _System_ (FR-18 to FR-20)         | _Escalation_                           |
| _QR reports_: scrambled QR account ID, reason, time | Users (FR-14)                     | _Evidence level_                       |

#### 2.3.2 Data stored persistently, and for how long

| ID        | Requirement                                                                                                                                                                                                                  | Priority | AC                                                                                     |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------- |
| **DR-01** | The _system_ shall not store any QR image. The _system_ shall delete each image from memory as soon as decoding finishes.                                                                                                    | M        | No image file or image bytes exist in any data store after a check.                    |
| **DR-02** | The _system_ shall store the decoded QR fields and the _claim_ of a _check_ for at most 15 minutes after the _check_ starts, and shall then delete them.                                                                     | M        | A check's data cannot be read 16 minutes after it started.                             |
| **DR-03** | The _system_ shall not store raw bank account numbers or raw QR payloads. For _QR reports_, the _system_ shall store only a scrambled QR account ID that cannot be turned back into the account number without a secret key. | M        | Inspection of stored reports shows no account digits and no payloads.                  |
| **DR-04** | The _system_ shall store user profiles and family links until the user sends "Berhenti" (FR-22).                                                                                                                             | M        | Profiles remain after 30 days of no use, and disappear after "Berhenti".               |
| **DR-05** | The _system_ shall store _pairing codes_ for at most 24 hours.                                                                                                                                                               | M        | Code unusable and deleted after 24 hours.                                              |
| **DR-06** | The _system_ shall store _alert_ records for at most 7 days.                                                                                                                                                                 | S        | Alert record deleted after 7 days.                                                     |
| **DR-07** | The _system_ shall store _QR reports_ (scrambled ID, reason, time, scrambled reporter ID) with no expiry date for the MVP.                                                                                                   | S        | Reports remain after 30 days.                                                          |
| **DR-08** | The _system_ shall never store the _family code word_.                                                                                                                                                                       | M        | No message flow asks the user to type the code word.                                   |
| **DR-09** | System logs shall not contain QR payloads, _payee names_, account numbers or full phone numbers. The _system_ shall keep logs for at most 14 days.                                                                           | M        | Log review during testing finds none of these items. Log retention setting is 14 days. |

#### 2.3.3 Data volume

The MVP is sized for the hackathon demo and testing only.

| Item                    | Expected volume (MVP)                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------------------- |
| Registered users        | Up to 10 (hackathon demo)                                                                                |
| _Checks_ per day        | Up to 200 (during testing)                                                                               |
| QR image size           | Up to 5 MB per image. Larger images are rejected with a message asking for a normal photo or screenshot. |
| Stored data per user    | Under 2 KB for the profile and links                                                                     |
| Stored data per _check_ | Under 2 KB, deleted after 15 minutes                                                                     |
| _QR reports_            | Up to 500 in total                                                                                       |

---

## 3. Non-functional requirements

### 3.1 Look and feel / user interface

The user interface consists of chat messages inside Telegram. The _system_ does not have its own app, website or screens.

| ID            | Requirement                                                                                                                                                                                                              | Priority | AC                                                                         |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------- |
| **NFR-UI-01** | The _system_ shall communicate only through text messages and buttons inside the _channel_. The _system_ shall not send images, voice notes, videos or files to users in the MVP.                                        | M        | Message log contains only text and button messages.                        |
| **NFR-UI-02** | A message shall contain at most 3 buttons. Each button label shall be at most 20 characters long.                                                                                                                        | M        | Automated check of the message catalogue.                                  |
| **NFR-UI-03** | A _verdict_ or _alert_ message shall be at most 10 lines and at most 700 characters long, including the _evidence level_ line.                                                                                           | M        | Automated check of the message catalogue with the longest variable values. |
| **NFR-UI-04** | A _STOP verdict_ shall begin with the 🛑 symbol and the words "JANGAN BAYAR". A _VERIFY verdict_ shall begin with the 🟡 symbol and the words "Tunggu dulu". The symbol shall never be the only signal of the _verdict_. | M        | Review of the message catalogue.                                           |
| **NFR-UI-05** | Messages shall address the _parent_ with the name chosen by the _primary contact_ (FR-01).                                                                                                                               | S        | A parent registered as "Ayah" sees "Ayah" in the messages.                 |

### 3.2 Usability

| ID            | Requirement                                                                                                                                                                                                                                                                                       | Priority | AC                                                           |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------ |
| **NFR-US-01** | A _parent_ shall be able to complete a _check_, from forwarding the image to reading the _verdict_, with 1 forward action and 1 button tap, and with no typing.                                                                                                                                   | M        | Count of user actions in the demo script.                    |
| **NFR-US-02** | A _primary contact_ shall be able to complete setup (FR-01, FR-02, FR-21) together with the _parent_ in under 5 minutes, without reading any documentation other than the bot's messages.                                                                                                         | S        | 2 test pairs complete setup in under 5 minutes each.         |
| **NFR-US-03** | At least 2 of 3 test users aged 50 or over shall complete a _practice check_ without help from the team.                                                                                                                                                                                          | S        | User test before 19 Oct 2026, results recorded.              |
| **NFR-US-04** | Messages shall use everyday BM or English words. Messages shall not contain these technical terms: "payload", "merchant", "EMV", "TLV", "MCC", "checksum", "error code".                                                                                                                          | M        | Automated word scan of the message catalogue.                |
| **NFR-US-05** | Every message that the _system_ sends to a _parent_ shall end with either buttons or one _action_.                                                                                                                                                                                                | M        | Review of the message catalogue.                             |
| **NFR-US-06** | The _VERIFY verdict_ for the KNOWN*PERSON \_claim* and every _alert_ shall remind the user to ask the _family code word_. During setup, the _system_ shall suggest that the _parent_ and _contact_ agree a _family code word_ in person, and shall state that the _system_ will never ask for it. | S        | Review of the 3 messages.                                    |
| **NFR-US-07** | A native BM speaker shall review every BM message before the demo.                                                                                                                                                                                                                                | M        | Review recorded with name and date.                          |
| **NFR-US-08** | The users need no training. The setup message from the _primary contact_ to the _parent_ (SDD section 6.1) is the only instruction.                                                                                                                                                               | M        | Not testable separately. Covered by NFR-US-02 and NFR-US-03. |

### 3.3 Performance

Times are measured from the moment the _channel_ delivers the user's message to the _system_ until the _system_ hands its reply to the _channel_. Network delivery time to the phone is not included.

| ID            | Requirement                                                                                                                                                             | Priority | AC                                 |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------- |
| **NFR-PF-01** | The _system_ shall send the "Who asked you to pay?" question (FR-08) within 3 seconds for at least 95% of _checks_.                                                     | M        | 20 timed test checks.              |
| **NFR-PF-02** | The _system_ shall send the _verdict_ within 3 seconds of the _claim_ tap for at least 95% of _checks_.                                                                 | M        | 20 timed test checks.              |
| **NFR-PF-03** | The _system_ shall send the _alert_ to the _primary contact_ within 3 seconds of sending the _STOP verdict_.                                                            | M        | 10 timed STOP tests.               |
| **NFR-PF-04** | The _system_ shall send the _escalation_ (FR-20) and the reminder (FR-24) within ±30 seconds of their target times (180 seconds and 120 seconds).                       | S        | 5 timed tests each.                |
| **NFR-PF-05** | The _system_ shall read the QR code correctly in at least 9 of 10 clear screenshots of QR codes, and in at least 6 of 10 photos of a QR code taken from a phone screen. | S        | Test with the fixture image set.   |
| **NFR-PF-06** | The _system_ shall process up to 10 _checks_ at the same time from different _parents_ without any reply taking longer than the limits in NFR-PF-01 and NFR-PF-02.      | C        | Load test with 10 parallel checks. |

**Memory and hardware:** Not applicable for users (the _system_ runs in the cloud). Server-side limits are in the SDD.

### 3.4 Maintainability

| ID            | Requirement                                                                                                                                                                                                                                                      | Priority | AC                                                          |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------- |
| **NFR-MT-01** | **Expected operating time:** the MVP shall run from 19 Oct 2026 until the end of the hackathon evaluation period.                                                                                                                                                | M        | System available during the evaluation period.              |
| **NFR-MT-02** | The team shall be able to change any message text, in either language, by editing a text file, without changing program code.                                                                                                                                    | M        | Change one message, redeploy, see the new text.             |
| **NFR-MT-03** | The team shall be able to add a new _channel_ (for example a third messaging app) by adding one new adapter module, without changing the verdict rules or the message text.                                                                                      | S        | Telegram is added this way (code review).                   |
| **NFR-MT-04** | **Extension points:** the design shall allow these additions later without rewriting the verdict rules: a phishing link check, a voice-note check that can only make a _verdict_ stricter, new languages, new _claim_ types, and official scam database lookups. | S        | Design review against the SDD.                              |
| **NFR-MT-05** | Automated tests shall cover every row of the decision table in section 2.2.3 and every failure case in FR-12.                                                                                                                                                    | M        | Test report lists each row and case.                        |
| **NFR-MT-06** | The team shall keep all code, tests and documents in one Git repository with a README that explains how to deploy the _system_ in at most 10 steps.                                                                                                              | M        | A team member who did not write the README deploys from it. |

### 3.5 Security

| ID            | Requirement                                                                                                                                                                                                      | Priority | AC                                                                                                                             |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **NFR-SE-01** | **Transmission:** all data between the _channels_ and the _system_ shall travel over HTTPS (TLS 1.2 or later).                                                                                                   | M        | Endpoint test rejects plain HTTP.                                                                                              |
| **NFR-SE-02** | **Authenticity:** the _system_ shall process only requests that carry a valid signature or secret token from Telegram. The _system_ shall reject every other request without processing it.                      | M        | A request with a wrong signature returns an error and produces no reply.                                                       |
| **NFR-SE-03** | **Data access:** only the _system's_ own cloud functions and the team's named administrators shall have access to stored data. Each cloud function shall have only the permissions it needs.                     | M        | Permission review.                                                                                                             |
| **NFR-SE-04** | **Secrets:** access tokens and the scrambling key shall not appear in the code repository or in logs.                                                                                                            | M        | Repository and log scan finds no secrets.                                                                                      |
| **NFR-SE-05** | **Abuse limits:** the _system_ shall accept at most 10 _checks_ per user per 10 minutes. When a user exceeds this limit, the _system_ shall tell them to wait.                                                   | S        | The 11th check within 10 minutes receives the "please wait" message.                                                           |
| **NFR-SE-06** | **Pairing codes** shall be random, single-use, at least 6 characters long, and shall exclude look-alike characters (0, O, 1, I).                                                                                 | M        | Code generator unit test.                                                                                                      |
| **NFR-SE-07** | **Consent and privacy notice:** before linking, the _system_ shall tell the _parent_ what data it keeps, why, and how to delete it ("Berhenti").                                                                 | M        | The consent message (FR-02) contains these 3 items.                                                                            |
| **NFR-SE-08** | **PDPA:** the _system_ shall meet the obligations of the PDPA that apply to this processing.                                                                                                                     | M        | Review against the 7 PDPA principles: General, Notice and Choice, Disclosure, Security, Retention, Data Integrity, and Access. |
| **NFR-SE-09** | **Report abuse:** the _system_ shall limit the effect of false _QR reports_ by applying FR-15 (only _scam-pattern reports_ count), FR-16 (one per user per QR) and FR-09 (reports never cause a _STOP verdict_). | M        | Covered by the ACs of FR-09, FR-15 and FR-16.                                                                                  |

### 3.6 Development and target environment

| Item                   | Development environment                                                  | Target environment                                            |
| ---------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------- |
| User device            | Not applicable                                                           | Any Android or iOS smartphone with a current Telegram version |
| Channels               | Telegram Bot API                                                         | Same. WhatsApp is future work (SDD section 17).               |
| Programming language   | Python 3.12                                                              | Python 3.12                                                   |
| Cloud platform         | Amazon Web Services, serverless (Lambda, API Gateway, SQS, DynamoDB)     | Same                                                          |
| Region                 | Asia Pacific (Singapore)                                                 | Same                                                          |
| Database               | Amazon DynamoDB                                                          | Same                                                          |
| Infrastructure as code | AWS SAM                                                                  | Same                                                          |
| Testing                | pytest, moto, a simulated channel                                        | Not applicable                                                |
| Version control        | Git (GitHub)                                                             | Not applicable                                                |
| Main libraries         | zxing-cpp, OpenCV, Pillow, boto3, PyYAML                                 | Same                                                          |

### 3.7 Other non-functional requirements

#### System support

| ID            | Requirement                                                                             | Priority |
| ------------- | --------------------------------------------------------------------------------------- | -------- |
| **NFR-SU-01** | The _system_ shall reply to the word "Bantuan" or "Help" with the help message (FR-23). | M        |
| **NFR-SU-02** | The team shall receive an automatic notification when any event fails 3 times.          | S        |

#### Legal and ethical

| ID            | Requirement                                                                                                                       | Priority |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------- | -------- |
| **NFR-LE-01** | The welcome message shall state that Semak Dulu is not a bank, the police or a government service, and that it gives advice only. | M        |
| **NFR-LE-02** | No message shall call a specific person or account a scammer ("penipu").                                                          | M        |

---

## 4. References

| #    | Reference                                                                                                                                                                                                        |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [1]  | Hackathon brief: Cybersecurity track (problem statement, RM2.7 billion figure, MVP and stretch goals)                                                                                                            |
| [2]  | Semak Dulu Software Design Document v1.2, 21 Oct 2026 (`docs/SDD.md`)                                                                                                                                            |
| [3]  | T. Anwar, "TFB2014 Software Engineering and Human Computer Interfaces, Week 04b: Specifying Requirements", lecture slides, Faculty of Science, Management and Computing, 2026 (slides © H. Lichter, RWTH Aachen) |
| [4]  | S. Robertson, J. Robertson, _Mastering the Requirements Process_, Addison-Wesley, 1999                                                                                                                           |
| [5]  | IEEE Std 830-1998, _IEEE Recommended Practice for Software Requirements Specifications_                                                                                                                          |
| [6]  | C. Rupp, "Linguistic methods of Requirements Engineering (NLP)", EuroSPI, 2000                                                                                                                                   |
| [9]  | Telegram, _Telegram Bot API_ documentation, core.telegram.org/bots/api                                                                                                                                           |
| [10] | EMVCo, _EMV QR Code Specification for Payment Systems: Merchant-Presented Mode_                                                                                                                                  |
| [11] | PayNet, _DuitNow QR_ specification                                                                                                                                                                               |
| [12] | Personal Data Protection Act 2010 (Act 709), Malaysia                                                                                                                                                            |
| [13] | PDRM Semak Mule website, semakmule.rmp.gov.my                                                                                                                                                                    |

---

## Appendix A: How the writing rules were applied

The lecture's rules R1 to R6 were applied to every requirement. These examples show the main changes from the earlier requirement list.

| Rule                      | Earlier wording                                                        | Problem                                                                          | Wording in this SRS                                                                                                                                      |
| ------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1 Active voice           | "The bot accepts a forwarded image... with no installs"                | Unclear who installs                                                             | FR-05: "The user shall not need to install any app other than Telegram"                                                                                  |
| R2 Main verbs             | "Reports separate scam-pattern reasons from seller disputes"           | "Separate" hides the process                                                     | FR-15: "Dispute and other reports shall not count toward the evidence level"                                                                             |
| R3 Complete process words | "The bot tells them to call their bank and 999"                        | Who, in what order, and what else happens?                                       | FR-13: 4 steps in order, plus the PAID alert to the primary contact                                                                                      |
| R4 Comparatives           | "Wording scales with evidence", "a stronger warning"                   | Stronger than what?                                                              | FR-15: 3 evidence levels with fixed counts and fixed text                                                                                                |
| R4 Quantify               | "after about 3 minutes"                                                | "About" is vague                                                                 | FR-20: 180 seconds, NFR-PF-04: ±30 seconds                                                                                                               |
| R5 Universal quantifiers  | "It never says a QR is safe"                                           | Which messages? Which languages? What counts as "safe"?                          | FR-10: "No message... in any language, to any user, shall contain a _safety claim_", with _safety claim_ defined in 1.4, including the negated exception |
| R5 Universal quantifiers  | "Every verdict leads with the action"                                  | Does it apply to failure messages too?                                           | FR-11 covers _verdicts_, FR-12 covers failure cases, NFR-US-05 covers all messages to _parents_                                                          |
| R6 Incomplete conditions  | "The alert fires only on a firm STOP"                                  | What happens on VERIFY? And after "already paid"?                                | FR-18: exactly two triggers, and an explicit "shall not" for VERIFY                                                                                      |
| R6 Incomplete conditions  | "If the child hasn't tapped after 3 minutes, alert the second contact" | What if there is no second contact? What if nobody responds to the second alert? | FR-20 covers all 3 outcomes                                                                                                                              |
| Nouns without reference   | "the bot", "the parent"                                                | Not defined                                                                      | Defined in 1.4 as _system_ and _parent_                                                                                                                  |
| Nominalisation            | "consent for the child alert"                                          | Who gives it, how, and what if they refuse?                                      | FR-02: the parent taps "Setuju", the system records the time, and without it no link exists                                                              |

## Appendix B: Traceability to the SDD

| Requirement                | SDD section                            | SDD test scenario            |
| -------------------------- | -------------------------------------- | ---------------------------- |
| FR-01, FR-02, FR-21        | 6.1 Setup flow, 3.2 Data               | Setup walkthrough            |
| FR-03, FR-20               | 5.4 Alerts and escalation              | S8                           |
| FR-04                      | 6.4 Message catalogue                  | Catalogue tests              |
| FR-05, FR-08               | 2.2 Architecture, 6.2 Check flow       | S1                           |
| FR-06, FR-07, FR-12        | 5.2 Decoding pipeline, 3.5 QR findings | Fixture tests, S2, S6        |
| FR-09, FR-10, FR-11        | 5.3 Verdict engine                     | S1 to S5, safety phrase test |
| FR-13, FR-18, FR-19, FR-27 | 5.4 Alerts                             | S1, S9                       |
| FR-14 to FR-17             | 5.5 Reports                            | S11, S12                     |
| FR-22                      | 9 Security and privacy                 | S14                          |
| FR-23, FR-25               | 4.4 Error handling                     | S13                          |
| FR-24, FR-26               | 5.6 Pending checks                     | S7                           |
| DR-01 to DR-09             | 3.6 Retention, 9.2 Privacy             | Data inspection              |
| NFR-PF-01 to 04            | 2.6 Performance targets                | Timed tests                  |
| NFR-SE-01 to 09            | 9 Security and privacy                 | Security review              |
