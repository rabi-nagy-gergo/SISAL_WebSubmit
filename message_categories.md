# QC Message Category Reference

This document lists **every** `warning`, `error`, and `fatal` message produced by the workbook QC script. It reflects the current severity model, where **`warning`** messages do not block submission, while **`error`** and **`fatal`** messages do.

The document is organized into three parts (**Fatal**, **Error**, **Warning**) and within each part, messages are grouped by the workbook sheet ("tab") they relate to.

---

# Part 1: Fatal messages

Fatal messages stop the script immediately, no further checks are performed once one of these fires.

## Workbook structure

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `Cannot read Excel file. An error occurred while pandas util tried to read the given excel file. Details: {e}` | Excel file cannot be opened at all | Triggers when `pandas.ExcelFile()` fails to open the uploaded file (corrupted file, wrong format, unreadable content) | fatal | Without being able to open the file, absolutely no checks or data extraction can proceed |
| `Cannot read in "Site metadata" spreadsheet, likely no spreadsheet called "Site metadata". Details: {e}` | Site metadata sheet missing/unreadable | Triggers when the "Site metadata" sheet cannot be parsed from the workbook | fatal | Site metadata is required infrastructure for the whole script (site name, coordinates); nothing downstream can run without it |
| `Cannot read in "Entity metadata" spreadsheet, likely no spreadsheet called "Entity metadata". Details: {e}` | Entity metadata sheet missing/unreadable | Triggers when the "Entity metadata" sheet cannot be parsed | fatal | Entity metadata defines every entity referenced throughout the workbook; without it nothing can be cross-checked |
| `Cannot read in "References" spreadsheet, likely no spreadsheet called "References". Details: {e}` | References sheet missing/unreadable | Triggers when the "References" sheet cannot be parsed | fatal | The References sheet is a required, separately-parsed table; a read failure prevents any reference-related checks |
| `Cannot read in "Dating information" spreadsheet, likely no spreadsheet called "Dating information". Details: {e}` | Dating information sheet missing/unreadable | Triggers when the "Dating information" sheet cannot be parsed | fatal | Dating information underlies the age model for every entity; a read failure blocks the majority of the script's checks |
| `Cannot read in "Lamina age vs depth" spreadsheet, likely no spreadsheet called "Lamina age vs depth". Details: {e}` | Lamina age vs depth sheet missing/unreadable | Triggers when the "Lamina age vs depth" sheet cannot be parsed | fatal | This sheet is required infrastructure for lamina-related cross-checks; a read failure prevents them entirely |
| `Cannot read in "Sample data" spreadsheet.` | Sample data sheet unreadable despite being found | Triggers when exactly one "Sample data" sheet is found by name but still fails to parse | fatal | Sample data is the core scientific content of the workbook; without it, no proxy or age-depth checks can run |
| `Sample data spreadsheet does not exist, likely no spreadsheet called "Sample data".` | No Sample data sheet found | Triggers when zero sheets matching "Sample data" are found in the workbook | fatal | Same reasoning, no sample data means nothing to validate |
| `More than one "Sample data" spreadsheet exists. This is not allowed.` | Duplicate Sample data sheets | Triggers when more than one sheet matching "Sample data" is found | fatal | An ambiguous, duplicated Sample data sheet makes it impossible to know which data is authoritative |
| `This workbook is likely not version 15. Columns in this workbook do not match v15 column schema. The checks cannot be performed.` | Workbook schema doesn't match v15 | Triggers after the initial column-existence check finds that one or more sheets are missing expected v15 columns | fatal | If the workbook isn't structured as v15, none of the subsequent checks (which assume v15 column names) can be trusted to run correctly |

## Site metadata

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `Site metadata table is either empty or has more than one site. Exactly one site per workbook is allowed.` | Wrong number of site rows | Triggers when the Site metadata sheet has zero rows or more than one row | fatal | Every downstream check assumes exactly one site per workbook; this assumption is violated at the very first step |
| `No coordinates have been provided. Please enter the coordinates of your site.` | Both latitude and longitude missing | Triggers when both `latitude` and `longitude` are missing from the single site row | fatal | Without any coordinates, the site cannot be georeferenced at all, and the later map-generation step also depends on this |

