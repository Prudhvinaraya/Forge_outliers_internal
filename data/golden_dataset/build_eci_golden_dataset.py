#!/usr/bin/env python3
"""Create a stratified, evidence-grounded golden dataset for the ECI EVM corpus."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

from pypdf import PdfReader


ROOT = Path("/workspace/scratch/96a08ada8e73")
UPLOAD = ROOT / "upload"
OUT = ROOT / "output" / "eci_golden_dataset_v1"
RAW_FAQ = Path("/workspace/scratch/eci_evm_faqs_raw.json")

DOCS = {
    "DOC_EVM_FAQ_2026": UPLOAD / "ECI_EVM_FAQs_Ingestion_Corpus(1).pdf",
    "DOC_EVM_MANUAL_2026": UPLOAD / "evm-manual-2026.pdf",
    "DOC_PRESIDING_OFFICER_2023": UPLOAD / "BROCHURE FOR PRESIDING OFFICER.pdf",
    "DOC_ELECTOR_BROCHURE_2023": UPLOAD / "EVM BROCHURE FOR ELECTORS.pdf",
    "DOC_CANDIDATE_PARTY_BROCHURE_2024": UPLOAD / "EVM BROCHURE FOR CANDIDATES & POLITICAL PARTIES.pdf",
}

DUPLICATE_DOC = UPLOAD / "EVM BROCHURE FOR.pdf"


def clean(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", text).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snippet(text: str, keyword: str | None = None, limit: int = 850) -> str:
    text = clean(text)
    if len(text) <= limit:
        return text
    position = text.lower().find((keyword or "").lower()) if keyword else 0
    if position < 0:
        position = 0
    start = max(0, position - limit // 3)
    end = min(len(text), start + limit)
    candidate = text[start:end]
    if start:
        candidate = "..." + candidate
    if end < len(text):
        candidate += "..."
    return candidate


def faq_locator(short_id: str) -> str:
    match = re.fullmatch(r"C(\d+)Q(\d+)", short_id)
    if not match:
        raise ValueError(f"Invalid FAQ locator: {short_id}")
    return f"ECI-EVM-C{int(match.group(1)):02d}-Q{int(match.group(2)):02d}"


def F(short_id: str, role: str, keyword: str | None = None) -> dict:
    return {"type": "faq", "locator": faq_locator(short_id), "role": role, "keyword": keyword}


def P(document_id: str, page: int, role: str, keyword: str) -> dict:
    return {"type": "page", "document_id": document_id, "page": page, "role": role, "keyword": keyword}


def item(question: str, answer: str, evidence: list[dict], claims: list[str], entities: list[str]) -> dict:
    return {
        "question": question,
        "reference_answer": answer,
        "evidence_specs": evidence,
        "reference_claims": claims,
        "required_entities": entities,
    }


SINGLE_HOP = [
    item("What three units make up an ECI-EVM system?", "An ECI-EVM system consists of a Ballot Unit (BU), a Control Unit (CU), and a Voter Verifiable Paper Audit Trail (VVPAT).", [F("C1Q1", "definition", "consists of")], ["The system contains BU, CU and VVPAT."], ["Ballot Unit", "Control Unit", "VVPAT"]),
    item("Where and when were EVMs first used in an Indian election?", "They were first used in the 1982 by-election to the Parur Assembly Constituency in Kerala.", [F("C1Q3", "historical fact", "Parur")], ["First use was at Parur, Kerala, in 1982."], ["Parur Assembly Constituency", "Kerala", "EVM"]),
    item("Where and when was VVPAT first used with EVMs?", "VVPAT was first used in the 2013 by-election to the Noksen Assembly Constituency in Nagaland.", [F("C1Q4", "historical fact", "Noksen")], ["First VVPAT use was at Noksen, Nagaland, in 2013."], ["VVPAT", "Noksen Assembly Constituency", "Nagaland"]),
    item("On what date was the legal framework for VVPAT introduced?", "The legal framework for VVPAT was introduced on 14 August 2013.", [F("C1Q5", "date", "14th August 2013")], ["The date was 14 August 2013."], ["VVPAT"]),
    item("Which model of ECI-EVM and VVPAT is presently used according to the FAQ corpus?", "The M3 model of ECI-EVM and VVPAT is presently used.", [F("C1Q6", "model", "M3 Model")], ["The current model is M3."], ["M3 EVM", "M3 VVPAT"]),
    item("Which organizations manufacture ECI EVMs and VVPATs?", "They are manufactured in India by Bharat Electronics Limited (BEL) and Electronics Corporation of India Limited (ECIL).", [F("C1Q8", "manufacturers", "Bharat Electronics")], ["BEL and ECIL manufacture the machines.", "The machines are not imported."], ["BEL", "ECIL", "EVM", "VVPAT"]),
    item("What is the maximum number of votes an ECI-EVM can record?", "An ECI-EVM can record a maximum of 2,000 votes, although it is generally used for up to 1,500 votes.", [F("C1Q10", "capacity", "2,000")], ["Maximum recording capacity is 2,000 votes."], ["ECI-EVM"]),
    item("What is the maximum number of candidates, including NOTA, that one EVM set can accommodate?", "One EVM set can accommodate up to 384 candidates including NOTA by connecting 24 Ballot Units, each supporting 16 candidates, to one Control Unit.", [F("C1Q11", "capacity", "384")], ["Maximum candidate capacity is 384 including NOTA."], ["Ballot Unit", "Control Unit", "NOTA"]),
    item("Do EVM and VVPAT require an external electricity supply?", "No. They operate on their own power packs and do not require an external electricity supply.", [F("C1Q12", "power source", "do not require")], ["No external power supply is required."], ["EVM", "VVPAT", "Power Pack"]),
    item("How many EVM sets are required at a polling station for simultaneous Parliament and State Assembly elections?", "Two separate EVM sets are required: one for the Parliamentary Constituency and one for the Legislative Assembly Constituency.", [F("C1Q13", "simultaneous election requirement", "two separate sets")], ["Two separate sets are required."], ["Parliamentary Constituency", "Legislative Assembly Constituency", "EVM"]),
    item("For approximately how long is a VVPAT slip visible to the voter?", "The VVPAT slip is visible through the window for about seven seconds before it is cut and falls into the sealed drop box.", [F("C1Q14", "visibility duration", "7 seconds")], ["The slip is visible for about seven seconds."], ["VVPAT slip"]),
    item("What are the voltage and capacity ratings of the Control Unit power pack?", "The Control Unit power pack is rated at 7.5 volts and 2 ampere-hours.", [F("C1Q17", "power specification", "7.5Volts")], ["CU power pack rating is 7.5 V, 2 Ah."], ["Control Unit", "Power Pack"]),
    item("What are the voltage and capacity ratings of the VVPAT power pack?", "The VVPAT power pack is rated at 22.5 volts and 4 ampere-hours.", [F("C1Q17", "power specification", "22.5 volts")], ["VVPAT power pack rating is 22.5 V, 4 Ah."], ["VVPAT", "Power Pack"]),
    item("What is the approximate size of a printed VVPAT slip?", "A printed VVPAT slip is approximately 99 mm by 56 mm.", [F("C1Q19", "dimensions", "99mm")], ["Approximate dimensions are 99 mm x 56 mm."], ["VVPAT slip"]),
    item("How long can a VVPAT slip retain its print when stored properly?", "The thermal-paper VVPAT slip has a print-retention capability of about five years when stored properly.", [F("C1Q19", "retention period", "five years")], ["Print retention is about five years under proper storage."], ["VVPAT slip", "Thermal Paper"]),
    item("Which five details are printed on a VVPAT slip?", "It contains the candidate serial number, candidate name, candidate or party symbol, session number, and VVPAT ID.", [F("C1Q20", "printed fields", "Candidate Serial Number")], ["The five printed fields are serial number, name, symbol, session number and VVPAT ID."], ["VVPAT slip", "Candidate"]),
    item("Who conducts First Level Checking of EVMs and VVPATs?", "Authorized BEL or ECIL engineers conduct FLC at district headquarters under the District Election Officer's supervision and in the presence of representatives of recognized political parties.", [F("C1Q22", "responsibility", "authorised engineers")], ["Authorized BEL/ECIL engineers conduct FLC.", "The DEO supervises it and party representatives are present."], ["BEL", "ECIL", "District Election Officer", "FLC"]),
    item("How long can a Control Unit retain an election result?", "It can retain the result until the data is deliberately deleted or cleared.", [F("C2Q14", "data retention", "until the data is deleted")], ["The CU retains results until deletion or clearing."], ["Control Unit"]),
    item("May the VVPAT thermal-paper roll be changed at a polling station?", "No. Changing the thermal-paper roll at a polling station is strictly prohibited; a reserve VVPAT is used if the roll is exhausted.", [F("C2Q16", "prohibition", "strictly prohibited")], ["The roll must not be changed at the polling station."], ["VVPAT", "Thermal Paper Roll"]),
    item("How many polling stations per Assembly Constituency or Assembly Segment undergo mandatory VVPAT-slip verification?", "VVPAT slips from five randomly selected polling stations in each Assembly Constituency or Assembly Segment are mandatorily verified before the result is declared.", [F("C2Q20", "verification sample", "five randomly selected")], ["Five randomly selected polling stations are verified."], ["VVPAT", "Assembly Constituency", "Assembly Segment"]),
    item("Which device is used to load candidate details and symbols into VVPATs during commissioning?", "A Symbol Loading Unit (SLU) is used to load the ballot sheet containing candidate serial numbers, names and symbols into VVPATs.", [F("C2Q21", "device", "Symbol Loading Unit")], ["The Symbol Loading Unit loads candidate details into VVPATs."], ["Symbol Loading Unit", "VVPAT"]),
    item("Can a voter cast more than one vote by repeatedly pressing a Ballot Unit button?", "No. After one button press records a vote, further presses are ignored until the Presiding Officer enables the Ballot Unit for the next verified voter.", [F("C3Q3", "single-vote behavior", "subsequent button pressing")], ["Repeated button presses do not record additional votes."], ["Ballot Unit", "Presiding Officer"]),
    item("Does an ECI-EVM have an operating system?", "No. It has firmware or machine-level instructions embedded in One Time Programmed memory, not an operating system.", [F("C3Q19", "technical architecture", "does not have an Operating System")], ["ECI-EVM has no operating system."], ["EVM", "Firmware", "OTP Memory"]),
    item("What is the first formal step when a voter alleges that the VVPAT slip shows a different candidate?", "Under Rule 49MA, the Presiding Officer first obtains a written declaration from the voter after warning the voter about the consequences of a false declaration.", [F("C4Q7", "complaint procedure", "written declaration")], ["The Presiding Officer obtains a written declaration after giving the prescribed warning."], ["Rule 49MA", "Presiding Officer", "Voter"]),
    item("Why is the VVPAT display window tinted?", "It is tinted to balance the voter's ability to verify the illuminated slip with the need to preserve vote secrecy from other people.", [F("C3Q15", "design rationale", "secrecy of vote")], ["The tint protects vote secrecy while permitting voter verification."], ["VVPAT", "Vote Secrecy"]),
    item("When must the mock poll begin relative to the scheduled actual poll?", "The mock poll must begin 90 minutes before the scheduled actual poll time.", [P("DOC_PRESIDING_OFFICER_2023", 4, "timing", "90 minutes")], ["Mock poll starts 90 minutes before the scheduled poll."], ["Mock Poll", "Presiding Officer"]),
    item("What is the minimum number of votes to cast during the polling-station mock poll?", "At least 50 votes must be cast, including votes for every contesting candidate and NOTA.", [P("DOC_PRESIDING_OFFICER_2023", 4, "minimum mock-poll votes", "atleast 50 votes")], ["At least 50 mock-poll votes are required."], ["Mock Poll", "NOTA"]),
    item("In which position should the VVPAT paper-roll knob be during transportation?", "The knob should be horizontal, which is the transportation or locked position.", [P("DOC_PRESIDING_OFFICER_2023", 2, "transport configuration", "VVPAT knob is horizontal")], ["The transportation position is horizontal."], ["VVPAT", "Paper Roll Knob"]),
    item("What accessibility feature is provided beside the Ballot Unit candidate buttons?", "Digits 1 through 16 are embossed in Braille beside the candidate buttons to guide visually impaired electors.", [P("DOC_ELECTOR_BROCHURE_2023", 2, "accessibility", "Braille signage")], ["Braille digits 1-16 are provided."], ["Ballot Unit", "Braille", "Visually Impaired Elector"]),
    item("What is the primary purpose of EVM Management System 2.0?", "EMS 2.0 manages ECI's EVM inventory, records EVM-related activities and tracks units and their locations without manual intervention across the operational chain.", [P("DOC_EVM_MANUAL_2026", 114, "system purpose", "managing inventory")], ["EMS 2.0 manages and tracks EVM inventory and activities."], ["EMS 2.0", "EVM Inventory"]),
]


MULTI_HOP = [
    item("Describe the complete voter-visible sequence from ballot enablement to confirmation that a vote was registered.", "The Presiding Officer enables the ballot from the Control Unit. The voter presses the chosen blue button on the Ballot Unit, its red light glows, and the VVPAT displays a slip with the candidate's serial number, name and symbol for about seven seconds. The slip is cut into the sealed drop box, after which the Control Unit emits a beep confirming registration.", [P("DOC_ELECTOR_BROCHURE_2023", 2, "vote sequence", "Control Unit is kept"), F("C1Q14", "audio and visual confirmation", "loud beep")], ["The Presiding Officer enables the ballot.", "The BU records the selection and shows a red light.", "VVPAT displays and deposits the slip.", "CU emits a confirmation beep."], ["Presiding Officer", "Control Unit", "Ballot Unit", "VVPAT"]),
    item("How does the system reach a capacity of 384 candidates from the capacity of one Ballot Unit?", "One Ballot Unit supports 16 candidates including NOTA. Up to 24 Ballot Units can be connected to one Control Unit, so 24 x 16 gives a maximum of 384 candidates including NOTA.", [F("C1Q11", "capacity relationship", "24 BUs"), P("DOC_ELECTOR_BROCHURE_2023", 2, "corroborating capacity", "384 candidates")], ["One BU supports 16 candidates.", "Twenty-four BUs can be connected.", "The combined maximum is 384."], ["Ballot Unit", "Control Unit", "NOTA"]),
    item("Compare how the Control Unit and VVPAT are powered and explain why polling can continue where grid electricity is unavailable.", "Both units use self-contained power packs, so they do not need grid electricity. The Control Unit uses a 7.5 V, 2 Ah pack, while the VVPAT uses a 22.5 V, 4 Ah pack.", [F("C1Q12", "independent power", "external power supply"), F("C1Q17", "power ratings", "22.5 volts")], ["Neither device needs external electricity.", "CU rating is 7.5 V, 2 Ah.", "VVPAT rating is 22.5 V, 4 Ah."], ["Control Unit", "VVPAT", "Power Pack"]),
    item("Give the main timeline from the first EVM use through VVPAT introduction and the current machine model.", "EVMs were first used at Parur, Kerala, in 1982. VVPAT was first used at Noksen, Nagaland, in 2013, and its legal framework was introduced on 14 August 2013. The corpus states that the M3 model is presently used.", [F("C1Q3", "EVM milestone", "1982"), F("C1Q4", "VVPAT milestone", "2013"), F("C1Q5", "legal milestone", "14th August 2013"), F("C1Q6", "current model", "M3")], ["EVM first use: 1982 Parur.", "VVPAT first use: 2013 Noksen.", "VVPAT legal framework: 14 August 2013.", "Current model: M3."], ["EVM", "VVPAT", "Parur", "Noksen", "M3"]),
    item("How do manufacturing responsibility and First Level Checking create institutional separation before machines are used?", "BEL and ECIL manufacture the machines. Their authorized engineers conduct FLC at district headquarters, but the process is supervised by the District Election Officer and observed by representatives of recognized political parties, providing administrative oversight beyond the manufacturer.", [F("C1Q8", "manufacturing", "BEL"), F("C1Q22", "FLC oversight", "District Election Officer")], ["BEL/ECIL manufacture the machines.", "Authorized manufacturer engineers conduct FLC.", "DEO supervision and political-party presence provide oversight."], ["BEL", "ECIL", "District Election Officer", "Political Parties", "FLC"]),
    item("What is the difference between first and second randomization in allocation level, timing and participants?", "First randomization uses EMS to allocate machines Assembly Constituency or Assembly Segment-wise and is conducted in the presence of recognized political parties. Second randomization occurs after candidate finalization and just before commissioning; it allocates machines polling-station-wise and identifies reserves in the presence of candidates or their representatives and the ECI Observer.", [P("DOC_EVM_MANUAL_2026", 31, "first randomization", "Assembly Constituency-wise"), P("DOC_EVM_MANUAL_2026", 35, "second randomization", "Polling Station-wise")], ["First randomization allocates AC/AS-wise.", "Second randomization allocates polling-station-wise and reserves.", "The two stages have different timing and participant groups."], ["First Randomization", "Second Randomization", "EMS", "Political Parties", "Candidates"]),
    item("How do FLC, randomization and commissioning progressively narrow the set of machines used at a polling station?", "FLC establishes which machines are fit for election use. First randomization allocates FLC-OK machines to an Assembly Constituency or Segment, second randomization assigns them to specific polling stations and reserves, and commissioning loads the finalized candidate details and tests and seals the assigned machines.", [P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 6, "FLC fitness", "Functionality check"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 8, "randomization", "First randomization"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 9, "commissioning", "Symbol loading")], ["FLC determines fitness.", "Randomizations allocate first by constituency and then by polling station.", "Commissioning configures and tests the final machines."], ["FLC", "First Randomization", "Second Randomization", "Commissioning"]),
    item("What checks must agree before a polling-station mock poll is accepted, and what cleanup follows?", "The electronic CU result must match the manual vote record, and the VVPAT-slip count must match the CU result. After agreement, the CU mock data is cleared, slips are stamped and sealed in a black envelope, the VVPAT drop box is shown empty and sealed, and the mock-poll certificate is completed.", [P("DOC_PRESIDING_OFFICER_2023", 4, "mock poll checks", "Mock poll tallies ONLY"), P("DOC_EVM_MANUAL_2026", 59, "cleanup", "Press CLEAR button")], ["CU result must match the manual record.", "VVPAT slips must match the CU result.", "Mock data and slips are cleared and documented before actual poll."], ["Mock Poll", "Control Unit", "VVPAT", "Mock Poll Certificate"]),
    item("During actual polling, how does replacement differ when only the VVPAT fails versus when the BU or CU fails?", "If only the VVPAT fails, only that VVPAT is replaced and no mock poll is required. If the BU or CU fails, the entire BU-CU-VVPAT set is replaced and a limited mock poll of one vote per candidate including NOTA is conducted before polling resumes.", [P("DOC_PRESIDING_OFFICER_2023", 6, "replacement comparison", "replace only VVPAT"), F("C2Q13", "vote preservation", "full set")], ["VVPAT-only failure requires only VVPAT replacement and no mock poll.", "BU/CU failure requires full-set replacement and a fresh limited mock poll."], ["Ballot Unit", "Control Unit", "VVPAT", "Replacement Protocol"]),
    item("If equipment fails during poll, how are previously cast votes preserved and included in the final polling-station result?", "Votes already recorded remain safe in the affected Control Unit and in the VVPAT slip compartment. Polling resumes with the prescribed replacement, and on counting day the votes from every EVM used at that polling station are aggregated. If a CU result cannot be obtained technically, its corresponding VVPAT slips are counted.", [F("C2Q13", "failure and aggregation", "remain safe"), P("DOC_PRESIDING_OFFICER_2023", 6, "replacement procedure", "Replacement Protocol for Actual Poll")], ["Previously recorded votes remain stored.", "All machines used at the station contribute to the aggregate result.", "VVPAT slips provide the fallback if a CU result cannot be read."], ["Control Unit", "VVPAT", "Reserve EVM"]),
    item("How can candidates monitor the custody of polled EVMs from transport through strong-room storage?", "Polling agents may follow the vehicles carrying polled machines to the collection centre. Storage occurs in the presence of candidates or representatives, who may place their seals on strong-room locks and monitor the strong room; the facility also has CCTV and armed, layered security.", [P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 11, "transport observation", "allowed to follow"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 11, "strong-room observation", "put their seals")], ["Agents may follow transport vehicles.", "Candidates may observe storage and seal the locks.", "CCTV and armed security protect the strong room."], ["Candidates", "Polling Agents", "Polled Strong Room", "CCTV", "CAPF"]),
    item("What safeguards apply to EVM movement both operationally and technologically?", "Operationally, movements use sealed or containerized vehicles, armed security, videography, advance information to political parties, registers and continuous monitoring. Technologically, GPS or mobile-app tracking monitors the end-to-end movement under DEO responsibility.", [P("DOC_EVM_MANUAL_2026", 14, "transport safeguards", "GPS enabled vehicles"), P("DOC_EVM_MANUAL_2026", 52, "poll-day tracking", "end-to-end movement")], ["Vehicles and consignments are sealed and guarded.", "Movements are documented and videographed.", "GPS/mobile tracking provides end-to-end monitoring."], ["EVM Movement", "GPS", "District Election Officer", "Armed Security"]),
    item("Trace when the Control Unit power pack is installed, protected and removed during an election cycle.", "A new CU power pack is installed and sealed during commissioning in the presence of candidates or representatives. The commissioned machine remains secured through storage and polling, and the CU is powered for result retrieval on counting day. The pack is removed only after counting is completed, again in the presence of candidates or representatives.", [F("C5Q30", "battery lifecycle", "new Power Pack"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 12, "post-count removal", "power packs are removed")], ["Installation occurs at commissioning.", "The battery compartment is sealed and custody is monitored.", "Removal occurs after counting."], ["Control Unit", "Power Pack", "Commissioning", "Counting Day"]),
    item("How does the EVM system support both accessibility and independent voter verification?", "Braille digits beside Ballot Unit buttons guide visually impaired electors. For every voter, the chosen button's red light and the VVPAT slip provide visual confirmation, while the CU beep provides audio confirmation; the slip shows the selected candidate details for about seven seconds.", [P("DOC_ELECTOR_BROCHURE_2023", 2, "Braille accessibility", "Braille signage"), F("C1Q14", "verification signals", "audio and visual")], ["Braille supports visually impaired voters.", "Red light and VVPAT slip provide visual feedback.", "The CU beep provides audio confirmation."], ["Braille", "Ballot Unit", "VVPAT", "Control Unit"]),
    item("How do standalone design, OTP memory and the Unauthorized Access Detection Module address three different attack paths?", "Standalone design and the absence of radio-frequency capability block network, Wi-Fi and Bluetooth access. OTP memory prevents the embedded program from being altered after programming. UADM protects the CU microcontroller and memory by rendering the machine inoperative if its secure module is opened.", [P("DOC_ELECTOR_BROCHURE_2023", 3, "technical safeguards", "Standalone"), F("C3Q19", "firmware architecture", "One Time Programmed")], ["Standalone/RF isolation addresses remote connectivity.", "OTP memory addresses reprogramming.", "UADM addresses physical access to the secure module."], ["OTP Chip", "UADM", "Radio Frequency", "Control Unit"]),
    item("At which major lifecycle stages can political parties, candidates or their agents observe or participate?", "They are involved in warehouse opening and closing, FLC, both randomizations, commissioning, dispersal, mock and actual poll, transport to the collection centre, strong-room sealing and monitoring, and counting. They may also select machines for prescribed higher mock polls, sign seals and receive machine lists and Form 17C copies at relevant stages.", [P("DOC_ELECTOR_BROCHURE_2023", 4, "early-stage participation", "First Level Checking"), P("DOC_ELECTOR_BROCHURE_2023", 5, "poll and count participation", "Counting Day")], ["Stakeholders participate from storage and preparation through counting.", "They can observe tests, sign seals and receive lists or records."], ["Political Parties", "Candidates", "Polling Agents", "FLC", "Counting"]),
    item("What actions close the poll and create the polling-station vote record?", "The Presiding Officer presses CLOSE, then TOTAL, records total polled votes plus poll start and end times in Form 17C and the diary, switches off the CU, disconnects the units, removes the VVPAT battery, and seals each carrying case with address tags signed by polling agents.", [P("DOC_PRESIDING_OFFICER_2023", 6, "close-of-poll sequence", "Closing of poll procedure"), P("DOC_EVM_MANUAL_2026", 97, "Form 17C record", "Part-I of Form 17C")], ["CLOSE prevents further polling.", "TOTAL supplies the figure recorded in Form 17C.", "Units are powered down, disconnected and sealed."], ["Presiding Officer", "Control Unit", "Form 17C", "Polling Agents"]),
    item("How are electronic results and VVPAT evidence used together on counting day?", "After seal verification, the CU result is displayed and recorded in Form 17C for compilation. Separately, VVPAT slips from five randomly selected polling stations per Assembly Constituency or Segment are mandatorily verified; VVPAT slips are also counted when a CU shows no result display.", [P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 12, "CU counting", "Counting of votes"), F("C2Q20", "VVPAT verification", "no display")], ["CU results are read after seal verification.", "Five randomly selected polling stations undergo mandatory VVPAT verification.", "VVPAT counting is used when CU result display fails."], ["Control Unit", "VVPAT", "Form 17C", "Counting Day"]),
    item("What happens from a Rule 49MA complaint through the possible outcomes of the supervised test vote?", "The voter gives a written declaration after being warned about a false claim. The Presiding Officer permits a test vote in the presence of candidates or polling agents and observes the slip. If the claim is true, voting on that machine stops and the RO is informed; if false, the test vote and prescribed remarks are entered in Forms 17A and 17C with the voter's signature or thumb impression.", [F("C4Q7", "complete complaint process", "test vote"), P("DOC_EVM_MANUAL_2026", 55, "presiding-officer duty", "Rule 49MA")], ["A written declaration precedes a supervised test vote.", "A true claim stops use of the machine and is reported.", "A false claim is documented in Forms 17A and 17C."], ["Rule 49MA", "Presiding Officer", "Returning Officer", "Form 17A", "Form 17C"]),
    item("How is correct candidate-symbol loading made observable, and how are used SLUs secured afterward?", "During commissioning, the ballot sheet is loaded into each VVPAT through an SLU while the symbols are simultaneously displayed on a monitor for candidates or representatives. Used SLUs are sealed in containers, inventoried, stored under double lock by the DEO, and retained through counting under the prescribed custody process.", [F("C2Q21", "observable symbol loading", "big monitor"), P("DOC_EVM_MANUAL_2026", 44, "SLU custody", "SLU STORAGE ROOM")], ["Symbols are displayed while being loaded.", "Used SLUs are sealed, inventoried and stored under double lock.", "DEO is responsible for SLU security."], ["Symbol Loading Unit", "VVPAT", "District Election Officer", "Candidates"]),
    item("Who holds the two sets of strong-room keys at district headquarters, and how is stakeholder visibility added when the room is opened or closed?", "At district headquarters, the DEO holds all keys for Lock 1 and the Deputy DEO or equivalent holds all keys for Lock 2. Political-party representatives or, after candidate finalization, candidates or representatives are invited to openings and closings, which are videographed.", [P("DOC_EVM_MANUAL_2026", 11, "key custody", "District Election Officer"), P("DOC_ELECTOR_BROCHURE_2023", 4, "opening and closing visibility", "Opening and Closing")], ["Separate officers hold the two lock keys.", "Stakeholders are present for opening and closing.", "The process is videographed."], ["District Election Officer", "Deputy District Election Officer", "Strong Room"]),
    item("How does security differ between routine non-election storage and storage of polled EVMs?", "Routine warehouse storage uses double locks, CCTV and at least half a section of armed security. A polled-EVM strong room uses stronger layered protection: at least one platoon of CAPF for the inner cordon, State Armed Police or State Police outside, CCTV, candidate seals and continuous candidate monitoring access.", [P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 5, "non-election security", "armed security"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 11, "post-poll security", "CAPF")], ["Routine storage has half-section armed security, double locks and CCTV.", "Polled storage adds a CAPF platoon and two-cordon security plus candidate monitoring."], ["EVM Warehouse", "Polled Strong Room", "CAPF", "CCTV"]),
    item("What must happen before a training or awareness EVM can be returned to election use?", "Training and awareness machines are kept separately. If they are needed for an election again, they must undergo de-novo FLC, randomization and commissioning before reintroduction.", [P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 7, "separate training storage", "stored separately"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 8, "training machine reuse", "de-novo FLC")], ["Training machines are stored separately.", "Reuse requires fresh FLC, randomization and commissioning."], ["Training EVM", "FLC", "Randomization", "Commissioning"]),
    item("For simultaneous Lok Sabha and Assembly elections, how do the two EVM sets remain distinct through allocation?", "The polling station uses separate EVM sets for the Parliamentary and Assembly contests. During first randomization they are allocated separately at Assembly Segment level for the Parliamentary contest and Assembly Constituency level for the Assembly contest; second randomization then assigns the corresponding sets polling-station-wise.", [F("C1Q13", "two-set requirement", "two separate sets"), P("DOC_EVM_MANUAL_2026", 31, "first-stage separation", "Simultaneous elections"), P("DOC_EVM_MANUAL_2026", 35, "polling-station allocation", "Simultaneous elections")], ["Two distinct sets are required.", "First randomization separates PC and Assembly allocation levels.", "Second randomization assigns both sets to polling stations."], ["Lok Sabha", "Legislative Assembly", "First Randomization", "Second Randomization"]),
    item("Why may a CU still display 99% after a full poll day, and at what voltages does it warn or stop functioning?", "With a light load, such as one BU and fewer than 1,000 votes, voltage may remain above 7.4 V, so the CU can still show 99%. The CU warns to change the battery below 5.8 V and stops functioning below 5.5 V, while stored data remains intact.", [F("C5Q34", "99 percent explanation", "less than 1000 votes"), F("C5Q31", "voltage thresholds", "less than 5.8 V")], ["Light load can keep voltage above the 99% display threshold.", "Warning threshold is below 5.8 V.", "Operation stops below 5.5 V but data remains safe."], ["Control Unit", "Power Pack", "Ballot Unit"]),
    item("How are polling agents shown that no pre-recorded mock votes remain before actual polling starts?", "Before mock poll, the Presiding Officer shows the empty VVPAT compartment and zero CU total. After the mock poll, CU data is cleared, mock slips are removed and sealed separately, the VVPAT drop box is again shown empty, and the CU total is shown as zero before actual poll.", [P("DOC_PRESIDING_OFFICER_2023", 4, "mock-poll clearing", "Press TOTAL button"), P("DOC_PRESIDING_OFFICER_2023", 6, "pre-actual-poll zero check", "confirm Zero vote")], ["Zero status and empty VVPAT are demonstrated before mock poll.", "Mock data and slips are removed afterward.", "Zero status is demonstrated again before actual poll."], ["Polling Agents", "Control Unit", "VVPAT", "Mock Poll"]),
    item("What prevents additional votes after poll closure, and what custody steps follow?", "Pressing CLOSE ends vote recording. The total is documented, the CU is switched off, units are disconnected and sealed in carrying cases, and the polled machines are transported under escort to a strong room where candidates may observe storage and sealing.", [P("DOC_PRESIDING_OFFICER_2023", 6, "closure", "Press CLOSE button"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 11, "post-poll custody", "transported from polling station")], ["CLOSE ends voting.", "The result total is documented and units are sealed.", "Guarded transport and strong-room custody follow."], ["Close Button", "Control Unit", "Polled Strong Room"]),
    item("How is the 5% higher mock-poll sample distributed during FLC, and what comparison is performed?", "Political-party representatives may randomly select the sample. Of all machines, 1% receive 1,200 votes, 2% receive 1,000 votes and 2% receive 500 votes. For each selected machine, the electronic result is tallied against the VVPAT-slip count.", [P("DOC_ELECTOR_BROCHURE_2023", 4, "FLC sample design", "1200 votes"), P("DOC_EVM_MANUAL_2026", 21, "comparison and stakeholder selection", "1200 votes")], ["The total sample is 5%.", "It is split 1%/2%/2% across 1200/1000/500 votes.", "Electronic and VVPAT counts are compared."], ["FLC", "Higher Mock Poll", "VVPAT"]),
    item("Why can neither the polling-station deployment of a specific machine nor the final candidate sequence be fixed far in advance?", "Machines pass through two EMS randomizations: first to constituencies or segments and later to specific polling stations and reserves. The second stage occurs only after the contesting-candidate list is finalized, while ballot order follows the finalized candidate arrangement, limiting advance knowledge of the machine and sequence combination.", [F("C2Q39", "deployment unpredictability", "randomization"), P("DOC_EVM_MANUAL_2026", 35, "timing after candidate finalization", "after finalization")], ["Two-stage randomization delays specific deployment knowledge.", "Second randomization follows candidate-list finalization."], ["Candidate Sequence", "First Randomization", "Second Randomization", "EMS"]),
    item("What legal provisions support both use of EVMs and a voter's VVPAT discrepancy complaint?", "Section 61A of the Representation of the People Act, inserted in 1988, empowers ECI to use voting machines. Rule 49MA of the Conduct of Elections Rules provides the procedure for a voter who alleges that the VVPAT slip shows a different candidate, including a written declaration and supervised test vote.", [P("DOC_EVM_MANUAL_2026", 103, "legal authority for EVM", "section 61A"), F("C4Q7", "VVPAT complaint rule", "Rule 49MA")], ["Section 61A authorizes voting machines.", "Rule 49MA governs VVPAT discrepancy complaints."], ["Section 61A", "Rule 49MA", "Representation of the People Act", "Conduct of Elections Rules"]),
]


CORPUS_SUMMARY = [
    item("Summarize what each document family in this ECI EVM corpus contributes.", "The 2026 EVM Manual supplies the detailed operational, legal, responsibility and annexure framework. The FAQ corpus explains common factual, administrative, technical, legal and misconception-related questions. The Presiding Officer brochure gives polling-station procedures, while the elector and candidate/party brochures explain voter operation, safeguards and stakeholder participation at a more accessible level.", [P("DOC_EVM_MANUAL_2026", 4, "manual scope", "four parts"), F("C1Q1", "FAQ and reference scope", "Manual on EVM"), P("DOC_PRESIDING_OFFICER_2023", 4, "presiding workflow", "Conduct of Mock Poll"), P("DOC_ELECTOR_BROCHURE_2023", 2, "elector workflow", "Functioning of EVM")], ["The manual is the detailed procedural source.", "FAQs cover multiple question families.", "Brochures target presiding officers, electors, and candidates or parties."], ["EVM Manual", "EVM FAQs", "Presiding Officer", "Elector", "Candidates"]),
    item("Summarize the four-part structure of the 2026 EVM Manual.", "Part I covers the non-election period through election announcement, including storage, FLC, training and awareness. Part II covers first randomization through post-counting, including commissioning, poll and counting. Part III covers roles, legal provisions, EMS, precautions, documentation and monitoring. Part IV contains annexures and operational formats.", [P("DOC_EVM_MANUAL_2026", 4, "manual organization", "Part-I"), P("DOC_EVM_MANUAL_2026", 6, "index", "PART-IV")], ["Part I covers storage/FLC/training.", "Part II covers randomization through counting.", "Part III covers legal and governance material.", "Part IV contains annexures."], ["EVM Manual", "Part I", "Part II", "Part III", "Part IV"]),
    item("Summarize the end-to-end operational lifecycle of an EVM for an election.", "Machines are stored and secured, pass FLC, and are separated for training or election use. EMS performs first and second randomization, after which assigned machines are commissioned, dispersed, checked by polling parties, mock-polled and used for actual poll. Polled machines are sealed, escorted and stored under monitored strong-room custody, then opened for counting, VVPAT verification and post-count retention.", [P("DOC_EVM_MANUAL_2026", 97, "lifecycle flow", "FLOW CHART"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 8, "allocation stages", "RANDOMIZATIONS"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 11, "post-poll stages", "STORAGE OF EVMS")], ["Lifecycle begins with secure storage and FLC.", "Randomization and commissioning precede poll.", "Mock poll and actual poll precede sealed transport and counting."], ["FLC", "Randomization", "Commissioning", "Poll", "Counting"]),
    item("Summarize the roles of the Ballot Unit, Control Unit and VVPAT during voting.", "The Control Unit, held by the Presiding or Polling Officer, enables each ballot and stores the recorded vote. The voter selects a candidate on the Ballot Unit in the voting compartment. The VVPAT prints and briefly displays the corresponding candidate details, then deposits the slip in its sealed box; the CU beep confirms completion.", [P("DOC_ELECTOR_BROCHURE_2023", 2, "unit roles", "Control Unit is kept"), F("C1Q14", "confirmation behavior", "loud beep")], ["CU enables and stores the vote.", "BU captures the voter's button selection.", "VVPAT displays and stores the paper record."], ["Ballot Unit", "Control Unit", "VVPAT"]),
    item("Summarize the principal technical safeguards described for ECI-EVMs.", "The corpus describes a standalone, non-networked design without radio-frequency communication; OTP-programmed firmware; a secure module and Unauthorized Access Detection Module; dynamic key-press coding; strong mutual authentication; encryption; and real-time timestamping of key presses. Together these address remote connectivity, reprogramming, unauthorized component interaction, cable-signal interpretation and physical secure-module access.", [P("DOC_ELECTOR_BROCHURE_2023", 3, "technical safeguards table", "One Time"), F("C3Q19", "firmware", "firmware")], ["No RF networking is present.", "OTP protects program immutability.", "UADM, authentication, coding, encryption and timestamps add layered controls."], ["OTP", "UADM", "Encryption", "Mutual Authentication", "Real Time Clock"]),
    item("Summarize the principal administrative safeguards applied across the EVM lifecycle.", "Administrative safeguards include documented custody, double locks, CCTV, armed security, logbooks, videography and controlled movement. Machines undergo FLC, two-stage randomization, commissioning, mock polls, sealing and result checks in the presence of political parties, candidates or agents. Lists, forms, seals and acknowledgements create an auditable record from storage through counting.", [F("C2Q3", "stakeholder participation", "political parties"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 5, "storage controls", "double lock"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 10, "poll controls", "mock poll")], ["Custody uses physical security and records.", "Preparation uses FLC, randomization and commissioning.", "Stakeholders observe, sign and receive records."], ["Double Lock", "CCTV", "FLC", "Randomization", "Commissioning"]),
    item("Summarize EVM warehouse and strong-room security requirements.", "Storage uses a single controlled entry where feasible, double locks with keys held by separate officers, armed guards, CCTV with retained recordings, entry and exit logbooks, fire safety and videography of openings and closings. Political-party or candidate representatives receive notice and may attend; polled strong rooms add stronger armed and layered security plus candidate monitoring and sealing rights.", [P("DOC_EVM_MANUAL_2026", 11, "warehouse security", "Double Lock System"), P("DOC_ELECTOR_BROCHURE_2023", 5, "polled strong room visibility", "monitor storage")], ["Double locks and split key custody are required.", "CCTV, guards, logs and videography are required.", "Stakeholders can observe and seal polled strong rooms."], ["EVM Warehouse", "Strong Room", "CCTV", "Armed Security"]),
    item("Summarize the safeguards for transporting and tracking EVMs.", "EVMs are moved through authorized processes in sealed or containerized vehicles with proper locks and seals, armed escort, documented dispatch and receipt, and videography. Recognized parties are informed where prescribed, and officials monitor movement. GPS or mobile-app tracking is used for end-to-end monitoring, including reserve EVM vehicles on dispersal and poll day.", [P("DOC_EVM_MANUAL_2026", 14, "general movement safeguards", "containerized trucks"), P("DOC_EVM_MANUAL_2026", 52, "poll-day tracking", "GPS/Mobile App-based tracking")], ["Authorized sealed vehicles and armed security protect transport.", "Movements are documented and videographed.", "GPS/mobile tracking provides monitoring."], ["EVM Transport", "GPS", "Armed Escort", "EMS"]),
    item("Summarize First Level Checking and its transparency measures.", "Before every election, authorized BEL or ECIL engineers conduct FLC under DEO supervision. Representatives of recognized parties are invited to observe, select machines for prescribed higher mock polls, witness cabinet and functional checks, compare electronic results with VVPAT slips, and sign seals and records. Machines are marked FLC-OK or rejected in EMS; rejected units go for rectification and accepted units enter secure storage.", [P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 6, "FLC checks", "Functionality check"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 7, "FLC outcomes", "FLC-Reject")], ["Manufacturer engineers conduct FLC under DEO oversight.", "Party representatives participate in tests and records.", "Accepted and rejected machines follow different controlled paths."], ["FLC", "BEL", "ECIL", "DEO", "Political Parties"]),
    item("Summarize how EVM training and voter-awareness activities are separated from election deployment.", "After FLC, up to 10% of machines may be selected for training and awareness in the presence of recognized parties and stored separately. Demonstration centres and mobile vans support awareness before the election announcement. A training machine can return to election use only after de-novo FLC, randomization and commissioning.", [P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 7, "training allocation", "up to 10%"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 8, "reuse conditions", "de-novo FLC")], ["Training machines are separately selected and stored.", "Awareness uses centres and mobile vans.", "Reuse requires fresh election preparation."], ["Training EVM", "EVM Demonstration Centre", "Mobile Demonstration Van"]),
    item("Summarize the purpose and sequence of the two EVM randomizations.", "EMS first randomizes FLC-OK machines to Assembly Constituencies or Segments in the presence of recognized parties. After the candidate list is finalized, second randomization assigns machines polling-station-wise and identifies reserve units in the presence of candidates or representatives and observers. Lists from both stages are shared with the relevant stakeholders.", [P("DOC_EVM_MANUAL_2026", 31, "first randomization", "1st Randomization"), P("DOC_EVM_MANUAL_2026", 35, "second randomization", "2nd Randomization")], ["First randomization allocates by constituency/segment.", "Second randomization allocates by polling station and reserve.", "EMS lists are shared."], ["EMS", "First Randomization", "Second Randomization"]),
    item("Summarize what happens during commissioning of EVMs and VVPATs.", "After candidate finalization, assigned machines are opened under videography in the presence of candidates or representatives. Candidate details are loaded into VVPATs through SLUs and displayed for observation; each machine is functionally checked, prescribed higher mock polls are run on a sample, and results are compared with VVPAT slips. Machines are then sealed and returned to strong-room custody, while SLUs enter their own sealed inventory and storage process.", [P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 9, "commissioning steps", "Symbol loading"), P("DOC_EVM_MANUAL_2026", 44, "SLU storage", "SLU Inventory Register")], ["Candidate data is loaded and observed.", "Functional and sample tests are performed.", "EVMs and SLUs are sealed into controlled custody."], ["Commissioning", "SLU", "VVPAT", "Candidates"]),
    item("Summarize the preliminary checks and prohibitions on dispersal day.", "Polling staff verify that BU, CU and VVPAT address tags match the assigned station, seals are intact, candidate buttons are correctly unmasked, the CU shows the expected candidate count and battery status, and the VVPAT battery and horizontal transport knob are correct. They must not connect or test the full set, damage seals, take machines to unauthorized places, use unauthorized vehicles or place the voting compartment near problematic light or openings.", [P("DOC_PRESIDING_OFFICER_2023", 2, "dispersal checks", "WHAT TO CHECK"), P("DOC_EVM_MANUAL_2026", 120, "dispersal prohibitions", "DURING DISPERSAL")], ["Station identity, seals and configuration are checked.", "The full set must not be connected during dispersal.", "Unauthorized places, vehicles and unsafe positioning are prohibited."], ["Dispersal Day", "Presiding Officer", "Address Tag", "VVPAT Knob"]),
    item("Summarize the polling-station mock-poll procedure and its purpose.", "The mock poll starts 90 minutes before actual polling and uses at least 50 votes distributed across every candidate and NOTA. Officials and agents confirm an empty VVPAT, zero CU total, compare the manual record, CU result and VVPAT-slip count, then clear CU data and remove and seal the mock slips. The process proves that the configured machine and paper trail agree before actual votes are accepted.", [P("DOC_PRESIDING_OFFICER_2023", 4, "mock-poll procedure", "90 minutes"), P("DOC_EVM_MANUAL_2026", 59, "mock-poll sequence", "Cast at least 50 votes")], ["Mock poll precedes actual poll by 90 minutes.", "At least 50 votes are tested.", "Manual, CU and VVPAT counts are reconciled and then cleared."], ["Mock Poll", "Control Unit", "VVPAT", "Polling Agents"]),
    item("Summarize the Presiding Officer's responsibilities during actual polling.", "The Presiding Officer is responsible for orderly conduct and understands the voting process, assists voters only through the approved demonstration method outside the compartment, investigates complaints, periodically ensures BU integrity and applies Rule 49MA to VVPAT allegations. The officer also manages replacement decisions, ensures secrecy and deposits EVMs and election materials securely after poll.", [P("DOC_EVM_MANUAL_2026", 55, "presiding responsibilities", "Responsibilities of Presiding Officers"), P("DOC_PRESIDING_OFFICER_2023", 6, "actual-poll operations", "Start of Actual Poll")], ["The Presiding Officer manages conduct, secrecy and complaints.", "The officer follows prescribed assistance and replacement rules.", "The officer secures and deposits machines after poll."], ["Presiding Officer", "Rule 49MA", "Ballot Unit"]),
    item("Summarize the close-of-poll procedure.", "At the notified end, the Presiding Officer presses CLOSE, then TOTAL, and records the total plus poll start and end times in Form 17C and the diary. The CU is switched off before cables are disconnected, the VVPAT power pack is removed, and BU, CU and VVPAT are placed in their cases. Each case is sealed with address tags and polling-agent signatures before authorized transport.", [P("DOC_PRESIDING_OFFICER_2023", 6, "closing sequence", "Closing of poll procedure"), P("DOC_EVM_MANUAL_2026", 97, "Form 17C and sealing", "Close button")], ["CLOSE and TOTAL finalize and report the poll.", "Power-down precedes disconnection.", "Units are cased, sealed and signed."], ["Close of Poll", "Form 17C", "Address Tag"]),
    item("Summarize the replacement rules for failures during mock poll and actual poll.", "During mock poll, the individual failed BU, CU or VVPAT is replaced. During actual poll, a VVPAT-only or power-pack problem is handled by replacing only that item without another mock poll; a BU or CU failure requires replacing the complete set and performing a limited mock poll before resumption. Previously cast votes remain safe and all used CUs contribute to the final result.", [P("DOC_PRESIDING_OFFICER_2023", 4, "mock-poll replacement", "replace the respective unit"), P("DOC_PRESIDING_OFFICER_2023", 6, "actual-poll replacement", "replace the whole set"), F("C2Q13", "stored-vote safety", "remain safe")], ["Mock-poll failures replace only the affected unit.", "Actual-poll VVPAT-only failures differ from BU/CU failures.", "Previously cast votes remain available."], ["Replacement Protocol", "Ballot Unit", "Control Unit", "VVPAT"]),
    item("Summarize post-poll transport and strong-room custody.", "After sealing, polled units travel under escort to the collection centre, and candidates or agents may follow the vehicles. The machines are stored in a polled strong room in their presence under CCTV, double locks and two-cordon armed security; candidates may add seals and monitor the entrance or a CCTV display. Unpolled non-functional and reserve machines are stored separately.", [P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 11, "post-poll custody", "TRANSPORTATION OF POLLED"), F("C5Q30", "strong-room detail", "platoon")], ["Polled machines travel under escort.", "Candidates can observe transport and storage.", "Polled and unpolled/reserve units remain separated."], ["Polled EVM", "Collection Centre", "Strong Room", "CAPF"]),
    item("Summarize the counting-day process described in the corpus.", "The polled strong room is opened under videography in the presence of candidates or representatives, the RO and the ECI Observer. After seals are verified, CU results are displayed, recorded in Form 17C and compiled round-wise. Mandatory VVPAT verification follows for the prescribed random sample, after which power packs are removed, machines are resealed and VVPAT slips are preserved separately under controlled custody.", [P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 12, "counting steps", "Counting of votes"), F("C2Q20", "VVPAT sample", "five randomly selected")], ["Strong-room opening and seal verification are observed.", "CU results are recorded and compiled.", "VVPAT verification and post-count sealing follow."], ["Counting Day", "Returning Officer", "Form 17C", "VVPAT"]),
    item("Summarize when and why VVPAT slips are counted or verified.", "VVPAT slips are mandatorily verified for five randomly selected polling stations per Assembly Constituency or Segment before result declaration. They are also counted when a CU provides no result display or when directed under applicable legal or procedural authority. The paper record therefore supports both routine sample verification and exception handling.", [F("C2Q20", "counting conditions", "Compulsory counting"), P("DOC_CANDIDATE_PARTY_BROCHURE_2024", 12, "routine sample", "mandatory verification")], ["Five-station sample verification is routine.", "No-display cases trigger VVPAT counting.", "Paper slips provide independent evidence."], ["VVPAT Slips", "Control Unit", "Assembly Constituency"]),
    item("Summarize how candidates and political parties participate across the EVM lifecycle.", "Recognized parties observe warehouse access, FLC and first randomization; candidates or their agents join after candidate finalization for second randomization, commissioning, dispersal, poll, transport, storage and counting. They may select prescribed samples, observe symbol loading, sign seals and registers, receive allocation lists and Form 17C copies, follow transport and monitor strong rooms. This creates recurring visibility rather than a single observation point.", [P("DOC_ELECTOR_BROCHURE_2023", 4, "pre-poll participation", "representatives"), P("DOC_ELECTOR_BROCHURE_2023", 5, "poll and count participation", "polling agents")], ["Parties participate before candidate finalization.", "Candidates and agents participate from allocation through counting.", "They observe, sign, receive records and monitor custody."], ["Political Parties", "Candidates", "Polling Agents"]),
    item("Summarize the main responsibilities of DEO, RO/ARO and polling parties in the EVM flow.", "The DEO is custodian, oversees FLC, training and first randomization, and manages key storage and inventory functions. The RO or ARO stores first-randomized units, conducts second randomization and commissioning, manages dispersal and election allocation. Polling parties conduct mock and actual poll, close and document the poll, seal machines and return them under security.", [P("DOC_EVM_MANUAL_2026", 97, "functionary roles", "District Election Officer"), P("DOC_EVM_MANUAL_2026", 31, "DEO first-stage duty", "DEO shall fix")], ["DEO owns district-level custody and first-stage preparation.", "RO/ARO owns polling-station allocation and commissioning.", "Polling parties conduct and close the poll."], ["DEO", "RO", "ARO", "Polling Parties"]),
    item("Summarize the voter-facing accessibility and verification features in the corpus.", "Braille numbers beside candidate buttons assist visually impaired electors. The selected button's red light, the VVPAT's approximately seven-second display of candidate details and the CU beep provide visual and audio confirmation. The tinted window preserves secrecy, while Rule 49MA supplies a formal complaint path if the displayed slip is alleged to be wrong.", [P("DOC_ELECTOR_BROCHURE_2023", 2, "voter features", "Braille"), F("C3Q15", "secrecy", "tint"), F("C4Q7", "complaint path", "Rule 49MA")], ["Braille provides accessibility.", "Light, slip and beep provide confirmation.", "Tinting and Rule 49MA balance secrecy and challenge rights."], ["Braille", "VVPAT", "Rule 49MA"]),
    item("Summarize how power packs are managed and why alkaline cells are used.", "CU and VVPAT use sealed, single-use alkaline-cell power packs because EVMs consume little power during elections and none during long storage, avoiding periodic charging or connectivity. Packs are installed and sealed during commissioning, monitored through voltage and capacity indications, replaced under documented observation if needed, and removed after prescribed stages such as VVPAT close of poll and CU post-counting.", [F("C5Q27", "battery rationale", "Alkaline"), F("C5Q30", "lifecycle", "Power Pack is installed"), P("DOC_PRESIDING_OFFICER_2023", 6, "VVPAT removal", "Remove Power Pack")], ["Alkaline packs suit intermittent low-power use and long storage.", "Installation and replacement are sealed and observed.", "Removal follows prescribed election stages."], ["Power Pack", "Alkaline Cell", "Control Unit", "VVPAT"]),
    item("Summarize the SLU lifecycle from symbol loading through post-count storage.", "SLUs load finalized candidate details into VVPATs during commissioning while candidates or representatives can view the symbols on a monitor. Used and reserve SLUs are sealed in labeled containers, recorded in an inventory register and stored under DEO-controlled double-lock custody; reserve SLUs may be returned at P+1 under the prescribed conditions. Used SLUs remain secured through counting and are thereafter stored with the relevant election material as directed.", [F("C2Q21", "symbol loading", "SLU"), P("DOC_EVM_MANUAL_2026", 44, "SLU storage", "used SLUs")], ["SLUs load and display symbols during commissioning.", "They are sealed, inventoried and stored under double lock.", "Used SLUs remain secured through counting."], ["SLU", "VVPAT", "DEO", "Commissioning"]),
    item("Summarize how the corpus handles machine malfunction without losing recorded votes.", "The CU identifies relevant errors and the prescribed protocol replaces either the affected VVPAT or power pack, or the complete set when BU/CU failure requires it. Data already recorded in the CU and VVPAT slips remains safe. Counting aggregates votes from all CUs used at the station, and VVPAT slips provide a result path if a CU cannot display its data.", [F("C2Q13", "malfunction and data safety", "remain safe"), P("DOC_PRESIDING_OFFICER_2023", 6, "replacement choices", "Replace VVPAT")], ["Different failures trigger different replacement scopes.", "Previously recorded evidence remains safe.", "All used machines are included at counting."], ["Machine Failure", "Control Unit", "VVPAT", "Reserve EVM"]),
    item("Summarize the legal and judicial framework described for EVM and VVPAT use.", "Following the early Parur use and a Supreme Court requirement for specific legal authority, Section 61A was inserted into the Representation of the People Act in 1988 to permit voting machines. VVPAT-related rules include the 2013 legal framework and Rule 49MA for discrepancy complaints. The corpus also describes judicial scrutiny and procedures for fresh poll, recount, verification and election-petition retention where applicable.", [P("DOC_EVM_MANUAL_2026", 103, "Section 61A history", "December 1988"), F("C1Q5", "VVPAT legal date", "14th August 2013"), F("C4Q7", "complaint provision", "Rule 49MA")], ["Section 61A authorizes EVM use.", "VVPAT obtained a legal framework in 2013.", "Rule 49MA governs a voter discrepancy claim."], ["Section 61A", "Rule 49MA", "Supreme Court", "VVPAT"]),
    item("Summarize how documentation and monitoring support traceability.", "EMS records inventory, locations, FLC and randomization activity, while paper and electronic registers track warehouse access, movement, SLUs, seals and unit status. Forms such as 17A, 17C and mock-poll certificates record voter, zero-check, mock-poll and poll totals. Videography, CCTV, GPS tracking, acknowledgements and stakeholder signatures connect these records to observable events.", [P("DOC_EVM_MANUAL_2026", 114, "EMS traceability", "recording all EVMs related activities"), P("DOC_EVM_MANUAL_2026", 59, "mock documentation", "Mock Poll Certificate"), P("DOC_EVM_MANUAL_2026", 97, "Form 17C", "Form 17C")], ["EMS records inventory and activity.", "Forms and registers capture key events and totals.", "Video, GPS and signatures link custody to evidence."], ["EMS", "Form 17A", "Form 17C", "Videography", "GPS"]),
    item("Summarize the critical operational mistakes the manual warns officials to avoid.", "The manual warns against incorrect FLC status updates, improper dummy symbols, failure to verify loaded symbols or shred test slips, transporting VVPAT with an unlocked paper roll, connecting the set during dispersal, and leaving mock data or slips before actual poll. It also warns against wrong VVPAT positioning or lighting, unsafe connection changes while powered, unnecessary mock polls after limited replacements, and failure to press CLOSE after poll.", [P("DOC_EVM_MANUAL_2026", 116, "critical mistakes", "Examples of Critical Mistakes"), P("DOC_EVM_MANUAL_2026", 120, "poll-day prohibitions", "DURING MOCK POLL")], ["Errors span FLC, commissioning, transport, dispersal, mock poll and actual poll.", "Many warnings protect configuration, paper evidence and safe electrical handling."], ["Critical Mistakes", "FLC", "Mock Poll", "VVPAT"]),
    item("Summarize how the corpus contrasts EVM voting with conventional paper-ballot voting.", "The corpus presents EVMs as eliminating invalid votes caused by unclear paper markings, limiting each enabled ballot to one recorded selection and reducing counting time. VVPAT adds a voter-visible paper record while electronic controls provide rapid totals. The corpus also emphasizes that these benefits depend on procedural safeguards, paper verification, transparency and the ability to abstain from unsupported claims about matters outside the documents.", [F("C1Q2", "paper-ballot comparison", "invalid vote"), F("C1Q1", "efficiency comparison", "reduce the time")], ["EVMs reduce invalid markings and counting time.", "Each enabled ballot records one selection.", "VVPAT adds a paper verification layer."], ["EVM", "Paper Ballot", "VVPAT"]),
]


UNANSWERABLE = [
    ("What is the live GPS location of the reserve EVM vehicle assigned to my polling station today?", "The corpus describes GPS tracking requirements but contains no live operational telemetry or vehicle assignment.", ["GPS", "Reserve EVM Vehicle"]),
    ("Which candidate won the 2024 election in a specific constituency, and by how many votes?", "The corpus explains EVM procedures, not constituency-level election results.", ["Candidate", "Election Result"]),
    ("What is my personal polling-station number based on my voter ID?", "The corpus contains no electoral-roll or individual voter lookup data.", ["Voter ID", "Polling Station"]),
    ("What is the secret encryption key currently programmed into M3 EVMs?", "No cryptographic keys or secrets are contained in the corpus.", ["M3 EVM", "Encryption Key"]),
    ("Provide the source code of the firmware installed in the Control Unit.", "The corpus describes firmware characteristics but does not provide source code.", ["Control Unit", "Firmware Source Code"]),
    ("What is the serial number of the EVM deployed at a named booth in the next election?", "No future booth-level deployment or unit serial-number list is present.", ["EVM Serial Number", "Booth"]),
    ("Show the CCTV recording from the strong room on a particular date.", "The corpus states CCTV requirements but contains no recordings.", ["CCTV", "Strong Room"]),
    ("What password should a DEO use to log in to EMS 2.0?", "The corpus does not contain passwords or authentication credentials.", ["DEO", "EMS 2.0 Password"]),
    ("What is the exact procurement price of every M3 unit ordered in September 2026?", "The corpus does not include a September 2026 procurement order or complete current unit-pricing schedule.", ["M3", "Procurement Price"]),
    ("Which political party's manifesto promises to replace EVMs with paper ballots?", "Party manifestos are outside this corpus.", ["Political Party Manifesto", "Paper Ballot"]),
    ("What criminal cases are pending against a named election candidate?", "Candidate legal or affidavit records are not included.", ["Candidate", "Criminal Case"]),
    ("What will be the polling date for the 2028 Telangana Assembly election?", "The corpus contains procedures but no future election schedule for 2028.", ["Telangana", "Election Schedule"]),
    ("How can I change the address on my voter registration?", "Electoral-roll registration and address-change procedures are not covered by these EVM documents.", ["Voter Registration", "Address Change"]),
    ("What documents are required to file a candidate nomination?", "Nomination-document requirements are outside this EVM/VVPAT corpus.", ["Candidate Nomination"]),
    ("How are postal ballots issued to service voters?", "Detailed postal-ballot issuance procedures are not present in this corpus.", ["Postal Ballot", "Service Voter"]),
    ("What is the latest turnout percentage in an ongoing election?", "The corpus has no live turnout data.", ["Voter Turnout"]),
    ("Which warehouse currently stores a particular EVM serial number?", "The corpus explains inventory tracking but contains no live EMS inventory records.", ["EVM Warehouse", "Serial Number"]),
    ("What is the mobile phone number of the District Election Officer?", "No current personal contact directory is included.", ["District Election Officer", "Phone Number"]),
    ("How many EVMs are available in national inventory today?", "The documents do not provide a live, current national inventory count.", ["EVM Inventory"]),
    ("What is the real-time battery percentage of the Control Unit at my booth?", "The corpus explains battery behavior but contains no live machine telemetry.", ["Control Unit", "Battery Percentage"]),
    ("Predict which candidate will receive the most votes at a specified polling station.", "The corpus provides no predictive model or voter-preference data.", ["Candidate", "Vote Prediction"]),
    ("Which contractor installed the CCTV system in a particular EVM warehouse?", "Vendor and contract details for individual warehouses are not included.", ["CCTV Contractor", "EVM Warehouse"]),
    ("What is the private network address of the EMS 2.0 production server?", "Infrastructure secrets and private network configuration are absent.", ["EMS 2.0", "Network Address"]),
    ("Give the complete binary image stored in an EVM microcontroller.", "The corpus does not include firmware binaries or chip dumps.", ["Microcontroller", "Firmware Binary"]),
    ("Who entered a particular warehouse last night according to the access log?", "The corpus requires logs but provides no live or historical warehouse log entries.", ["Warehouse Access Log"]),
    ("What is the result of an election petition currently pending before a named High Court?", "The corpus explains retention during petitions but does not contain current case status or judgments for named matters.", ["Election Petition", "High Court"]),
    ("Which EVM will fail during the next poll?", "The corpus provides procedures for failures but cannot predict a future unit failure.", ["EVM Failure Prediction"]),
    ("What is the biometric identity of the voter who cast the 500th vote?", "The corpus contains no biometric data and voting secrecy precludes such linkage.", ["Voter Biometrics", "Vote Secrecy"]),
    ("How should votes be counted in a blockchain-based voting system?", "Blockchain voting is not covered by this ECI EVM corpus.", ["Blockchain Voting"]),
    ("What changes will ECI definitely make to EVM design in 2030?", "The corpus does not contain a binding 2030 design roadmap.", ["EVM Design", "2030 Roadmap"]),
]


def load_sources():
    page_texts: dict[str, list[str]] = {}
    page_counts: dict[str, int] = {}
    for document_id, path in DOCS.items():
        reader = PdfReader(str(path))
        pages = [clean(page.extract_text() or "") for page in reader.pages]
        page_texts[document_id] = pages
        page_counts[document_id] = len(pages)

    with RAW_FAQ.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    faq_lookup = {}
    for category_index, category in enumerate(raw["categories"], start=1):
        for faq in category["faqs"]:
            locator = f"ECI-EVM-C{category_index:02d}-Q{int(faq['faq_index']):02d}"
            faq_lookup[locator] = {
                "question": clean(faq["question"]),
                "answer": clean(faq["answer"]),
                "category": clean(category["category"]),
            }

    faq_pages = {}
    for locator in faq_lookup:
        matches = [
            page_number
            for page_number, text in enumerate(page_texts["DOC_EVM_FAQ_2026"], start=1)
            if locator in text
        ]
        if not matches:
            raise ValueError(f"FAQ locator {locator} did not match the FAQ PDF")
        # The corpus index contains range endpoints; the latest match is the
        # actual FAQ heading because all category content follows the index.
        faq_pages[locator] = max(matches)
    return page_texts, page_counts, faq_lookup, faq_pages


def resolve_evidence(spec: dict, page_texts, faq_lookup, faq_pages) -> dict:
    if spec["type"] == "faq":
        locator = spec["locator"]
        if locator not in faq_lookup:
            raise ValueError(f"Unknown FAQ evidence locator: {locator}")
        record = faq_lookup[locator]
        keyword = spec.get("keyword")
        if keyword and keyword.lower() not in record["answer"].lower():
            raise ValueError(f"Keyword {keyword!r} not found in {locator}")
        return {
            "evidence_id": f"DOC_EVM_FAQ_2026#{locator}",
            "document_id": "DOC_EVM_FAQ_2026",
            "page": faq_pages[locator],
            "locator": locator,
            "role": spec["role"],
            "evidence_text": snippet(record["answer"], keyword),
        }

    document_id = spec["document_id"]
    page = int(spec["page"])
    if document_id not in page_texts:
        raise ValueError(f"Unknown document ID: {document_id}")
    if page < 1 or page > len(page_texts[document_id]):
        raise ValueError(f"Page {page} is outside {document_id}")
    text = page_texts[document_id][page - 1]
    keyword = spec["keyword"]
    if keyword.lower() not in text.lower():
        raise ValueError(f"Keyword {keyword!r} not found in {document_id} page {page}")
    return {
        "evidence_id": f"{document_id}#p{page:03d}",
        "document_id": document_id,
        "page": page,
        "locator": f"page:{page}",
        "role": spec["role"],
        "evidence_text": snippet(text, keyword),
    }


def build_record(prefix: str, number: int, query_class: str, source: dict, page_texts, faq_lookup, faq_pages) -> dict:
    evidence = [
        resolve_evidence(spec, page_texts, faq_lookup, faq_pages)
        for spec in source["evidence_specs"]
    ]
    relevant_evidence_ids = list(dict.fromkeys(entry["evidence_id"] for entry in evidence))
    relevant_document_ids = list(dict.fromkeys(entry["document_id"] for entry in evidence))
    return {
        "id": f"ECI-GOLD-{prefix}-{number:03d}",
        "split": "development" if number % 3 == 0 else "test",
        "query_class": query_class,
        "question": source["question"],
        "answerable": True,
        "reference_answer": source["reference_answer"],
        "reference_claims": source["reference_claims"],
        "required_entities": source["required_entities"],
        "evidence": evidence,
        "relevant_evidence_ids": relevant_evidence_ids,
        "relevant_document_ids": relevant_document_ids,
        "relevant_chunk_ids": [],
        "requires_cross_document": len(relevant_document_ids) > 1,
        "expected_behavior": "answer_with_citations",
    }


def build_dataset(page_texts, faq_lookup, faq_pages) -> list[dict]:
    expected_sizes = {
        "single_hop_factual": len(SINGLE_HOP),
        "multi_hop_relational": len(MULTI_HOP),
        "corpus_summary": len(CORPUS_SUMMARY),
        "unanswerable": len(UNANSWERABLE),
    }
    if expected_sizes != {
        "single_hop_factual": 30,
        "multi_hop_relational": 30,
        "corpus_summary": 30,
        "unanswerable": 30,
    }:
        raise ValueError(f"Unexpected class distribution: {expected_sizes}")

    records = []
    for number, source in enumerate(SINGLE_HOP, start=1):
        records.append(build_record("SHF", number, "single_hop_factual", source, page_texts, faq_lookup, faq_pages))
    for number, source in enumerate(MULTI_HOP, start=1):
        record = build_record("MHR", number, "multi_hop_relational", source, page_texts, faq_lookup, faq_pages)
        if len(record["evidence"]) < 2:
            raise ValueError(f"Multi-hop item {record['id']} needs at least two evidence units")
        records.append(record)
    for number, source in enumerate(CORPUS_SUMMARY, start=1):
        record = build_record("CS", number, "corpus_summary", source, page_texts, faq_lookup, faq_pages)
        if len(record["evidence"]) < 2:
            raise ValueError(f"Summary item {record['id']} needs at least two evidence units")
        records.append(record)
    for number, (question, reason, entities) in enumerate(UNANSWERABLE, start=1):
        records.append({
            "id": f"ECI-GOLD-UA-{number:03d}",
            "split": "development" if number % 3 == 0 else "test",
            "query_class": "unanswerable",
            "question": question,
            "answerable": False,
            "reference_answer": None,
            "reference_claims": [],
            "required_entities": entities,
            "evidence": [],
            "relevant_evidence_ids": [],
            "relevant_document_ids": [],
            "relevant_chunk_ids": [],
            "requires_cross_document": False,
            "expected_behavior": "abstain",
            "abstention_reason": reason,
        })
    return records


def validate(records: list[dict], page_counts: dict[str, int]) -> dict:
    ids = [record["id"] for record in records]
    normalized_questions = [clean(record["question"]).lower() for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate record IDs found")
    if len(normalized_questions) != len(set(normalized_questions)):
        raise ValueError("Duplicate questions found")

    class_counts = {}
    doc_usage = {document_id: 0 for document_id in DOCS}
    answerable = 0
    unanswerable = 0
    evidence_units = 0
    split_counts = {}
    for record in records:
        class_counts[record["query_class"]] = class_counts.get(record["query_class"], 0) + 1
        split_counts[record["split"]] = split_counts.get(record["split"], 0) + 1
        if record["answerable"]:
            answerable += 1
            if not record["reference_answer"] or not record["evidence"]:
                raise ValueError(f"Answerable item lacks answer/evidence: {record['id']}")
            for evidence in record["evidence"]:
                evidence_units += 1
                document_id = evidence["document_id"]
                doc_usage[document_id] += 1
                if not evidence["evidence_text"]:
                    raise ValueError(f"Empty evidence text: {record['id']}")
                if evidence["page"] < 1 or evidence["page"] > page_counts[document_id]:
                    raise ValueError(f"Invalid page reference: {record['id']}")
        else:
            unanswerable += 1
            if record["reference_answer"] is not None or record["evidence"]:
                raise ValueError(f"Unanswerable item contains answer/evidence: {record['id']}")

    expected = {"single_hop_factual": 30, "multi_hop_relational": 30, "corpus_summary": 30, "unanswerable": 30}
    if class_counts != expected:
        raise ValueError(f"Bad final distribution: {class_counts}")
    if split_counts != {"test": 80, "development": 40}:
        raise ValueError(f"Bad split distribution: {split_counts}")
    return {
        "total_questions": len(records),
        "class_distribution": class_counts,
        "split_distribution": split_counts,
        "answerable_questions": answerable,
        "unanswerable_questions": unanswerable,
        "evidence_units": evidence_units,
        "document_evidence_usage": doc_usage,
        "duplicate_question_count": 0,
        "invalid_page_reference_count": 0,
        "empty_evidence_count": 0,
    }


def write_outputs(records: list[dict], page_counts: dict[str, int], validation: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dataset_path = OUT / "eci_evm_golden_set_v1.jsonl"
    manifest_path = OUT / "corpus_manifest.json"
    readme_path = OUT / "README.md"
    report_path = OUT / "validation_report.json"
    script_path = OUT / "build_eci_golden_dataset.py"
    zip_path = ROOT / "output" / "ECI_EVM_Golden_Dataset_v1.zip"

    with dataset_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "corpus_id": "ECI_EVM_CORPUS_V1",
        "benchmark_dataset": "ECI_EVM_GOLDEN_SET_V1",
        "included_documents": [
            {
                "document_id": document_id,
                "filename": path.name,
                "pages": page_counts[document_id],
                "sha256": sha256(path),
                "included": True,
            }
            for document_id, path in DOCS.items()
        ],
        "excluded_documents": [
            {
                "filename": DUPLICATE_DOC.name,
                "sha256": sha256(DUPLICATE_DOC),
                "included": False,
                "reason": "Exact byte-for-byte duplicate of EVM BROCHURE FOR CANDIDATES & POLITICAL PARTIES.pdf",
                "duplicate_of": "DOC_CANDIDATE_PARTY_BROCHURE_2024",
            }
        ],
        "matching_contract": {
            "primary_gold_key": "relevant_evidence_ids",
            "faq_locator_format": "DOC_EVM_FAQ_2026#ECI-EVM-CNN-QNN",
            "page_locator_format": "DOCUMENT_ID#pNNN",
            "relevant_chunk_ids": "Populate after the production chunking pipeline assigns immutable chunk IDs.",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(validation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    readme = """# ECI EVM Golden Dataset v1