## Entity metadata

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `There are no entities in this workbook. The checks will terminate here.` | Entity metadata sheet is empty | Triggers when the Entity metadata sheet has zero rows | fatal | With no entities defined, there is nothing for any other sheet (Sample data, Dating information, etc.) to be cross-checked against |
| `There are repeated entity_name(s): %s. The checking script cannot continue and will terminate here.` | Duplicate entity names | Triggers when the same `entity_name` value appears more than once in Entity metadata | fatal | Duplicate entity names make it impossible to unambiguously link data in other sheets back to a specific entity |
| `Required workbook value 'entity_name' is missing in Entity metadata. The checking script cannot continue.` | Missing entity_name value(s) | Triggers when one or more rows in Entity metadata have an empty `entity_name` | fatal | An entity with no name cannot be referenced or cross-checked against any other sheet |

## Sample data

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `There are no samples filled in. The checks will terminate here.` | Sample data sheet is empty | Triggers when the Sample data sheet has zero rows | fatal | With no sample rows, there is no scientific content at all to validate in the rest of the script |

---

# Part 2: Error messages

Error messages are collected throughout the run (via `error_ctr`) and, together with fatal messages, determine whether the workbook is rejected.
## Site metadata

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `Site metadata table is missing column(s): %s.` | Required column(s) missing from Site metadata | Triggers during the initial v15 schema check if an expected Site metadata column is absent | error | A missing required column means the sheet doesn't match the expected v15 structure, undermining every later check on it |
| `At column latitude: %d row(s) is not a number. See row(s): %s.` | Latitude is non-numeric | Triggers when the `latitude` value cannot be interpreted as a number | error | Latitude is core georeferencing data; a non-numeric value makes the site's location entirely unusable |
| `At column latitude: %d row(s) is not within the valid range (>=-90.00 and <=90.00) (or not a number). See row(s): %s.` | Latitude out of valid range | Triggers when latitude falls outside ±90° | error | An out-of-range latitude is physically impossible and indicates a serious data entry error (e.g. swapped lat/lon) |
| `At column longitude: %d row(s) is not a number. See row(s): %s.` | Longitude is non-numeric | Triggers when the `longitude` value cannot be interpreted as a number | error | Same reasoning as latitude, critical georeferencing field |
| `At column longitude: %d row(s) is not within the valid range (>=-180.00 and <=180.00) (or not a number). See row(s): %s.` | Longitude out of valid range | Triggers when longitude falls outside ±180° | error | Same reasoning as latitude range check |
| `The coordinates for this site are definitely wrong, please check.` | Summary message after lat/lon check failure | Triggers after any of the four lat/lon checks above has failed | error | This is the human-readable summary of the same georeferencing failure already flagged above |

## Entity metadata

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `Entity metadata table is missing column(s): %s.` | Required column(s) missing from Entity metadata | Triggers during the initial v15 schema check if an expected Entity metadata column is absent | error | Same reasoning as the Site metadata column-existence check |
| `Entity %s is missing from the list. (Found in %s spreadsheet)` | Entity name referenced elsewhere but absent from Entity metadata | Triggers when an `entity_name` value used in Sample data, Dating information, Lamina age vs depth, or References doesn't exist in Entity metadata | error | An entity name with no matching Entity metadata record cannot be linked to any actual speleothem entity |
| `Contact column is empty. At least one contact is required.` | No contact person listed | Triggers when every row in the `contact` column is empty | error | A submission with no listed contact cannot be attributed or followed up on |
| `If one_and_only = "no", entity_status_info cannot be "not applicable". See row(s): %s.` | Logical inconsistency between `one_and_only` and `entity_status_info` | Triggers when `one_and_only = "no"` but `entity_status_info` is "not applicable", which contradicts it | error | Direct logical contradiction in required metadata describing how the entity relates to related entities |
| `If one_and_only = "no", entity_status_notes cannot be empty, "NA", "unknown", "not known" (...). See row(s): %s.` | Missing explanation when entity is not the sole record | Triggers when `one_and_only = "no"` but `entity_status_notes` is empty or a placeholder | error | Without these notes, the entity's status relative to related entities cannot be understood. |
| `The NOAA/PANGEA URL or DOI of the data in row(s) %s is incorrect. This cannot be "unknown", "N/A", "not known", etc. or have spaces before/after the text. It must either be the URL/DOI or just empty (...)` | Malformed `data_DOI_URL` placeholder value | Triggers when `data_DOI_URL` contains a placeholder string instead of being empty or a real URL/DOI | error | An invalid but non-empty value actively misleads database consumers, worse than leaving the field empty |
| `The NOAA/PANGEA URL or DOI of the data in row(s) %s is incorrect. The URL or DOI must start with either "10.", "ftp", or "http".` | `data_DOI_URL` doesn't match expected format | Triggers when `data_DOI_URL` is filled in but doesn't start with a recognized prefix | error | Same reasoning as above, a malformed but present link is a data-integrity problem |

## Sample data

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `Sample data table is missing column(s): %s` | Required column(s) missing from Sample data | Triggers during the initial v15 schema check if an expected Sample data column is absent | error | Same reasoning as other sheets' column-existence checks |
| `Entity %s has samples (not identified as hiatuses) that are missing depths. Checks for possible hiatuses cannot be performed.` | Missing `depth_sample` blocks hiatus detection | Triggers when non-hiatus rows for an entity have missing depth values | error | Missing depths block an entire category of downstream scientific checks and represent incomplete core sample metadata |
| `At entity %s the following %s occurred more than once: %s. See row(s): %s.` | Duplicate values within an entity (e.g. `depth_sample`, `interp_age`) | Triggers when the same value appears more than once for the same entity | error | Duplicate depths/ages make it ambiguous which measurement belongs to which physical sample. |
| `If mineralogy = "aragonite" or "mixed", arag_corr must be something different than "not applicable". See row(s): %s.` | Missing aragonite correction status | Triggers when `mineralogy` indicates aragonite/mixed but `arag_corr` is "not applicable" | error | Aragonite mineralogy directly affects isotope values; undocumented correction status is a scientific data-quality failure |
| `If mineralogy = unknown, arag_corr cannot be anything other than "unknown". See row(s): %s.` | Inconsistent `arag_corr` when mineralogy is unknown | Triggers when `mineralogy` is "unknown" but `arag_corr` has a definite value | error | Logical inconsistency, cannot know the correction status if mineralogy itself is unknown |
| `Entity {i} is likely missing an age model. This is not allowed except for some VERY special cases. (...)` | Entire entity lacks an age model | Triggers when all of an entity's samples (excluding hiatuses) have missing `interp_age` | error | Without an age model, none of the entity's proxy data can be placed in time. |
| `At entity %s, depth_ref is likely wrong. The oldest speleothem sample cannot be the one at the top! Further checks cannot be completed until this is fixed.` | Inferred depth direction contradicts age progression | Triggers when the oldest sample ends up at the shallowest inferred depth | error | Indicates the age-depth relationship for the entire entity is inverted or corrupted, invalidating every derived age |
| `Entity %s has a hiatus in this tab that does not match that of the dating spreadsheet. See depth_sample %s.` | Hiatus depth mismatch (Sample vs. Dating) | Triggers when a hiatus depth recorded in Sample data doesn't match the corresponding depth in Dating information | error | Mismatched hiatus depths mean the sample record and the age model disagree about where the interruption occurred |
| `Entity %s is laminated and therefore ann_lam_check cannot not be "not applicable".` | Laminated entity has invalid `ann_lam_check` | Triggers when Dating information marks the entity as laminated but `ann_lam_check` is "not applicable" | error | Direct cross-table contradiction between lamination status and its verification-method field |