## Purpose

This package provides a 120-question golden set for benchmarking an adaptive retrieval engine over five unique Election Commission of India EVM/VVPAT documents.

## Distribution

| Query class | Count | Evaluation intent |
|---|---:|---|
| `single_hop_factual` | 30 | Direct facts expected from one evidence unit |
| `multi_hop_relational` | 30 | Questions requiring two or more evidence units and synthesis |
| `corpus_summary` | 30 | Broad process or theme summaries supported by multiple sources/sections |
| `unanswerable` | 30 | Plausible ECI questions not supported by this corpus; expected action is abstention |

## Important design choices

- No expected retrieval strategy is stored. The cheapest sufficient strategy must be derived empirically from A1-A5 outcomes, not manually labelled in the gold set.
- Each class contains 10 `development` and 20 `test` items. Tune router thresholds only on development items; report final results on the held-out 80-item test split.
- `EVM BROCHURE FOR.pdf` was excluded because it is an exact duplicate of the candidate/political-party brochure.
- Every answerable item contains a reference answer, atomic reference claims, required entities, and verified source evidence.
- Every unanswerable item has `reference_answer: null`, no evidence, `expected_behavior: abstain`, and an abstention reason.
- `relevant_chunk_ids` is intentionally empty until the ingestion pipeline assigns immutable production chunk IDs.