## Dating information

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `Dating information table is missing column(s): %s.` | Required column(s) missing from Dating information | Triggers during the initial v15 schema check if an expected column is absent | error | Same reasoning as other sheets' column-existence checks |
| `The depth_ref chosen is not "from top" or "from base".` | Invalid depth reference direction | Triggers when an inferred/derived `depth_ref` value isn't one of the two valid options | error | `depth_ref` determines how every depth value in the entity is interpreted; an invalid value makes the whole age-depth chain unreliable |
| `At entity %s depth_ref is likely wrong. (all ages are inverted)` | All ages inverted relative to depth | Triggers when, after sorting by depth, every single age comparison is inverted | error | A fully inverted age sequence means the age model for the entity is built backwards |
| `Entity %s has %s inversion at the following paired %s: %s` | Age/depth inversion at specific depths | Triggers when one or more (but not all) consecutive depth-age pairs are inverted | error | A partial inversion still represents a physically impossible sequence in the age model |
| `"min_weight" is greater than "max_weight" at row %s.` | Logical contradiction between sample weight bounds | Triggers when `min_weight` exceeds `max_weight` for the same measurement | error | A minimum greater than a maximum is a direct logical impossibility in the measurement data |
| `Column %s is not filled in when date_used = "yes" or "unknown". %d row(s). See row(s): %s.` | Missing `corr_age`/uncertainty values for dates used in the age model | Triggers when `corr_age`, `corr_age_uncert_pos`, or `corr_age_uncert_neg` is empty for a date marked as used | error | If a date is marked as used in the age model but lacks its core value/uncertainty, the age model cannot actually incorporate it |
| `Column decay_constant must be filled in when date_type is of U/Th type. See row(s): %s.` | Missing decay constant for U/Th dates | Triggers when `date_type` involves U/Th methods but `decay_constant` is empty | error | Without the decay constant, the U/Th age calculation cannot be independently verified or reproduced |
| `There is at least one date in this tab but the dating information table does not contain an "Event; start of laminations".` | Lamina data present without a start-of-laminations event | Triggers when Lamina age vs depth has data for an entity but Dating information lacks the required marker | error | Cross-table contradiction: lamina data exists but its chronological anchor is missing |
| `There is an "Event; start of laminations" but no data in the lamina age vs depth spreadsheet.` | Start-of-laminations event without lamina data | Triggers when Dating information records the event but Lamina age vs depth has no corresponding rows | error | Reverse cross-table contradiction. An event is documented but its supporting data is entirely absent |
| `Entity %s has a hiatus in this tab that does not match that of the sample data spreadsheet. See depth_dating %s.` | Hiatus depth mismatch (Dating vs. Sample) | Triggers when a hiatus depth in Dating information doesn't match the corresponding depth in Sample data | error | The age model and the physical sample record disagree about where the interruption occurred |
| `Entity %s has laminae information but no dating information. date_type = "Event; start of laminations" and "Event; end of laminations" must be entered!` | Lamina data present but Dating information entirely empty for the entity | Triggers when an entity has Lamina age vs depth rows but no Dating information rows at all | error | Without any dating information, the lamina data has no chronological anchor whatsoever |
| `Entity %s has no dating information.` | Entity entirely missing from Dating information | Triggers when a non-composite entity has no rows in Dating information | error | Every non-composite entity is expected to have dating information; total absence prevents any age model |
| `There is date_type = "Event; end of laminations" but no date_type = "Event; start of laminations" for Entity %s. Both must be entered!` | Unpaired end-of-laminations event | Triggers when an entity has an end-marker but no matching start-marker | error | Lamination chronology requires both bookends; a missing pair leaves the lamina age model's boundaries undefined |
| `There is date_type = "Event; start of laminations" but no date_type = "Event; end of laminations" for entity %s. Both must be entered!` | Unpaired start-of-laminations event | Same as above, in the reverse direction | error | Same reasoning as above |
| `Lamina age vs depth tab: According to the Dating information tab, entity %s is laminated (...). However, there is no information on the laminae in the lamina age vs depth table. (...)` | Laminated entity missing all lamina data | Triggers when Dating information marks an entity as laminated but Lamina age vs depth has no rows for it | error | A laminated entity with zero supporting lamina data prevents any lamina-based analysis |
| `Entity %s has laminae data but is missing date_type = "Event; start of laminations" in the dating information spreadsheet.` | Lamina data present but missing chronological start marker | Triggers when Lamina age vs depth has rows for an entity, but Dating information lacks the start marker | error | Without this marker, the lamina age-depth data cannot be tied into the entity's overall age model |
| `The youngest date related to laminae for entity %s is not linked to an "Event; end of laminations". (...)` | Lamina chronology missing its youngest anchor | Triggers when the shallowest lamination-related date isn't marked as the end-of-laminations event | error | Breaks the expected chronological bookending of the lamina sequence |
| `The oldest date related to laminae for entity %s is not linked to an "Event; start of laminations". This may be missing. (...)` | Lamina chronology missing its oldest anchor | Triggers when the deepest lamination-related date isn't marked as the start-of-laminations event | error | Same reasoning, this is the other required bookend of the lamina chronology |
| `There are two consecutive "Event; end of laminations" or "Event; start of laminations" when the dating information of entity %s is sorted by depth. (...)` | Non-alternating lamination event sequence | Triggers when two events of the same type appear consecutively instead of alternating | error | A non-alternating sequence indicates the lamination chronology is internally inconsistent |
| `At column depth_dating: %d value(s) is missing. See row(s): %s.` | Missing `depth_dating` values | Triggers when a Dating information row has no depth value | error | Depth is the anchor linking a date to a physical position in the sample; without it the date cannot be placed in the age model |
| `At column depth_dating: %d row(s) is not a number. See row(s): %s.` | `depth_dating` contains non-numeric values | Triggers when `depth_dating` cannot be interpreted as a number | error | Same reasoning, depth is essential for placing the date in the age model |
| `At column depth_dating: %d row(s) is not a positive number (or not a number). See row(s): %s.` | `depth_dating` contains negative or non-numeric values | Triggers when `depth_dating` is negative or invalid | error | A negative dating depth is physically meaningless |
| `At column entity_name: %d value(s) is missing. See row(s): %s.` | Missing `entity_name` in Dating information | Triggers when a Dating information row has no entity name | error | Without an entity name the row cannot be associated with any speleothem record at all |
| `At column date_type: %d value(s) is missing. See row(s): %s.` | Missing `date_type` values | Triggers when a Dating information row has no `date_type` entered | error | `date_type` determines how every other check in this row is interpreted; without it the row cannot be validated at all |
| `At column date_used: %d value(s) is missing. See row(s): %s.` | Missing `date_used` values | Triggers when a Dating information row has no `date_used` entered | error | `date_used` determines whether a date is included in the age model; without it, downstream age-model checks cannot run correctly |
| `At column uncorr_age: %d row(s) is not a number. See row(s): %s.` | `uncorr_age` is non-numeric | Triggers when `uncorr_age` cannot be interpreted as a number | error | The uncorrected age is core measurement data feeding into the age model calculation |
| `At column corr_age: %d row(s) is not a number. See row(s): %s.` | `corr_age` is non-numeric | Triggers when `corr_age` cannot be interpreted as a number | error | The corrected age is the primary dating result used to build the age model |
| `At column corr_age: %d row(s) is not within the valid range (>=-70.00 and <=800000.00) (or not a number). See row(s): %s.` | `corr_age` outside plausible range | Triggers when a corrected age used in the age model falls outside -70 to 800,000 years BP | error | An implausible corrected age would silently corrupt the entity's entire age model if left unflagged |
| `For %s, %s should be filled in but is empty. See row(s): %s.` | Required column empty for a hiatus/gap/event row | Triggers when a row marked as a hiatus, gap, or dating event is missing one of the columns required for that event type | error | These are structural requirements for the dating chain; violating them breaks the ability to interpret the age model |
| `For %s, there are columns which must be empty but are filled in. See row(s): %s. See column(s): %s.` | Column unexpectedly filled for a hiatus/gap/event row | Triggers when a hiatus/gap/event row has a value in a column that should be empty for that event type | error | A hiatus/gap row with conflicting data creates ambiguity about whether the row represents an event or an actual date |
| `For %s, only %s should be filled in. Other columns must be empty. See row(s): %s` | Extra unexpected data in a restricted event row | Triggers for event rows where only a specific small set of columns is allowed to be filled and others aren't | error | Violates the structural contract that keeps the dating chain interpretable |

## Lamina age vs depth

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `Lamina age vs depth table is missing column(s): %s.` | Required column(s) missing from Lamina age vs depth | Triggers during the initial v15 schema check if an expected column is absent | error | Same reasoning as other sheets' column-existence checks |
| `At column entity_name: %d value(s) is missing. See row(s): %s.` | Missing `entity_name` in Lamina age vs depth | Triggers when a row has no entity name | error | Without an entity name the row cannot be linked to any entity |
| `At column depth_lam: %d value(s) is missing. See row(s): %s.` | Missing `depth_lam` values | Triggers when a row has no lamina depth value | error | Depth is the anchor linking a lamina age to a physical position; without it the value cannot be placed in the record |
| `At column lam_age: %d value(s) is missing. See row(s): %s.` | Missing `lam_age` values | Triggers when a row has no lamina age value | error | The lamina age is the core scientific value of this sheet; without it, the row carries no usable information |
| `At column lam_age: %d row(s) is not within the valid range (>=-70.00 and <=800000.00) (or not a number). See row(s): %s.` | `lam_age` outside plausible range | Triggers when a lamina age falls outside -70 to 800,000 years BP | error | An implausible lamina age indicates a serious data entry error and would corrupt any lamina-based age analysis |

## References

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `References table is missing column(s): %s.` | Required column(s) missing from References | Triggers during the initial v15 schema check if an expected column is absent | error | Same reasoning as other sheets' column-existence checks |
| `Entity %s is missing a reference.` | No bibliographic reference entered for entity | Triggers when an entity has no row in the References sheet | error | Every submitted entity is expected to be traceable to a publication; a complete absence is a required-metadata failure |

---

# Part 3: Warning messages

Warning messages are collected (via `warning_ctr`) but do not block submission on their own. They flag issues worth reviewing manually.

## Site metadata

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `The site_name either starts or ends with a space. Please remove the extra space.` | Leading/trailing whitespace in site name | Triggers when `site_name` has a leading or trailing space | warning | Purely cosmetic formatting issue; easy to fix and doesn't affect data interpretation |