## Evidence matching

Use `relevant_evidence_ids` as the stable source-level gold key:

- FAQ evidence: `DOC_EVM_FAQ_2026#ECI-EVM-CNN-QNN`
- Other PDF evidence: `DOCUMENT_ID#pNNN`

During ingestion, copy the matching locator into every derived chunk's metadata. After chunking is frozen, resolve each gold evidence locator to one or more chunk IDs and populate `relevant_chunk_ids`. This makes Recall@K, MRR and nDCG reproducible even if the Elasticsearch internal `_id` changes.

## Recommended benchmark protocol

1. Freeze corpus files, chunking, embedding model and prompts.
2. Map source locators to immutable chunk IDs.
3. Run A1-A6 on the same 120 questions.
4. Evaluate retrieval overall and per query class.
5. Evaluate answers for correctness, faithfulness, citation support and abstention.
6. Derive the cheapest sufficient oracle strategy from A1-A5 results; compare A6 using quality regret, cost regret and retry success.

## Leakage control

Do not tune router thresholds on all 120 items. Use a development subset for threshold selection and preserve a held-out test subset. If examples are generated or expanded later, keep document hashes and dataset versions fixed in the benchmark report.
"""
    readme_path.write_text(readme, encoding="utf-8")
    script_path.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")

    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [dataset_path, manifest_path, readme_path, report_path, script_path]:
            archive.write(path, arcname=path.name)

    print(json.dumps({
        "dataset": str(dataset_path),
        "manifest": str(manifest_path),
        "readme": str(readme_path),
        "validation": str(report_path),
        "script": str(script_path),
        "zip": str(zip_path),
        "stats": validation,
    }, indent=2))


def main() -> None:
    page_texts, page_counts, faq_lookup, faq_pages = load_sources()
    records = build_dataset(page_texts, faq_lookup, faq_pages)
    validation = validate(records, page_counts)
    write_outputs(records, page_counts, validation)


if __name__ == "__main__":
    main()