## Entity metadata

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `The entity_name %s either starts or ends with a space. Please remove the extra space.` | Leading/trailing whitespace in entity name | Triggers when an `entity_name` value has a leading or trailing space | warning | Cosmetic formatting issue that doesn't prevent the entity from being identified |
| `Contact in row {idx} is numeric instead of text. Name and surname(s) are required.` | Contact field contains a number instead of a name | Triggers when a `contact` value is numeric | warning | Administrative metadata issue; doesn't affect the scientific content of the submission |
| `Contact in row {idx} is just spaces. Name and surname(s) are required.` | Contact field contains only whitespace | Triggers when a `contact` value is all spaces | warning | Same reasoning, administrative/contact metadata formatting issue |
| `Contact in row {idx} starts or ends with spaces. Name and surname(s) are required.` | Leading/trailing whitespace in contact name | Triggers when a `contact` value has leading/trailing spaces | warning | Cosmetic formatting issue |
| `Contact "{contact}" in row {idx} is only one word. Name and surname(s) are required.` | Contact name missing surname | Triggers when `contact` contains only a single word | warning | Administrative completeness issue, not a scientific data problem |
| `Contact "{contact}" in row {idx} seems incomplete. Name and surname(s) are required.` | Contact name appears to be initials/incomplete | Triggers when a heuristic detects the contact name is mostly initials | warning | Same administrative reasoning as above |
| `ORCID iD in row {idx} is not associated with a contact. Please provide a contact or remove the ORCID iD.` | Orphaned ORCID entry | Triggers when an ORCID iD is filled in but the corresponding `contact` cell is empty | warning | Administrative metadata inconsistency, not a scientific data issue |
| `ORCID iD in row {idx} is only spaces. Please leave the cell empty or provide an ORCID iD.` | ORCID field contains only whitespace | Triggers when an ORCID cell is all spaces | warning | Cosmetic/administrative formatting issue |
| `ORCID iD in row {idx} starts or ends with a space. Please remove any extra spaces.` | Leading/trailing whitespace in ORCID | Triggers when an ORCID value has leading/trailing spaces | warning | Cosmetic formatting issue |
| `ORCID iD in row {idx} is not separated by dashes. Please include the dashes of the ORCID iD.` | ORCID missing expected dash formatting | Triggers when an ORCID value has no dashes | warning | Administrative formatting issue with a well-defined fix |
| `ORCID iD in row {idx} is lacking digits. Please check.` | ORCID has wrong digit count | Triggers when the ORCID (dashes removed) isn't 16 digits long | warning | Administrative/contact metadata formatting issue |
| `ORCID iD in row {idx} is not in a 4 by 4 format. Please check.` | ORCID isn't grouped in four groups of four | Triggers when the ORCID doesn't split into four 4-character groups | warning | Same administrative reasoning |
| `ORCID iD in row {idx} contains invalid characters. Please check.` | ORCID contains characters outside 0-9/X | Triggers when the ORCID (dashes removed) has invalid characters | warning | Same administrative reasoning |
| `If one_and_only = "yes", entity_status_info must be "not applicable". See row(s): %s.` | Inconsistent `entity_status_info` when entity is the sole record | Triggers when `one_and_only = "yes"` but `entity_status_info` isn't "not applicable" | warning | An easily corrected metadata inconsistency; doesn't affect the entity's core scientific data |
| `If one_and_only = "yes", entity_status_notes must be empty. See row(s): %s.` | Unexpected notes when entity is the sole record | Triggers when `one_and_only = "yes"` but `entity_status_notes` is filled in | warning | Same reasoning, minor metadata inconsistency, not a scientific data problem |
| `At column data_DOI_URL entity %s likely has the same data_DOI_URL as publication_DOI in References tab. (...)` | Possible confusion between data and publication DOI/URL | Triggers when the last 10 characters of `data_DOI_URL` match those of a `publication_DOI` for the same entity | warning | Likely a data entry mix-up worth double-checking, but not a structural or scientific data-integrity failure |

## Sample data

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `At column %s: %d row(s) contains values not in the dropdown lists. See row(s): %s. Value(s): %s.` | Value not from the expected dropdown list | Triggers for any dropdown-constrained column across sheets (e.g. `geology`, `rock_age`, `mineralogy`, `hiatus`, `gap`, `date_type`, `date_used`, etc.) when the entered value isn't in the allowed list | warning | Formatting/vocabulary issue, the underlying data may still be scientifically meaningful even if not in the standard vocabulary; treated as structural rather than blocking |
| `{number_of_rows} row(s) have {dependent_column} but no {independent_column}. See row(s): {row_numbers}.` | Dependent value present without its required companion | Triggers whenever a "dependent" column (e.g. a precision/uncertainty value) is filled in but its paired "independent" column is empty, across multiple sheets | warning | Indicates a data-completeness gap in secondary/precision fields, not a failure of the core measurement itself |
| `There is at least one row with isotope standard and no d13C or d18O measurement. Ensure that only isotope measurements have iso_std info. %d rows. See row(s): %s.` | `iso_std` filled without a corresponding isotope measurement | Triggers when `iso_std` has a value but both `d18O_measurement` and `d13C_measurement` are empty | warning | Formatting/completeness issue in secondary isotope-standard metadata, not a failure of the core sample record |
| `At entity %s it looks like %s and %s have been entered as ranges (min/max) instead of uncertainties. Effected %d row(s). See row(s): %s.` | Uncertainty columns look like min/max bounds | Triggers when the age value falls between its own "uncertainty" columns, suggesting min/max bounds were entered instead of ± uncertainties | warning | This can be a false positive (e.g. coincidental crossing of continuously-varying uncertainty curves), so it is flagged for manual review rather than auto-blocked |
| `Entity %s has no Sample data. This will only be accepted if this entity is part of a composite (...)` | Entity has zero rows in Sample data | Triggers when an entity defined in Entity metadata has no corresponding Sample data rows | warning | There's a legitimate exception (composite entities), so this is flagged for manual review rather than blocking outright |
| `If mineralogy is not "aragonite" or "mixed", arag_corr must be "not applicable". See row(s): %s.` | `arag_corr` filled in when not expected | Triggers when `mineralogy` is calcite/vaterite/secondary calcite but `arag_corr` isn't "not applicable" | warning | A correction marked as applied when it shouldn't be needed is a completeness/consistency issue, not a scientific-validity failure |
| `A gap column is filled in with non-composite entities. Check if this should be a hiatus instead.` | `gap` used outside composite context | Triggers when the `gap` column is filled in for a non-composite entity | warning | Likely a terminology mix-up (gap vs. hiatus) worth reviewing, but not inherently invalidating the data |
| `If entity {i} has no age model, interp_age_uncert_pos should be empty.` | Uncertainty value present despite missing age model | Triggers when an entity has no age model but `interp_age_uncert_pos` is filled in anyway | warning | A secondary consistency check tied to an already-flagged missing age model; doesn't add new blocking information |
| `If entity {i} has no age model, interp_age_uncert_neg should be empty.` | Uncertainty value present despite missing age model | Same as above, for `interp_age_uncert_neg` | warning | Same reasoning |
| `Entity {i} is likely missing an age model (i.e. no interp_ages). If this is correct, age_model_type should be empty.` | `age_model_type` filled in despite missing age model | Triggers when an entity has no age model but `age_model_type` has a value | warning | Secondary consistency check on an already-flagged condition |
| `Entity {i} is likely missing an age model (i.e. no interp_ages). If this is correct, ann_lam_check should be empty.` | `ann_lam_check` filled in despite missing age model | Same pattern, for `ann_lam_check` | warning | Same reasoning |
| `Entity {i} is likely missing an age model (i.e. no interp_ages). If this is correct, dep_rate_check should be empty.` | `dep_rate_check` filled in despite missing age model | Same pattern, for `dep_rate_check` | warning | Same reasoning |
| `Column ann_lam_check for entity %s must be "not applicable" if this is a non-laminated speleothem. (...)` | `ann_lam_check` inconsistent with non-laminated status | Triggers when an entity has no lamination events but `ann_lam_check` isn't "not applicable" | warning | Metadata consistency issue in a secondary annotation field, not a core scientific-integrity failure |

## Dating information

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `Entity %s has no dating info other than hiatuses and/or not used dates. This is not allowed except for very special cases (...)` | Entity has only unusable dating rows | Triggers when all of an entity's Dating information rows are hiatuses or dates marked as not used | warning | There's a documented exception for special cases, so this is flagged for manual judgment rather than auto-blocked |
| `Column calib_used must be empty when date_type is not C14. See row(s): %s.` | `calib_used` filled in for non-C14 dates | Triggers when `calib_used` has a value but `date_type` isn't C14 | warning | Formatting/consistency issue in a metadata field that doesn't affect the actual age value |
| `Column 14C_correction must be empty when date_type is not C14. See row(s): %s.` | `14C_correction` filled in for non-C14 dates | Triggers when `14C_correction` has a value but `date_type` isn't C14 | warning | Same reasoning as above |
| `Column decay_constant must be empty when date_type is not of U/Th type. See row(s): %s.` | `decay_constant` filled in for non-U/Th dates | Triggers when `decay_constant` has a value but `date_type` isn't U/Th-based | warning | Formatting/consistency issue that doesn't affect the validity of the actual date used |
| `At entity %s, there are multiple hiatuses recorded at depth_dating: %s.` | Duplicate hiatus depths within an entity | Triggers when the same depth has more than one hiatus recorded | warning | An unusual but not necessarily invalid situation; flagged for manual review |
| `At entity %s, a hiatus cannot be at the same depth as a date. See depth_dating: %s.` | Hiatus and a regular date share the same depth | Triggers when a hiatus depth coincides with a non-hiatus date's depth for the same entity | warning | An inconsistency worth checking manually, but not automatically indicative of unusable data |
| `At entity %s, there are more than one actively growing event.` | Multiple "actively forming" events for one entity | Triggers when more than one Dating information row has `date_type = "Event; actively forming"` for the same entity | warning | Logically unusual but not necessarily wrong (e.g. multiple growth phases); flagged for review |
| `At entity %s, there is an actively growing event corr_age > 0 (older than 1950 BP). This is very unlikely. Please check.` | Actively-forming event has an implausible age | Triggers when the "actively forming" event's `corr_age` is greater than zero (i.e. older than 1950) | warning | Suspicious but not impossible without further context; flagged for manual verification |
| `If depths in Dating information table really cannot be obtained, please add dummy depths to make sure that other checks can be performed. (...)` | Suggestion after depth_dating checks failed | Triggers as a helper suggestion when the depth_dating presence check failed earlier | warning | This is advisory guidance for the data steward, not itself a data-integrity finding |

## References

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `There is more than one DOI associated to %s. Possible drag-down error with the DOI. See row(s): %s.` | Multiple DOIs for the same citation | Triggers when a citation string is associated with more than one distinct `publication_DOI` | warning | Often caused by an accidental spreadsheet drag-down; worth reviewing but not necessarily a fatal data problem |
| `There is more than one DOI associated to one of the references. This could not be printed due to special characters in the citation. (...)` | Same as above, but citation text couldn't be safely formatted for the message | Triggers in the same scenario as above, when the citation text contains characters (e.g. a "%" sign) that interfere with message formatting | warning | Same underlying issue as the message above, just with a citation that couldn't be printed directly |
| `Unexpected internal state: citation "%s" has zero associated publication_DOI values despite appearing more than once.` | Internal defensive check (should not normally occur) | Triggers only if a citation appears multiple times but ends up with zero associated DOI values | warning | This is a defensive/diagnostic message for a state the code doesn't expect to reach; not a standard data-validation failure |
| `One same DOI (%s) is linked to multiple citations. If two citations are reported as "unpublished" or if the same DOI is from different chapters of the same book (...)` | Multiple citations share the same DOI | Triggers when the same `publication_DOI` is associated with more than one distinct citation | warning | There are legitimate reasons this can happen (unpublished works, book chapters); flagged for manual review |
| `Unexpected internal state: DOI "%s" has zero associated citation values despite appearing more than once.` | Internal defensive check (should not normally occur) | Same defensive pattern as the citation version above, for DOIs | warning | Same reasoning, diagnostic message for an unreachable state, not a standard validation failure |
| `There are repeated citation(s) in %s.` | Duplicate citations for the same entity | Triggers when the same citation string appears more than once for a given entity | warning | Likely a data entry duplication; worth reviewing but not inherently invalidating the reference data |
| `The DOI(s) entered in row %s is incorrect. This must be either a DOI, URL or "unpublished". (...)` | Malformed `publication_DOI` placeholder value | Triggers when `publication_DOI` contains a placeholder-like string instead of a real DOI/URL/"unpublished" | warning | Formatting issue in the References sheet; doesn't affect the entity's core scientific data |
| `Incorrect DOI(s) entered in row %s. DOI/URL must either be "unpublished" (...) or start with "http", "10."` | `publication_DOI` doesn't match expected format | Triggers when `publication_DOI` is filled in but doesn't start with a recognized prefix or equal "unpublished" | warning | Same formatting-issue reasoning as above |
| `The citation(s) in row %s is incorrect. This cannot be empty, "unknown", "N/A", "not known", etc or have spaces before/after the text.` | Malformed citation placeholder value | Triggers when `citation` contains a placeholder-like string or has leading/trailing spaces | warning | Formatting issue in the citation text field |

## Other

| Message text | Short description | When it occurs | Category | Reason |
|---|---|---|---|---|
| `If depths in the Sample data table really cannot be obtained, please add dummy depths to make sure that other checks can be performed. (...)` | Suggestion after depth_sample checks failed | Same pattern as the Dating information version, for `depth_sample` | warning | Advisory guidance, not a new finding |
| `Could not generate site map. Details: %s` | Site map image generation failed | Triggers when the final map-plotting step (cartopy/matplotlib) throws an exception | warning | The map is a supplementary visualization aid; its failure doesn't affect the validity of the underlying workbook data |
